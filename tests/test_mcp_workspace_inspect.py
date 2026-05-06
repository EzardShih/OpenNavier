import json
from contextlib import suppress
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

import pytest
from opennavier.mcp.workspace_tools import workspace_inspect
from pytest import MonkeyPatch

KNOWN_ARTIFACT_FOLDERS = (
    "specs",
    "geometry",
    "case",
    "logs",
    "diagnostics",
    "reports",
    "exports",
)


def _workspace_path(prefix: str) -> Path:
    return Path("tests") / ".tmp" / f"{prefix}-{uuid4().hex}"


def _make_file(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _make_symlink(link_path: Path, target_path: Path, *, is_directory: bool = False) -> None:
    link_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        link_path.symlink_to(target_path.resolve(), target_is_directory=is_directory)
    except (NotImplementedError, OSError) as error:
        pytest.skip(f"symlink creation is unavailable: {error}")


def _empty_artifact_groups() -> dict[str, list[str]]:
    return {folder: [] for folder in KNOWN_ARTIFACT_FOLDERS}


def _create_workspace() -> Path:
    path = _workspace_path("mcp-workspace-inspect")
    path.mkdir(parents=True)
    return path


def _remove_workspace(path: Path) -> None:
    rmtree(path, ignore_errors=True)
    with suppress(OSError):
        path.parent.rmdir()


def test_workspace_inspect_reports_manifest_and_known_artifacts() -> None:
    workspace = _create_workspace()
    manifest = {"simulation_id": "duct-001", "solver": "simpleFoam"}
    try:
        _make_file(workspace / "simulation.onv.json", json.dumps(manifest))
        _make_file(workspace / "specs" / "simulation.json", "{}")
        _make_file(workspace / "specs" / "nested" / "mesh.json", "{}")
        _make_file(workspace / "geometry" / "duct.step")
        _make_file(workspace / "logs" / "simpleFoam.log")

        result = workspace_inspect(str(workspace))

        assert result["workspace_root"] == str(workspace.resolve())
        assert result["manifest_path"] == "simulation.onv.json"
        assert result["manifest_found"] is True
        assert result["manifest_valid"] is True
        assert result["manifest"] == manifest
        assert result["manifest_error"] is None
        assert result["artifacts"] == {
            "specs": ["specs/nested/mesh.json", "specs/simulation.json"],
            "geometry": ["geometry/duct.step"],
            "case": [],
            "logs": ["logs/simpleFoam.log"],
            "diagnostics": [],
            "reports": [],
            "exports": [],
        }
    finally:
        _remove_workspace(workspace)


def test_workspace_inspect_reports_non_utf8_manifest_without_failing() -> None:
    workspace = _create_workspace()
    try:
        _make_bytes(workspace / "simulation.onv.json", b"\xff")
        _make_file(workspace / "logs" / "simpleFoam.log")

        result = workspace_inspect(str(workspace))

        assert result["workspace_root"] == str(workspace.resolve())
        assert result["manifest_path"] == "simulation.onv.json"
        assert result["manifest_found"] is True
        assert result["manifest_valid"] is False
        assert result["manifest"] is None
        assert (
            result["manifest_error"]
            == "Invalid UTF-8 in simulation.onv.json: invalid start byte at byte 0"
        )
        assert result["artifacts"] == {
            **_empty_artifact_groups(),
            "logs": ["logs/simpleFoam.log"],
        }
    finally:
        _remove_workspace(workspace)


def test_workspace_inspect_rejects_manifest_symlink_escape() -> None:
    workspace = _create_workspace()
    external = _workspace_path("external-manifest")
    external_manifest = external / "simulation.onv.json"
    manifest = {"simulation_id": "outside", "private": "do not expose"}
    try:
        _make_file(external_manifest, json.dumps(manifest))
        _make_symlink(workspace / "simulation.onv.json", external_manifest)

        result = workspace_inspect(str(workspace))

        assert result["workspace_root"] == str(workspace.resolve())
        assert result["manifest_path"] == "simulation.onv.json"
        assert result["manifest_found"] is True
        assert result["manifest_valid"] is False
        assert result["manifest"] is None
        assert result["manifest_error"] == "Path escapes workspace root: simulation.onv.json"
        assert result["artifacts"] == _empty_artifact_groups()
    finally:
        _remove_workspace(workspace)
        _remove_workspace(external)


def test_workspace_inspect_reports_unreadable_manifest_without_failing(
    monkeypatch: MonkeyPatch,
) -> None:
    workspace = _create_workspace()
    manifest_path = workspace / "simulation.onv.json"
    resolved_manifest_path = manifest_path.resolve()
    original_read_text = Path.read_text

    def raise_for_manifest(path: Path, *args: object, **kwargs: object) -> str:
        if path.resolve() == resolved_manifest_path:
            raise PermissionError("permission denied by test")
        return original_read_text(path, *args, **kwargs)

    try:
        _make_file(manifest_path, "{}")
        _make_file(workspace / "reports" / "summary.md")
        monkeypatch.setattr(Path, "read_text", raise_for_manifest)

        result = workspace_inspect(str(workspace))

        assert result["workspace_root"] == str(workspace.resolve())
        assert result["manifest_path"] == "simulation.onv.json"
        assert result["manifest_found"] is True
        assert result["manifest_valid"] is False
        assert result["manifest"] is None
        assert (
            result["manifest_error"]
            == "Unable to read simulation.onv.json: permission denied by test"
        )
        assert result["artifacts"] == {
            **_empty_artifact_groups(),
            "reports": ["reports/summary.md"],
        }
    finally:
        _remove_workspace(workspace)


def test_workspace_inspect_skips_artifact_folder_symlink_escape() -> None:
    workspace = _create_workspace()
    external = _workspace_path("external-artifacts")
    try:
        _make_file(external / "private.log", "do not list")
        _make_symlink(workspace / "logs", external, is_directory=True)

        result = workspace_inspect(str(workspace))

        assert result["workspace_root"] == str(workspace.resolve())
        assert result["artifacts"] == _empty_artifact_groups()
    finally:
        _remove_workspace(workspace)
        _remove_workspace(external)


def test_workspace_inspect_reports_malformed_manifest_without_writing() -> None:
    workspace = _create_workspace()
    try:
        _make_file(workspace / "simulation.onv.json", "{ invalid")

        result = workspace_inspect(str(workspace))

        assert result["workspace_root"] == str(workspace.resolve())
        assert result["manifest_path"] == "simulation.onv.json"
        assert result["manifest_found"] is True
        assert result["manifest_valid"] is False
        assert result["manifest"] is None
        assert (
            result["manifest_error"]
            == "Invalid JSON in simulation.onv.json: Expecting property name enclosed in "
            "double quotes at line 1 column 3"
        )
        assert result["artifacts"] == _empty_artifact_groups()
        assert all(not (workspace / folder).exists() for folder in KNOWN_ARTIFACT_FOLDERS)
    finally:
        _remove_workspace(workspace)
