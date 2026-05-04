from enum import StrEnum

from pydantic import BaseModel, Field


class DiagnosticStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"


class DiagnosticResult(BaseModel):
    status: DiagnosticStatus
    code: str
    message: str
    path: str
    details: dict[str, str] = Field(default_factory=dict)


def has_failures(diagnostics: list[DiagnosticResult]) -> bool:
    return any(diagnostic.status is DiagnosticStatus.FAIL for diagnostic in diagnostics)
