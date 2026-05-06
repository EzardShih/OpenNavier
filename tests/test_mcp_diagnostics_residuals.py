import json
from collections.abc import Generator
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

import pytest
from opennavier.mcp.diagnostics_tools import diagnostics_residuals


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
