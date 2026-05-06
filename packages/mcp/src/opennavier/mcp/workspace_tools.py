import json
import os
from pathlib import Path
from typing import Any

from opennavier.mcp.paths import WorkspacePathError, resolve_workspace_path, resolve_workspace_root

MANIFEST_PATH = "simulation.onv.json"
KNOWN_ARTIFACT_FOLDERS = (
    "specs",
    "geometry",
    "case",
    "logs",
    "diagnostics",
    "reports",
    "exports",
)


def workspace_inspect(workspace_root: str) -> dict[str, object]:
    root = resolve_workspace_root(workspace_root)
    manifest_path = root / MANIFEST_PATH
    manifest_found = manifest_path.is_file() or manifest_path.is_symlink()
    manifest: Any | None = None
    manifest_error: str | None = None
    manifest_valid = False

    if manifest_found:
        try:
            resolved_manifest_path = resolve_workspace_path(root, MANIFEST_PATH)
            manifest = json.loads(resolved_manifest_path.read_text(encoding="utf-8"))
            manifest_valid = True
        except WorkspacePathError as error:
            manifest_error = str(error)
        except UnicodeDecodeError as error:
            manifest_error = _format_manifest_encoding_error(error)
        except OSError as error:
            manifest_error = _format_manifest_read_error(error)
        except json.JSONDecodeError as error:
            manifest_error = _format_manifest_error(error)

    return {
        "workspace_root": str(root),
        "manifest_path": MANIFEST_PATH,
        "manifest_found": manifest_found,
        "manifest_valid": manifest_valid,
        "manifest": manifest,
        "manifest_error": manifest_error,
        "artifacts": _list_artifacts(root),
    }


def _format_manifest_error(error: json.JSONDecodeError) -> str:
    return (
        f"Invalid JSON in {MANIFEST_PATH}: {error.msg} "
        f"at line {error.lineno} column {error.colno}"
    )


def _format_manifest_encoding_error(error: UnicodeDecodeError) -> str:
    return f"Invalid UTF-8 in {MANIFEST_PATH}: {error.reason} at byte {error.start}"


def _format_manifest_read_error(error: OSError) -> str:
    detail = error.strerror or str(error) or error.__class__.__name__
    return f"Unable to read {MANIFEST_PATH}: {detail}"


def _list_artifacts(root: Path) -> dict[str, list[str]]:
    artifacts: dict[str, list[str]] = {}

    for folder in KNOWN_ARTIFACT_FOLDERS:
        try:
            folder_path = resolve_workspace_path(root, folder)
        except WorkspacePathError:
            artifacts[folder] = []
            continue

        if not folder_path.is_dir():
            artifacts[folder] = []
            continue

        artifacts[folder] = sorted(_iter_artifact_files(root, folder, folder_path))

    return artifacts


def _iter_artifact_files(root: Path, folder: str, folder_path: Path) -> list[str]:
    artifact_paths: list[str] = []
    for current_dir, dir_names, file_names in os.walk(folder_path, followlinks=False):
        current_path = Path(current_dir)
        dir_names[:] = [
            dir_name
            for dir_name in dir_names
            if _path_stays_under_root(current_path / dir_name, root)
        ]

        for file_name in file_names:
            file_path = current_path / file_name
            if not _path_stays_under_root(file_path, root) or not file_path.is_file():
                continue

            relative_path = file_path.relative_to(folder_path)
            artifact_paths.append((Path(folder) / relative_path).as_posix())

    return artifact_paths


def _path_stays_under_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root)
    except ValueError:
        return False
    return True
