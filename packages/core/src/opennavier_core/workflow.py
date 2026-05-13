from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from opennavier_core.case_build_spec import CaseBuildSpec
from opennavier_core.diagnostics import DiagnosticResult, DiagnosticStatus
from opennavier_core.manifest import write_reproducibility_manifest
from opennavier_core.plan import simulation_plan_to_json
from opennavier_core.planner import plan_simulation
from opennavier_core.reporting import write_markdown_report
from opennavier_core.simulation_spec import SimulationSpec


class WorkflowModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WorkflowRequest(WorkflowModel):
    workspace_root: str
    simulation_spec: dict[str, object]
    case_build_spec: dict[str, object]
    run_solver: bool = False
    solver_command: list[str] | None = None
    force_case_write: bool = False


class WorkflowStep(WorkflowModel):
    name: str
    status: Literal["completed", "failed", "skipped"]
    details: dict[str, str] = Field(default_factory=dict)


class WorkflowArtifact(WorkflowModel):
    kind: str
    path: str


class WorkflowResult(WorkflowModel):
    status: Literal["completed", "failed"]
    steps: list[WorkflowStep] = Field(default_factory=list)
    artifacts: list[WorkflowArtifact] = Field(default_factory=list)
    diagnostics: list[dict[str, object]] = Field(default_factory=list)
    solver_run: dict[str, object] | None = None
    summary: str


class WorkflowSolverRun(Protocol):
    command: list[str]
    log_path: Path
    return_code: int | None

    @property
    def succeeded(self) -> bool: ...


WriteCaseBuildSpec = Callable[[CaseBuildSpec, Path, bool], Path]
ValidateCaseStructure = Callable[[Path], list[DiagnosticResult]]
CollectCaseDiagnostics = Callable[[Path], list[DiagnosticResult]]
RunLocalSolver = Callable[[Sequence[str], Path, Path], WorkflowSolverRun]


@dataclass(frozen=True)
class WorkflowOperations:
    write_case_build_spec: WriteCaseBuildSpec
    validate_case_structure: ValidateCaseStructure
    collect_case_diagnostics: CollectCaseDiagnostics
    run_local_solver: RunLocalSolver


