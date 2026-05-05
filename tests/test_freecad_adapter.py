import sys
from collections.abc import Generator
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

import pytest
from opennavier.freecad.adapter import run_freecad_script, write_freecad_box_channel_script


@pytest.fixture
def freecad_tmp_path() -> Generator[Path, None, None]:
    path = Path(".tmp") / f"freecad-adapter-{uuid4().hex}"
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        rmtree(path, ignore_errors=True)


def test_write_freecad_box_channel_script_writes_deterministic_python(
    freecad_tmp_path: Path,
) -> None:
    script_path = freecad_tmp_path / "channel.py"
    cad_path = freecad_tmp_path / "channel.step"
    mesh_path = freecad_tmp_path / "channel.stl"

    result = write_freecad_box_channel_script(
        script_path,
        length=2.0,
        width=0.4,
        height=0.2,
        output_cad_path=cad_path,
        output_mesh_path=mesh_path,
    )

    assert result == script_path
    assert script_path.read_text(encoding="utf-8") == (
        "# OpenNavier generated FreeCAD box channel geometry\n"
        "import FreeCAD\n"
        "import Mesh\n"
        "import Part\n"
        "\n"
        "length = 2\n"
        "width = 0.4\n"
        "height = 0.2\n"
        f"output_cad_path = r\"{cad_path}\"\n"
        f"output_mesh_path = r\"{mesh_path}\"\n"
        "\n"
        "doc = FreeCAD.newDocument(\"OpenNavierBoxChannel\")\n"
        "solid = Part.makeBox(length, width, height)\n"
        "solid.translate(FreeCAD.Vector(0, -width / 2, -height / 2))\n"
        "Part.export([solid], output_cad_path)\n"
        "fluid = doc.addObject(\"Part::Feature\", \"fluid\")\n"
        "fluid.Shape = solid\n"
        "doc.recompute()\n"
        "Mesh.export([fluid], output_mesh_path)\n"
    )


def test_run_freecad_script_invokes_console_command_and_writes_log(
    freecad_tmp_path: Path,
) -> None:
    script_path = freecad_tmp_path / "channel.py"
    cad_path = freecad_tmp_path / "channel.step"
    mesh_path = freecad_tmp_path / "channel.stl"
    script_path.write_text("# geometry\n", encoding="utf-8")

    result = run_freecad_script(
        [
            sys.executable,
            "-c",
            (
                "from pathlib import Path; "
                "import sys; "
                "print('|'.join(sys.argv[1:])); "
                "Path(sys.argv[-1]).with_suffix('.step').write_text('cad\\n', "
                "encoding='utf-8'); "
                "Path(sys.argv[-1]).with_suffix('.stl').write_text('mesh\\n', "
                "encoding='utf-8')"
            ),
        ],
        script_path,
        output_cad_path=cad_path,
        output_mesh_path=mesh_path,
    )

    assert result.command == [
        sys.executable,
        "-c",
        result.command[2],
        "--console",
        str(script_path),
    ]
    assert result.script_path == script_path
    assert result.output_cad_path == cad_path
    assert result.output_mesh_path == mesh_path
    assert result.return_code == 0
    assert result.succeeded is True
    assert result.stdout == f"--console|{script_path}\n"
    assert result.stderr == ""
    assert result.log_path == freecad_tmp_path / "log.freecad"
    assert result.log_path.read_text(encoding="utf-8") == (
        "$ "
        + " ".join(result.command)
        + "\n\n"
        + "[stdout]\n"
        + result.stdout
    )


def test_run_freecad_script_returns_failure_result_with_stdout_and_stderr(
    freecad_tmp_path: Path,
) -> None:
    script_path = freecad_tmp_path / "channel.py"
    log_path = freecad_tmp_path / "logs" / "freecad.log"
    script_path.write_text("# geometry\n", encoding="utf-8")

    result = run_freecad_script(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "print('freecad stdout'); "
                "print('bad cad', file=sys.stderr); "
                "raise SystemExit(9)"
            ),
        ],
        script_path,
        log_path=log_path,
    )

    assert result.succeeded is False
    assert result.return_code == 9
    assert result.stdout == "freecad stdout\n"
    assert result.stderr == "bad cad\n"
    assert result.command[-2:] == ["--console", str(script_path)]
    assert result.log_path == log_path
    assert log_path.read_text(encoding="utf-8") == (
        "$ "
        + " ".join(result.command)
        + "\n\n"
        + "[stdout]\nfreecad stdout\n\n"
        + "[stderr]\nbad cad\n"
    )


def test_run_freecad_script_returns_logged_failure_when_executable_is_missing(
    freecad_tmp_path: Path,
) -> None:
    script_path = freecad_tmp_path / "channel.py"
    script_path.write_text("# geometry\n", encoding="utf-8")

    result = run_freecad_script(
        ["__opennavier_missing_freecad_executable__"],
        script_path,
    )

    assert result.succeeded is False
    assert result.return_code is None
    assert result.stdout == ""
    assert result.stderr == "Executable not found: __opennavier_missing_freecad_executable__\n"
    assert result.command == [
        "__opennavier_missing_freecad_executable__",
        "--console",
        str(script_path),
    ]
    assert result.log_path == freecad_tmp_path / "log.freecad"
    assert result.log_path.read_text(encoding="utf-8") == (
        "$ "
        + " ".join(result.command)
        + "\n\n"
        + "[stdout]\n\n"
        + "[stderr]\nExecutable not found: __opennavier_missing_freecad_executable__\n"
    )


def test_run_freecad_script_rejects_command_string_without_spawning(
    freecad_tmp_path: Path,
) -> None:
    script_path = freecad_tmp_path / "channel.py"
    script_path.write_text("# geometry\n", encoding="utf-8")

    with pytest.raises(TypeError, match="not a string"):
        run_freecad_script("FreeCADCmd", script_path)

    assert not (freecad_tmp_path / "log.freecad").exists()


def test_run_freecad_script_rejects_empty_command_without_spawning(
    freecad_tmp_path: Path,
) -> None:
    script_path = freecad_tmp_path / "channel.py"
    script_path.write_text("# geometry\n", encoding="utf-8")

    with pytest.raises(ValueError, match="must include an executable"):
        run_freecad_script([], script_path)

    assert not (freecad_tmp_path / "log.freecad").exists()


def test_run_freecad_script_rejects_missing_script_without_creating_artifacts(
    freecad_tmp_path: Path,
) -> None:
    script_path = freecad_tmp_path / "missing.py"
    cad_path = freecad_tmp_path / "channel.step"
    mesh_path = freecad_tmp_path / "channel.stl"

    with pytest.raises(FileNotFoundError, match="FreeCAD script does not exist"):
        run_freecad_script(
            [sys.executable, "-c", "print('should not run')"],
            script_path,
            output_cad_path=cad_path,
            output_mesh_path=mesh_path,
        )

    assert not cad_path.exists()
    assert not mesh_path.exists()
    assert not (freecad_tmp_path / "log.freecad").exists()
