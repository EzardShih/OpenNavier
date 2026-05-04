from collections.abc import Generator
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

import pytest
from opennavier.cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def case_tmp_path() -> Generator[Path, None, None]:
    path = Path(".tmp") / f"init-{uuid4().hex}"
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        rmtree(path, ignore_errors=True)


def test_init_cavity_creates_minimal_openfoam_case_tree(case_tmp_path: Path) -> None:
    case_path = case_tmp_path / "cavity"

    result = runner.invoke(app, ["init", "cavity", str(case_path)])

    assert result.exit_code == 0
    assert sorted(path.relative_to(case_path).as_posix() for path in case_path.rglob("*")) == [
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


def test_init_cavity_system_dictionaries_include_foamfile_headers(
    case_tmp_path: Path,
) -> None:
    case_path = case_tmp_path / "cavity"

    result = runner.invoke(app, ["init", "cavity", str(case_path)])

    assert result.exit_code == 0
    for relative_path in [
        Path("system/blockMeshDict"),
        Path("system/controlDict"),
        Path("system/fvSchemes"),
        Path("system/fvSolution"),
    ]:
        content = (case_path / relative_path).read_text(encoding="utf-8")
        assert "FoamFile" in content
        assert "class       dictionary;" in content


def test_init_cavity_cli_reports_success(case_tmp_path: Path) -> None:
    case_path = case_tmp_path / "cavity"

    result = runner.invoke(app, ["init", "cavity", str(case_path)])

    assert result.exit_code == 0
    assert f"Created cavity case: {case_path}" in result.output


def test_init_cavity_refuses_to_overwrite_non_empty_path(case_tmp_path: Path) -> None:
    case_path = case_tmp_path / "cavity"
    case_path.mkdir()
    existing_file = case_path / "notes.txt"
    existing_file.write_text("keep me\n", encoding="utf-8")

    result = runner.invoke(app, ["init", "cavity", str(case_path)])

    assert result.exit_code == 1
    assert "Refusing to overwrite non-empty path" in result.output
    assert existing_file.read_text(encoding="utf-8") == "keep me\n"
    assert not (case_path / "system").exists()


def test_init_cavity_refuses_to_overwrite_existing_file_path(
    case_tmp_path: Path,
) -> None:
    case_path = case_tmp_path / "cavity"
    case_path.write_text("keep me\n", encoding="utf-8")

    result = runner.invoke(app, ["init", "cavity", str(case_path)])

    assert result.exit_code == 1
    assert "Refusing to overwrite existing path" in result.output
    assert case_path.read_text(encoding="utf-8") == "keep me\n"


def test_init_cavity_force_overwrites_generated_cavity_case(case_tmp_path: Path) -> None:
    case_path = case_tmp_path / "cavity"
    first_result = runner.invoke(app, ["init", "cavity", str(case_path)])

    second_result = runner.invoke(app, ["init", "cavity", str(case_path), "--force"])

    assert first_result.exit_code == 0
    assert second_result.exit_code == 0
    assert (case_path / "system" / "controlDict").is_file()


def test_init_cavity_force_allows_empty_target_directory(case_tmp_path: Path) -> None:
    case_path = case_tmp_path / "cavity"
    case_path.mkdir()

    result = runner.invoke(app, ["init", "cavity", str(case_path), "--force"])

    assert result.exit_code == 0
    assert (case_path / "system" / "controlDict").is_file()


def test_init_cavity_force_refuses_current_working_directory(
    case_tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    existing_file = (case_tmp_path / "notes.txt").resolve()
    existing_file.write_text("keep me\n", encoding="utf-8")
    monkeypatch.chdir(case_tmp_path)

    result = runner.invoke(app, ["init", "cavity", ".", "--force"])

    assert result.exit_code == 1
    assert "Refusing to force-overwrite protected path" in result.output
    assert existing_file.read_text(encoding="utf-8") == "keep me\n"


def test_init_cavity_force_refuses_repository_root(case_tmp_path: Path) -> None:
    existing_file = Path("pyproject.toml")

    result = runner.invoke(app, ["init", "cavity", ".", "--force"])

    assert result.exit_code == 1
    assert "Refusing to force-overwrite protected path" in result.output
    assert existing_file.is_file()


def test_init_cavity_force_refuses_populated_unknown_directory(case_tmp_path: Path) -> None:
    case_path = case_tmp_path / "project"
    case_path.mkdir()
    existing_file = case_path / "notes.txt"
    existing_file.write_text("keep me\n", encoding="utf-8")

    result = runner.invoke(app, ["init", "cavity", str(case_path), "--force"])

    assert result.exit_code == 1
    assert "Refusing to force-overwrite unknown non-empty path" in result.output
    assert existing_file.read_text(encoding="utf-8") == "keep me\n"
    assert not (case_path / "system").exists()


def test_init_cavity_force_refuses_home_directory() -> None:
    result = runner.invoke(app, ["init", "cavity", str(Path.home()), "--force"])

    assert result.exit_code == 1
    assert "Refusing to force-overwrite protected path" in result.output


def test_init_cavity_force_refuses_existing_file_path(case_tmp_path: Path) -> None:
    case_path = case_tmp_path / "cavity"
    case_path.write_text("keep me\n", encoding="utf-8")

    result = runner.invoke(app, ["init", "cavity", str(case_path), "--force"])

    assert result.exit_code == 1
    assert "Refusing to overwrite existing path" in result.output
    assert case_path.read_text(encoding="utf-8") == "keep me\n"
