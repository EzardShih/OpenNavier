import json
from collections.abc import Sequence
from json import JSONDecodeError
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from opennavier_core.diagnostics import DiagnosticResult

SCHEMA_VERSION = "1.0"


class SessionLoadError(ValueError):
    """Raised when a session artifact cannot be loaded as a valid session."""


class SessionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProvenanceRecord(SessionModel):
    tool: str = Field(min_length=1)
    action: str = Field(min_length=1)


class ArtifactReference(SessionModel):
    kind: str = Field(min_length=1)
    path: str | Path
    provenance: ProvenanceRecord
    metadata: dict[str, str] = Field(default_factory=dict)


class CommandRecord(SessionModel):
    runner: str = Field(min_length=1)
    command: list[str] = Field(min_length=1)
    cwd: str | Path | None = None
    return_code: int | None = None
    log_path: str | Path | None = None
    provenance: ProvenanceRecord


class AgentSession(SessionModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    session_id: str = Field(min_length=1)
    workspace_root: str | Path
    engineering_intent: str = Field(min_length=1)
    validated_spec_refs: list[ArtifactReference] = Field(default_factory=list)
    plan_refs: list[ArtifactReference] = Field(default_factory=list)
    command_records: list[CommandRecord] = Field(default_factory=list)
    diagnostics: list[DiagnosticResult] = Field(default_factory=list)
    report_refs: list[ArtifactReference] = Field(default_factory=list)
    generated_artifacts: list[ArtifactReference] = Field(default_factory=list)
    provenance: list[ProvenanceRecord] = Field(default_factory=list)
    local_only: bool = True
    cloud_upload: bool = False

    @model_validator(mode="after")
    def validate_local_session_paths(self) -> Self:
        if not self.local_only:
            raise ValueError("Session artifacts must remain local-only")
        if self.cloud_upload:
            raise ValueError("Session artifacts do not allow cloud upload")

        root = Path(self.workspace_root).expanduser().resolve()
        if not root.is_dir():
            raise ValueError(f"Workspace root is not a directory: {root}")
        self.workspace_root = str(root)

        for reference in self._artifact_references():
            reference.path = _workspace_relative_path(root, reference.path)

        for command in self.command_records:
            if command.cwd is not None:
                command.cwd = _workspace_relative_path(root, command.cwd)
            if command.log_path is not None:
                command.log_path = _workspace_relative_path(root, command.log_path)

        return self

    def _artifact_references(self) -> list[ArtifactReference]:
        return [
            *self.validated_spec_refs,
            *self.plan_refs,
            *self.report_refs,
            *self.generated_artifacts,
        ]


def create_agent_session(
    *,
    workspace_root: Path | str,
    session_id: str,
    engineering_intent: str,
    validated_spec_refs: Sequence[ArtifactReference] = (),
    plan_refs: Sequence[ArtifactReference] = (),
    command_records: Sequence[CommandRecord] = (),
    diagnostics: Sequence[DiagnosticResult] = (),
    report_refs: Sequence[ArtifactReference] = (),
    generated_artifacts: Sequence[ArtifactReference] = (),
    provenance: Sequence[ProvenanceRecord] = (),
) -> AgentSession:
    return AgentSession(
        session_id=session_id,
        workspace_root=workspace_root,
        engineering_intent=engineering_intent,
        validated_spec_refs=list(validated_spec_refs),
        plan_refs=list(plan_refs),
        command_records=list(command_records),
        diagnostics=list(diagnostics),
        report_refs=list(report_refs),
        generated_artifacts=list(generated_artifacts),
        provenance=list(provenance),
    )


def load_agent_session(path: Path | str) -> AgentSession:
    session_path = Path(path)
    try:
        payload = session_path.read_text(encoding="utf-8")
    except OSError as error:
        raise SessionLoadError(f"Unable to read session artifact: {session_path}") from error

    try:
        data = json.loads(payload)
    except JSONDecodeError as error:
        raise SessionLoadError(f"Malformed JSON in session artifact: {session_path}") from error

    try:
        return AgentSession.model_validate(data)
    except ValidationError as error:
        raise SessionLoadError(f"Invalid session artifact: {session_path}") from error


def write_agent_session(session: AgentSession, output_path: Path | str) -> Path:
    root = Path(session.workspace_root)
    output = _workspace_path(root, output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(session_to_json(session), encoding="utf-8")
    return output


def session_to_json(session: AgentSession) -> str:
    return (
        json.dumps(
            session.model_dump(mode="json"),
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def _workspace_relative_path(root: Path, value: Path | str) -> str:
    path = _workspace_path(root, value)
    relative_path = path.relative_to(root)
    return "." if relative_path == Path(".") else relative_path.as_posix()


def _workspace_path(root: Path, value: Path | str) -> Path:
    path = Path(value).expanduser()
    candidate = _workspace_candidate(root, path)
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError(f"Path escapes workspace root: {value}") from error
    return candidate


def _workspace_candidate(root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path.resolve()

    existing_parent = _nearest_existing_parent(path)
    if existing_parent is not None:
        try:
            existing_parent.resolve().relative_to(root)
        except ValueError:
            pass
        else:
            return path.resolve()

    return (root / path).resolve()


def _nearest_existing_parent(path: Path) -> Path | None:
    for candidate in [path, *path.parents]:
        if candidate.exists():
            return candidate
    return None
