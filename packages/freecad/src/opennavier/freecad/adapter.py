"""Minimal FreeCAD adapter utilities."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from subprocess import run


@dataclass(frozen=True)
class FreeCADRunResult:
    command: list[str]
    script_path: Path
    output_cad_path: Path | None
    output_mesh_path: Path | None
    log_path: Path
    return_code: int | None
    stdout: str
    stderr: str

    @property
    def succeeded(self) -> bool:
        return self.return_code == 0


def write_freecad_box_channel_script(
    script_path: Path,
    *,
    length: float,
    width: float,
    height: float,
    output_cad_path: Path,
    output_mesh_path: Path,
) -> Path:
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(
        "# OpenNavier generated FreeCAD box channel geometry\n"
        "import FreeCAD\n"
        "import Mesh\n"
        "import Part\n"
        "\n"
        f"length = {_format_number(length)}\n"
        f"width = {_format_number(width)}\n"
        f"height = {_format_number(height)}\n"
        f'output_cad_path = r"{output_cad_path}"\n'
        f'output_mesh_path = r"{output_mesh_path}"\n'
        "\n"
        'doc = FreeCAD.newDocument("OpenNavierBoxChannel")\n'
        "solid = Part.makeBox(length, width, height)\n"
        "solid.translate(FreeCAD.Vector(0, -width / 2, -height / 2))\n"
        "Part.export([solid], output_cad_path)\n"
        'fluid = doc.addObject("Part::Feature", "fluid")\n'
        "fluid.Shape = solid\n"
        "doc.recompute()\n"
        "Mesh.export([fluid], output_mesh_path)\n",
        encoding="utf-8",
    )
    return script_path


def run_freecad_script(
    freecad_command: Sequence[str],
    script_path: Path,
    *,
    output_cad_path: Path | None = None,
    output_mesh_path: Path | None = None,
    log_path: Path | None = None,
) -> FreeCADRunResult:
    if isinstance(freecad_command, str):
        raise TypeError("freecad_command must be a sequence of arguments, not a string")
    if not freecad_command:
        raise ValueError("freecad_command must include an executable")
    if not script_path.exists():
        raise FileNotFoundError(f"FreeCAD script does not exist: {script_path}")

    resolved_log_path = log_path or script_path.parent / "log.freecad"
    command = [str(part) for part in freecad_command]
    command.extend(["--console", str(script_path)])

    try:
        completed = run(command, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        result = FreeCADRunResult(
            command=command,
            script_path=script_path,
            output_cad_path=output_cad_path,
            output_mesh_path=output_mesh_path,
            log_path=resolved_log_path,
            return_code=None,
            stdout="",
            stderr=f"Executable not found: {command[0]}\n",
        )
    else:
        result = FreeCADRunResult(
            command=command,
            script_path=script_path,
            output_cad_path=output_cad_path,
            output_mesh_path=output_mesh_path,
            log_path=resolved_log_path,
            return_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    resolved_log_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_log_path.write_text(
        _format_log(result.command, result.stdout, result.stderr),
        encoding="utf-8",
    )

    return result


def _format_number(value: float) -> str:
    return f"{value:g}"


def _format_log(command: Sequence[str], stdout: str, stderr: str) -> str:
    log = "$ " + " ".join(command) + "\n\n" + "[stdout]\n" + stdout
    if stderr:
        log += "\n[stderr]\n" + stderr
    return log
