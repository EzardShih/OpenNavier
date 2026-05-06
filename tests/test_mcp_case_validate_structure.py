import json
from collections.abc import Generator
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

import pytest
from opennavier.mcp.case_validation_tools import case_validate_structure


@pytest.fixture
def workspace_tmp_path() -> Generator[Path, None, None]:
    path = Path(".tmp") / f"mcp-case-validation-{uuid4().hex}"
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        rmtree(path, ignore_errors=True)


def create_valid_case(case_path: Path) -> None:
    for directory in ("0", "constant", "system"):
        (case_path / directory).mkdir(parents=True, exist_ok=True)
    for filename in ("controlDict", "fvSchemes", "fvSolution"):
        (case_path / "system" / filename).write_text("FoamFile {}\n", encoding="utf-8")


def create_symlink(link_path: Path, target_path: Path, *, is_directory: bool = False) -> None:
    link_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        link_path.symlink_to(target_path.resolve(), target_is_directory=is_directory)
    except (NotImplementedError, OSError) as error:
        pytest.skip(f"symlink creation is unavailable: {error}")


def test_case_validate_structure_returns_serializable_summary(
    workspace_tmp_path: Path,
) -> None:
    create_valid_case(workspace_tmp_path / "case")

    result = case_validate_structure(str(workspace_tmp_path))

    assert result["case_path"] == "case"
    assert result["summary"] == {
        "total": 9,
        "passed": 9,
        "failed": 0,
        "warnings": 0,
    }
    assert len(result["diagnostics"]) == 9
    assert {diagnostic["status"] for diagnostic in result["diagnostics"]} == {"PASS"}
    json.dumps(result)


def test_case_validate_structure_reports_missing_case_paths(
    workspace_tmp_path: Path,
) -> None:
    result = case_validate_structure(str(workspace_tmp_path), "case")

    assert result["case_path"] == "case"
    assert result["summary"] == {
        "total": 6,
        "passed": 0,
        "failed": 6,
        "warnings": 0,
    }
    assert [diagnostic["code"] for diagnostic in result["diagnostics"]] == [
        "openfoam.required_directory.0",
        "openfoam.required_directory.constant",
        "openfoam.required_directory.system",
        "openfoam.required_file.system_controlDict",
        "openfoam.required_file.system_fvSchemes",
        "openfoam.required_file.system_fvSolution",
    ]


def test_case_validate_structure_rejects_paths_that_escape_workspace(
    workspace_tmp_path: Path,
) -> None:
    outside_case = workspace_tmp_path.parent / f"outside-case-{uuid4().hex}"
    create_valid_case(outside_case)
    try:
        result = case_validate_structure(str(workspace_tmp_path), f"../{outside_case.name}")
    finally:
        rmtree(outside_case, ignore_errors=True)

    assert result == {
        "case_path": f"../{outside_case.name}",
        "diagnostics": [
            {
                "status": "FAIL",
                "code": "mcp.workspace_path.invalid",
                "message": f"Path escapes workspace root: ../{outside_case.name}",
                "path": f"../{outside_case.name}",
                "details": {},
            }
        ],
        "summary": {
            "total": 1,
            "passed": 0,
            "failed": 1,
            "warnings": 0,
        },
    }


def test_case_validate_structure_rejects_system_symlink_escape(
    workspace_tmp_path: Path,
) -> None:
    case_path = workspace_tmp_path / "case"
    outside_case = workspace_tmp_path.parent / f"outside-system-{uuid4().hex}"
    create_valid_case(case_path)
    create_valid_case(outside_case)
    rmtree(case_path / "system")

    try:
        create_symlink(case_path / "system", outside_case / "system", is_directory=True)

        result = case_validate_structure(str(workspace_tmp_path), "case")
    finally:
        rmtree(outside_case, ignore_errors=True)

    assert result["case_path"] == "case"
    assert result["summary"] == {
        "total": 1,
        "passed": 0,
        "failed": 1,
        "warnings": 0,
    }
    assert result["diagnostics"] == [
        {
            "status": "FAIL",
            "code": "mcp.workspace_path.invalid",
            "message": "Path escapes workspace root: case/system",
            "path": "case/system",
            "details": {},
        }
    ]


def test_case_validate_structure_rejects_required_dictionary_symlink_escape(
    workspace_tmp_path: Path,
) -> None:
    case_path = workspace_tmp_path / "case"
    outside_case = workspace_tmp_path.parent / f"outside-dictionary-{uuid4().hex}"
    create_valid_case(case_path)
    create_valid_case(outside_case)
    (case_path / "system" / "controlDict").unlink()

    try:
        create_symlink(
            case_path / "system" / "controlDict",
            outside_case / "system" / "controlDict",
        )

        result = case_validate_structure(str(workspace_tmp_path), "case")
    finally:
        rmtree(outside_case, ignore_errors=True)

    assert result["case_path"] == "case"
    assert result["summary"] == {
        "total": 1,
        "passed": 0,
        "failed": 1,
        "warnings": 0,
    }
    assert result["diagnostics"] == [
        {
            "status": "FAIL",
            "code": "mcp.workspace_path.invalid",
            "message": "Path escapes workspace root: case/system/controlDict",
            "path": "case/system/controlDict",
            "details": {},
        }
    ]
