import json
from collections.abc import Generator
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

import pytest
from opennavier.mcp.case_build_tools import (
    case_build_dry_run,
    case_build_validate,
    case_build_write,
)
from opennavier_core.case_build_spec import CaseBuildSpec
from test_case_build_spec import minimal_cavity_case_build_payload


@pytest.fixture
def workspace_tmp_path() -> Generator[Path, None, None]:
    path = Path("tests") / ".tmp" / f"mcp-case-build-{uuid4().hex}"
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        rmtree(path, ignore_errors=True)


def test_case_build_validate_accepts_payload_inside_workspace(
    workspace_tmp_path: Path,
) -> None:
    result = case_build_validate(
        workspace_root=str(workspace_tmp_path),
        build_spec=minimal_cavity_case_build_payload(),
    )

    assert result["valid"] is True
    assert result["errors"] == []
    assert result["source"] == "payload"
    assert result["case_build_spec"]["case_path"] == "runs/lid_driven_cavity/case"


def test_case_build_validate_reads_json_spec_inside_workspace(
    workspace_tmp_path: Path,
) -> None:
    spec_path = workspace_tmp_path / "specs" / "case-build.json"
    spec_path.parent.mkdir()
    spec_path.write_text(
        json.dumps(minimal_cavity_case_build_payload()),
        encoding="utf-8",
    )

    result = case_build_validate(workspace_root=str(workspace_tmp_path))

    assert result["valid"] is True
    assert result["source"] == "specs/case-build.json"


def test_case_build_validate_rejects_paths_that_escape_workspace(
    workspace_tmp_path: Path,
) -> None:
    payload = minimal_cavity_case_build_payload()
    payload["case_path"] = "../outside/case"

    result = case_build_validate(workspace_root=str(workspace_tmp_path), build_spec=payload)

    assert result["valid"] is False
    assert result["case_build_spec"] is None
    assert result["errors"]
    assert result["errors"][0]["type"] == "validation_error"
    assert "case_path" in result["errors"][0]["message"]


def test_case_build_dry_run_returns_planned_operations_without_writing(
    workspace_tmp_path: Path,
) -> None:
    result = case_build_dry_run(
        workspace_root=str(workspace_tmp_path),
        build_spec=minimal_cavity_case_build_payload(),
    )

    assert result["valid"] is True
    assert result["dry_run"]["case_path"] == "runs/lid_driven_cavity/case"
    assert result["dry_run"]["file_operations"][0] == {
        "action": "write",
        "path": "runs/lid_driven_cavity/case/0/U",
        "writer_operation_id": "write_case_tree",
    }
    assert not (workspace_tmp_path / "runs" / "lid_driven_cavity" / "case").exists()


def test_case_build_write_creates_case_and_refuses_unapproved_overwrite(
    workspace_tmp_path: Path,
) -> None:
    first_result = case_build_write(
        workspace_root=str(workspace_tmp_path),
        build_spec=minimal_cavity_case_build_payload(),
    )

    assert first_result["changed_paths"] == [
        "runs/lid_driven_cavity/case/0/U",
        "runs/lid_driven_cavity/case/0/p",
        "runs/lid_driven_cavity/case/constant/transportProperties",
        "runs/lid_driven_cavity/case/system/blockMeshDict",
        "runs/lid_driven_cavity/case/system/controlDict",
        "runs/lid_driven_cavity/case/system/fvSchemes",
        "runs/lid_driven_cavity/case/system/fvSolution",
    ]
    assert all(diagnostic["status"] == "PASS" for diagnostic in first_result["diagnostics"])
    assert "openfoam.required_directory.0" in {
        diagnostic["code"] for diagnostic in first_result["diagnostics"]
    }
    assert "openfoam.boundary_conditions.valid" in {
        diagnostic["code"] for diagnostic in first_result["diagnostics"]
    }

    second_result = case_build_write(
        workspace_root=str(workspace_tmp_path),
        build_spec=minimal_cavity_case_build_payload(),
    )

    assert second_result["changed_paths"] == []
    assert {diagnostic["code"] for diagnostic in second_result["diagnostics"]} == {
        "mcp.case_build_write.refused"
    }


