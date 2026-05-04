from opennavier.openfoam.mesh_quality import (
    MeshQualitySummary,
    diagnose_mesh_quality,
    parse_check_mesh,
)
from opennavier_core.diagnostics import DiagnosticStatus


def test_parse_check_mesh_extracts_passing_summary_values() -> None:
    content = """
Mesh non-orthogonality Max: 42 average: 8
Max skewness = 1.7 OK.
Mesh OK.
"""

    summary = parse_check_mesh(content)

    assert summary == MeshQualitySummary(
        mesh_ok=True,
        max_non_orthogonality=42.0,
        max_skewness=1.7,
    )


def test_parse_check_mesh_extracts_failed_status() -> None:
    content = """
***Max skewness = 12, 1 highly skew faces detected which may impair the quality
Failed 1 mesh checks.
"""

    summary = parse_check_mesh(content)

    assert summary.mesh_ok is False
    assert summary.max_skewness == 12.0


def test_parse_check_mesh_ignores_unrelated_lines() -> None:
    content = """
Create time
Time = 0
End
"""

    assert parse_check_mesh(content) == MeshQualitySummary()


def test_diagnose_mesh_quality_passes_for_mesh_ok_summary() -> None:
    diagnostic = diagnose_mesh_quality(
        MeshQualitySummary(mesh_ok=True, max_non_orthogonality=20.0, max_skewness=1.0)
    )

    assert diagnostic.status is DiagnosticStatus.PASS
    assert diagnostic.code == "openfoam.mesh_quality.ok"


def test_diagnose_mesh_quality_fails_for_explicit_failed_mesh_check() -> None:
    diagnostic = diagnose_mesh_quality(MeshQualitySummary(mesh_ok=False))

    assert diagnostic.status is DiagnosticStatus.FAIL
    assert diagnostic.code == "openfoam.mesh_quality.failed"


def test_diagnose_mesh_quality_warns_for_high_non_orthogonality() -> None:
    diagnostic = diagnose_mesh_quality(
        MeshQualitySummary(mesh_ok=True, max_non_orthogonality=75.0, max_skewness=1.0)
    )

    assert diagnostic.status is DiagnosticStatus.WARN
    assert diagnostic.code == "openfoam.mesh_quality.warning"
    assert diagnostic.details["non_orthogonality"] == "75.0"


def test_diagnose_mesh_quality_warns_for_missing_summary_values() -> None:
    diagnostic = diagnose_mesh_quality(MeshQualitySummary())

    assert diagnostic.status is DiagnosticStatus.WARN
    assert diagnostic.code == "openfoam.mesh_quality.incomplete"
