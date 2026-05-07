import json
from collections.abc import Generator
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

import pytest
from opennavier_core.diagnostics import DiagnosticResult, DiagnosticStatus
from opennavier_core.session import (
    AgentSession,
    ArtifactReference,
    ProvenanceRecord,
    SessionLoadError,
    create_agent_session,
    load_agent_session,
    session_to_json,
    write_agent_session,
)
from pydantic import ValidationError


@pytest.fixture
def workspace_tmp_path() -> Generator[Path, None, None]:
    path = Path(".tmp") / f"session-artifact-{uuid4().hex}"
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        rmtree(path, ignore_errors=True)


def provenance() -> ProvenanceRecord:
    return ProvenanceRecord(tool="opennavier.test", action="wrote artifact")


def test_create_session_defaults_to_local_only_and_stores_audit_trail(
    workspace_tmp_path: Path,
) -> None:
    (workspace_tmp_path / "specs").mkdir()
    spec_path = workspace_tmp_path / "specs" / "simulation.json"
    spec_path.write_text("{}", encoding="utf-8")
    session = create_agent_session(
        workspace_root=workspace_tmp_path,
        session_id="session-001",
        engineering_intent="Run a lid-driven cavity case.",
        validated_spec_refs=[
            ArtifactReference(
                kind="simulation_spec",
                path=spec_path,
                provenance=provenance(),
            )
        ],
        diagnostics=[
            DiagnosticResult(
                status=DiagnosticStatus.PASS,
                code="openfoam.required_directory.system",
                message="Required directory exists",
                path="case/system",
            )
        ],
        generated_artifacts=[
            ArtifactReference(
                kind="case_file",
                path="case/system/controlDict",
                provenance=provenance(),
            )
        ],
    )

    assert session.schema_version == "1.0"
    assert session.workspace_root == str(workspace_tmp_path.resolve())
    assert session.engineering_intent == "Run a lid-driven cavity case."
    assert session.validated_spec_refs[0].path == "specs/simulation.json"
    assert session.generated_artifacts[0].provenance.tool == "opennavier.test"
    assert session.diagnostics[0].code == "openfoam.required_directory.system"
    assert session.local_only is True
    assert session.cloud_upload is False


def test_session_schema_rejects_unknown_fields(workspace_tmp_path: Path) -> None:
    payload = {
        "schema_version": "1.0",
        "session_id": "session-001",
        "workspace_root": str(workspace_tmp_path),
        "engineering_intent": "Run a lid-driven cavity case.",
        "local_only": True,
        "cloud_upload": False,
        "unexpected": "not part of the session contract",
    }

    with pytest.raises(ValidationError, match="unexpected"):
        AgentSession.model_validate(payload)


def test_session_rejects_cloud_upload_opt_in(workspace_tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="cloud upload"):
        AgentSession.model_validate(
            {
                "schema_version": "1.0",
                "session_id": "session-001",
                "workspace_root": str(workspace_tmp_path),
                "engineering_intent": "Run a lid-driven cavity case.",
                "cloud_upload": True,
            }
        )


def test_session_rejects_artifact_references_that_escape_workspace(
    workspace_tmp_path: Path,
) -> None:
    with pytest.raises(ValidationError, match="escapes workspace root"):
        create_agent_session(
            workspace_root=workspace_tmp_path,
            session_id="session-001",
            engineering_intent="Run a lid-driven cavity case.",
            report_refs=[
                ArtifactReference(
                    kind="report",
                    path="../outside/report.md",
                    provenance=provenance(),
                )
            ],
        )


def test_session_rejects_command_log_paths_that_escape_workspace(
    workspace_tmp_path: Path,
) -> None:
    with pytest.raises(ValidationError, match="escapes workspace root"):
        AgentSession.model_validate(
            {
                "schema_version": "1.0",
                "session_id": "session-001",
                "workspace_root": str(workspace_tmp_path),
                "engineering_intent": "Run a lid-driven cavity case.",
                "command_records": [
                    {
                        "runner": "local",
                        "command": ["icoFoam", "-case", "case"],
                        "log_path": str(workspace_tmp_path.resolve().parent / "solver.log"),
                        "provenance": provenance().model_dump(),
                    }
                ],
            }
        )


