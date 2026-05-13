from collections.abc import Generator
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

import pytest
from opennavier.openfoam.init_case import create_cavity_case
from opennavier.openfoam.solver_compatibility import check_solver_compatibility
from opennavier_core.diagnostics import DiagnosticStatus


@pytest.fixture
def case_tmp_path() -> Generator[Path, None, None]:
    path = Path(".tmp") / f"solver-compatibility-{uuid4().hex}"
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        rmtree(path, ignore_errors=True)


def test_solver_compatibility_passes_for_cavity_case(case_tmp_path: Path) -> None:
    create_cavity_case(case_tmp_path)

    diagnostics = check_solver_compatibility(
        case_tmp_path,
        solver_family="incompressible_laminar",
        solver="icoFoam",
    )

    assert {diagnostic.status for diagnostic in diagnostics} == {DiagnosticStatus.PASS}
    assert {diagnostic.code for diagnostic in diagnostics} >= {
        "openfoam.solver_compatibility.solver_family",
        "openfoam.solver_compatibility.application",
        "openfoam.solver_compatibility.required_fields",
        "openfoam.solver_compatibility.algorithm",
    }


def test_solver_compatibility_passes_for_duct_case(case_tmp_path: Path) -> None:
    from opennavier.openfoam.init_case import create_duct_pressure_drop_case

    create_duct_pressure_drop_case(case_tmp_path)

    diagnostics = check_solver_compatibility(
        case_tmp_path,
        solver_family="incompressible_laminar",
        solver="simpleFoam",
    )

    assert {diagnostic.status for diagnostic in diagnostics} == {DiagnosticStatus.PASS}


def test_solver_compatibility_fails_for_known_invalid_solver_dictionary_combo(
    case_tmp_path: Path,
) -> None:
    create_cavity_case(case_tmp_path)

    diagnostics = check_solver_compatibility(
        case_tmp_path,
        solver_family="incompressible_laminar",
        solver="simpleFoam",
    )

    assert {
        (diagnostic.status, diagnostic.code)
        for diagnostic in diagnostics
        if diagnostic.status is DiagnosticStatus.FAIL
    } == {
        (DiagnosticStatus.FAIL, "openfoam.solver_compatibility.application"),
        (DiagnosticStatus.FAIL, "openfoam.solver_compatibility.algorithm"),
    }


def test_solver_compatibility_reports_missing_required_fields(case_tmp_path: Path) -> None:
    create_cavity_case(case_tmp_path)
    (case_tmp_path / "0" / "p").unlink()

    diagnostics = check_solver_compatibility(
        case_tmp_path,
        solver_family="incompressible_laminar",
        solver="icoFoam",
    )

    missing = [
        diagnostic
        for diagnostic in diagnostics
        if diagnostic.code == "openfoam.solver_compatibility.required_fields"
    ]
    assert missing[0].status is DiagnosticStatus.FAIL
    assert missing[0].details == {"missing_fields": "p"}