def test_case_build_write_persists_payload_spec_at_requested_path(
    workspace_tmp_path: Path,
) -> None:
    result = case_build_write(
        workspace_root=str(workspace_tmp_path),
        build_spec_path="runs/lid_driven_cavity/case-build.json",
        build_spec=minimal_cavity_case_build_payload(),
        persist_build_spec=True,
    )

    assert "runs/lid_driven_cavity/case-build.json" in result["changed_paths"]
    persisted = json.loads(
        (workspace_tmp_path / "runs" / "lid_driven_cavity" / "case-build.json").read_text(
            encoding="utf-8"
        )
    )
    assert persisted == CaseBuildSpec.model_validate(
        minimal_cavity_case_build_payload()
    ).model_dump(mode="json")


def test_case_build_write_refuses_persisted_spec_path_that_collides_with_case_file(
    workspace_tmp_path: Path,
) -> None:
    result = case_build_write(
        workspace_root=str(workspace_tmp_path),
        build_spec_path="runs/lid_driven_cavity/case/system/controlDict",
        build_spec=minimal_cavity_case_build_payload(),
        persist_build_spec=True,
    )

    assert result["changed_paths"] == []
    assert result["diagnostics"] == [
        {
            "status": "FAIL",
            "code": "mcp.case_build_write.refused",
            "message": (
                "Refusing to persist case-build spec over generated case file: "
                "runs/lid_driven_cavity/case/system/controlDict"
            ),
            "path": "runs/lid_driven_cavity/case",
            "details": {},
        }
    ]
    assert not (workspace_tmp_path / "runs" / "lid_driven_cavity" / "case").exists()


def test_case_build_write_force_refuses_to_overwrite_existing_persisted_spec(
    workspace_tmp_path: Path,
) -> None:
    existing = workspace_tmp_path / "README.md"
    existing.write_text("existing project documentation\n", encoding="utf-8")

    result = case_build_write(
        workspace_root=str(workspace_tmp_path),
        build_spec_path="README.md",
        build_spec=minimal_cavity_case_build_payload(),
        force=True,
        persist_build_spec=True,
    )

    assert result["changed_paths"] == []
    assert result["diagnostics"] == [
        {
            "status": "FAIL",
            "code": "mcp.case_build_write.refused",
            "message": "Refusing to overwrite existing case-build spec: README.md",
            "path": "runs/lid_driven_cavity/case",
            "details": {},
        }
    ]
    assert existing.read_text(encoding="utf-8") == "existing project documentation\n"
    assert not (workspace_tmp_path / "runs" / "lid_driven_cavity" / "case").exists()


def test_case_build_write_refuses_persisted_spec_path_with_file_parent_before_writing(
    workspace_tmp_path: Path,
) -> None:
    (workspace_tmp_path / "specs").write_text("not a directory\n", encoding="utf-8")

    result = case_build_write(
        workspace_root=str(workspace_tmp_path),
        build_spec_path="specs/case-build.json",
        build_spec=minimal_cavity_case_build_payload(),
        persist_build_spec=True,
    )

    assert result["changed_paths"] == []
    assert result["diagnostics"] == [
        {
            "status": "FAIL",
            "code": "mcp.case_build_write.refused",
            "message": (
                "Refusing to persist case-build spec because parent is not a "
                "directory: specs"
            ),
            "path": "runs/lid_driven_cavity/case",
            "details": {},
        }
    ]
    assert not (workspace_tmp_path / "runs" / "lid_driven_cavity" / "case").exists()


def test_case_build_write_refuses_persisted_spec_path_that_would_be_case_directory(
    workspace_tmp_path: Path,
) -> None:
    result = case_build_write(
        workspace_root=str(workspace_tmp_path),
        build_spec_path="runs/lid_driven_cavity/case",
        build_spec=minimal_cavity_case_build_payload(),
        persist_build_spec=True,
    )

    assert result["changed_paths"] == []
    assert result["diagnostics"] == [
        {
            "status": "FAIL",
            "code": "mcp.case_build_write.refused",
            "message": (
                "Refusing to persist case-build spec over generated case directory: "
                "runs/lid_driven_cavity/case"
            ),
            "path": "runs/lid_driven_cavity/case",
            "details": {},
        }
    ]
    assert not (workspace_tmp_path / "runs" / "lid_driven_cavity" / "case").exists()
