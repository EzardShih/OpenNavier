from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from opennavier_core.diagnostics import DiagnosticResult, DiagnosticStatus

SCHEMA_VERSION = "1.0"
ARTIFACT_TYPE = "diagnostics"

JsonScalar = str | int | float | bool | None

_STATUS_SORT_ORDER = {
    DiagnosticStatus.FAIL: 0,
    DiagnosticStatus.WARN: 1,
    DiagnosticStatus.PASS: 2,
}
_COUNT_STATUSES = (
    DiagnosticStatus.PASS,
    DiagnosticStatus.WARN,
    DiagnosticStatus.FAIL,
)


class DiagnosticsArtifactModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DiagnosticRecord(DiagnosticsArtifactModel):
    status: DiagnosticStatus
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    path: str = Field(min_length=1)
    metadata: dict[str, JsonScalar] = Field(default_factory=dict)


DiagnosticInput = DiagnosticResult | DiagnosticRecord | Mapping[str, object]


class DiagnosticsArtifact(DiagnosticsArtifactModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    artifact_type: Literal["diagnostics"] = ARTIFACT_TYPE
    local_only: bool = True
    cloud_upload: bool = False
    counts_by_status: dict[str, int] = Field(default_factory=dict)
    diagnostics: list[DiagnosticRecord] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize_artifact(self) -> Self:
        if not self.local_only:
            raise ValueError("Diagnostics artifacts must remain local-only")
        if self.cloud_upload:
            raise ValueError("Diagnostics artifacts do not allow cloud upload")

        self.diagnostics = _sort_diagnostic_records(self.diagnostics)
        self.counts_by_status = _count_diagnostics_by_status(self.diagnostics)
        return self


def build_diagnostics_artifact(
    diagnostics: Sequence[DiagnosticInput],
) -> DiagnosticsArtifact:
    return DiagnosticsArtifact(
        diagnostics=[_coerce_diagnostic_record(diagnostic) for diagnostic in diagnostics]
    )


def diagnostics_artifact_to_json(artifact: DiagnosticsArtifact) -> str:
    return json.dumps(artifact.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def write_diagnostics_artifact(
    artifact: DiagnosticsArtifact | Sequence[DiagnosticInput],
    output_path: Path | str,
    *,
    overwrite: bool = True,
) -> Path:
    output = Path(output_path)
    if output.exists() and not overwrite:
        raise FileExistsError(f"Diagnostics artifact already exists: {output}")

    diagnostics_artifact = artifact
    if not isinstance(artifact, DiagnosticsArtifact):
        diagnostics_artifact = build_diagnostics_artifact(artifact)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(diagnostics_artifact_to_json(diagnostics_artifact), encoding="utf-8")
    return output


def _coerce_diagnostic_record(diagnostic: DiagnosticInput) -> DiagnosticRecord:
    if isinstance(diagnostic, DiagnosticRecord):
        return diagnostic

    if isinstance(diagnostic, DiagnosticResult):
        return DiagnosticRecord(
            status=diagnostic.status,
            code=diagnostic.code,
            message=diagnostic.message,
            path=diagnostic.path,
            metadata=dict(diagnostic.details),
        )

    payload = dict(diagnostic)
    if "metadata" not in payload and "details" in payload:
        payload["metadata"] = payload.pop("details")
    return DiagnosticRecord.model_validate(payload)


def _sort_diagnostic_records(records: Sequence[DiagnosticRecord]) -> list[DiagnosticRecord]:
    return sorted(
        records,
        key=lambda record: (
            _STATUS_SORT_ORDER[record.status],
            record.code,
            record.path,
            record.message,
            json.dumps(record.metadata, sort_keys=True),
        ),
    )


def _count_diagnostics_by_status(records: Sequence[DiagnosticRecord]) -> dict[str, int]:
    return {
        status.value: sum(record.status == status for record in records)
        for status in _COUNT_STATUSES
    }
