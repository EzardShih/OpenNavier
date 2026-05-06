from pathlib import Path

from opennavier.mcp.paths import (
    WorkspacePathError,
    resolve_workspace_path,
    resolve_workspace_root,
)
from opennavier.openfoam.case_structure import (
    REQUIRED_DIRECTORIES,
    REQUIRED_SYSTEM_FILES,
    validate_case_structure,
)


def case_validate_structure(workspace_root: str, case_path: str = "case") -> dict[str, object]:
    try:
        resolved_workspace_root = resolve_workspace_root(workspace_root)
        resolved_case_path = resolve_workspace_path(resolved_workspace_root, case_path)
    except WorkspacePathError as error:
        diagnostics = [_workspace_path_diagnostic(path=case_path, message=str(error))]
        return {
            "case_path": case_path,
            "diagnostics": diagnostics,
            "summary": _summarize(diagnostics),
        }

    diagnostics = _required_child_workspace_diagnostics(
        workspace_root=resolved_workspace_root,
        case_path=case_path,
    )
    if diagnostics:
        return {
            "case_path": case_path,
            "diagnostics": diagnostics,
            "summary": _summarize(diagnostics),
        }

    diagnostics = [
        diagnostic.model_dump(mode="json")
        for diagnostic in validate_case_structure(resolved_case_path)
    ]
    return {
        "case_path": case_path,
        "diagnostics": diagnostics,
        "summary": _summarize(diagnostics),
    }


def _required_child_workspace_diagnostics(
    *,
    workspace_root: Path,
    case_path: str,
) -> list[dict[str, object]]:
    for required_path in _required_case_paths():
        child_path = _case_child_path(case_path, required_path)
        try:
            resolve_workspace_path(workspace_root, child_path)
        except WorkspacePathError as error:
            return [_workspace_path_diagnostic(path=child_path, message=str(error))]

    return []


def _required_case_paths() -> list[Path]:
    return [
        *(Path(directory) for directory in REQUIRED_DIRECTORIES),
        *(Path("system") / filename for filename in REQUIRED_SYSTEM_FILES),
    ]


def _case_child_path(case_path: str, child_path: Path) -> str:
    parent = Path(case_path)
    if parent == Path("."):
        return child_path.as_posix()

    return (parent / child_path).as_posix()


def _workspace_path_diagnostic(*, path: str, message: str) -> dict[str, object]:
    return {
        "status": "FAIL",
        "code": "mcp.workspace_path.invalid",
        "message": message,
        "path": path,
        "details": {},
    }


def _summarize(diagnostics: list[dict[str, object]]) -> dict[str, int]:
    statuses = [diagnostic["status"] for diagnostic in diagnostics]
    return {
        "total": len(diagnostics),
        "passed": statuses.count("PASS"),
        "failed": statuses.count("FAIL"),
        "warnings": statuses.count("WARN"),
    }
