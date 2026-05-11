from pathlib import Path, PurePosixPath, PureWindowsPath

_NON_PORTABLE_PATH_CHARACTERS = frozenset('<>:"|?*')


def normalize_workspace_relative_path(
    value: Path | str,
    *,
    field_name: str = "path",
) -> str:
    raw = str(value)
    if not raw.strip():
        raise ValueError(f"{field_name} must not be empty")
    if raw.startswith("~"):
        raise ValueError(f"{field_name} must be workspace-relative")

    windows_path = PureWindowsPath(raw)
    if windows_path.drive or windows_path.root:
        raise ValueError(f"{field_name} must be workspace-relative")

    path = PurePosixPath(raw.replace("\\", "/"))
    if path.is_absolute() or not path.parts:
        raise ValueError(f"{field_name} must be workspace-relative")
    if ".." in path.parts:
        raise ValueError(f"{field_name} must not escape the workspace")

    parts = [part for part in path.parts if part not in {"", "."}]
    if not parts:
        raise ValueError(f"{field_name} must be workspace-relative")
    for part in parts:
        if any(character in _NON_PORTABLE_PATH_CHARACTERS for character in part):
            raise ValueError(f"{field_name} contains non-portable path characters")

    return "/".join(parts)
