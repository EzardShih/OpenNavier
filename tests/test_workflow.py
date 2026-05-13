import json
import sys
from collections.abc import Generator
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

import pytest
from opennavier.openfoam.workflow_operations import openfoam_workflow_operations
from opennavier_core.workflow import WorkflowRequest, run_no_llm_workflow
from test_case_build_spec import minimal_cavity_case_build_payload
from test_planner import minimal_cavity_payload


@pytest.fixture
def workspace_tmp_path() -> Generator[Path, None, None]:
    path = Path(".tmp") / f"workflow-{uuid4().hex}"
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        rmtree(path, ignore_errors=True)


def run_openfoam_workflow(request: WorkflowRequest):
    return run_no_llm_workflow(request, operations=openfoam_workflow_operations())


def test_no_llm_workflow_orders_tools_and_writes_artifacts(
    workspace_tmp_path: Path,
) -> None:
    result = run_openfoam_workflow(
        WorkflowRequest(
            workspace_root=str(workspace_tmp_path),
            simulation_spec=minimal_cavity_payload(),
            case_build_spec=minimal_cavity_case_build_payload(),
            run_solver=False,
        )
    )

    assert result.status == "completed"
    assert [step.name for step in result.steps] == [
        "inspect_workspace",
        "validate_simulation_spec",
        "validate_case_build_spec",
        "plan_simulation",
        "write_plan_artifact",
        "initialize_case",
        "preflight_check",
        "solver_execution_skipped",
        "collect_diagnostics",
        "write_report",
        "write_manifest",
        "summarize",
    ]
    assert result.summary == (
        "Completed deterministic workflow for lid_driven_cavity. "
        "Solver execution was skipped. Diagnostics reported 0 failures and 0 warnings. "
        "Next actions: approve_solver_execution."
    )
    assert "runs/lid_driven_cavity/plan.json" in {
        artifact.path for artifact in result.artifacts
    }
    assert "runs/lid_driven_cavity/reports/report.md" in {
        artifact.path for artifact in result.artifacts
    }
    assert (
        workspace_tmp_path / "runs" / "lid_driven_cavity" / "reports" / "manifest.json"
    ).is_file()
    assert "llm" not in result.model_dump_json().lower()


def test_no_llm_workflow_can_execute_requested_solver_command(
    workspace_tmp_path: Path,
) -> None:
    result = run_openfoam_workflow(
        WorkflowRequest(
            workspace_root=str(workspace_tmp_path),
            simulation_spec=minimal_cavity_payload(),
            case_build_spec=minimal_cavity_case_build_payload(),
            run_solver=True,
            solver_command=[sys.executable, "-c", "print('workflow solver')"],
        )
    )

    assert result.status == "completed"
    assert "execute_solver" in [step.name for step in result.steps]
    assert result.solver_run is not None
    assert result.solver_run["return_code"] == 0
    log_path = (
        workspace_tmp_path
        / "runs"
        / "lid_driven_cavity"
        / "case"
        / f"log.{Path(sys.executable).name}"
    )
    assert log_path.read_text(encoding="utf-8").endswith("[stdout]\nworkflow solver\n")


def test_no_llm_workflow_records_solver_execution_in_report_and_manifest(
    workspace_tmp_path: Path,
) -> None:
    result = run_openfoam_workflow(
        WorkflowRequest(
            workspace_root=str(workspace_tmp_path),
            simulation_spec=minimal_cavity_payload(),
            case_build_spec=minimal_cavity_case_build_payload(),
            run_solver=True,
            solver_command=[sys.executable, "-c", "print('workflow solver')"],
        )
    )

    report_path = (
        workspace_tmp_path / "runs" / "lid_driven_cavity" / "reports" / "report.md"
    )
    manifest_path = (
        workspace_tmp_path / "runs" / "lid_driven_cavity" / "reports" / "manifest.json"
    )

    assert result.status == "completed"
    assert "OpenFOAM was executed locally." in report_path.read_text(encoding="utf-8")
    assert "OpenFOAM was not executed." not in report_path.read_text(encoding="utf-8")
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["openfoam_executed"] is True


def test_no_llm_workflow_writes_evidence_artifacts_when_solver_fails(
    workspace_tmp_path: Path,
) -> None:
    result = run_openfoam_workflow(
        WorkflowRequest(
            workspace_root=str(workspace_tmp_path),
            simulation_spec=minimal_cavity_payload(),
            case_build_spec=minimal_cavity_case_build_payload(),
            run_solver=True,
            solver_command=[
                sys.executable,
                "-c",
                "import sys; print('workflow solver failed'); sys.exit(7)",
            ],
        )
    )

    artifact_paths = {artifact.path for artifact in result.artifacts}

    assert result.status == "failed"
    assert result.solver_run is not None
    assert result.solver_run["return_code"] == 7
    assert "runs/lid_driven_cavity/reports/report.md" in artifact_paths
    assert "runs/lid_driven_cavity/reports/manifest.json" in artifact_paths
    assert (
        workspace_tmp_path / "runs" / "lid_driven_cavity" / "reports" / "report.md"
    ).is_file()
    assert [step.name for step in result.steps][-3:] == [
        "collect_diagnostics",
        "write_report",
        "write_manifest",
    ]


def test_no_llm_workflow_stops_before_writing_case_when_spec_is_invalid(
    workspace_tmp_path: Path,
) -> None:
    payload = minimal_cavity_payload()
    del payload["geometry"]

    result = run_openfoam_workflow(
        WorkflowRequest(
            workspace_root=str(workspace_tmp_path),
            simulation_spec=payload,
            case_build_spec=minimal_cavity_case_build_payload(),
        )
    )

    assert result.status == "failed"
    assert [step.name for step in result.steps] == [
        "inspect_workspace",
        "validate_simulation_spec",
    ]
    assert "geometry" in result.summary
    assert not (workspace_tmp_path / "runs").exists()


def test_no_llm_workflow_summary_is_stable(workspace_tmp_path: Path) -> None:
    request = WorkflowRequest(
        workspace_root=str(workspace_tmp_path),
        simulation_spec=minimal_cavity_payload(),
        case_build_spec=minimal_cavity_case_build_payload(),
        run_solver=False,
    )

    first = run_openfoam_workflow(request)
    rmtree(workspace_tmp_path / "runs")
    second = run_openfoam_workflow(request)

    assert first.summary == second.summary
    json.dumps(first.model_dump(mode="json"))


def test_core_workflow_does_not_import_openfoam_package_directly() -> None:
    source = Path("packages/core/src/opennavier_core/workflow.py").read_text(
        encoding="utf-8"
    )

    assert "opennavier.openfoam" not in source
