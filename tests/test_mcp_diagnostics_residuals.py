import json
from collections.abc import Generator
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

import pytest
from opennavier.mcp.diagnostics_tools import (
    diagnostics_artifact,
    diagnostics_case,
    diagnostics_mesh_quality,
    diagnostics_residuals,
    report_generate,
)


@pytest.fixture
def workspace_tmp_path() -> Generator[Path, None, None]:
    path = Path(".tmp") / f"mcp-diagnostics-residuals-{uuid4().hex}"
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        rmtree(path, ignore_errors=True)


def test_diagnostics_residuals_returns_serializable_records_and_diagnostic(
    workspace_tmp_path: Path,
) -> None:
    log_path = workspace_tmp_path / "logs" / "simpleFoam.log"
    log_path.parent.mkdir()
    log_path.write_text(
        """
Time = 1
Solving for p, Initial residual = 0.01, Final residual = 1e-05, No Iterations 2
Solving for Ux, Initial residual = 0.02, Final residual = 5e-04, No Iterations 3
""",
        encoding="utf-8",
    )

    result = diagnostics_residuals(str(workspace_tmp_path), "logs/simpleFoam.log")

    assert result["log_path"] == "logs/simpleFoam.log"
    assert result["records"] == [
        {"field": "p", "initial": 0.01, "final": 1e-05, "iterations": 2},
        {"field": "Ux", "initial": 0.02, "final": 5e-04, "iterations": 3},
    ]
    assert result["diagnostic"] == {
        "status": "PASS",
        "code": "openfoam.residuals.convergence",
        "message": "Final residuals are below the configured threshold.",
        "path": "logs/simpleFoam.log",
        "details": {"threshold": "0.001"},
    }
    json.dumps(result)


def test_diagnostics_residuals_reports_missing_log_as_mcp_failure(
    workspace_tmp_path: Path,
) -> None:
    result = diagnostics_residuals(str(workspace_tmp_path), "missing.log")

    assert result["log_path"] == "missing.log"
    assert result["records"] == []
    assert result["diagnostic"] == {
        "status": "FAIL",
        "code": "mcp.log.unreadable",
        "message": "Could not read solver log: missing.log",
        "path": "missing.log",
        "details": {"read_error": "FileNotFoundError"},
    }


def test_diagnostics_residuals_reports_path_escape_as_mcp_failure(
    workspace_tmp_path: Path,
) -> None:
    result = diagnostics_residuals(str(workspace_tmp_path), "../outside.log")

    assert result["log_path"] == "../outside.log"
    assert result["records"] == []
    assert result["diagnostic"] == {
        "status": "FAIL",
        "code": "mcp.workspace_path.invalid",
        "message": "Path must stay inside the workspace root: ../outside.log",
        "path": "../outside.log",
        "details": {},
    }


def test_diagnostics_mesh_quality_returns_parsed_summary_and_diagnostic(
    workspace_tmp_path: Path,
) -> None:
    log_path = workspace_tmp_path / "logs" / "checkMesh.log"
    log_path.parent.mkdir()
    log_path.write_text(
        """
Mesh non-orthogonality Max: 42 average: 8
Max skewness = 1.7 OK.
Mesh OK.
""",
        encoding="utf-8",
    )

    result = diagnostics_mesh_quality(str(workspace_tmp_path), "logs/checkMesh.log")

    assert result["summary"] == {
        "mesh_ok": True,
        "max_non_orthogonality": 42.0,
        "max_skewness": 1.7,
    }
    assert result["diagnostic"]["code"] == "openfoam.mesh_quality.ok"
    json.dumps(result)


def test_diagnostics_case_scopes_full_case_diagnostics_to_workspace(
    workspace_tmp_path: Path,
) -> None:
    (workspace_tmp_path / "case").mkdir()

    result = diagnostics_case(str(workspace_tmp_path), "case")

    assert result["case_path"] == "case"
    assert result["diagnostics"][0]["code"] == "openfoam.required_directory.0"
    assert diagnostics_case(str(workspace_tmp_path), "../case")["diagnostics"] == [
        {
            "status": "FAIL",
            "code": "mcp.workspace_path.invalid",
            "message": "Path must stay inside the workspace root: ../case",
            "path": "../case",
            "details": {},
        }
    ]


def test_diagnostics_artifact_writes_stable_output_inside_workspace(
    workspace_tmp_path: Path,
) -> None:
    (workspace_tmp_path / "case").mkdir()

    result = diagnostics_artifact(
        str(workspace_tmp_path),
        "case",
        "artifacts/diagnostics.json",
    )

    assert result["diagnostics_output"] == "artifacts/diagnostics.json"
    artifact = json.loads(
        (workspace_tmp_path / "artifacts" / "diagnostics.json").read_text(
            encoding="utf-8"
        )
    )
    assert artifact["local_only"] is True
    assert artifact["counts_by_status"]["FAIL"] > 0


def test_diagnostics_artifact_reports_invalid_case_path_not_output_path(
    workspace_tmp_path: Path,
) -> None:
    result = diagnostics_artifact(
        str(workspace_tmp_path),
        "../case",
        "artifacts/diagnostics.json",
    )

    assert result["diagnostics"] == [
        {
            "status": "FAIL",
            "code": "mcp.workspace_path.invalid",
            "message": "Path must stay inside the workspace root: ../case",
            "path": "../case",
            "details": {},
        }
    ]


def test_report_generate_wraps_existing_report_api(workspace_tmp_path: Path) -> None:
    (workspace_tmp_path / "case").mkdir()

    result = report_generate(
        str(workspace_tmp_path),
        "case",
        "reports/report.md",
        manifest_output_path="reports/manifest.json",
    )

    assert result["report_path"] == "reports/report.md"
    assert result["manifest_path"] == "reports/manifest.json"
    assert (workspace_tmp_path / "reports" / "report.md").is_file()
    assert (workspace_tmp_path / "reports" / "manifest.json").is_file()


def test_report_generate_reports_invalid_report_output_path(
    workspace_tmp_path: Path,
) -> None:
    (workspace_tmp_path / "case").mkdir()

    result = report_generate(str(workspace_tmp_path), "case", "../report.md")

    assert result["diagnostics"] == [
        {
            "status": "FAIL",
            "code": "mcp.workspace_path.invalid",
            "message": "Path must stay inside the workspace root: ../report.md",
            "path": "../report.md",
            "details": {},
        }
    ]


def test_report_generate_reports_invalid_manifest_output_path(
    workspace_tmp_path: Path,
) -> None:
    (workspace_tmp_path / "case").mkdir()

    result = report_generate(
        str(workspace_tmp_path),
        "case",
        "reports/report.md",
        manifest_output_path="../manifest.json",
    )

    assert result["diagnostics"] == [
        {
            "status": "FAIL",
            "code": "mcp.workspace_path.invalid",
            "message": "Path must stay inside the workspace root: ../manifest.json",
            "path": "../manifest.json",
            "details": {},
        }
    ]


def test_report_generate_rejects_report_manifest_path_collision(
    workspace_tmp_path: Path,
) -> None:
    (workspace_tmp_path / "case").mkdir()

    result = report_generate(
        str(workspace_tmp_path),
        "case",
        "reports/report.md",
        manifest_output_path="reports/report.md",
    )

    assert result["diagnostics"] == [
        {
            "status": "FAIL",
            "code": "mcp.artifact_path.conflict",
            "message": (
                "report_output_path and manifest_output_path must be different: "
                "reports/report.md"
            ),
            "path": "reports/report.md",
            "details": {},
        }
    ]
    assert not (workspace_tmp_path / "reports" / "report.md").exists()
