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
        "openfoam.dictionary_header.system_controlDict",
        "openfoam.dictionary_header.system_fvSchemes",
        "openfoam.dictionary_header.system_fvSolution",
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


def test_valid_required_system_dictionaries_containing_foamfile_pass(
    case_tmp_path: Path,
) -> None:
    create_valid_case(case_tmp_path)

    diagnostics = validate_case_structure(case_tmp_path)

    header_diagnostics = [
        diagnostic
        for diagnostic in diagnostics
        if diagnostic.code.startswith("openfoam.dictionary_header.")
    ]
    assert [(diagnostic.code, diagnostic.status) for diagnostic in header_diagnostics] == [
        ("openfoam.dictionary_header.system_controlDict", DiagnosticStatus.PASS),
        ("openfoam.dictionary_header.system_fvSchemes", DiagnosticStatus.PASS),
        ("openfoam.dictionary_header.system_fvSolution", DiagnosticStatus.PASS),
    ]


def test_malformed_existing_system_fvschemes_without_foamfile_fails(
    case_tmp_path: Path,
) -> None:
    create_valid_case(case_tmp_path)
    (case_tmp_path / "system" / "fvSchemes").write_text(
        "ddtSchemes {}\n",
        encoding="utf-8",
    )

    diagnostics = validate_case_structure(case_tmp_path)

    failures = [
        diagnostic for diagnostic in diagnostics if diagnostic.status is DiagnosticStatus.FAIL
    ]
    assert [failure.code for failure in failures] == [
        "openfoam.dictionary_header.system_fvSchemes"
    ]


def test_missing_system_file_only_reports_missing_file_diagnostic(
    case_tmp_path: Path,
) -> None:
    create_valid_case(case_tmp_path)
    (case_tmp_path / "system" / "fvSchemes").unlink()

    diagnostics = validate_case_structure(case_tmp_path)

    failures = [
        diagnostic for diagnostic in diagnostics if diagnostic.status is DiagnosticStatus.FAIL
    ]
    assert [failure.code for failure in failures] == [
        "openfoam.required_file.system_fvSchemes"
    ]
    assert "openfoam.dictionary_header.system_fvSchemes" not in {
        diagnostic.code for diagnostic in diagnostics
    }


def test_dictionary_header_validation_does_not_edit_invalid_files(
    case_tmp_path: Path,
) -> None:
    create_valid_case(case_tmp_path)
    path = case_tmp_path / "system" / "fvSchemes"
    original_content = "ddtSchemes {}\n"
    path.write_text(original_content, encoding="utf-8")

    validate_case_structure(case_tmp_path)

    assert path.read_text(encoding="utf-8") == original_content


def test_dictionary_header_requires_foamfile_block(
    case_tmp_path: Path,
) -> None:
    create_valid_case(case_tmp_path)
    (case_tmp_path / "system" / "fvSchemes").write_text(
        "// FoamFile header still needs to be added\n"
        'note "FoamFile appears in plain text only";\n',
        encoding="utf-8",
    )

    diagnostics = validate_case_structure(case_tmp_path)

    failures = [
        diagnostic for diagnostic in diagnostics if diagnostic.status is DiagnosticStatus.FAIL
    ]
    assert [failure.code for failure in failures] == [
        "openfoam.dictionary_header.system_fvSchemes"
    ]


def test_dictionary_header_ignores_foamfile_block_inside_quoted_text(
    case_tmp_path: Path,
) -> None:
    create_valid_case(case_tmp_path)
    (case_tmp_path / "system" / "fvSchemes").write_text(
        'note "FoamFile {";\n',
        encoding="utf-8",
    )

    diagnostics = validate_case_structure(case_tmp_path)

    failures = [
        diagnostic for diagnostic in diagnostics if diagnostic.status is DiagnosticStatus.FAIL
    ]
    assert [failure.code for failure in failures] == [
        "openfoam.dictionary_header.system_fvSchemes"
    ]


def test_dictionary_header_allows_line_comments_before_foamfile_block(
    case_tmp_path: Path,
) -> None:
    create_valid_case(case_tmp_path)
    (case_tmp_path / "system" / "fvSchemes").write_text(
        "// OpenFOAM banner comment\n"
        "// generated by a local template\n"
        "FoamFile {}\n",
        encoding="utf-8",
    )

    diagnostics = validate_case_structure(case_tmp_path)

    header_diagnostics = [
        diagnostic
        for diagnostic in diagnostics
        if diagnostic.code.startswith("openfoam.dictionary_header.")
    ]
    assert [(diagnostic.code, diagnostic.status) for diagnostic in header_diagnostics] == [
        ("openfoam.dictionary_header.system_controlDict", DiagnosticStatus.PASS),
        ("openfoam.dictionary_header.system_fvSchemes", DiagnosticStatus.PASS),
        ("openfoam.dictionary_header.system_fvSolution", DiagnosticStatus.PASS),
    ]


def test_unreadable_dictionary_text_is_reported_as_diagnostic(
    case_tmp_path: Path,
) -> None:
    create_valid_case(case_tmp_path)
    (case_tmp_path / "system" / "fvSchemes").write_bytes(b"\xff\xfe\x00")

    diagnostics = validate_case_structure(case_tmp_path)

    failures = [
        diagnostic for diagnostic in diagnostics if diagnostic.status is DiagnosticStatus.FAIL
    ]
    assert [failure.code for failure in failures] == [
        "openfoam.dictionary_header.system_fvSchemes"
    ]
    assert failures[0].details["read_error"] == "UnicodeDecodeError"
