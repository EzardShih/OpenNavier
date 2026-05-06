from collections.abc import Generator
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

import pytest
from opennavier.mcp.case_init_tools import case_init_cavity


def _workspace_path() -> Path:
    return Path(".tmp") / f"mcp-case-init-cavity-{uuid4().hex}"


def _diagnostic_codes(result: dict[str, object]) -> set[str]:
    diagnostics = result["diagnostics"]
    assert isinstance(diagnostics, list)
    return {diagnostic["code"] for diagnostic in diagnostics}


def _diagnostic_statuses(result: dict[str, object]) -> set[str]:
    diagnostics = result["diagnostics"]
    assert isinstance(diagnostics, list)
    return {diagnostic["status"] for diagnostic in diagnostics}


def _provenance() -> dict[str, object]:
    return {"producer": "case_init_cavity", "inputs": []}


def _next_actions(result: dict[str, object]) -> list[str]:
    next_actions = result["next_actions"]
    assert isinstance(next_actions, list)
    return next_actions


def _changed_paths(result: dict[str, object]) -> list[str]:
    changed_paths = result["changed_paths"]
    assert isinstance(changed_paths, list)
    return changed_paths


def _expected_changed_paths(case_path: str = "case") -> list[str]:
    return [
        f"{case_path}/0/U",
        f"{case_path}/0/p",
        f"{case_path}/constant/transportProperties",
        f"{case_path}/system/blockMeshDict",
        f"{case_path}/system/controlDict",
        f"{case_path}/system/fvSchemes",
        f"{case_path}/system/fvSolution",
    ]


@pytest.fixture
def workspace_tmp_path() -> Generator[Path, None, None]:
    path = _workspace_path()
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        rmtree(path, ignore_errors=True)


def test_case_init_cavity_creates_case_inside_workspace(
    workspace_tmp_path: Path,
) -> None:
    result = case_init_cavity(str(workspace_tmp_path), "case")

    assert _changed_paths(result) == _expected_changed_paths()
    assert result["provenance"] == _provenance()
    assert "case_validate_structure" in _next_actions(result)
    assert _diagnostic_statuses(result) == {"PASS"}
    assert "openfoam.required_directory.0" in _diagnostic_codes(result)
    for relative_path in _expected_changed_paths():
        assert (workspace_tmp_path / relative_path).is_file()
    assert not (workspace_tmp_path / "simulation.onv.json").exists()


def test_case_init_cavity_rejects_case_path_that_escapes_workspace(
    workspace_tmp_path: Path,
) -> None:
    result = case_init_cavity(str(workspace_tmp_path), "../outside")

    assert _changed_paths(result) == []
    assert result["provenance"] == _provenance()
    assert "case_validate_structure" in _next_actions(result)
    assert _diagnostic_statuses(result) == {"FAIL"}
    assert _diagnostic_codes(result) == {"mcp.workspace_path.invalid"}
    assert not (workspace_tmp_path.parent / "outside").exists()


def test_case_init_cavity_refuses_to_overwrite_non_empty_case_path(
    workspace_tmp_path: Path,
) -> None:
    case_path = workspace_tmp_path / "case"
    case_path.mkdir()
    existing_file = case_path / "notes.txt"
    existing_file.write_text("keep me\n", encoding="utf-8")

    result = case_init_cavity(str(workspace_tmp_path), "case")

    assert _changed_paths(result) == []
    assert result["provenance"] == _provenance()
    assert "case_validate_structure" in _next_actions(result)
    assert _diagnostic_statuses(result) == {"FAIL"}
    assert _diagnostic_codes(result) == {"mcp.case_init_cavity.refused"}
    assert existing_file.read_text(encoding="utf-8") == "keep me\n"
    assert not (case_path / "system").exists()