def run_no_llm_workflow(
    request: WorkflowRequest,
    *,
    operations: WorkflowOperations,
) -> WorkflowResult:
    steps: list[WorkflowStep] = []
    artifacts: list[WorkflowArtifact] = []

    root = Path(request.workspace_root).resolve()
    if not root.is_dir():
        return _failed(
            steps,
            f"Workspace root is not a directory: {root}",
            failed_step="inspect_workspace",
        )
    steps.append(WorkflowStep(name="inspect_workspace", status="completed"))

    try:
        simulation_spec = SimulationSpec.model_validate(request.simulation_spec)
    except ValidationError as error:
        return _failed(
            steps,
            _validation_summary(error),
            failed_step="validate_simulation_spec",
        )
    steps.append(WorkflowStep(name="validate_simulation_spec", status="completed"))

    try:
        case_build_spec = CaseBuildSpec.model_validate(request.case_build_spec)
    except ValidationError as error:
        return _failed(
            steps,
            _validation_summary(error),
            failed_step="validate_case_build_spec",
        )
    steps.append(WorkflowStep(name="validate_case_build_spec", status="completed"))

    planning_result = plan_simulation(simulation_spec, case_build_spec)
    if planning_result.status != "planned":
        steps.append(WorkflowStep(name="plan_simulation", status="failed"))
        reasons = ", ".join(reason.code for reason in planning_result.reasons)
        return WorkflowResult(
            status="failed",
            steps=steps,
            artifacts=artifacts,
            summary=f"Workflow stopped because the request is not executable: {reasons}.",
        )
    steps.append(WorkflowStep(name="plan_simulation", status="completed"))

    run_root = root / Path(case_build_spec.case_path).parent
    plan_path = run_root / "plan.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(simulation_plan_to_json(planning_result.plan), encoding="utf-8")
    artifacts.append(_artifact(root, "simulation_plan", plan_path))
    steps.append(WorkflowStep(name="write_plan_artifact", status="completed"))

    try:
        case_path = operations.write_case_build_spec(
            case_build_spec,
            root,
            request.force_case_write,
        )
    except ValueError as error:
        return _failed(steps, str(error), failed_step="initialize_case")
    steps.append(WorkflowStep(name="initialize_case", status="completed"))
    artifacts.extend(
        _artifact(root, "openfoam_case_file", path)
        for path in sorted(case_path.rglob("*"))
        if path.is_file()
    )

    preflight = operations.validate_case_structure(case_path)
    steps.append(WorkflowStep(name="preflight_check", status="completed"))
    if any(diagnostic.status is DiagnosticStatus.FAIL for diagnostic in preflight):
        return WorkflowResult(
            status="failed",
            steps=steps,
            artifacts=artifacts,
            diagnostics=[diagnostic.model_dump(mode="json") for diagnostic in preflight],
            summary="Workflow stopped because pre-flight checks failed.",
        )

    solver_run: dict[str, object] | None = None
    solver_failed = False
    solver_was_executed = False
    if request.run_solver:
        command = request.solver_command or [case_build_spec.solver, "-case", str(case_path)]
        run_result = operations.run_local_solver(command, case_path, root)
        solver_failed = not run_result.succeeded
        solver_was_executed = run_result.return_code is not None
        solver_run = {
            "command": run_result.command,
            "return_code": run_result.return_code,
            "log_path": _relative_path(root, run_result.log_path),
        }
        artifacts.append(_artifact(root, "solver_log", run_result.log_path))
        steps.append(
            WorkflowStep(
                name="execute_solver",
                status="completed" if run_result.succeeded else "failed",
            )
        )
    else:
        steps.append(WorkflowStep(name="solver_execution_skipped", status="skipped"))

    diagnostics = operations.collect_case_diagnostics(case_path)
    steps.append(WorkflowStep(name="collect_diagnostics", status="completed"))

    report_path = run_root / "reports" / "report.md"
    manifest_path = run_root / "reports" / "manifest.json"
    write_markdown_report(
        case_path=case_path,
        diagnostics=diagnostics,
        output_path=report_path,
        openfoam_executed=solver_was_executed,
    )
    artifacts.append(_artifact(root, "report", report_path))
    steps.append(WorkflowStep(name="write_report", status="completed"))

    write_reproducibility_manifest(
        case_path=case_path,
        diagnostics=diagnostics,
        generated_artifacts=[report_path],
        output_path=manifest_path,
        openfoam_executed=solver_was_executed,
    )
    artifacts.append(_artifact(root, "manifest", manifest_path))
    steps.append(WorkflowStep(name="write_manifest", status="completed"))

    if solver_failed:
        return WorkflowResult(
            status="failed",
            steps=steps,
            artifacts=artifacts,
            diagnostics=[diagnostic.model_dump(mode="json") for diagnostic in diagnostics],
            solver_run=solver_run,
            summary="Workflow stopped because solver execution failed.",
        )

    summary = _summary(
        case_name=simulation_spec.case_name,
        diagnostics=diagnostics,
        solver_was_run=request.run_solver,
    )
    steps.append(WorkflowStep(name="summarize", status="completed"))

    return WorkflowResult(
        status="completed",
        steps=steps,
        artifacts=artifacts,
        diagnostics=[diagnostic.model_dump(mode="json") for diagnostic in diagnostics],
        solver_run=solver_run,
        summary=summary,
    )


def _failed(
    steps: list[WorkflowStep],
    summary: str,
    *,
    failed_step: str,
) -> WorkflowResult:
    return WorkflowResult(
        status="failed",
        steps=[*steps, WorkflowStep(name=failed_step, status="failed")],
        summary=summary,
    )


def _validation_summary(error: ValidationError) -> str:
    first_error = error.errors()[0]
    location = ".".join(str(part) for part in first_error.get("loc", ()))
    message = str(first_error.get("msg", "Validation error"))
    return f"{location}: {message}" if location else message


def _artifact(root: Path, kind: str, path: Path) -> WorkflowArtifact:
    return WorkflowArtifact(kind=kind, path=_relative_path(root, path))


def _relative_path(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root).as_posix()


def _summary(
    *,
    case_name: str,
    diagnostics: list[DiagnosticResult],
    solver_was_run: bool,
) -> str:
    failures = sum(diagnostic.status is DiagnosticStatus.FAIL for diagnostic in diagnostics)
    warnings = sum(diagnostic.status is DiagnosticStatus.WARN for diagnostic in diagnostics)
    solver_sentence = (
        "Solver execution completed."
        if solver_was_run
        else "Solver execution was skipped."
    )
    next_actions = (
        "review_failed_diagnostics"
        if failures
        else "approve_solver_execution"
        if not solver_was_run
        else "review_report"
    )
    return (
        f"Completed deterministic workflow for {case_name}. "
        f"{solver_sentence} "
        f"Diagnostics reported {failures} failures and {warnings} warnings. "
        f"Next actions: {next_actions}."
    )
