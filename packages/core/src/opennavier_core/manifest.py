from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from opennavier_core.diagnostics import DiagnosticStatus

SCHEMA_VERSION = "1.0"


class ReproducibilityManifest(BaseModel):
    schema_version: str = SCHEMA_VERSION
    generated_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds")
    )
    case_path: str
    diagnostics_summary: dict[str, int]
    diagnostic_codes: list[str]
    generated_artifacts: list[str]
    cloud_upload: bool = False
    openfoam_executed: bool = False


def build_reproducibility_manifest(
    *,
    case_path: Path | str,
    diagnostics: Sequence[object],
    generated_artifacts: Sequence[Path | str],
) -> ReproducibilityManifest:
    return ReproducibilityManifest(
        case_path=str(Path(case_path).resolve()),
        diagnostics_summary=_diagnostics_summary(diagnostics),
        diagnostic_codes=[str(diagnostic.code) for diagnostic in diagnostics],
        generated_artifacts=[str(Path(artifact).resolve()) for artifact in generated_artifacts],
    )


def write_reproducibility_manifest(
    *,
    case_path: Path | str,
    diagnostics: Sequence[object],
    generated_artifacts: Sequence[Path | str],
    output_path: Path | str,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = build_reproducibility_manifest(
        case_path=case_path,
        diagnostics=diagnostics,
        generated_artifacts=generated_artifacts,
    )
    output.write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return output


def _diagnostics_summary(diagnostics: Sequence[object]) -> dict[str, int]:
    return {
        "total": len(diagnostics),
        "passed": sum(
            diagnostic.status == DiagnosticStatus.PASS for diagnostic in diagnostics
        ),
        "failed": sum(
            diagnostic.status == DiagnosticStatus.FAIL for diagnostic in diagnostics
        ),
        "warnings": sum(
            diagnostic.status == DiagnosticStatus.WARN for diagnostic in diagnostics
        ),
    }
