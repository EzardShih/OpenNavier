from pathlib import Path

from opennavier.openfoam.init_case import (
    CasePathNotEmptyError,
    create_cavity_case,
    create_duct_pressure_drop_case,
)
from opennavier_core.case_build_spec import (
    CaseBuildSpec,
    case_build_writer_capability_issues,
)


class CaseBuildWriteError(ValueError):
    """Raised when a validated CaseBuildSpec has no available writer implementation."""


def write_case_build_spec(
    spec: CaseBuildSpec,
    workspace_root: Path | str,
    *,
    force: bool = False,
) -> Path:
    root = Path(workspace_root).resolve()
    case_path = (root / spec.case_path).resolve()
    try:
        case_path.relative_to(root)
    except ValueError as error:
        raise CaseBuildWriteError("Case build path escapes the workspace") from error

    capability_issues = case_build_writer_capability_issues(spec)
    if capability_issues:
        raise CaseBuildWriteError(
            "; ".join(issue.message for issue in capability_issues)
        )

    case_family = spec.writer_operations[0].parameters.get("case_family")
    try:
        if case_family == "duct":
            return create_duct_pressure_drop_case(case_path, force=force)
        return create_cavity_case(case_path, force=force)
    except CasePathNotEmptyError:
        raise
