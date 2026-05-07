import sys
from collections.abc import Generator
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

import pytest
from opennavier.openfoam.runner import run_docker_solver, run_local_solver


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
    log_path = case_path / "logs" / "solver.log"

    result = run_local_solver(
        [sys.executable, "-c", "print('custom log')"],
        case_path,
        log_path=log_path,
    )

    assert result.succeeded is True
    assert result.log_path == log_path
    assert log_path.read_text(encoding="utf-8").endswith("[stdout]\ncustom log\n")


def test_run_local_solver_writes_default_log_to_explicit_run_directory(
    runner_tmp_path: Path,
) -> None:
    case_path = runner_tmp_path / "case"
    case_path.mkdir()
    run_directory = runner_tmp_path / "runs"

    result = run_local_solver(
        [sys.executable, "-c", "print('run directory log')"],
        case_path,
        run_directory=run_directory,
    )

    assert result.succeeded is True
    assert result.log_path == run_directory / f"log.{Path(sys.executable).name}"
    assert result.log_path.read_text(encoding="utf-8").endswith(
        "[stdout]\nrun directory log\n"
    )


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


def test_run_local_solver_rejects_case_path_outside_workspace_root(
    runner_tmp_path: Path,
) -> None:
    workspace_root = runner_tmp_path / "workspace"
    workspace_root.mkdir()
    outside_case = runner_tmp_path / "outside-case"
    outside_case.mkdir()
    marker_path = outside_case / "should-not-run.txt"

    with pytest.raises(ValueError, match="Case path must be inside workspace root"):
        run_local_solver(
            [
                sys.executable,
                "-c",
                (
                    "from pathlib import Path; "
                    f"Path({str(marker_path)!r}).write_text('ran', encoding='utf-8')"
                ),
            ],
            outside_case,
            workspace_root=workspace_root,
        )

    assert not marker_path.exists()


def test_run_local_solver_rejects_absolute_log_path_outside_case(
    runner_tmp_path: Path,
) -> None:
    case_path = runner_tmp_path / "case"
    case_path.mkdir()
    log_path = (runner_tmp_path / "outside.log").resolve()

    with pytest.raises(ValueError, match="Log path must stay inside"):
        run_local_solver(
            [sys.executable, "-c", "print('should not run')"],
            case_path,
            log_path=log_path,
        )

    assert not log_path.exists()


def test_run_local_solver_rejects_parent_traversal_log_path_outside_case(
    runner_tmp_path: Path,
) -> None:
    case_path = runner_tmp_path / "case"
    case_path.mkdir()
    log_path = case_path / ".." / "outside.log"

    with pytest.raises(ValueError, match="Log path must stay inside"):
        run_local_solver(
            [sys.executable, "-c", "print('should not run')"],
            case_path,
            log_path=log_path,
        )

    assert not (runner_tmp_path / "outside.log").exists()


def test_run_local_solver_rejects_log_path_outside_explicit_run_directory(
    runner_tmp_path: Path,
) -> None:
    case_path = runner_tmp_path / "case"
    case_path.mkdir()
    run_directory = runner_tmp_path / "runs"
    log_path = runner_tmp_path / "other" / "solver.log"

    with pytest.raises(ValueError, match="Log path must stay inside"):
        run_local_solver(
            [sys.executable, "-c", "print('should not run')"],
            case_path,
            run_directory=run_directory,
            log_path=log_path,
        )

    assert not log_path.exists()


def test_run_local_solver_passes_shell_metacharacters_as_arguments(
    runner_tmp_path: Path,
) -> None:
    case_path = runner_tmp_path / "case"
    case_path.mkdir()
    injected_path = case_path / "shell-injected.txt"
    argument = f"literal; {sys.executable} -c \"open({str(injected_path)!r}, 'w').close()\""

    result = run_local_solver(
        [
            sys.executable,
            "-c",
            "import sys; print(sys.argv[1])",
            argument,
        ],
        case_path,
    )

    assert result.succeeded is True
    assert result.stdout == f"{argument}\n"
    assert not injected_path.exists()


def test_run_docker_solver_mounts_case_sets_workdir_appends_solver_and_writes_log(
    runner_tmp_path: Path,
) -> None:
    case_path = runner_tmp_path / "case"
    case_path.mkdir()
    fake_docker_script = (
        "import sys; "
        "print('ARGS=' + repr(sys.argv[1:])); "
        "print('docker stderr', file=sys.stderr)"
    )

    result = run_docker_solver(
        ["simpleFoam", "-case", "."],
        case_path,
        image="openfoam/openfoam-run:latest",
        docker_command=[sys.executable, "-c", fake_docker_script],
    )

    expected_command = [
        sys.executable,
        "-c",
        fake_docker_script,
        "run",
        "--rm",
        "--volume",
        f"{case_path.resolve()}:/case",
        "--workdir",
        "/case",
        "openfoam/openfoam-run:latest",
        "simpleFoam",
        "-case",
        ".",
    ]
    assert result.command == expected_command
    assert result.case_path == case_path
    assert result.return_code == 0
    assert result.succeeded is True
    assert repr(expected_command[3:]) in result.stdout
    assert result.stderr == "docker stderr\n"
    assert result.log_path == case_path / "log.simpleFoam"
    assert result.log_path.read_text(encoding="utf-8").startswith(
        "$ " + " ".join(expected_command) + "\n\n[stdout]\n"
    )


