from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt

from opennavier_core.diagnostics import DiagnosticResult, DiagnosticStatus
from opennavier_core.session import (
    AgentSession,
    ArtifactReference,
    CommandRecord,
    ProvenanceRecord,
    create_agent_session,
)


class IterationPolicyModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ApprovalCheckpoint(IterationPolicyModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)


class IterationProposal(IterationPolicyModel):
    diagnostic_code: str = Field(min_length=1)
    recommended_action: str = Field(min_length=1)
    changed_paths: list[str] = Field(default_factory=list)
    commands: list[list[str]] = Field(default_factory=list)
    requires_approval: bool = True


class IterationPolicyRequest(IterationPolicyModel):
    workspace_root: str = Field(min_length=1)
    case_path: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    engineering_intent: str = Field(min_length=1)
    diagnostics: list[DiagnosticResult] = Field(default_factory=list)
    solver_command: list[str] | None = None
    completed_reruns: NonNegativeInt = 0
    max_reruns: NonNegativeInt = 2


class IterationPolicyResult(IterationPolicyModel):
    status: Literal["proposal_ready", "no_action", "stopped"]
    proposals: list[IterationProposal] = Field(default_factory=list)
    approval_checkpoints: list[ApprovalCheckpoint] = Field(default_factory=list)
    requires_approval: bool = False
    stop_reason: str | None = None
    session: AgentSession
    summary: str


def propose_iteration(request: IterationPolicyRequest) -> IterationPolicyResult:
    failed_diagnostics = [
        diagnostic
        for diagnostic in request.diagnostics
        if diagnostic.status is DiagnosticStatus.FAIL
    ]

    if not failed_diagnostics:
        return IterationPolicyResult(
            status="no_action",
            session=_session(request, action="no iteration needed"),
            summary="No failed diagnostics require an iteration proposal.",
        )

    if request.completed_reruns >= request.max_reruns:
        return IterationPolicyResult(
            status="stopped",
            stop_reason="rerun_limit_reached",
            session=_session(request, action="stopped iteration at rerun limit"),
            summary="Iteration stopped because the configured rerun limit was reached.",
        )

    proposals = [_proposal_for_diagnostic(request, diagnostic) for diagnostic in failed_diagnostics]
    approval_checkpoints = _approval_checkpoints(proposals)
    return IterationPolicyResult(
        status="proposal_ready",
        proposals=proposals,
        approval_checkpoints=approval_checkpoints,
        requires_approval=True,
        session=_session(
            request,
            action="proposed remediation",
            proposals=proposals,
        ),
        summary=(
            f"Prepared {len(proposals)} approval-gated remediation proposal(s). "
            "No files were changed."
        ),
    )


def _proposal_for_diagnostic(
    request: IterationPolicyRequest,
    diagnostic: DiagnosticResult,
) -> IterationProposal:
    code = diagnostic.code
    if code.startswith("openfoam.required_file.") or code.startswith(
        "openfoam.dictionary_header."
    ):
        return IterationProposal(
            diagnostic_code=code,
            recommended_action=(
                "Regenerate the affected OpenFOAM case file through the approved "
                "CaseBuildSpec writer, then rerun structure diagnostics."
            ),
            changed_paths=[diagnostic.path],
        )

    if code.startswith("openfoam.required_directory."):
        return IterationProposal(
            diagnostic_code=code,
            recommended_action=(
                "Regenerate the missing case directory from a validated CaseBuildSpec "
                "before running solver commands."
            ),
            changed_paths=[diagnostic.path],
        )

    if code.startswith("openfoam.boundary_conditions."):
        return IterationProposal(
            diagnostic_code=code,
            recommended_action=(
                "Rebuild boundary-condition fields from typed boundary data and "
                "run boundary-condition diagnostics again."
            ),
            changed_paths=[diagnostic.path],
        )

    if code.startswith("openfoam.mesh_quality."):
        return IterationProposal(
            diagnostic_code=code,
            recommended_action=(
                "Review mesh controls and regenerate the mesh only after explicit approval."
            ),
            changed_paths=[f"{request.case_path}/system/blockMeshDict"],
            commands=[["checkMesh", "-case", request.case_path]],
        )

    if code == "openfoam.residuals.high_final":
        commands = [] if request.solver_command is None else [request.solver_command]
        return IterationProposal(
            diagnostic_code=code,
            recommended_action=(
                "Review solver controls, relaxation, and time-step settings before an "
                "approved rerun."
            ),
            changed_paths=[
                f"{request.case_path}/system/fvSolution",
                f"{request.case_path}/system/controlDict",
            ],
            commands=commands,
        )

    return IterationProposal(
        diagnostic_code=code,
        recommended_action=(
            "Inspect this diagnostic manually and propose a typed remediation before "
            "changing files or rerunning commands."
        ),
    )


def _approval_checkpoints(
    proposals: list[IterationProposal],
) -> list[ApprovalCheckpoint]:
    checkpoints: list[ApprovalCheckpoint] = []
    seen: set[str] = set()
    for proposal in proposals:
        code = (
            "approve_solver_rerun"
            if proposal.commands
            else "approve_case_file_remediation"
            if proposal.changed_paths
            else "approve_manual_diagnostic_review"
        )
        if code in seen:
            continue
        seen.add(code)
        checkpoints.append(
            ApprovalCheckpoint(
                code=code,
                message=_approval_message(code),
            )
        )
    return checkpoints


def _approval_message(code: str) -> str:
    messages = {
        "approve_case_file_remediation": (
            "Explicit approval is required before changing case files."
        ),
        "approve_solver_rerun": (
            "Explicit approval is required before changing controls or rerunning a solver."
        ),
        "approve_manual_diagnostic_review": (
            "Explicit approval is required before applying a manual diagnostic fix."
        ),
    }
    return messages[code]


def _session(
    request: IterationPolicyRequest,
    *,
    action: str,
    proposals: list[IterationProposal] | None = None,
) -> AgentSession:
    provenance = ProvenanceRecord(tool="opennavier.iteration_policy", action=action)
    proposals = proposals or []
    changed_paths = sorted(
        {
            changed_path
            for proposal in proposals
            for changed_path in proposal.changed_paths
        }
    )
    commands = [
        command
        for proposal in proposals
        for command in proposal.commands
    ]
    return create_agent_session(
        workspace_root=request.workspace_root,
        session_id=request.session_id,
        engineering_intent=request.engineering_intent,
        generated_artifacts=[
            ArtifactReference(
                kind="proposed_change",
                path=path,
                provenance=provenance,
            )
            for path in changed_paths
        ],
        command_records=[
            CommandRecord(
                runner="proposed_rerun",
                command=command,
                cwd=request.case_path,
                provenance=provenance,
            )
            for command in commands
        ],
        provenance=[provenance],
    )
