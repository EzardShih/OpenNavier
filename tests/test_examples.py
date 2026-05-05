from pathlib import Path

from opennavier.openfoam.case_structure import validate_case_structure
from opennavier.openfoam.init_case import CAVITY_TEMPLATE_FILES
from opennavier_core.diagnostics import DiagnosticStatus


def test_committed_cavity_example_matches_template_and_validates_read_only() -> None:
    case_path = Path("examples") / "cavity"

    before_paths = sorted(
        path.relative_to(case_path).as_posix() for path in case_path.rglob("*")
    )
    diagnostics = validate_case_structure(case_path)
    after_paths = sorted(
        path.relative_to(case_path).as_posix() for path in case_path.rglob("*")
    )

    assert case_path.is_dir()
    assert all(diagnostic.status is DiagnosticStatus.PASS for diagnostic in diagnostics)
    assert before_paths == after_paths
    assert before_paths == [
        "0",
        "0/U",
        "0/p",
        "constant",
        "constant/transportProperties",
        "system",
        "system/blockMeshDict",
        "system/controlDict",
        "system/fvSchemes",
        "system/fvSolution",
    ]
    assert {
        path.relative_to(case_path): path.read_text(encoding="utf-8")
        for path in case_path.rglob("*")
        if path.is_file()
    } == CAVITY_TEMPLATE_FILES
