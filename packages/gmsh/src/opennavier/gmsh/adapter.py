import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GmshRunResult:
    command: list[str]
    geometry_script_path: Path
    mesh_path: Path
    log_path: Path
    return_code: int | None
    stdout: str
    stderr: str

    @property
    def succeeded(self) -> bool:
        return self.return_code == 0


def write_gmsh_box_channel_script(
    path: Path | str,
    *,
    length: float,
    width: float,
    height: float,
    cell_size: float,
) -> Path:
    script_path = Path(path)
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(
        "\n".join(
            [
                "// OpenNavier generated Gmsh box channel geometry",
                'SetFactory("OpenCASCADE");',
                f"length = {_format_gmsh_number(length)};",
                f"width = {_format_gmsh_number(width)};",
                f"height = {_format_gmsh_number(height)};",
                f"cell_size = {_format_gmsh_number(cell_size)};",
                "Box(1) = {0, -width / 2, -height / 2, length, width, height};",
                'Physical Surface("inlet") = {1};',
                'Physical Surface("outlet") = {2};',
                'Physical Surface("walls") = {3, 4, 5, 6};',
                'Physical Volume("fluid") = {1};',
                "Mesh.CharacteristicLengthMin = cell_size;",
                "Mesh.CharacteristicLengthMax = cell_size;",
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )
    return script_path


def run_gmsh_mesh(
    command: Sequence[str],
    geometry_script_path: Path | str,
    mesh_path: Path | str,
    *,
    log_path: Path | str | None = None,
) -> GmshRunResult:
    if isinstance(command, str):
        raise TypeError("command must be a sequence of arguments, not a string")
    if not command:
        raise ValueError("command must include an executable")

    script_path = Path(geometry_script_path)
    if not script_path.is_file():
        raise FileNotFoundError(f"Gmsh geometry script does not exist: {script_path}")

    target_mesh_path = Path(mesh_path)
    target_log_path = Path(log_path) if log_path is not None else script_path.parent / "log.gmsh"
    full_command = [
        *[str(part) for part in command],
        str(script_path),
        "-3",
        "-format",
        "msh2",
        "-o",
        str(target_mesh_path),
    ]

    try:
        completed = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        result = GmshRunResult(
            command=full_command,
            geometry_script_path=script_path,
            mesh_path=target_mesh_path,
            log_path=target_log_path,
            return_code=None,
            stdout="",
            stderr=f"Executable not found: {full_command[0]}\n",
        )
    else:
        result = GmshRunResult(
            command=full_command,
            geometry_script_path=script_path,
            mesh_path=target_mesh_path,
            log_path=target_log_path,
            return_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
    _write_gmsh_log(result)
    return result


def _format_gmsh_number(value: float) -> str:
    return f"{value:g}"


def _write_gmsh_log(result: GmshRunResult) -> None:
    result.log_path.parent.mkdir(parents=True, exist_ok=True)
    content = f"$ {' '.join(result.command)}\n"
    if result.stdout:
        content += f"\n[stdout]\n{result.stdout}"
    if result.stderr:
        content += f"\n[stderr]\n{result.stderr}"
    result.log_path.write_text(content, encoding="utf-8", newline="\n")
