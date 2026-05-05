import sys
from collections.abc import Generator
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

import pytest
from opennavier.openfoam.runner import run_local_solver


@pytest.fixture
def runner_tmp_path() -> Generator[Path, None, None]:
    path = Path(".tmp") / f"runner-{uuid4().hex}"
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        rmtree(path, ignore_errors=True)


def test_run_local_solver_executes_command_in_case_directory_and_writes_default_log(
    runner_tmp_path: Path,
) -> None:
    case_path = runner_tmp_path / "case"
    case_path.mkdir()

    result = run_local_solver(
        [
            sys.executable,
            "-c",
            (
                "from pathlib import Path; "
                "print(Path.cwd().name); "
                "print('solver stderr', file=__import__('sys').stderr)"
            ),
        ],
        case_path,
    )

    assert result.command == [sys.executable, "-c", result.command[2]]
    assert result.case_path == case_path
    assert result.return_code == 0
    assert result.succeeded is True
    assert result.stdout == "case\n"
    assert result.stderr == "solver stderr\n"
    assert result.log_path == case_path / f"log.{Path(sys.executable).name}"
    assert result.log_path.read_text(encoding="utf-8") == (
        "$ "
        + " ".join(result.command)
        + "\n\n"
        + "[stdout]\ncase\n\n"
        + "[stderr]\nsolver stderr\n"
    )


def test_run_local_solver_writes_caller_provided_log_path(runner_tmp_path: Path) -> None:
    case_path = runner_tmp_path / "case"
    case_path.mkdir()
    log_path = runner_tmp_path / "logs" / "solver.log"

    result = run_local_solver(
        [sys.executable, "-c", "print('custom log')"],
        case_path,
        log_path=log_path,
    )

    assert result.succeeded is True
    assert result.log_path == log_path
    assert log_path.read_text(encoding="utf-8").endswith("[stdout]\ncustom log\n")


def test_run_local_solver_returns_failure_result_for_nonzero_exit(
    runner_tmp_path: Path,
) -> None:
    case_path = runner_tmp_path / "case"
    case_path.mkdir()

    result = run_local_solver(
        [
            sys.executable,
            "-c",
            "import sys; print('bad input', file=sys.stderr); raise SystemExit(7)",
        ],
        case_path,
    )

    assert result.succeeded is False
    assert result.return_code == 7
    assert result.stderr == "bad input\n"
    assert "bad input" in result.log_path.read_text(encoding="utf-8")


def test_run_local_solver_returns_clear_failure_for_missing_executable(
    runner_tmp_path: Path,
) -> None:
    case_path = runner_tmp_path / "case"
    case_path.mkdir()

    result = run_local_solver(["definitely-missing-openfoam-command"], case_path)

    assert result.succeeded is False
    assert result.return_code is None
    assert result.stdout == ""
    assert "Executable not found: definitely-missing-openfoam-command" in result.stderr
    assert result.log_path == case_path / "log.definitely-missing-openfoam-command"
    assert "Executable not found" in result.log_path.read_text(encoding="utf-8")


def test_run_local_solver_rejects_bare_string_command(runner_tmp_path: Path) -> None:
    case_path = runner_tmp_path / "case"
    case_path.mkdir()

    with pytest.raises(TypeError, match="command must be a sequence of arguments"):
        run_local_solver("definitely-missing-openfoam-command", case_path)  # type: ignore[arg-type]

    assert not (case_path / "log.d").exists()


def test_run_local_solver_rejects_missing_case_path_without_creating_it(
    runner_tmp_path: Path,
) -> None:
    case_path = runner_tmp_path / "missing-case"

    with pytest.raises(NotADirectoryError, match="Case path is not a directory"):
        run_local_solver([sys.executable, "-c", "print('should not run')"], case_path)

    assert not case_path.exists()
