from pathlib import Path

from opennavier.openfoam.residuals import (
    ResidualRecord,
    diagnose_residuals,
    parse_residuals,
)
from opennavier_core.diagnostics import DiagnosticStatus


def test_parse_residuals_extracts_scalar_and_vector_component_records() -> None:
    content = """
Time = 1
smoothSolver:  Solving for Ux, Initial residual = 0.1, Final residual = 0.001, No Iterations 2
smoothSolver:  Solving for Uy, Initial residual = 0.2, Final residual = 0.002, No Iterations 3
GAMG:  Solving for p, Initial residual = 0.05, Final residual = 0.0005, No Iterations 4
"""

    records = parse_residuals(content)

    assert records == [
        ResidualRecord(field="Ux", initial=0.1, final=0.001, iterations=2),
        ResidualRecord(field="Uy", initial=0.2, final=0.002, iterations=3),
        ResidualRecord(field="p", initial=0.05, final=0.0005, iterations=4),
    ]


def test_parse_residuals_preserves_multiple_timesteps() -> None:
    content = """
Time = 1
Solving for p, Initial residual = 1e-02, Final residual = 1e-04, No Iterations 2
Time = 2
Solving for p, Initial residual = 5e-03, Final residual = 5e-05, No Iterations 2
"""

    records = parse_residuals(content)

    assert [record.final for record in records] == [1e-04, 5e-05]


def test_parse_residuals_extracts_dotted_field_names() -> None:
    content = (
        "PBiCGStab:  Solving for alpha.water, Initial residual = 0.12, "
        "Final residual = 8e-05, No Iterations 3"
    )

    records = parse_residuals(content)

    assert records == [
        ResidualRecord(field="alpha.water", initial=0.12, final=8e-05, iterations=3)
    ]


def test_parse_residuals_ignores_unrelated_log_lines() -> None:
    content = """
Create time
ExecutionTime = 1.23 s
End
"""

    assert parse_residuals(content) == []


def test_diagnose_residuals_passes_when_final_residuals_are_below_threshold() -> None:
    diagnostic = diagnose_residuals(
        [ResidualRecord(field="p", initial=0.01, final=1e-05, iterations=2)]
    )

    assert diagnostic.status is DiagnosticStatus.PASS
    assert diagnostic.code == "openfoam.residuals.convergence"


def test_diagnose_residuals_warns_when_no_records_are_found() -> None:
    diagnostic = diagnose_residuals([])

    assert diagnostic.status is DiagnosticStatus.WARN
    assert diagnostic.code == "openfoam.residuals.missing"


def test_diagnose_residuals_warns_when_final_residuals_remain_high() -> None:
    diagnostic = diagnose_residuals(
        [ResidualRecord(field="p", initial=0.1, final=0.02, iterations=2)]
    )

    assert diagnostic.status is DiagnosticStatus.WARN
    assert diagnostic.code == "openfoam.residuals.high_final"
    assert diagnostic.details["fields"] == "p"


def test_diagnose_residuals_uses_latest_record_per_field() -> None:
    diagnostic = diagnose_residuals(
        [
            ResidualRecord(field="p", initial=0.1, final=0.02, iterations=2),
            ResidualRecord(field="p", initial=0.01, final=1e-05, iterations=2),
        ]
    )

    assert diagnostic.status is DiagnosticStatus.PASS
    assert diagnostic.code == "openfoam.residuals.convergence"


def test_diagnose_residuals_reports_unreadable_log_path() -> None:
    missing_log = Path(".tmp") / "missing-residual.log"

    diagnostic = diagnose_residuals(missing_log)

    assert diagnostic.status is DiagnosticStatus.FAIL
    assert diagnostic.code == "openfoam.residuals.unreadable"
    assert diagnostic.path == str(missing_log)
