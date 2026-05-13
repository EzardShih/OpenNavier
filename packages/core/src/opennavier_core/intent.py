from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from opennavier_core.case_build_spec import (
    CaseBuildCapabilityError,
    CaseBuildSpec,
    create_case_build_dry_run,
)
from opennavier_core.model_runner import (
    CommandRunner,
    ModelRunnerConfig,
    ModelRunnerRequest,
    ResponseKind,
    run_model_request,
)
from opennavier_core.questions import ClarifyingQuestionResult
from opennavier_core.session import AgentSession, ProvenanceRecord, create_agent_session
from opennavier_core.simulation_spec import SimulationSpec


class IntentModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IntentRequest(IntentModel):
    request_text: str = Field(min_length=1)
    workspace_root: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    expected_response_kind: ResponseKind | None = None


class IntentPlanRequest(IntentModel):
    simulation_spec: dict[str, object] | None = None
    case_build_spec: dict[str, object] | None = None
    approval_required: bool = True
    requested_artifacts: list[str] = Field(default_factory=list)

    @field_validator("approval_required")
    @classmethod
    def validate_approval_required(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("plan_request approval_required must remain true")
        return value

    @model_validator(mode="after")
    def validate_plan_input(self) -> "IntentPlanRequest":
        if self.simulation_spec is None and self.case_build_spec is None:
            raise ValueError(
                "plan_request must include simulation_spec or case_build_spec"
            )
        return self


class IntentResult(IntentModel):
    status: Literal[
        "draft_simulation_spec",
        "clarifying_questions",
        "draft_case_build_spec",
        "draft_plan_request",
        "rejected",
    ]
    kind: ResponseKind | None = None
    payload: dict[str, object] = Field(default_factory=dict)
    validation: dict[str, object] = Field(default_factory=dict)
    issues: list[dict[str, str]] = Field(default_factory=list)
    session: AgentSession
    raw_text: str = ""
    summary: str


STATUS_BY_KIND: dict[ResponseKind, str] = {
    "simulation_spec": "draft_simulation_spec",
    "clarifying_questions": "clarifying_questions",
    "case_build_spec": "draft_case_build_spec",
    "plan_request": "draft_plan_request",
}


def build_intent_prompt(request_text: str) -> str:
    return (
        "You are OpenNavier's local-only engineering intent interface.\n"
        "Return one JSON object with keys kind and payload.\n"
        "Allowed kind values are simulation_spec, clarifying_questions, "
        "case_build_spec, or plan_request.\n"
        "Use typed schemas only. Do not write OpenFOAM dictionaries, do not "
        "mutate files, and do not include raw dictionary text.\n"
        "A case_build_spec is only a draft typed artifact; deterministic "
        "validation, dry-run, and explicit approval happen before writes.\n"
        "Keep all assumptions local-only and engineer-verifiable.\n"
        "\n"
        "Engineering request:\n"
        f"{request_text}\n"
    )


def ask_intent(
    request: IntentRequest,
    config: ModelRunnerConfig,
    *,
    command_runner: CommandRunner | None = None,
) -> IntentResult:
    response = run_model_request(
        ModelRunnerRequest(
            prompt=build_intent_prompt(request.request_text),
        ),
        config,
        command_runner=command_runner,
    )

    try:
        validation = _validate_intent_payload(response.kind, response.payload)
    except CaseBuildCapabilityError as error:
        return IntentResult(
            status="rejected",
            kind=response.kind,
            payload=response.payload,
            issues=[
                {
                    "code": issue.code,
                    "message": issue.message,
                    "path": issue.path,
                }
                for issue in error.issues
            ],
            session=_session(
                request,
                config,
                action=f"rejected {response.kind}",
            ),
            raw_text=response.raw_text,
            summary=f"Rejected {response.kind}; deterministic validation failed.",
        )
    except ValidationError as error:
        return IntentResult(
            status="rejected",
            kind=response.kind,
            payload=response.payload,
            issues=[
                {
                    "code": "intent.schema_validation_failed",
                    "message": str(error.errors()[0].get("msg", "Validation error")),
                    "path": ".".join(str(part) for part in error.errors()[0].get("loc", ())),
                }
            ],
            session=_session(
                request,
                config,
                action=f"rejected {response.kind}",
            ),
            raw_text=response.raw_text,
            summary=f"Rejected {response.kind}; payload did not match the intent schema.",
        )

    return IntentResult(
        status=STATUS_BY_KIND[response.kind],
        kind=response.kind,
        payload=response.payload,
        validation=validation,
        session=_session(
            request,
            config,
            action=f"drafted {response.kind}",
        ),
        raw_text=response.raw_text,
        summary=f"Accepted typed {response.kind} draft from {config.provider}.",
    )


def _validate_intent_payload(
    kind: ResponseKind,
    payload: dict[str, object],
) -> dict[str, object]:
    if kind == "simulation_spec":
        spec = SimulationSpec.model_validate(payload)
        return {"simulation_spec": spec.model_dump(mode="json")}
    if kind == "clarifying_questions":
        questions = ClarifyingQuestionResult.model_validate(payload)
        return {"clarifying_questions": questions.model_dump(mode="json")}
    if kind == "case_build_spec":
        spec = CaseBuildSpec.model_validate(payload)
        dry_run = create_case_build_dry_run(spec)
        return {"dry_run": dry_run.model_dump(mode="json")}

    plan_request = IntentPlanRequest.model_validate(payload)
    validation: dict[str, object] = {
        "plan_request": plan_request.model_dump(mode="json")
    }
    if plan_request.simulation_spec is not None:
        validation["simulation_spec"] = SimulationSpec.model_validate(
            plan_request.simulation_spec
        ).model_dump(mode="json")
    if plan_request.case_build_spec is not None:
        case_build_spec = CaseBuildSpec.model_validate(
            plan_request.case_build_spec
        )
        validation["case_build_spec"] = case_build_spec.model_dump(mode="json")
        validation["case_build_dry_run"] = create_case_build_dry_run(
            case_build_spec
        ).model_dump(mode="json")
    return validation


def _session(
    request: IntentRequest,
    config: ModelRunnerConfig,
    *,
    action: str,
) -> AgentSession:
    return create_agent_session(
        workspace_root=request.workspace_root,
        session_id=request.session_id,
        engineering_intent=request.request_text,
        provenance=[
            ProvenanceRecord(
                tool=f"model_runner.{config.provider}",
                action=action,
            )
        ],
    )
