from collections.abc import Callable, Iterable
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


DiagnosticSource = Callable[[], Iterable[DiagnosticResult]]


class DiagnosticCollector:
    def __init__(self, sources: Iterable[DiagnosticSource]) -> None:
        self._sources = tuple(sources)

    def collect(self) -> list[DiagnosticResult]:
        diagnostics: list[DiagnosticResult] = []
        for source in self._sources:
            diagnostics.extend(source())
        return diagnostics


def has_failures(diagnostics: list[DiagnosticResult]) -> bool:
    return any(diagnostic.status is DiagnosticStatus.FAIL for diagnostic in diagnostics)
