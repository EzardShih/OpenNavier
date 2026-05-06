import sys
from collections.abc import Generator
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

import pytest
from opennavier.paraview.adapter import (
    run_paraview_script,
    write_paraview_case_screenshot_script,
)


@pytest.fixture
def paraview_tmp_path() -> Generator[Path, None, None]:
    path = Path(".tmp") / f"paraview-adapter-{uuid4().hex}"
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        rmtree(path, ignore_errors=True)


def test_write_paraview_case_screenshot_script_writes_deterministic_python(
    paraview_tmp_path: Path,
) -> None:
    script_path = paraview_tmp_path / "screenshot.py"
    case_path = paraview_tmp_path / "case.foam"
    screenshot_path = paraview_tmp_path / "screenshot.png"

    result = write_paraview_case_screenshot_script(
        script_path,
        case_path=case_path,
        screenshot_path=screenshot_path,
        view_size=(1280, 720),
    )

    assert result == script_path
    assert script_path.read_text(encoding="utf-8") == (
        "# OpenNavier generated ParaView case screenshot\n"
        "from paraview.simple import OpenFOAMReader, SaveScreenshot, Show, GetActiveViewOrCreate\n"
        "\n"
        f"case_path = r\"{case_path}\"\n"
        f"screenshot_path = r\"{screenshot_path}\"\n"
        "view_size = [1280, 720]\n"
        "\n"
        "reader = OpenFOAMReader(FileName=case_path)\n"
        "view = GetActiveViewOrCreate(\"RenderView\")\n"
        "view.ViewSize = view_size\n"
        "display = Show(reader, view)\n"
        "display.Representation = \"Surface\"\n"
        "view.ResetCamera()\n"
        "SaveScreenshot(screenshot_path, view, ImageResolution=view_size)\n"
    )


def test_write_paraview_case_screenshot_script_uses_foam_marker_for_case_directory(
    paraview_tmp_path: Path,
) -> None:
    script_path = paraview_tmp_path / "screenshot.py"
    case_path = paraview_tmp_path / "cavity"
    screenshot_path = paraview_tmp_path / "screenshot.png"
    case_path.mkdir()

    write_paraview_case_screenshot_script(
        script_path,
        case_path=case_path,
        screenshot_path=screenshot_path,
    )

    marker_path = case_path / "cavity.foam"
    assert marker_path.is_file()
    assert f'case_path = r"{marker_path}"\n' in script_path.read_text(encoding="utf-8")


def test_run_paraview_script_invokes_command_with_script_and_writes_log(
    paraview_tmp_path: Path,
) -> None:
    script_path = paraview_tmp_path / "screenshot.py"
    screenshot_path = paraview_tmp_path / "screenshot.png"
    script_path.write_text("# paraview\n", encoding="utf-8")

    result = run_paraview_script(
        [
            sys.executable,
            "-c",
            (
                "from pathlib import Path; "
                "import sys; "
                "print('|'.join(sys.argv[1:])); "
                "Path(sys.argv[-1]).with_suffix('.png').write_text('png\\n', encoding='utf-8')"
            ),
        ],
        script_path,
        screenshot_path=screenshot_path,
    )

    assert result.command == [
        sys.executable,
        "-c",
        result.command[2],
        str(script_path),
    ]
    assert result.script_path == script_path
    assert result.screenshot_path == screenshot_path
    assert result.return_code == 0
    assert result.succeeded is True
    assert result.stdout == f"{script_path}\n"
    assert result.stderr == ""
    assert result.log_path == paraview_tmp_path / "log.paraview"
    assert screenshot_path.read_text(encoding="utf-8") == "png\n"
    assert result.log_path.read_text(encoding="utf-8") == (
        "$ "
        + " ".join(result.command)
        + "\n\n"
        + "[stdout]\n"
        + result.stdout
    )


def test_run_paraview_script_returns_failure_result_with_stdout_and_stderr(
    paraview_tmp_path: Path,
) -> None:
    script_path = paraview_tmp_path / "screenshot.py"
    log_path = paraview_tmp_path / "logs" / "paraview.log"
    script_path.write_text("# paraview\n", encoding="utf-8")

    result = run_paraview_script(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "print('paraview stdout'); "
                "print('bad pipeline', file=sys.stderr); "
                "raise SystemExit(7)"
            ),
        ],
        script_path,
        log_path=log_path,
    )

    assert result.succeeded is False
    assert result.return_code == 7
    assert result.stdout == "paraview stdout\n"
    assert result.stderr == "bad pipeline\n"
    assert result.command[-1] == str(script_path)
    assert result.log_path == log_path
    assert log_path.read_text(encoding="utf-8") == (
        "$ "
        + " ".join(result.command)
        + "\n\n"
        + "[stdout]\nparaview stdout\n\n"
        + "[stderr]\nbad pipeline\n"
    )


def test_run_paraview_script_returns_logged_failure_when_executable_is_missing(
    paraview_tmp_path: Path,
) -> None:
    script_path = paraview_tmp_path / "screenshot.py"
    script_path.write_text("# paraview\n", encoding="utf-8")

    result = run_paraview_script(
        ["__opennavier_missing_paraview_executable__"],
        script_path,
    )

    assert result.succeeded is False
    assert result.return_code is None
    assert result.stdout == ""
    assert result.stderr == "Executable not found: __opennavier_missing_paraview_executable__\n"
    assert result.command == [
        "__opennavier_missing_paraview_executable__",
        str(script_path),
    ]
    assert result.log_path == paraview_tmp_path / "log.paraview"
    assert result.log_path.read_text(encoding="utf-8") == (
        "$ "
        + " ".join(result.command)
        + "\n\n"
        + "[stderr]\nExecutable not found: __opennavier_missing_paraview_executable__\n"
    )


def test_run_paraview_script_rejects_command_string_without_spawning(
    paraview_tmp_path: Path,
) -> None:
    script_path = paraview_tmp_path / "screenshot.py"
    script_path.write_text("# paraview\n", encoding="utf-8")

    with pytest.raises(TypeError, match="not a string"):
        run_paraview_script("pvpython", script_path)

    assert not (paraview_tmp_path / "log.paraview").exists()


def test_run_paraview_script_rejects_empty_command_without_spawning(
    paraview_tmp_path: Path,
) -> None:
    script_path = paraview_tmp_path / "screenshot.py"
    script_path.write_text("# paraview\n", encoding="utf-8")

    with pytest.raises(ValueError, match="must include an executable"):
        run_paraview_script([], script_path)

    assert not (paraview_tmp_path / "log.paraview").exists()


def test_run_paraview_script_rejects_missing_script_without_creating_artifacts(
    paraview_tmp_path: Path,
) -> None:
    script_path = paraview_tmp_path / "missing.py"
    screenshot_path = paraview_tmp_path / "screenshot.png"

    with pytest.raises(FileNotFoundError, match="ParaView script does not exist"):
        run_paraview_script(
            [sys.executable, "-c", "print('should not run')"],
            script_path,
            screenshot_path=screenshot_path,
        )

    assert not screenshot_path.exists()
    assert not (paraview_tmp_path / "log.paraview").exists()
