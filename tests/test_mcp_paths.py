from collections.abc import Generator
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

import pytest
from opennavier.mcp.paths import WorkspacePathError, resolve_workspace_path, resolve_workspace_root


@pytest.fixture
def workspace_tmp_path() -> Generator[Path, None, None]:
    path = Path(".tmp") / f"mcp-paths-{uuid4().hex}"
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        rmtree(path, ignore_errors=True)


def test_resolve_workspace_root_requires_existing_directory() -> None:
    missing_path = Path(".tmp") / f"missing-mcp-root-{uuid4().hex}"

    with pytest.raises(WorkspacePathError, match="Workspace root is not a directory"):
        resolve_workspace_root(missing_path)


def test_resolve_workspace_path_accepts_relative_paths_inside_workspace(
    workspace_tmp_path: Path,
) -> None:
    resolved_path = resolve_workspace_path(workspace_tmp_path, "specs/simulation.json")

    assert resolved_path == (workspace_tmp_path / "specs" / "simulation.json").resolve()


def test_resolve_workspace_path_rejects_paths_that_escape_workspace(
    workspace_tmp_path: Path,
) -> None:
    with pytest.raises(WorkspacePathError, match="escapes workspace root"):
        resolve_workspace_path(workspace_tmp_path, "../outside.json")