def test_session_rejects_diagnostic_paths_that_escape_workspace(
    workspace_tmp_path: Path,
) -> None:
    with pytest.raises(ValidationError, match="escapes workspace root"):
        create_agent_session(
            workspace_root=workspace_tmp_path,
            session_id="session-001",
            engineering_intent="Run a lid-driven cavity case.",
            diagnostics=[
                DiagnosticResult(
                    status=DiagnosticStatus.FAIL,
                    code="openfoam.path.escape",
                    message="Diagnostic path escapes the workspace.",
                    path="../outside.txt",
                )
            ],
        )


def test_session_rejects_blank_workspace_root() -> None:
    with pytest.raises(ValidationError, match="must not be blank"):
        AgentSession.model_validate(
            {
                "schema_version": "1.0",
                "session_id": "session-001",
                "workspace_root": "",
                "engineering_intent": "Run a lid-driven cavity case.",
            }
        )


def test_session_rejects_blank_artifact_paths(workspace_tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="must not be blank"):
        create_agent_session(
            workspace_root=workspace_tmp_path,
            session_id="session-001",
            engineering_intent="Run a lid-driven cavity case.",
            report_refs=[
                ArtifactReference(
                    kind="report",
                    path="",
                    provenance=provenance(),
                )
            ],
        )


def test_session_rejects_blank_diagnostic_paths(workspace_tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="must not be blank"):
        create_agent_session(
            workspace_root=workspace_tmp_path,
            session_id="session-001",
            engineering_intent="Run a lid-driven cavity case.",
            diagnostics=[
                DiagnosticResult(
                    status=DiagnosticStatus.FAIL,
                    code="openfoam.blank.path",
                    message="Diagnostic path is blank.",
                    path="",
                )
            ],
        )


@pytest.mark.parametrize("field_name", ["cwd", "log_path"])
def test_session_rejects_blank_command_paths(
    workspace_tmp_path: Path,
    field_name: str,
) -> None:
    command_record = {
        "runner": "local",
        "command": ["icoFoam", "-case", "case"],
        "provenance": provenance().model_dump(),
        field_name: "",
    }

    with pytest.raises(ValidationError, match="must not be blank"):
        AgentSession.model_validate(
            {
                "schema_version": "1.0",
                "session_id": "session-001",
                "workspace_root": str(workspace_tmp_path),
                "engineering_intent": "Run a lid-driven cavity case.",
                "command_records": [command_record],
            }
        )


def test_load_session_validates_existing_artifact_and_normalizes_paths(
    workspace_tmp_path: Path,
) -> None:
    (workspace_tmp_path / "reports").mkdir()
    session_path = workspace_tmp_path / "session.onv.json"
    session_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "session_id": "session-001",
                "workspace_root": str(workspace_tmp_path.resolve()),
                "engineering_intent": "Run a lid-driven cavity case.",
                "report_refs": [
                    {
                        "kind": "report",
                        "path": str(workspace_tmp_path / "reports" / "report.md"),
                        "provenance": provenance().model_dump(),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    session = load_agent_session(session_path)

    assert session.report_refs[0].path == "reports/report.md"
    assert session.local_only is True
    assert session.cloud_upload is False


def test_load_session_reports_malformed_json(workspace_tmp_path: Path) -> None:
    session_path = workspace_tmp_path / "session.onv.json"
    session_path.write_text("{ invalid", encoding="utf-8")

    with pytest.raises(SessionLoadError, match="Malformed JSON"):
        load_agent_session(session_path)


def test_write_session_uses_deterministic_json_output(workspace_tmp_path: Path) -> None:
    session = create_agent_session(
        workspace_root=workspace_tmp_path,
        session_id="session-001",
        engineering_intent="Run a lid-driven cavity case.",
        plan_refs=[
            ArtifactReference(
                kind="simulation_plan",
                path="plans/cavity.json",
                provenance=provenance(),
            )
        ],
    )
    output_path = workspace_tmp_path / "session.onv.json"

    write_agent_session(session, output_path)

    content = output_path.read_text(encoding="utf-8")
    assert content == session_to_json(session)
    assert content.endswith("\n")
    assert "generated_at" not in content
    assert json.loads(content)["plan_refs"][0]["path"] == "plans/cavity.json"
