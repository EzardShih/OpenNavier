from pathlib import Path

from opennavier_core.diagnostics import DiagnosticResult, DiagnosticStatus

REQUIRED_DIRECTORIES = ("0", "constant", "system")
REQUIRED_SYSTEM_FILES = ("controlDict", "fvSchemes", "fvSolution")


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
        diagnostics.append(
            _path_diagnostic(
                path=path,
                exists=path.is_file(),
                code=f"openfoam.required_file.system_{filename}",
                pass_message=f"Required OpenFOAM system file exists: {relative.as_posix()}",
                fail_message=f"Missing required OpenFOAM system file: {relative.as_posix()}",
                expected_type="file",
            )
        )

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
