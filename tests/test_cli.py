import json
import subprocess
import sys
from collections.abc import Generator
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

import pytest
from opennavier.cli import main
from opennavier.cli.main import app
from opennavier_core.diagnostics import DiagnosticResult, DiagnosticStatus
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def case_tmp_path() -> Generator[Path, None, None]:
    path = Path(".tmp") / f"cli-{uuid4().hex}"
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


def test_help_shows_core_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "check" in result.output
    assert "doctor" in result.output
    assert "run" in result.output
    assert "report" in result.output


def test_module_entry_point_shows_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "opennavier.cli", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "check" in result.stdout
    assert "doctor" in result.stdout
    assert "report" in result.stdout


def test_check_returns_success_for_valid_case(case_tmp_path: Path) -> None:
    create_valid_case(case_tmp_path)

    result = runner.invoke(app, ["check", str(case_tmp_path)])

    assert result.exit_code == 0
    assert "PASS" in result.output
    assert "Case structure checks passed" in result.output


def test_check_returns_failure_for_invalid_case(case_tmp_path: Path) -> None:
    result = runner.invoke(app, ["check", str(case_tmp_path)])

    assert result.exit_code == 1
    assert "FAIL" in result.output
    assert "Missing required OpenFOAM directory: 0" in result.output


def test_check_returns_failure_for_malformed_required_system_dictionary(
    case_tmp_path: Path,
) -> None:
    create_valid_case(case_tmp_path)
    (case_tmp_path / "system" / "fvSchemes").write_text(
        "ddtSchemes {}\n", encoding="utf-8"
    )

    result = runner.invoke(app, ["check", str(case_tmp_path)])

    assert result.exit_code == 1
    assert "FAIL" in result.output
    assert "openfoam.dictionary_header.system_fvSchemes" in result.output


def test_check_json_returns_diagnostics_for_valid_case(case_tmp_path: Path) -> None:
    create_valid_case(case_tmp_path)

    result = runner.invoke(app, ["check", str(case_tmp_path), "--format", "json"])

    assert result.exit_code == 0
    diagnostics = json.loads(result.output)
    assert diagnostics
    assert {diagnostic["status"] for diagnostic in diagnostics} == {"PASS"}
    assert {"status", "code", "message", "path", "details"} <= set(diagnostics[0])


def test_check_json_returns_nonzero_for_invalid_case(case_tmp_path: Path) -> None:
    result = runner.invoke(app, ["check", str(case_tmp_path), "--format", "json"])

    assert result.exit_code == 1
    diagnostics = json.loads(result.output)
    assert any(diagnostic["status"] == "FAIL" for diagnostic in diagnostics)
    assert diagnostics[0]["code"] == "openfoam.required_directory.0"


def test_doctor_json_returns_diagnostics_without_text_summary(case_tmp_path: Path) -> None:
    result = runner.invoke(app, ["doctor", str(case_tmp_path), "--format", "json"])

    assert result.exit_code == 1
    diagnostics = json.loads(result.output)
    assert any(diagnostic["status"] == "FAIL" for diagnostic in diagnostics)
    assert "Likely issues" not in result.output


def test_doctor_returns_nonzero_for_invalid_case(case_tmp_path: Path) -> None:
    result = runner.invoke(app, ["doctor", str(case_tmp_path)])

    assert result.exit_code == 1
    assert "Likely issues" in result.output
    assert "OpenFOAM case structure is incomplete" in result.output


def test_run_executes_local_solver_and_writes_log(case_tmp_path: Path) -> None:
    create_valid_case(case_tmp_path)

    result = runner.invoke(
        app,
        [
            "run",
            str(case_tmp_path),
            "--solver",
            sys.executable,
            "--solver-arg=-c",
            "--solver-arg",
            "print('cli solver')",
        ],
    )

    assert result.exit_code == 0
    assert "Runner: local" in result.output
    assert f"Command: {sys.executable} -c print('cli solver')" in result.output
    assert "Return code: 0" in result.output
    log_path = case_tmp_path / f"log.{Path(sys.executable).name}"
    assert f"Log path: {log_path}" in result.output
    assert log_path.read_text(encoding="utf-8").endswith("[stdout]\ncli solver\n")


def test_run_returns_nonzero_for_missing_local_executable(case_tmp_path: Path) -> None:
    create_valid_case(case_tmp_path)

    result = runner.invoke(
        app,
        ["run", str(case_tmp_path), "--solver", "definitely-missing-openfoam-command"],
    )

    assert result.exit_code == 1
    assert "Runner: local" in result.output
    assert "Return code: missing executable" in result.output
    log_path = case_tmp_path / "log.definitely-missing-openfoam-command"
    assert f"Log path: {log_path}" in result.output
    assert "Executable not found" in log_path.read_text(encoding="utf-8")


