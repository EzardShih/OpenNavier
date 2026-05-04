import subprocess
import sys
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
    path = Path(".tmp") / f"cli-{uuid4().hex}"
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


def test_help_shows_core_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "check" in result.output
    assert "doctor" in result.output
    assert "report" in result.output


def test_module_entry_point_shows_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "opennavier.cli", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "check" in result.stdout
    assert "doctor" in result.stdout
    assert "report" in result.stdout


def test_check_returns_success_for_valid_case(case_tmp_path: Path) -> None:
    create_valid_case(case_tmp_path)

    result = runner.invoke(app, ["check", str(case_tmp_path)])

    assert result.exit_code == 0
    assert "PASS" in result.output
    assert "Case structure checks passed" in result.output


def test_check_returns_failure_for_invalid_case(case_tmp_path: Path) -> None:
    result = runner.invoke(app, ["check", str(case_tmp_path)])

    assert result.exit_code == 1
    assert "FAIL" in result.output
    assert "Missing required OpenFOAM directory: 0" in result.output


def test_check_returns_failure_for_malformed_required_system_dictionary(
    case_tmp_path: Path,
) -> None:
    create_valid_case(case_tmp_path)
    (case_tmp_path / "system" / "fvSchemes").write_text(
        "ddtSchemes {}\n", encoding="utf-8"
    )

    result = runner.invoke(app, ["check", str(case_tmp_path)])

    assert result.exit_code == 1
    assert "FAIL" in result.output
    assert "openfoam.dictionary_header.system_fvSchemes" in result.output


def test_doctor_returns_nonzero_for_invalid_case(case_tmp_path: Path) -> None:
    result = runner.invoke(app, ["doctor", str(case_tmp_path)])

    assert result.exit_code == 1
    assert "Likely issues" in result.output
    assert "OpenFOAM case structure is incomplete" in result.output


def test_report_writes_markdown_report(case_tmp_path: Path) -> None:
    case_path = case_tmp_path / "case"
    case_path.mkdir()
    output_path = case_tmp_path / "report.md"

    result = runner.invoke(app, ["report", str(case_path), "--output", str(output_path)])

    assert result.exit_code == 1
    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "# OpenNavier Case Report" in content
    assert f"Inspected case: `{case_path.resolve()}`" in content
    assert "No cloud upload occurred" in content
    assert "openfoam.required_directory.0" in content


def test_report_includes_malformed_system_dictionary_header_diagnostic(
    case_tmp_path: Path,
) -> None:
    case_path = case_tmp_path / "case"
    create_valid_case(case_path)
    (case_path / "system" / "fvSchemes").write_text(
        "divSchemes {}\n", encoding="utf-8"
    )
    output_path = case_tmp_path / "report.md"

    result = runner.invoke(app, ["report", str(case_path), "--output", str(output_path)])

    assert result.exit_code == 1
    content = output_path.read_text(encoding="utf-8")
    assert "openfoam.dictionary_header.system_fvSchemes" in content
