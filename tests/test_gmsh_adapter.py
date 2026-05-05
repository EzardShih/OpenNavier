import sys
from collections.abc import Generator
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

import pytest
from opennavier.gmsh.adapter import run_gmsh_mesh, write_gmsh_box_channel_script


@pytest.fixture
def gmsh_tmp_path() -> Generator[Path, None, None]:
    path = Path(".tmp") / f"gmsh-adapter-{uuid4().hex}"
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        rmtree(path, ignore_errors=True)


def test_write_gmsh_box_channel_script_writes_deterministic_geo(gmsh_tmp_path: Path) -> None:
    script_path = gmsh_tmp_path / "channel.geo"

    result = write_gmsh_box_channel_script(
        script_path,
        length=2.0,
        width=0.4,
        height=0.2,
        cell_size=0.05,
    )

    assert result == script_path
    assert script_path.read_text(encoding="utf-8") == (
        "// OpenNavier generated Gmsh box channel geometry\n"
        "SetFactory(\"OpenCASCADE\");\n"
        "length = 2;\n"
        "width = 0.4;\n"
        "height = 0.2;\n"
        "cell_size = 0.05;\n"
        "Box(1) = {0, -width / 2, -height / 2, length, width, height};\n"
        "Physical Surface(\"inlet\") = {1};\n"
        "Physical Surface(\"outlet\") = {2};\n"
        "Physical Surface(\"walls\") = {3, 4, 5, 6};\n"
        "Physical Volume(\"fluid\") = {1};\n"
        "Mesh.CharacteristicLengthMin = cell_size;\n"
        "Mesh.CharacteristicLengthMax = cell_size;\n"
    )


def test_run_gmsh_mesh_invokes_command_with_explicit_input_and_output_paths(
    gmsh_tmp_path: Path,
) -> None:
    script_path = gmsh_tmp_path / "channel.geo"
    mesh_path = gmsh_tmp_path / "channel.msh"
    script_path.write_text("// geometry\n", encoding="utf-8")

    result = run_gmsh_mesh(
        [
            sys.executable,
            "-c",
            (
                "from pathlib import Path; "
                "import sys; "
                "print('|'.join(sys.argv[1:])); "
                "Path(sys.argv[sys.argv.index('-o') + 1]).write_text('mesh\\n', "
                "encoding='utf-8')"
            ),
        ],
        script_path,
        mesh_path,
    )

    assert result.command == [
        sys.executable,
        "-c",
        result.command[2],
        str(script_path),
        "-3",
        "-format",
        "msh2",
        "-o",
        str(mesh_path),
    ]
    assert result.geometry_script_path == script_path
    assert result.mesh_path == mesh_path
    assert result.return_code == 0
    assert result.succeeded is True
    assert result.stdout == (
        f"{script_path}|-3|-format|msh2|-o|{mesh_path}\n"
    )
    assert result.stderr == ""
    assert result.log_path == gmsh_tmp_path / "log.gmsh"
    assert mesh_path.read_text(encoding="utf-8") == "mesh\n"
    assert result.log_path.read_text(encoding="utf-8") == (
        "$ "
        + " ".join(result.command)
        + "\n\n"
        + "[stdout]\n"
        + result.stdout
    )


def test_run_gmsh_mesh_returns_failure_result_with_log(gmsh_tmp_path: Path) -> None:
    script_path = gmsh_tmp_path / "channel.geo"
    mesh_path = gmsh_tmp_path / "channel.msh"
    log_path = gmsh_tmp_path / "logs" / "gmsh.log"
    script_path.write_text("// geometry\n", encoding="utf-8")

    result = run_gmsh_mesh(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "print('gmsh stdout'); "
                "print('bad mesh', file=sys.stderr); "
                "raise SystemExit(12)"
            ),
        ],
        script_path,
        mesh_path,
        log_path=log_path,
    )

    assert result.succeeded is False
    assert result.return_code == 12
    assert result.stdout == "gmsh stdout\n"
    assert result.stderr == "bad mesh\n"
    assert result.command[-2:] == ["-o", str(mesh_path)]
    assert result.log_path == log_path
    assert log_path.read_text(encoding="utf-8") == (
        "$ "
        + " ".join(result.command)
        + "\n\n"
        + "[stdout]\ngmsh stdout\n\n"
        + "[stderr]\nbad mesh\n"
    )


def test_run_gmsh_mesh_returns_logged_failure_when_executable_is_missing(
    gmsh_tmp_path: Path,
) -> None:
    script_path = gmsh_tmp_path / "channel.geo"
    mesh_path = gmsh_tmp_path / "channel.msh"
    script_path.write_text("// geometry\n", encoding="utf-8")

    result = run_gmsh_mesh(
        ["__opennavier_missing_gmsh_executable__"],
        script_path,
        mesh_path,
    )

    assert result.succeeded is False
    assert result.return_code is None
    assert result.stdout == ""
    assert result.stderr == "Executable not found: __opennavier_missing_gmsh_executable__\n"
    assert result.command == [
        "__opennavier_missing_gmsh_executable__",
        str(script_path),
        "-3",
        "-format",
        "msh2",
        "-o",
        str(mesh_path),
    ]
    assert result.log_path == gmsh_tmp_path / "log.gmsh"
    assert result.log_path.read_text(encoding="utf-8") == (
        "$ "
        + " ".join(result.command)
        + "\n\n"
        + "[stderr]\nExecutable not found: __opennavier_missing_gmsh_executable__\n"
    )
    assert not mesh_path.exists()


def test_run_gmsh_mesh_rejects_missing_geometry_without_creating_mesh(
    gmsh_tmp_path: Path,
) -> None:
    script_path = gmsh_tmp_path / "missing.geo"
    mesh_path = gmsh_tmp_path / "channel.msh"

    with pytest.raises(FileNotFoundError, match="Gmsh geometry script does not exist"):
        run_gmsh_mesh(
            [sys.executable, "-c", "print('should not run')"],
            script_path,
            mesh_path,
        )

    assert not mesh_path.exists()
    assert not (gmsh_tmp_path / "log.gmsh").exists()
