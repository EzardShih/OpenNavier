import re
from pathlib import Path

from opennavier_core.diagnostics import DiagnosticResult, DiagnosticStatus

SUPPORTED_SOLVERS_BY_FAMILY = {
    "incompressible_laminar": {"icoFoam", "simpleFoam"},
}
REQUIRED_FIELDS_BY_SOLVER = {
    "icoFoam": {"U", "p"},
    "simpleFoam": {"U", "p"},
}
REQUIRED_ALGORITHM_BY_SOLVER = {
    "icoFoam": "PISO",
    "simpleFoam": "SIMPLE",
}
APPLICATION_PATTERN = re.compile(r"\bapplication\s+(?P<solver>[A-Za-z0-9_./+-]+)\s*;")


def check_solver_compatibility(
    case_path: Path | str,
    *,
    solver_family: str,
    solver: str,
) -> list[DiagnosticResult]:
    root = Path(case_path)
    return [
        _solver_family_diagnostic(root, solver_family=solver_family, solver=solver),
        _application_diagnostic(root, solver=solver),
        _required_fields_diagnostic(root, solver=solver),
        _algorithm_diagnostic(root, solver=solver),
    ]


def _solver_family_diagnostic(
    root: Path,
    *,
    solver_family: str,
    solver: str,
) -> DiagnosticResult:
    supported_solvers = SUPPORTED_SOLVERS_BY_FAMILY.get(solver_family, set())
    if solver in supported_solvers:
        return DiagnosticResult(
            status=DiagnosticStatus.PASS,
            code="openfoam.solver_compatibility.solver_family",
            message="Solver is compatible with the selected solver family.",
            path=str(root),
            details={"solver_family": solver_family, "solver": solver},
        )

    return DiagnosticResult(
        status=DiagnosticStatus.FAIL,
        code="openfoam.solver_compatibility.solver_family",
        message="Solver is not compatible with the selected solver family.",
        path=str(root),
        details={
            "solver_family": solver_family,
            "solver": solver,
            "supported_solvers": ",".join(sorted(supported_solvers)),
        },
    )


def _application_diagnostic(root: Path, *, solver: str) -> DiagnosticResult:
    control_dict = root / "system" / "controlDict"
    content = _read_text(control_dict)
    if content is None:
        return DiagnosticResult(
            status=DiagnosticStatus.FAIL,
            code="openfoam.solver_compatibility.application",
            message="Could not read system/controlDict to verify solver application.",
            path=str(control_dict),
            details={"expected_solver": solver},
        )

    match = APPLICATION_PATTERN.search(content)
    observed_solver = match.group("solver") if match else ""
    if observed_solver == solver:
        return DiagnosticResult(
            status=DiagnosticStatus.PASS,
            code="openfoam.solver_compatibility.application",
            message="controlDict application matches the selected solver.",
            path=str(control_dict),
            details={"solver": solver},
        )

    return DiagnosticResult(
        status=DiagnosticStatus.FAIL,
        code="openfoam.solver_compatibility.application",
        message="controlDict application does not match the selected solver.",
        path=str(control_dict),
        details={"expected_solver": solver, "observed_solver": observed_solver},
    )


def _required_fields_diagnostic(root: Path, *, solver: str) -> DiagnosticResult:
    required_fields = REQUIRED_FIELDS_BY_SOLVER.get(solver, set())
    missing_fields = sorted(
        field for field in required_fields if not (root / "0" / field).is_file()
    )
    if not missing_fields:
        return DiagnosticResult(
            status=DiagnosticStatus.PASS,
            code="openfoam.solver_compatibility.required_fields",
            message="Required initial fields exist for the selected solver.",
            path=str(root / "0"),
            details={"required_fields": ",".join(sorted(required_fields))},
        )

    return DiagnosticResult(
        status=DiagnosticStatus.FAIL,
        code="openfoam.solver_compatibility.required_fields",
        message="Required initial fields are missing for the selected solver.",
        path=str(root / "0"),
        details={"missing_fields": ",".join(missing_fields)},
    )


def _algorithm_diagnostic(root: Path, *, solver: str) -> DiagnosticResult:
    fv_solution = root / "system" / "fvSolution"
    required_algorithm = REQUIRED_ALGORITHM_BY_SOLVER.get(solver, "")
    content = _read_text(fv_solution)
    if content is None:
        return DiagnosticResult(
            status=DiagnosticStatus.FAIL,
            code="openfoam.solver_compatibility.algorithm",
            message="Could not read system/fvSolution to verify solver algorithm.",
            path=str(fv_solution),
            details={"required_algorithm": required_algorithm},
        )

    if required_algorithm and re.search(rf"\b{re.escape(required_algorithm)}\b", content):
        return DiagnosticResult(
            status=DiagnosticStatus.PASS,
            code="openfoam.solver_compatibility.algorithm",
            message="fvSolution contains the algorithm block required by the solver.",
            path=str(fv_solution),
            details={"required_algorithm": required_algorithm},
        )

    return DiagnosticResult(
        status=DiagnosticStatus.FAIL,
        code="openfoam.solver_compatibility.algorithm",
        message="fvSolution does not contain the algorithm block required by the solver.",
        path=str(fv_solution),
        details={"required_algorithm": required_algorithm},
    )


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
