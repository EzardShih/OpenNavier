from collections.abc import Generator
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

import pytest
from opennavier.openfoam.case_structure import validate_case_structure
from opennavier_core.diagnostics import DiagnosticStatus


@pytest.fixture
def case_tmp_path() -> Generator[Path, None, None]:
    path = Path(".tmp") / f"case-structure-{uuid4().hex}"
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        rmtree(path, ignore_errors=True)


def create_valid_case(case_path: Path) -> None:
    for directory in ["0", "constant", "system"]:
        (case_path / directory).mkdir(parents=True, exist_ok=True)
    for filename in ["controlDict", "fvSchemes", "fvSolution"]:
        (case_path / "system" / filename).write_text("FoamFile {}\n", encoding="utf-8")


def test_valid_openfoam_case_structure_passes(case_tmp_path: Path) -> None:
    create_valid_case(case_tmp_path)

    diagnostics = validate_case_structure(case_tmp_path)

    assert all(diagnostic.status is DiagnosticStatus.PASS for diagnostic in diagnostics)
    assert {diagnostic.code for diagnostic in diagnostics} == {
        "openfoam.required_directory.0",
        "openfoam.required_directory.constant",
        "openfoam.required_directory.system",
        "openfoam.required_file.system_controlDict",
        "openfoam.required_file.system_fvSchemes",
        "openfoam.required_file.system_fvSolution",
    }


def test_missing_openfoam_case_paths_are_reported_without_creating_them(
    case_tmp_path: Path,
) -> None:
    (case_tmp_path / "system").mkdir()
    (case_tmp_path / "system" / "controlDict").write_text("FoamFile {}\n", encoding="utf-8")

    diagnostics = validate_case_structure(case_tmp_path)

    failures = [
        diagnostic for diagnostic in diagnostics if diagnostic.status is DiagnosticStatus.FAIL
    ]
    assert [(failure.code, failure.path) for failure in failures] == [
        ("openfoam.required_directory.0", str(case_tmp_path / "0")),
        ("openfoam.required_directory.constant", str(case_tmp_path / "constant")),
        (
            "openfoam.required_file.system_fvSchemes",
            str(case_tmp_path / "system" / "fvSchemes"),
        ),
        (
            "openfoam.required_file.system_fvSolution",
            str(case_tmp_path / "system" / "fvSolution"),
        ),
    ]
    assert not (case_tmp_path / "0").exists()
    assert not (case_tmp_path / "constant").exists()
