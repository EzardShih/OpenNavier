import re
from pathlib import Path

from opennavier_core.diagnostics import DiagnosticResult, DiagnosticStatus

REQUIRED_DIRECTORIES = ("0", "constant", "system")
REQUIRED_SYSTEM_FILES = ("controlDict", "fvSchemes", "fvSolution")
FOAMFILE_HEADER_PATTERN = re.compile(r"\bFoamFile\b\s*\{")


def validate_case_structure(case_path: Path | str) -> list[DiagnosticResult]:
    root = Path(case_path)
    diagnostics: list[DiagnosticResult] = []

    for directory in REQUIRED_DIRECTORIES:
        path = root / directory
        diagnostics.append(
            _path_diagnostic(
                path=path,
                exists=path.is_dir(),
                code=f"openfoam.required_directory.{directory}",
                pass_message=f"Required OpenFOAM directory exists: {directory}",
                fail_message=f"Missing required OpenFOAM directory: {directory}",
                expected_type="directory",
            )
        )

    for filename in REQUIRED_SYSTEM_FILES:
        relative = Path("system") / filename
        path = root / relative
        exists = path.is_file()
        diagnostics.append(
            _path_diagnostic(
                path=path,
                exists=exists,
                code=f"openfoam.required_file.system_{filename}",
                pass_message=f"Required OpenFOAM system file exists: {relative.as_posix()}",
                fail_message=f"Missing required OpenFOAM system file: {relative.as_posix()}",
                expected_type="file",
            )
        )
        if exists:
            diagnostics.append(_dictionary_header_diagnostic(path=path, filename=filename))

    return diagnostics


def _path_diagnostic(
    *,
    path: Path,
    exists: bool,
    code: str,
    pass_message: str,
    fail_message: str,
    expected_type: str,
) -> DiagnosticResult:
    return DiagnosticResult(
        status=DiagnosticStatus.PASS if exists else DiagnosticStatus.FAIL,
        code=code,
        message=pass_message if exists else fail_message,
        path=str(path),
        details={"expected_type": expected_type},
    )


def _dictionary_header_diagnostic(*, path: Path, filename: str) -> DiagnosticResult:
    relative = Path("system") / filename
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        return DiagnosticResult(
            status=DiagnosticStatus.FAIL,
            code=f"openfoam.dictionary_header.system_{filename}",
            message=f"Could not read OpenFOAM dictionary text: {relative.as_posix()}",
            path=str(path),
            details={
                "required_header": "FoamFile",
                "read_error": type(error).__name__,
            },
        )

    has_header = _has_foamfile_header(content)
    return DiagnosticResult(
        status=DiagnosticStatus.PASS if has_header else DiagnosticStatus.FAIL,
        code=f"openfoam.dictionary_header.system_{filename}",
        message=(
            f"OpenFOAM dictionary header exists: {relative.as_posix()}"
            if has_header
            else f"Missing OpenFOAM dictionary header: {relative.as_posix()}"
        ),
        path=str(path),
        details={"required_header": "FoamFile"},
    )


def _has_foamfile_header(content: str) -> bool:
    return FOAMFILE_HEADER_PATTERN.search(_strip_comments_and_strings(content)) is not None


def _strip_comments_and_strings(content: str) -> str:
    output: list[str] = []
    index = 0
    while index < len(content):
        char = content[index]
        next_char = content[index + 1] if index + 1 < len(content) else ""

        if char == "/" and next_char == "/":
            index += 2
            while index < len(content) and content[index] not in "\r\n":
                index += 1
            continue

        if char == "/" and next_char == "*":
            index += 2
            while index + 1 < len(content) and content[index : index + 2] != "*/":
                index += 1
            index = min(index + 2, len(content))
            continue

        if char == '"':
            index += 1
            while index < len(content):
                if content[index] == "\\":
                    index += 2
                    continue
                if content[index] == '"':
                    index += 1
                    break
                index += 1
            continue

        output.append(char)
        index += 1

    return "".join(output)
