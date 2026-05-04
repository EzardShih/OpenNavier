import json
from collections.abc import Generator
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

import pytest
from opennavier.cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def case_tmp_path() -> Generator[Path, None, None]:
    path = Path(".tmp") / f"doctor-logs-{uuid4().hex}"
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        rmtree(path, ignore_errors=True)


def create_valid_case(case_path: Path) -> None:
    for directory in ["0", "constant", "system"]:
        (case_path / directory).mkdir(parents=True, exist_ok=True)
    for filename in ["controlDict", "fvSchemes", "fvSolution"]:
        (case_path / "system" / filename).write_text("FoamFile {}\n", encoding="utf-8")


def test_check_remains_case_structure_only_when_optional_logs_exist(
    case_tmp_path: Path,
) -> None:
    create_valid_case(case_tmp_path)
    (case_tmp_path / "log.checkMesh").write_text(
        "Mesh non-orthogonality Max: 75 average: 12\nMesh OK.\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["check", str(case_tmp_path), "--format", "json"])

    assert result.exit_code == 0
    diagnostics = json.loads(result.output)
    assert diagnostics
    codes = [diagnostic["code"] for diagnostic in diagnostics]
    assert all(not code.startswith("openfoam.mesh_quality") for code in codes)
    assert all(not code.startswith("openfoam.residuals") for code in codes)


def test_doctor_includes_mesh_warnings_from_check_mesh_log(case_tmp_path: Path) -> None:
    create_valid_case(case_tmp_path)
    (case_tmp_path / "log.checkMesh").write_text(
        "Mesh non-orthogonality Max: 75 average: 12\nMax skewness = 1.2 OK.\nMesh OK.\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["doctor", str(case_tmp_path), "--format", "json"])

    assert result.exit_code == 0
    diagnostics = json.loads(result.output)
    mesh_diagnostic = next(
        diagnostic
        for diagnostic in diagnostics
        if diagnostic["code"] == "openfoam.mesh_quality.warning"
    )
    assert mesh_diagnostic["status"] == "WARN"
    assert mesh_diagnostic["path"] == str(case_tmp_path / "log.checkMesh")
    assert mesh_diagnostic["details"]["non_orthogonality"] == "75.0"


def test_doctor_includes_residual_warnings_from_solver_log(case_tmp_path: Path) -> None:
    create_valid_case(case_tmp_path)
    (case_tmp_path / "log.simpleFoam").write_text(
        (
            "Time = 1\n"
            "Solving for p, Initial residual = 0.1, Final residual = 0.02, No Iterations 2\n"
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["doctor", str(case_tmp_path), "--format", "json"])

    assert result.exit_code == 0
    diagnostics = json.loads(result.output)
    residual_diagnostic = next(
        diagnostic
        for diagnostic in diagnostics
        if diagnostic["code"] == "openfoam.residuals.high_final"
    )
    assert residual_diagnostic["status"] == "WARN"
    assert residual_diagnostic["path"] == str(case_tmp_path / "log.simpleFoam")
    assert residual_diagnostic["details"]["fields"] == "p"


@pytest.mark.parametrize(
    "solver_log_name",
    ["simpleFoam.log", "icoFoam.log", "pisoFoam.log", "pimpleFoam.log"],
)
def test_doctor_includes_residual_warnings_from_logs_directory_solver_logs(
    case_tmp_path: Path, solver_log_name: str
) -> None:
    create_valid_case(case_tmp_path)
    (case_tmp_path / "logs").mkdir()
    solver_log_path = case_tmp_path / "logs" / solver_log_name
    solver_log_path.write_text(
        (
            "Time = 1\n"
            "Solving for p, Initial residual = 0.1, Final residual = 0.02, No Iterations 2\n"
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["doctor", str(case_tmp_path), "--format", "json"])

    assert result.exit_code == 0
    diagnostics = json.loads(result.output)
    residual_diagnostic = next(
        diagnostic
        for diagnostic in diagnostics
        if diagnostic["code"] == "openfoam.residuals.high_final"
    )
    assert residual_diagnostic["status"] == "WARN"
    assert residual_diagnostic["path"] == str(solver_log_path)
    assert residual_diagnostic["details"]["fields"] == "p"


def test_report_includes_optional_log_diagnostics(case_tmp_path: Path) -> None:
    create_valid_case(case_tmp_path)
    (case_tmp_path / "logs").mkdir()
    (case_tmp_path / "logs" / "checkMesh.log").write_text(
        "Mesh non-orthogonality Max: 76 average: 14\nMesh OK.\n",
        encoding="utf-8",
    )
    (case_tmp_path / "log.icoFoam").write_text(
        (
            "Time = 1\n"
            "Solving for Ux, Initial residual = 0.1, Final residual = 0.03, No Iterations 2\n"
        ),
        encoding="utf-8",
    )
    output_path = case_tmp_path / "report.md"

    result = runner.invoke(app, ["report", str(case_tmp_path), "--output", str(output_path)])

    assert result.exit_code == 0
    content = output_path.read_text(encoding="utf-8")
    assert "- Warning checks: 2" in content
    assert "openfoam.mesh_quality.warning" in content
    assert "openfoam.residuals.high_final" in content
    assert str(case_tmp_path / "logs" / "checkMesh.log") in content
    assert str(case_tmp_path / "log.icoFoam") in content


def test_missing_optional_logs_do_not_make_valid_cases_fail(case_tmp_path: Path) -> None:
    create_valid_case(case_tmp_path)

    result = runner.invoke(app, ["doctor", str(case_tmp_path), "--format", "json"])

    assert result.exit_code == 0
    diagnostics = json.loads(result.output)
    assert all(diagnostic["status"] == "PASS" for diagnostic in diagnostics)
    codes = [diagnostic["code"] for diagnostic in diagnostics]
    assert all(not code.startswith("openfoam.mesh_quality") for code in codes)
    assert all(not code.startswith("openfoam.residuals") for code in codes)
