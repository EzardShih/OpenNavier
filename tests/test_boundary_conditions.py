import json
from collections.abc import Generator
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

import pytest
from opennavier.cli.main import app
from opennavier.openfoam.boundary_conditions import diagnose_boundary_conditions
from opennavier.openfoam.init_case import create_cavity_case
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def case_tmp_path() -> Generator[Path, None, None]:
    path = Path(".tmp") / f"boundary-conditions-{uuid4().hex}"
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        rmtree(path, ignore_errors=True)


def test_valid_cavity_boundary_conditions_pass(case_tmp_path: Path) -> None:
    create_cavity_case(case_tmp_path)

    diagnostics = diagnose_boundary_conditions(case_tmp_path)

    assert len(diagnostics) == 1
    assert diagnostics[0].status == "PASS"
    assert diagnostics[0].code == "openfoam.boundary_conditions.valid"
    assert diagnostics[0].details["patches"] == "fixedWalls,frontAndBack,movingWall"
    assert diagnostics[0].details["fields"] == "U,p"


def test_missing_boundary_condition_files_warn(case_tmp_path: Path) -> None:
    create_cavity_case(case_tmp_path)
    (case_tmp_path / "0" / "p").unlink()

    diagnostics = diagnose_boundary_conditions(case_tmp_path)

    assert len(diagnostics) == 1
    assert diagnostics[0].status == "WARN"
    assert diagnostics[0].code == "openfoam.boundary_conditions.missing_optional"
    assert diagnostics[0].details["missing_files"] == "0/p"


def test_boundary_field_patch_mismatch_fails(case_tmp_path: Path) -> None:
    create_cavity_case(case_tmp_path)
    u_path = case_tmp_path / "0" / "U"
    u_path.write_text(
        u_path.read_text(encoding="utf-8").replace("movingWall", "lid", 1),
        encoding="utf-8",
        newline="\n",
    )

    diagnostics = diagnose_boundary_conditions(case_tmp_path)

    assert len(diagnostics) == 1
    assert diagnostics[0].status == "FAIL"
    assert diagnostics[0].code == "openfoam.boundary_conditions.mismatch"
    assert diagnostics[0].details["0/U.missing_patches"] == "movingWall"
    assert diagnostics[0].details["0/U.extra_patches"] == "lid"


def test_doctor_includes_boundary_condition_failures(case_tmp_path: Path) -> None:
    create_cavity_case(case_tmp_path)
    p_path = case_tmp_path / "0" / "p"
    p_path.write_text(
        p_path.read_text(encoding="utf-8").replace("frontAndBack", "frontOnly", 1),
        encoding="utf-8",
        newline="\n",
    )

    result = runner.invoke(app, ["doctor", str(case_tmp_path), "--format", "json"])

    assert result.exit_code == 1
    diagnostics = json.loads(result.output)
    boundary_diagnostic = next(
        diagnostic
        for diagnostic in diagnostics
        if diagnostic["code"] == "openfoam.boundary_conditions.mismatch"
    )
    assert boundary_diagnostic["status"] == "FAIL"
    assert boundary_diagnostic["details"]["0/p.missing_patches"] == "frontAndBack"
    assert boundary_diagnostic["details"]["0/p.extra_patches"] == "frontOnly"
