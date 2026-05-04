import json
from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

import pytest
from opennavier.cli.main import app
from opennavier_core.diagnostics import DiagnosticResult, DiagnosticStatus
from opennavier_core.manifest import build_reproducibility_manifest
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def case_tmp_path() -> Generator[Path, None, None]:
    path = Path(".tmp") / f"manifest-{uuid4().hex}"
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        rmtree(path, ignore_errors=True)


def test_manifest_builder_counts_diagnostics_and_sets_deterministic_execution_flags(
    case_tmp_path: Path,
) -> None:
    diagnostics = [
        DiagnosticResult(
            status=DiagnosticStatus.PASS,
            code="openfoam.required_directory.system",
            message="Required directory exists",
            path=str(case_tmp_path / "system"),
        ),
        DiagnosticResult(
            status=DiagnosticStatus.WARN,
            code="openfoam.mesh_quality.skewness",
            message="Skewness was not inspected",
            path=str(case_tmp_path),
        ),
        DiagnosticResult(
            status=DiagnosticStatus.FAIL,
            code="openfoam.required_file.system_controlDict",
            message="Missing controlDict",
            path=str(case_tmp_path / "system" / "controlDict"),
        ),
    ]

    manifest = build_reproducibility_manifest(
        case_path=case_tmp_path,
        diagnostics=diagnostics,
        generated_artifacts=[case_tmp_path / "report.md"],
    )

    assert manifest.schema_version == "1.0"
    assert manifest.case_path == str(case_tmp_path.resolve())
    assert manifest.diagnostics_summary == {
        "total": 3,
        "passed": 1,
        "failed": 1,
        "warnings": 1,
    }
    assert manifest.diagnostic_codes == [
        "openfoam.required_directory.system",
        "openfoam.mesh_quality.skewness",
        "openfoam.required_file.system_controlDict",
    ]
    assert manifest.generated_artifacts == [str((case_tmp_path / "report.md").resolve())]
    assert manifest.cloud_upload is False
    assert manifest.openfoam_executed is False


def test_report_manifest_output_writes_reproducibility_manifest_for_invalid_case(
    case_tmp_path: Path,
) -> None:
    case_path = case_tmp_path / "case"
    case_path.mkdir()
    report_path = case_tmp_path / "report.md"
    manifest_path = case_tmp_path / "manifest.json"

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

    assert result.exit_code == 1
    assert report_path.exists()
    assert manifest_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    datetime.fromisoformat(manifest["generated_at"])
    assert manifest["schema_version"] == "1.0"
    assert manifest["case_path"] == str(case_path.resolve())
    assert manifest["diagnostics_summary"] == {
        "total": 6,
        "passed": 0,
        "failed": 6,
        "warnings": 0,
    }
    assert manifest["diagnostic_codes"] == [
        "openfoam.required_directory.0",
        "openfoam.required_directory.constant",
        "openfoam.required_directory.system",
        "openfoam.required_file.system_controlDict",
        "openfoam.required_file.system_fvSchemes",
        "openfoam.required_file.system_fvSolution",
    ]
    assert manifest["generated_artifacts"] == [str(report_path.resolve())]
    assert manifest["cloud_upload"] is False
    assert manifest["openfoam_executed"] is False
