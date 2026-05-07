import json
from collections.abc import Generator
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

import pytest
from opennavier_core.diagnostic_artifact import (
    DiagnosticsArtifact,
    build_diagnostics_artifact,
    diagnostics_artifact_to_json,
    write_diagnostics_artifact,
)
from opennavier_core.diagnostics import DiagnosticResult, DiagnosticStatus
from pydantic import ValidationError


@pytest.fixture
def artifact_tmp_path() -> Generator[Path, None, None]:
    path = Path(".tmp") / f"diagnostics-artifact-{uuid4().hex}"
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        rmtree(path, ignore_errors=True)


def diagnostic(
    *,
    status: DiagnosticStatus,
    code: str,
    message: str,
    path: str,
    details: dict[str, str] | None = None,
) -> DiagnosticResult:
    return DiagnosticResult(
        status=status,
        code=code,
        message=message,
        path=path,
        details=details or {},
    )


def test_build_diagnostics_artifact_normalizes_records_and_counts_statuses() -> None:
    artifact = build_diagnostics_artifact(
        [
            diagnostic(
                status=DiagnosticStatus.PASS,
                code="openfoam.required_directory.system",
                message="Required directory exists.",
                path="case/system",
                details={"component": "system"},
            ),
            diagnostic(
                status=DiagnosticStatus.FAIL,
                code="openfoam.required_file.system_controlDict",
                message="Missing required system/controlDict file.",
                path="case/system/controlDict",
            ),
            diagnostic(
                status=DiagnosticStatus.WARN,
                code="openfoam.mesh_quality.non_orthogonality",
                message="Maximum non-orthogonality is high.",
                path="case/log.checkMesh",
                details={"non_orthogonality": "75.0"},
            ),
        ]
    )

    assert artifact.schema_version == "1.0"
    assert artifact.artifact_type == "diagnostics"
    assert artifact.local_only is True
    assert artifact.cloud_upload is False
    assert artifact.counts_by_status == {"PASS": 1, "WARN": 1, "FAIL": 1}
    assert [record.code for record in artifact.diagnostics] == [
        "openfoam.required_file.system_controlDict",
        "openfoam.mesh_quality.non_orthogonality",
        "openfoam.required_directory.system",
    ]
    assert artifact.diagnostics[0].metadata == {}
    assert artifact.diagnostics[1].metadata == {"non_orthogonality": "75.0"}
    assert artifact.diagnostics[2].metadata == {"component": "system"}


def test_diagnostics_artifact_json_is_deterministically_ordered() -> None:
    diagnostics = [
        diagnostic(
            status=DiagnosticStatus.WARN,
            code="openfoam.mesh_quality.non_orthogonality",
            message="Maximum non-orthogonality is high.",
            path="case/log.checkMesh",
            details={"zeta": "last", "alpha": "first"},
        ),
        diagnostic(
            status=DiagnosticStatus.FAIL,
            code="openfoam.required_file.system_controlDict",
            message="Missing required system/controlDict file.",
            path="case/system/controlDict",
        ),
        diagnostic(
            status=DiagnosticStatus.PASS,
            code="openfoam.required_directory.system",
            message="Required directory exists.",
            path="case/system",
        ),
    ]

    content = diagnostics_artifact_to_json(build_diagnostics_artifact(diagnostics))
    reversed_content = diagnostics_artifact_to_json(
        build_diagnostics_artifact(list(reversed(diagnostics)))
    )

    assert content == reversed_content
    assert content.endswith("\n")
    payload = json.loads(content)
    assert list(payload["counts_by_status"]) == ["FAIL", "PASS", "WARN"]
    assert set(payload["diagnostics"][0]) == {
        "code",
        "message",
        "metadata",
        "path",
        "status",
    }
    assert "details" not in payload["diagnostics"][0]


def test_diagnostics_artifact_rejects_cloud_upload_flags() -> None:
    with pytest.raises(ValidationError, match="local-only"):
        DiagnosticsArtifact.model_validate({"local_only": False})

    with pytest.raises(ValidationError, match="cloud upload"):
        DiagnosticsArtifact.model_validate({"cloud_upload": True})


def test_write_diagnostics_artifact_creates_parents_and_overwrites_by_default(
    artifact_tmp_path: Path,
) -> None:
    output_path = artifact_tmp_path / "diagnostics" / "diagnostics.json"
    first_artifact = build_diagnostics_artifact(
        [
            diagnostic(
                status=DiagnosticStatus.PASS,
                code="openfoam.required_directory.system",
                message="Required directory exists.",
                path="case/system",
            )
        ]
    )
    replacement_artifact = build_diagnostics_artifact(
        [
            diagnostic(
                status=DiagnosticStatus.FAIL,
                code="openfoam.required_file.system_controlDict",
                message="Missing required system/controlDict file.",
                path="case/system/controlDict",
            )
        ]
    )

    written_path = write_diagnostics_artifact(first_artifact, output_path)
    write_diagnostics_artifact(replacement_artifact, output_path)

    assert written_path == output_path
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["counts_by_status"] == {"FAIL": 1, "PASS": 0, "WARN": 0}
    assert payload["diagnostics"][0]["code"] == "openfoam.required_file.system_controlDict"

    with pytest.raises(FileExistsError):
        write_diagnostics_artifact(first_artifact, output_path, overwrite=False)
