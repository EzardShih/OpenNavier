from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from opennavier_core.case_build_spec import CaseBuildSpec
from opennavier_core.planner import plan_simulation
from opennavier_core.questions import ClarifyingQuestion, build_clarifying_questions
from opennavier_core.simulation_spec import SimulationSpec


class ClarificationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ClarificationState(ClarificationModel):
    request_text: str
    partial_spec: dict[str, object] = Field(default_factory=dict)
    case_build_spec: dict[str, object] | None = None
    answers: list[str] = Field(default_factory=list)
    turns: int = 0
    max_turns: int = 5
    stopped: bool = False
    stop_reason: str | None = None


class ClarificationStatus(ClarificationModel):
    status: Literal[
        "more_questions",
        "ready_to_plan",
        "complete_but_not_executable",
        "stopped",
    ]
    questions: list[ClarifyingQuestion] = Field(default_factory=list)
    planning_result: dict[str, object] | None = None
    stop_reason: str | None = None


def clarification_update(
    state: ClarificationState,
    user_answer: dict[str, object],
) -> ClarificationState:
    if user_answer.get("cancel") is True:
        return state.model_copy(
            update={"stopped": True, "stop_reason": "cancelled", "turns": state.turns + 1}
        )
    if user_answer.get("declined_required_information") is True:
        return state.model_copy(
            update={
                "stopped": True,
                "stop_reason": "declined_required_information",
                "turns": state.turns + 1,
            }
        )

    partial_update = user_answer.get("partial_spec", {})
    if not isinstance(partial_update, dict):
        partial_update = {}

    answers = [*state.answers]
    answer_summary = user_answer.get("answer_summary")
    if isinstance(answer_summary, str) and answer_summary:
        answers.append(answer_summary)

    case_build_spec = state.case_build_spec
    case_build_spec_update = user_answer.get("case_build_spec")
    if isinstance(case_build_spec_update, dict):
        case_build_spec = case_build_spec_update

    return state.model_copy(
        update={
            "partial_spec": _deep_merge(state.partial_spec, partial_update),
            "case_build_spec": case_build_spec,
            "answers": answers,
            "turns": state.turns + 1,
        }
    )


def clarification_status(state: ClarificationState) -> ClarificationStatus:
    if state.stopped:
        return ClarificationStatus(status="stopped", stop_reason=state.stop_reason)

    question_result = build_clarifying_questions(
        request_text=state.request_text,
        partial_spec=state.partial_spec,
    )
    if question_result.status == "needs_answers":
        if _max_turns_reached(state):
            return ClarificationStatus(status="stopped", stop_reason="max_turns")
        return ClarificationStatus(
            status="more_questions",
            questions=question_result.questions,
        )

    try:
        simulation_spec = SimulationSpec.model_validate(state.partial_spec)
    except ValidationError as error:
        if _max_turns_reached(state):
            return ClarificationStatus(status="stopped", stop_reason="max_turns")
        return ClarificationStatus(
            status="more_questions",
            questions=[
                ClarifyingQuestion(
                    missing_field="simulation_spec",
                    why_it_matters="The provided answers do not validate as a SimulationSpec.",
                    acceptable_answer_shape=str(error.errors()[0].get("loc", "")),
                )
            ],
        )

    if state.case_build_spec is None:
        if _max_turns_reached(state):
            return ClarificationStatus(status="stopped", stop_reason="max_turns")
        return ClarificationStatus(
            status="more_questions",
            questions=[
                ClarifyingQuestion(
                    missing_field="case_build_spec",
                    why_it_matters="Planner readiness requires a validated CaseBuildSpec.",
                    acceptable_answer_shape="Provide a schema-backed CaseBuildSpec payload.",
                )
            ],
        )

    try:
        case_build_spec = CaseBuildSpec.model_validate(state.case_build_spec)
    except ValidationError:
        return ClarificationStatus(
            status="complete_but_not_executable",
            planning_result=None,
            stop_reason="case_build_spec_invalid",
        )

    planning_result = plan_simulation(simulation_spec, case_build_spec).model_dump(
        mode="json"
    )
    if planning_result["status"] == "planned":
        return ClarificationStatus(
            status="ready_to_plan",
            planning_result=planning_result,
        )

    return ClarificationStatus(
        status="complete_but_not_executable",
        planning_result=planning_result,
        stop_reason="capability_not_available",
    )


def _max_turns_reached(state: ClarificationState) -> bool:
    return state.turns >= state.max_turns


def _deep_merge(
    original: dict[str, object],
    update: dict[str, object],
) -> dict[str, object]:
    merged = dict(original)
    for key, value in update.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = _deep_merge(existing, value)
        else:
            merged[key] = value
    return merged