def test_run_docker_solver_writes_caller_provided_log_path(
    runner_tmp_path: Path,
) -> None:
    case_path = runner_tmp_path / "case"
    case_path.mkdir()
    log_path = case_path / "logs" / "docker.log"

    result = run_docker_solver(
        ["pisoFoam"],
        case_path,
        image="openfoam/openfoam-run:latest",
        docker_command=[sys.executable, "-c", "print('custom docker log')"],
        log_path=log_path,
    )

    assert result.succeeded is True
    assert result.log_path == log_path
    assert log_path.read_text(encoding="utf-8").endswith("[stdout]\ncustom docker log\n")


def test_run_docker_solver_writes_default_log_to_explicit_run_directory(
    runner_tmp_path: Path,
) -> None:
    case_path = runner_tmp_path / "case"
    case_path.mkdir()
    run_directory = runner_tmp_path / "runs"

    result = run_docker_solver(
        ["pisoFoam"],
        case_path,
        image="openfoam/openfoam-run:latest",
        docker_command=[sys.executable, "-c", "print('docker run directory log')"],
        run_directory=run_directory,
    )

    assert result.succeeded is True
    assert result.log_path == run_directory / "log.pisoFoam"
    assert result.log_path.read_text(encoding="utf-8").endswith(
        "[stdout]\ndocker run directory log\n"
    )


def test_run_docker_solver_returns_clear_failure_for_missing_docker(
    runner_tmp_path: Path,
) -> None:
    case_path = runner_tmp_path / "case"
    case_path.mkdir()

    result = run_docker_solver(
        ["simpleFoam"],
        case_path,
        image="openfoam/openfoam-run:latest",
        docker_command=["definitely-missing-docker-command"],
    )

    assert result.succeeded is False
    assert result.return_code is None
    assert result.stdout == ""
    assert "Docker executable not found: definitely-missing-docker-command" in result.stderr
    assert result.log_path == case_path / "log.simpleFoam"
    assert "Docker executable not found" in result.log_path.read_text(encoding="utf-8")


def test_run_docker_solver_rejects_bare_string_solver_command(
    runner_tmp_path: Path,
) -> None:
    case_path = runner_tmp_path / "case"
    case_path.mkdir()

    with pytest.raises(TypeError, match="solver_command must be a sequence of arguments"):
        run_docker_solver(  # type: ignore[arg-type]
            "simpleFoam",
            case_path,
            image="openfoam/openfoam-run:latest",
        )

    assert not (case_path / "log.s").exists()


def test_run_docker_solver_rejects_bare_string_docker_command(
    runner_tmp_path: Path,
) -> None:
    case_path = runner_tmp_path / "case"
    case_path.mkdir()

    with pytest.raises(TypeError, match="docker_command must be a sequence of arguments"):
        run_docker_solver(
            ["simpleFoam"],
            case_path,
            image="openfoam/openfoam-run:latest",
            docker_command="docker",  # type: ignore[arg-type]
        )

    assert not (case_path / "log.simpleFoam").exists()


def test_run_docker_solver_rejects_missing_case_path_without_creating_it(
    runner_tmp_path: Path,
) -> None:
    case_path = runner_tmp_path / "missing-case"

    with pytest.raises(NotADirectoryError, match="Case path is not a directory"):
        run_docker_solver(
            ["simpleFoam"],
            case_path,
            image="openfoam/openfoam-run:latest",
            docker_command=[sys.executable, "-c", "print('should not run')"],
        )

    assert not case_path.exists()


def test_run_docker_solver_rejects_case_path_outside_workspace_root(
    runner_tmp_path: Path,
) -> None:
    workspace_root = runner_tmp_path / "workspace"
    workspace_root.mkdir()
    outside_case = runner_tmp_path / "outside-case"
    outside_case.mkdir()

    with pytest.raises(ValueError, match="Case path must be inside workspace root"):
        run_docker_solver(
            ["simpleFoam"],
            outside_case,
            image="openfoam/openfoam-run:latest",
            docker_command=[sys.executable, "-c", "print('should not run')"],
            workspace_root=workspace_root,
        )

    assert not (outside_case / "log.simpleFoam").exists()


def test_run_docker_solver_rejects_absolute_log_path_outside_case(
    runner_tmp_path: Path,
) -> None:
    case_path = runner_tmp_path / "case"
    case_path.mkdir()
    log_path = (runner_tmp_path / "outside-docker.log").resolve()

    with pytest.raises(ValueError, match="Log path must stay inside"):
        run_docker_solver(
            ["simpleFoam"],
            case_path,
            image="openfoam/openfoam-run:latest",
            docker_command=[sys.executable, "-c", "print('should not run')"],
            log_path=log_path,
        )

    assert not log_path.exists()


def test_run_docker_solver_rejects_parent_traversal_log_path_outside_run_directory(
    runner_tmp_path: Path,
) -> None:
    case_path = runner_tmp_path / "case"
    case_path.mkdir()
    run_directory = runner_tmp_path / "runs"
    log_path = run_directory / ".." / "outside-docker.log"

    with pytest.raises(ValueError, match="Log path must stay inside"):
        run_docker_solver(
            ["simpleFoam"],
            case_path,
            image="openfoam/openfoam-run:latest",
            docker_command=[sys.executable, "-c", "print('should not run')"],
            run_directory=run_directory,
            log_path=log_path,
        )

    assert not (runner_tmp_path / "outside-docker.log").exists()
