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
    log_path: Path | str | None = None,
) -> SolverRunResult:
    if isinstance(command, str):
        raise TypeError("command must be a sequence of arguments, not a string")

    if not command:
        raise ValueError("command must include an executable")

    command_parts = [str(part) for part in command]
    root = Path(case_path)
    if not root.is_dir():
        raise NotADirectoryError(f"Case path is not a directory: {root}")

    target_log_path = (
        Path(log_path) if log_path is not None else root / _default_log_name(command_parts)
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


def _default_log_name(command: Sequence[str]) -> str:
    return f"log.{Path(command[0]).name}"


def _write_solver_log(result: SolverRunResult) -> None:
    result.log_path.parent.mkdir(parents=True, exist_ok=True)
    content = f"$ {' '.join(result.command)}\n"
    if result.stdout:
        content += f"\n[stdout]\n{result.stdout}"
    if result.stderr:
        content += f"\n[stderr]\n{result.stderr}"
    result.log_path.write_text(content, encoding="utf-8", newline="\n")
