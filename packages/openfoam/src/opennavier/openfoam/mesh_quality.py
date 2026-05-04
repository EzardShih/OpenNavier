import re

from opennavier_core.diagnostics import DiagnosticResult, DiagnosticStatus
from pydantic import BaseModel

NON_ORTHOGONALITY_PATTERN = re.compile(
    r"Mesh non-orthogonality Max:\s*(?P<value>[+-]?(?:\d+(?:\.\d*)?|\.\d+))"
)
SKEWNESS_PATTERN = re.compile(
    r"Max skewness\s*=\s*(?P<value>[+-]?(?:\d+(?:\.\d*)?|\.\d+))"
)
DEFAULT_NON_ORTHOGONALITY_WARN_THRESHOLD = 70.0
DEFAULT_SKEWNESS_WARN_THRESHOLD = 4.0


class MeshQualitySummary(BaseModel):
    mesh_ok: bool | None = None
    max_non_orthogonality: float | None = None
    max_skewness: float | None = None


def parse_check_mesh(content: str) -> MeshQualitySummary:
    non_orthogonality_match = NON_ORTHOGONALITY_PATTERN.search(content)
    skewness_match = SKEWNESS_PATTERN.search(content)
    mesh_ok = _parse_mesh_ok(content)

    return MeshQualitySummary(
        mesh_ok=mesh_ok,
        max_non_orthogonality=(
            float(non_orthogonality_match.group("value"))
            if non_orthogonality_match
            else None
        ),
        max_skewness=float(skewness_match.group("value")) if skewness_match else None,
    )


def diagnose_mesh_quality(
    summary: MeshQualitySummary,
    *,
    non_orthogonality_warn_threshold: float = DEFAULT_NON_ORTHOGONALITY_WARN_THRESHOLD,
    skewness_warn_threshold: float = DEFAULT_SKEWNESS_WARN_THRESHOLD,
) -> DiagnosticResult:
    if summary.mesh_ok is False:
        return DiagnosticResult(
            status=DiagnosticStatus.FAIL,
            code="openfoam.mesh_quality.failed",
            message="OpenFOAM checkMesh reported failed mesh checks.",
            path="",
            details={},
        )

    warning_details: dict[str, str] = {}
    if (
        summary.max_non_orthogonality is not None
        and summary.max_non_orthogonality > non_orthogonality_warn_threshold
    ):
        warning_details["non_orthogonality"] = str(summary.max_non_orthogonality)
    if (
        summary.max_skewness is not None
        and summary.max_skewness > skewness_warn_threshold
    ):
        warning_details["skewness"] = str(summary.max_skewness)

    if warning_details:
        return DiagnosticResult(
            status=DiagnosticStatus.WARN,
            code="openfoam.mesh_quality.warning",
            message="OpenFOAM mesh quality metrics exceed conservative warning thresholds.",
            path="",
            details=warning_details,
        )

    if summary.mesh_ok is True:
        return DiagnosticResult(
            status=DiagnosticStatus.PASS,
            code="openfoam.mesh_quality.ok",
            message="OpenFOAM checkMesh reported Mesh OK.",
            path="",
            details={},
        )

    return DiagnosticResult(
        status=DiagnosticStatus.WARN,
        code="openfoam.mesh_quality.incomplete",
        message="OpenFOAM checkMesh summary did not include a clear mesh status.",
        path="",
        details={},
    )


def _parse_mesh_ok(content: str) -> bool | None:
    if "Mesh OK." in content:
        return True
    if re.search(r"Failed\s+\d+\s+mesh checks?", content):
        return False
    return None
