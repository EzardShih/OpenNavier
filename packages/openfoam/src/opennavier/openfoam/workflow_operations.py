from collections.abc import Sequence
from pathlib import Path

from opennavier.openfoam.case_build_writer import write_case_build_spec
from opennavier.openfoam.case_structure import validate_case_structure
from opennavier.openfoam.diagnostics import collect_case_diagnostics
from opennavier.openfoam.runner import SolverRunResult, run_local_solver
from opennavier_core.case_build_spec import CaseBuildSpec
from opennavier_core.diagnostics import DiagnosticResult
from opennavier_core.workflow import WorkflowOperations


def openfoam_workflow_operations() -> WorkflowOperations:
    return WorkflowOperations(
        write_case_build_spec=_write_case_build_spec,
        validate_case_structure=_validate_case_structure,
        collect_case_diagnostics=_collect_case_diagnostics,
        run_local_solver=_run_local_solver,
    )


def _write_case_build_spec(
    spec: CaseBuildSpec,
    workspace_root: Path,
    force: bool,
) -> Path:
    return write_case_build_spec(spec, workspace_root, force=force)


def _validate_case_structure(case_path: Path) -> list[DiagnosticResult]:
    return validate_case_structure(case_path)


def _collect_case_diagnostics(case_path: Path) -> list[DiagnosticResult]:
    return collect_case_diagnostics(case_path)


def _run_local_solver(
    command: Sequence[str],
    case_path: Path,
    workspace_root: Path,
) -> SolverRunResult:
    return run_local_solver(command, case_path, workspace_root=workspace_root)
