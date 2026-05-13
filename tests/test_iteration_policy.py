from pathlib import Path

import pytest
from opennavier_core.diagnostics import DiagnosticResult, DiagnosticStatus
from opennavier_core.iteration_policy import IterationPolicyRequest, propose_iteration


def failing_diagnostic(code: str, path: str) -> DiagnosticResult:
    return DiagnosticResult(
        status=DiagnosticStatus.FAIL,
        code=code,
        message=f"{code} failed",
        path=path,
    )


def test_iteration_policy_proposes_approval_gated_fix_for_known_failures(
    tmp_path: Path,
) -> None:
    result = propose_iteration(
        IterationPolicyRequest(
            workspace_root=str(tmp_path),
            case_path="runs/cavity/case",
            session_id="iteration-001",
            engineering_intent="Fix cavity diagnostics.",
            diagnostics=[
                failing_diagnostic(
                    "openfoam.required_file.system_controlDict",
                    "runs/cavity/case/system/controlDict",
                )
            ],
        )
    )

    assert result.status == "proposal_ready"
    assert result.requires_approval is True
    assert result.proposals[0].diagnostic_code == "openfoam.required_file.system_controlDict"
    assert result.proposals[0].requires_approval is True
    assert result.proposals[0].changed_paths == ["runs/cavity/case/system/controlDict"]
    assert result.approval_checkpoints[0].code == "approve_case_file_remediation"
    assert result.session.generated_artifacts[0].path == "runs/cavity/case/system/controlDict"
    assert result.session.generated_artifacts[0].kind == "proposed_change"
    assert result.session.provenance[0].tool == "opennavier.iteration_policy"


def test_iteration_policy_records_rerun_command_proposals_in_session(
    tmp_path: Path,
) -> None:
    result = propose_iteration(
        IterationPolicyRequest(
            workspace_root=str(tmp_path),
            case_path="runs/duct/case",
            session_id="iteration-002",
            engineering_intent="Investigate duct convergence.",
            solver_command=["simpleFoam", "-case", "runs/duct/case"],
            diagnostics=[
                failing_diagnostic("openfoam.residuals.high_final", "runs/duct/case/log.simpleFoam")
            ],
        )
    )

    assert result.status == "proposal_ready"
    assert result.proposals[0].commands == [["simpleFoam", "-case", "runs/duct/case"]]
    assert result.session.command_records[0].runner == "proposed_rerun"
    assert result.session.command_records[0].command == ["simpleFoam", "-case", "runs/duct/case"]
    assert result.session.command_records[0].cwd == "runs/duct/case"


def test_iteration_policy_rejects_empty_solver_command(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="solver_command"):
        IterationPolicyRequest(
            workspace_root=str(tmp_path),
            case_path="runs/duct/case",
            session_id="iteration-empty-command",
            engineering_intent="Investigate duct convergence.",
            solver_command=[],
            diagnostics=[
                failing_diagnostic(
                    "openfoam.residuals.high_final",
                    "runs/duct/case/log.simpleFoam",
                )
            ],
        )


def test_iteration_policy_stops_at_rerun_limit_without_proposals(
    tmp_path: Path,
) -> None:
    result = propose_iteration(
        IterationPolicyRequest(
            workspace_root=str(tmp_path),
            case_path="runs/cavity/case",
            session_id="iteration-003",
            engineering_intent="Fix cavity diagnostics.",
            diagnostics=[
                failing_diagnostic("openfoam.mesh_quality.failed", "runs/cavity/case/log.checkMesh")
            ],
            completed_reruns=2,
            max_reruns=2,
        )
    )

    assert result.status == "stopped"
    assert result.stop_reason == "rerun_limit_reached"
    assert result.proposals == []
    assert result.requires_approval is False


def test_iteration_policy_returns_no_action_when_diagnostics_pass(
    tmp_path: Path,
) -> None:
    result = propose_iteration(
        IterationPolicyRequest(
            workspace_root=str(tmp_path),
            case_path="runs/cavity/case",
            session_id="iteration-004",
            engineering_intent="Review cavity diagnostics.",
            diagnostics=[
                DiagnosticResult(
                    status=DiagnosticStatus.PASS,
                    code="openfoam.mesh_quality.ok",
                    message="Mesh quality passed.",
                    path="runs/cavity/case/log.checkMesh",
                )
            ],
        )
    )

    assert result.status == "no_action"
    assert result.proposals == []
    assert result.summary == "No failed diagnostics require an iteration proposal."