def test_run_returns_nonzero_for_solver_failure(case_tmp_path: Path) -> None:
    create_valid_case(case_tmp_path)

    result = runner.invoke(
        app,
        [
            "run",
            str(case_tmp_path),
            "--solver",
            sys.executable,
            "--solver-arg=-c",
            "--solver-arg",
            "import sys; print('bad input', file=sys.stderr); raise SystemExit(4)",
        ],
    )

    assert result.exit_code == 1
    assert "Runner: local" in result.output
    assert "Return code: 4" in result.output
    assert "bad input" in (
        case_tmp_path / f"log.{Path(sys.executable).name}"
    ).read_text(encoding="utf-8")


def test_run_uses_docker_only_when_explicitly_selected(case_tmp_path: Path) -> None:
    create_valid_case(case_tmp_path)
    fake_docker_script = "import sys; print('DOCKER_ARGS=' + repr(sys.argv[1:]))"

    result = runner.invoke(
        app,
        [
            "run",
            str(case_tmp_path),
            "--runner",
            "docker",
            "--docker-image",
            "openfoam/openfoam-run:latest",
            "--docker-command",
            sys.executable,
            "--docker-command=-c",
            "--docker-command",
            fake_docker_script,
            "--solver",
            "simpleFoam",
        ],
    )

    assert result.exit_code == 0
    assert "Runner: docker" in result.output
    assert "openfoam/openfoam-run:latest simpleFoam" in result.output
    assert "Return code: 0" in result.output
    assert "DOCKER_ARGS=" in (case_tmp_path / "log.simpleFoam").read_text(
        encoding="utf-8"
    )


def test_report_writes_markdown_report(case_tmp_path: Path) -> None:
    case_path = case_tmp_path / "case"
    case_path.mkdir()
    output_path = case_tmp_path / "report.md"

    result = runner.invoke(app, ["report", str(case_path), "--output", str(output_path)])

    assert result.exit_code == 1
    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "# OpenNavier Case Report" in content
    assert f"Inspected case: `{case_path.resolve()}`" in content
    assert "No cloud upload occurred" in content
    assert "openfoam.required_directory.0" in content


def test_report_includes_malformed_system_dictionary_header_diagnostic(
    case_tmp_path: Path,
) -> None:
    case_path = case_tmp_path / "case"
    create_valid_case(case_path)
    (case_path / "system" / "fvSchemes").write_text(
        "divSchemes {}\n", encoding="utf-8"
    )
    output_path = case_tmp_path / "report.md"

    result = runner.invoke(app, ["report", str(case_path), "--output", str(output_path)])

    assert result.exit_code == 1
    content = output_path.read_text(encoding="utf-8")
    assert "openfoam.dictionary_header.system_fvSchemes" in content


def test_report_rejects_manifest_output_resolving_to_report_output_without_overwriting(
    case_tmp_path: Path,
) -> None:
    case_path = case_tmp_path / "case"
    case_path.mkdir()
    output_path = case_tmp_path / "report.md"
    output_path.write_text("existing artifact\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "report",
            str(case_path),
            "--output",
            str(output_path),
            "--manifest-output",
            str(case_tmp_path / "." / "report.md"),
        ],
    )

    assert result.exit_code == 2
    assert "must be different" in result.output
    assert output_path.read_text(encoding="utf-8") == "existing artifact\n"


def test_report_and_manifest_use_same_warn_diagnostics(
    case_tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case_path = case_tmp_path / "case"
    case_path.mkdir()
    report_path = case_tmp_path / "report.md"
    manifest_path = case_tmp_path / "manifest.json"
    diagnostics = [
        DiagnosticResult(
            status=DiagnosticStatus.PASS,
            code="openfoam.required_directory.system",
            message="Required directory exists",
            path=str(case_path / "system"),
        ),
        DiagnosticResult(
            status=DiagnosticStatus.WARN,
            code="openfoam.collector.warn",
            message="Collector warning propagated",
            path=str(case_path),
        ),
    ]

    monkeypatch.setattr(main, "collect_case_diagnostics", lambda _: diagnostics)

    result = runner.invoke(
        app,
        [
            "report",
            str(case_path),
            "--output",
            str(report_path),
            "--manifest-output",
            str(manifest_path),
        ],
    )

    assert result.exit_code == 0
    report_content = report_path.read_text(encoding="utf-8")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "openfoam.collector.warn" in report_content
    assert manifest["diagnostic_codes"] == [
        "openfoam.required_directory.system",
        "openfoam.collector.warn",
    ]
    assert manifest["diagnostics_summary"]["warnings"] == 1
