from pathlib import Path

from opennavier.mcp.paths import WorkspacePathError, resolve_workspace_path, resolve_workspace_root
from opennavier.openfoam.case_structure import validate_case_structure
from opennavier.openfoam.init_case import CasePathNotEmptyError, create_cavity_case
from opennavier_core.diagnostics import DiagnosticResult, DiagnosticStatus


def case_init_cavity(
    workspace_root: str, case_path: str = "case", force: bool = False
) -> dict[str, object]:
    provenance = _provenance()
    next_actions = _next_actions()

    try:
        root = resolve_workspace_root(workspace_root)
        resolved_case_path = resolve_workspace_path(root, case_path)
        create_cavity_case(resolved_case_path, force=force)
    except WorkspacePathError as error:
        return {
            "changed_paths": [],
            "diagnostics": [
                _failure_diagnostic(
                    code="mcp.workspace_path.invalid",
                    message=str(error),
                    path=str(case_path),
                )
            ],
            "provenance": provenance,
            "next_actions": next_actions,
        }
    except CasePathNotEmptyError as error:
        return {
            "changed_paths": [],
            "diagnostics": [
                _failure_diagnostic(
                    code="mcp.case_init_cavity.refused",
                    message=str(error),
                    path=str(resolved_case_path),
                )
            ],
            "provenance": provenance,
            "next_actions": next_actions,
        }

    changed_paths = _case_file_paths(root=root, case_path=resolved_case_path)
    diagnostics = [
        diagnostic.model_dump(mode="json")
        for diagnostic in validate_case_structure(resolved_case_path)
    ]
    return {
        "changed_paths": changed_paths,
        "diagnostics": diagnostics,
        "provenance": provenance,
        "next_actions": next_actions,
    }


def _case_file_paths(*, root: Path, case_path: Path) -> list[str]:
    return sorted(
        path.relative_to(root).as_posix()
        for path in case_path.rglob("*")
        if path.is_file()
    )


def _failure_diagnostic(*, code: str, message: str, path: str) -> dict[str, object]:
    return DiagnosticResult(
        status=DiagnosticStatus.FAIL,
        code=code,
        message=message,
        path=path,
    ).model_dump(mode="json")


def _provenance() -> dict[str, object]:
    return {"producer": "case_init_cavity", "inputs": []}


def _next_actions() -> list[str]:
    return ["case_validate_structure"]
