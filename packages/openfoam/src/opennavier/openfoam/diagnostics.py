from pathlib import Path

from opennavier.openfoam.case_structure import validate_case_structure
from opennavier.openfoam.mesh_quality import diagnose_mesh_quality, parse_check_mesh
from opennavier.openfoam.residuals import diagnose_residuals
from opennavier_core.diagnostics import (
    DiagnosticCollector,
    DiagnosticResult,
    DiagnosticStatus,
)

CHECK_MESH_LOG_PATHS = (
    Path("log.checkMesh"),
    Path("logs") / "checkMesh.log",
)
SOLVER_LOG_PATHS = (
    Path("log.simpleFoam"),
    Path("log.icoFoam"),
    Path("log.pisoFoam"),
    Path("log.pimpleFoam"),
)


def collect_case_diagnostics(case_path: Path | str) -> list[DiagnosticResult]:
    root = Path(case_path)
    collector = DiagnosticCollector(
        (
            lambda: validate_case_structure(root),
            lambda: _collect_check_mesh_diagnostics(root),
            lambda: _collect_solver_log_diagnostics(root),
        )
    )
    return collector.collect()


def _collect_check_mesh_diagnostics(root: Path) -> list[DiagnosticResult]:
    diagnostics: list[DiagnosticResult] = []
    for relative_path in CHECK_MESH_LOG_PATHS:
        path = root / relative_path
        if not path.exists():
            continue
        try:
            summary = parse_check_mesh(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError) as error:
            diagnostics.append(
                DiagnosticResult(
                    status=DiagnosticStatus.FAIL,
                    code="openfoam.mesh_quality.unreadable",
                    message=f"Could not read OpenFOAM checkMesh log: {relative_path.as_posix()}",
                    path=str(path),
                    details={"read_error": type(error).__name__},
                )
            )
            continue

        diagnostics.append(diagnose_mesh_quality(summary).model_copy(update={"path": str(path)}))
    return diagnostics


def _collect_solver_log_diagnostics(root: Path) -> list[DiagnosticResult]:
    diagnostics: list[DiagnosticResult] = []
    for relative_path in SOLVER_LOG_PATHS:
        path = root / relative_path
        if not path.exists():
            continue

        diagnostic = diagnose_residuals(path).model_copy(update={"path": str(path)})
        diagnostics.append(diagnostic)
    return diagnostics
