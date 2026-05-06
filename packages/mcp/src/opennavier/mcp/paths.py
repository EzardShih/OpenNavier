from pathlib import Path


class WorkspacePathError(ValueError):
    """Raised when an MCP tool path is outside its declared workspace."""


def resolve_workspace_root(workspace_root: Path | str) -> Path:
    root = Path(workspace_root).expanduser().resolve()
    if not root.is_dir():
        raise WorkspacePathError(f"Workspace root is not a directory: {root}")
    return root


def resolve_workspace_path(workspace_root: Path | str, relative_path: Path | str) -> Path:
    root = resolve_workspace_root(workspace_root)
    path = Path(relative_path).expanduser()
    candidate = path.resolve() if path.is_absolute() else (root / path).resolve()

    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise WorkspacePathError(f"Path escapes workspace root: {relative_path}") from error

    return candidate
