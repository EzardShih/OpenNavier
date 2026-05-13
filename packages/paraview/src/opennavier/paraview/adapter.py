import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

ASSET_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


@dataclass(frozen=True)
class ParaViewRunResult:
    command: list[str]
    script_path: Path
    screenshot_path: Path | None
    log_path: Path
    return_code: int | None
    stdout: str
    stderr: str

    @property
    def succeeded(self) -> bool:
        return self.return_code == 0


@dataclass(frozen=True)
class ParaViewReportAsset:
    asset_name: str
    script_path: Path
    screenshot_path: Path
    log_path: Path
    integration_only: bool = True


def prepare_paraview_report_asset(
    *,
    case_path: Path | str,
    output_dir: Path | str,
    asset_name: str = "case-surface",
    view_size: tuple[int, int] = (1280, 720),
) -> ParaViewReportAsset:
    asset_name = _validated_asset_name(asset_name)
    report_root = Path(output_dir)
    script_path = report_root / "paraview" / f"{asset_name}.py"
    screenshot_path = report_root / "screenshots" / f"{asset_name}.png"
    log_path = report_root / "logs" / f"{asset_name}.log"
    write_paraview_case_screenshot_script(
        script_path,
        case_path=case_path,
        screenshot_path=screenshot_path,
        view_size=view_size,
    )
    return ParaViewReportAsset(
        asset_name=asset_name,
        script_path=script_path,
        screenshot_path=screenshot_path,
        log_path=log_path,
    )


def write_paraview_case_screenshot_script(
    script_path: Path | str,
    *,
    case_path: Path | str,
    screenshot_path: Path | str,
    view_size: tuple[int, int] = (1280, 720),
) -> Path:
    target_script_path = Path(script_path)
    reader_case_path = _openfoam_reader_case_path(Path(case_path))
    target_script_path.parent.mkdir(parents=True, exist_ok=True)
    target_script_path.write_text(
        "# OpenNavier generated ParaView case screenshot\n"
        "from paraview.simple import OpenFOAMReader, SaveScreenshot, Show, GetActiveViewOrCreate\n"
        "\n"
        f'case_path = r"{reader_case_path}"\n'
        f'screenshot_path = r"{Path(screenshot_path)}"\n'
        f"view_size = [{view_size[0]}, {view_size[1]}]\n"
        "\n"
        "reader = OpenFOAMReader(FileName=case_path)\n"
        'view = GetActiveViewOrCreate("RenderView")\n'
        "view.ViewSize = view_size\n"
        "display = Show(reader, view)\n"
        'display.Representation = "Surface"\n'
        "view.ResetCamera()\n"
        "SaveScreenshot(screenshot_path, view, ImageResolution=view_size)\n",
        encoding="utf-8",
        newline="\n",
    )
    return target_script_path


def _validated_asset_name(asset_name: str) -> str:
    if not ASSET_NAME_PATTERN.fullmatch(asset_name):
        raise ValueError(
            "asset_name must contain only ASCII letters, numbers, underscores, or hyphens"
        )
    return asset_name


def _openfoam_reader_case_path(case_path: Path) -> Path:
    if not case_path.is_dir():
        return case_path

    marker_path = case_path / f"{case_path.name}.foam"
    marker_path.touch(exist_ok=True)
    return marker_path


def run_paraview_script(
    command: Sequence[str],
    script_path: Path | str,
    *,
    screenshot_path: Path | str | None = None,
    log_path: Path | str | None = None,
) -> ParaViewRunResult:
    if isinstance(command, str):
        raise TypeError("command must be a sequence of arguments, not a string")
    if not command:
        raise ValueError("command must include an executable")

    target_script_path = Path(script_path)
    if not target_script_path.is_file():
        raise FileNotFoundError(f"ParaView script does not exist: {target_script_path}")

    target_screenshot_path = Path(screenshot_path) if screenshot_path is not None else None
    target_log_path = (
        Path(log_path) if log_path is not None else target_script_path.parent / "log.paraview"
    )
    full_command = [*[str(part) for part in command], str(target_script_path)]

    try:
        completed = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        result = ParaViewRunResult(
            command=full_command,
            script_path=target_script_path,
            screenshot_path=target_screenshot_path,
            log_path=target_log_path,
            return_code=None,
            stdout="",
            stderr=f"Executable not found: {full_command[0]}\n",
        )
    else:
        result = ParaViewRunResult(
            command=full_command,
            script_path=target_script_path,
            screenshot_path=target_screenshot_path,
            log_path=target_log_path,
            return_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    _write_paraview_log(result)
    return result


def _write_paraview_log(result: ParaViewRunResult) -> None:
    result.log_path.parent.mkdir(parents=True, exist_ok=True)
    content = f"$ {' '.join(result.command)}\n"
    if result.stdout:
        content += f"\n[stdout]\n{result.stdout}"
    if result.stderr:
        content += f"\n[stderr]\n{result.stderr}"
    result.log_path.write_text(content, encoding="utf-8", newline="\n")
