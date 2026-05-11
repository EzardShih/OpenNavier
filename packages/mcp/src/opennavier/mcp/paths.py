from pathlib import Path

from opennavier_core.workspace_path import normalize_workspace_relative_path


class WorkspacePathError(ValueError):
    """Raised when an MCP tool path is outside its declared workspace."""


def resolve_workspace_root(workspace_root: Path | str) -> Path:
    root = Path(workspace_root).expanduser().resolve()
    if not root.is_dir():
        raise WorkspacePathError(f"Workspace root is not a directory: {root}")
    return root


def resolve_workspace_path(workspace_root: Path | str, relative_path: Path | str) -> Path:
    root = resolve_workspace_root(workspace_root)
    try:
        normalized_path = normalize_workspace_relative_path(
            relative_path,
            field_name="path",
        )
    except ValueError as error:
        message = str(error)
        if "escape" in message:
            raise WorkspacePathError(
                f"Path escapes workspace root: {relative_path}"
            ) from error
        raise WorkspacePathError(
            f"Path must be workspace-relative: {relative_path}"
        ) from error

    candidate = (root / Path(normalized_path)).resolve()

    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise WorkspacePathError(f"Path escapes workspace root: {relative_path}") from error

    return candidate
