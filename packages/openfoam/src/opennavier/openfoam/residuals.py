import re
from collections.abc import Sequence
from pathlib import Path

from opennavier_core.diagnostics import DiagnosticResult, DiagnosticStatus
from pydantic import BaseModel

RESIDUAL_PATTERN = re.compile(
    r"Solving for (?P<field>[^,\s]+),\s+"
    r"Initial residual = (?P<initial>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?),\s+"
    r"Final residual = (?P<final>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?),\s+"
    r"No Iterations (?P<iterations>\d+)"
)
DEFAULT_FINAL_RESIDUAL_THRESHOLD = 1e-3


class ResidualRecord(BaseModel):
    field: str
    initial: float
    final: float
    iterations: int


def parse_residuals(content: str) -> list[ResidualRecord]:
    return [
        ResidualRecord(
            field=match.group("field"),
            initial=float(match.group("initial")),
            final=float(match.group("final")),
            iterations=int(match.group("iterations")),
        )
        for match in RESIDUAL_PATTERN.finditer(content)
    ]


def diagnose_residuals(
    residuals: Sequence[ResidualRecord] | Path,
    *,
    final_residual_threshold: float = DEFAULT_FINAL_RESIDUAL_THRESHOLD,
) -> DiagnosticResult:
    if isinstance(residuals, Path):
        try:
            residuals = parse_residuals(residuals.read_text(encoding="utf-8"))
        except (OSError, UnicodeError) as error:
            return DiagnosticResult(
                status=DiagnosticStatus.FAIL,
                code="openfoam.residuals.unreadable",
                message=f"Could not read OpenFOAM solver log: {residuals}",
                path=str(residuals),
                details={"read_error": type(error).__name__},
            )

    if not residuals:
        return DiagnosticResult(
            status=DiagnosticStatus.WARN,
            code="openfoam.residuals.missing",
            message="No OpenFOAM residual records were found.",
            path="",
            details={},
        )

    latest_records_by_field = {record.field: record for record in residuals}
    high_records = [
        record
        for record in latest_records_by_field.values()
        if record.final > final_residual_threshold
    ]
    if high_records:
        fields = ",".join(record.field for record in high_records)
        return DiagnosticResult(
            status=DiagnosticStatus.WARN,
            code="openfoam.residuals.high_final",
            message="Final residuals remain above the configured threshold.",
            path="",
            details={
                "threshold": str(final_residual_threshold),
                "fields": fields,
            },
        )

    return DiagnosticResult(
        status=DiagnosticStatus.PASS,
        code="openfoam.residuals.convergence",
        message="Final residuals are below the configured threshold.",
        path="",
        details={"threshold": str(final_residual_threshold)},
    )
