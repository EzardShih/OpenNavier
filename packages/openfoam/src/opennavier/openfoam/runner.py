import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SolverRunResult:
    command: list[str]
    case_path: Path
    log_path: Path
    return_code: int | None
    stdout: str
    stderr: str

    @property
    def succeeded(self) -> bool:
        return self.return_code == 0


def run_local_solver(
    command: Sequence[str],
    case_path: Path | str,
    *,
    workspace_root: Path | str | None = None,
    run_directory: Path | str | None = None,
    log_path: Path | str | None = None,
) -> SolverRunResult:
    if isinstance(command, str):
        raise TypeError("command must be a sequence of arguments, not a string")

    if not command:
        raise ValueError("command must include an executable")

    command_parts = [str(part) for part in command]
    root = _validated_case_path(case_path, workspace_root=workspace_root)
    target_log_path = _validated_log_path(
        command_parts,
        case_path=root,
        run_directory=run_directory,
        log_path=log_path,
    )

    try:
        completed = subprocess.run(
            command_parts,
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        result = SolverRunResult(
            command=command_parts,
            case_path=root,
            log_path=target_log_path,
            return_code=None,
            stdout="",
            stderr=f"Executable not found: {command_parts[0]}\n",
        )
    else:
        result = SolverRunResult(
            command=command_parts,
            case_path=root,
            log_path=target_log_path,
            return_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    _write_solver_log(result)
    return result


def run_docker_solver(
    solver_command: Sequence[str],
    case_path: Path | str,
    *,
    image: str,
    docker_command: Sequence[str] = ("docker",),
    workspace_root: Path | str | None = None,
    run_directory: Path | str | None = None,
    log_path: Path | str | None = None,
) -> SolverRunResult:
    if isinstance(solver_command, str):
        raise TypeError("solver_command must be a sequence of arguments, not a string")

    if isinstance(docker_command, str):
        raise TypeError("docker_command must be a sequence of arguments, not a string")

    if not solver_command:
        raise ValueError("solver_command must include an executable")

    if not docker_command:
        raise ValueError("docker_command must include an executable")

    solver_parts = [str(part) for part in solver_command]
    docker_parts = [str(part) for part in docker_command]
    root = _validated_case_path(case_path, workspace_root=workspace_root)
    target_log_path = _validated_log_path(
        solver_parts,
        case_path=root,
        run_directory=run_directory,
        log_path=log_path,
    )
    command_parts = [
        *docker_parts,
        "run",
        "--rm",
        "--volume",
        f"{root.resolve()}:/case",
        "--workdir",
        "/case",
        image,
        *solver_parts,
    ]

    try:
        completed = subprocess.run(
            command_parts,
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        result = SolverRunResult(
            command=command_parts,
            case_path=root,
            log_path=target_log_path,
            return_code=None,
            stdout="",
            stderr=f"Docker executable not found: {docker_parts[0]}\n",
        )
    else:
        result = SolverRunResult(
            command=command_parts,
            case_path=root,
            log_path=target_log_path,
            return_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    _write_solver_log(result)
    return result


def _default_log_name(command: Sequence[str]) -> str:
    return f"log.{Path(command[0]).name}"


def _validated_case_path(
    case_path: Path | str,
    *,
    workspace_root: Path | str | None,
) -> Path:
    root = Path(case_path)
    if not root.is_dir():
        raise NotADirectoryError(f"Case path is not a directory: {root}")

    if workspace_root is not None:
        workspace = Path(workspace_root).resolve()
        if not _is_relative_to(root.resolve(), workspace):
            raise ValueError("Case path must be inside workspace root")

    return root


def _validated_log_path(
    command: Sequence[str],
    *,
    case_path: Path,
    run_directory: Path | str | None,
    log_path: Path | str | None,
) -> Path:
    target_root = Path(run_directory) if run_directory is not None else case_path
    target_log_path = (
        Path(log_path) if log_path is not None else target_root / _default_log_name(command)
    )

    if not _is_relative_to(target_log_path.resolve(), target_root.resolve()):
        raise ValueError(f"Log path must stay inside {target_root}")

    return target_log_path


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _write_solver_log(result: SolverRunResult) -> None:
    result.log_path.parent.mkdir(parents=True, exist_ok=True)
    content = f"$ {' '.join(result.command)}\n"
    if result.stdout:
        content += f"\n[stdout]\n{result.stdout}"
    if result.stderr:
        content += f"\n[stderr]\n{result.stderr}"
    result.log_path.write_text(content, encoding="utf-8", newline="\n")
