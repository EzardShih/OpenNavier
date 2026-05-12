from collections.abc import Generator
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

import pytest
from opennavier.openfoam.boundary_conditions import diagnose_boundary_conditions
from opennavier.openfoam.case_build_writer import write_case_build_spec
from opennavier.openfoam.case_structure import validate_case_structure
from opennavier.openfoam.init_case import CasePathNotEmptyError
from opennavier_core.case_build_spec import CaseBuildSpec
from opennavier_core.diagnostics import DiagnosticStatus
from test_case_build_spec import minimal_duct_case_build_payload


@pytest.fixture
def workspace_tmp_path() -> Generator[Path, None, None]:
    path = Path(".tmp") / f"case-build-writer-{uuid4().hex}"
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        rmtree(path, ignore_errors=True)


def test_case_build_writer_generates_valid_duct_case(
    workspace_tmp_path: Path,
) -> None:
    spec = CaseBuildSpec.model_validate(minimal_duct_case_build_payload())

    case_path = write_case_build_spec(spec, workspace_tmp_path)

    assert case_path == (
        workspace_tmp_path / "runs" / "duct_pressure_drop" / "case"
    ).resolve()
    diagnostics = [
        *validate_case_structure(case_path),
        *diagnose_boundary_conditions(case_path),
    ]
    assert {diagnostic.status for diagnostic in diagnostics} == {DiagnosticStatus.PASS}


def test_generated_duct_case_matches_committed_example(workspace_tmp_path: Path) -> None:
    spec = CaseBuildSpec.model_validate(minimal_duct_case_build_payload())
    generated_case = write_case_build_spec(spec, workspace_tmp_path)
    example_case = Path("examples") / "duct-pressure-drop"

    generated_files = {
        path.relative_to(generated_case): path.read_text(encoding="utf-8")
        for path in generated_case.rglob("*")
        if path.is_file()
    }
    example_files = {
        path.relative_to(example_case): path.read_text(encoding="utf-8")
        for path in example_case.rglob("*")
        if path.is_file()
    }

    assert generated_files == example_files


def test_generated_duct_case_includes_simplefoam_laminar_turbulence_properties(
    workspace_tmp_path: Path,
) -> None:
    spec = CaseBuildSpec.model_validate(minimal_duct_case_build_payload())

    generated_case = write_case_build_spec(spec, workspace_tmp_path)

    turbulence_properties = generated_case / "constant" / "turbulenceProperties"
    assert turbulence_properties.is_file()
    content = turbulence_properties.read_text(encoding="utf-8")
    assert "simulationType  laminar;" in content


def test_case_build_writer_preserves_overwrite_guard_for_duct(
    workspace_tmp_path: Path,
) -> None:
    spec = CaseBuildSpec.model_validate(minimal_duct_case_build_payload())
    write_case_build_spec(spec, workspace_tmp_path)

    with pytest.raises(CasePathNotEmptyError, match="Refusing to overwrite"):
        write_case_build_spec(spec, workspace_tmp_path)
