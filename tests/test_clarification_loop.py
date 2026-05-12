from opennavier_core.clarification_loop import (
    ClarificationState,
    clarification_status,
    clarification_update,
)
from test_case_build_spec import minimal_cavity_case_build_payload
from test_planner import minimal_cavity_payload


def complete_cavity_intake() -> dict[str, object]:
    payload = minimal_cavity_payload()
    payload["units"] = {"length": "m", "velocity": "m/s"}
    payload["objective"] = "validate lid-driven cavity setup"
    payload["output_expectations"] = ["diagnostics", "report"]
    return payload


def test_clarification_loop_accumulates_answers_until_ready_to_plan() -> None:
    state = ClarificationState(
        request_text="run a cavity case",
        partial_spec={"case_name": "lid_driven_cavity"},
        case_build_spec=minimal_cavity_case_build_payload(),
    )

    first = clarification_status(state)
    assert first.status == "more_questions"
    assert first.questions[0].missing_field == "geometry"

    updated = clarification_update(
        state,
        {
            "partial_spec": complete_cavity_intake(),
            "answer_summary": "Provided the complete reference cavity spec.",
        },
    )
    status = clarification_status(updated)

    assert status.status == "ready_to_plan"
    assert status.planning_result["status"] == "planned"
    assert updated.turns == 1
    assert updated.answers == ["Provided the complete reference cavity spec."]


def test_clarification_loop_reports_complete_but_not_executable() -> None:
    unsupported_spec = complete_cavity_intake()
    unsupported_spec["geometry"] = {
        "kind": "external_wing",
        "dimensions": {"length": 1.0, "width": 1.0, "height": 0.1},
    }
    build_spec = minimal_cavity_case_build_payload()
    build_spec["geometry"] = {"kind": "external_wing"}
    build_spec["writer_operations"] = [
        {
            "id": "write_case_tree",
            "operation": "openfoam.write_case_tree",
            "parameters": {"case_family": "external_wing"},
        }
    ]

    status = clarification_status(
        ClarificationState(
            request_text="simulate an external wing",
            partial_spec=unsupported_spec,
            case_build_spec=build_spec,
        )
    )

    assert status.status == "complete_but_not_executable"
    assert status.planning_result["status"] == "not_executable"
    assert status.stop_reason == "capability_not_available"


def test_clarification_loop_preserves_stop_conditions() -> None:
    cancelled = clarification_update(
        ClarificationState(request_text="stop this", partial_spec={}),
        {"cancel": True},
    )

    assert clarification_status(cancelled).status == "stopped"
    assert clarification_status(cancelled).stop_reason == "cancelled"

    maxed = ClarificationState(
        request_text="ambiguous",
        partial_spec={},
        turns=2,
        max_turns=2,
    )

    assert clarification_status(maxed).status == "stopped"
    assert clarification_status(maxed).stop_reason == "max_turns"


def test_clarification_loop_applies_max_turns_to_validation_followups() -> None:
    invalid_spec = complete_cavity_intake()
    invalid_spec["run_control"] = {
        "start_time": 1.0,
        "end_time": 1.0,
        "time_step": 0.005,
        "write_interval": 0.1,
    }
    invalid_status = clarification_status(
        ClarificationState(
            request_text="run a cavity case",
            partial_spec=invalid_spec,
            case_build_spec=minimal_cavity_case_build_payload(),
            turns=2,
            max_turns=2,
        )
    )

    missing_build_spec_status = clarification_status(
        ClarificationState(
            request_text="run a cavity case",
            partial_spec=complete_cavity_intake(),
            turns=2,
            max_turns=2,
        )
    )

    assert invalid_status.status == "stopped"
    assert invalid_status.stop_reason == "max_turns"
    assert missing_build_spec_status.status == "stopped"
    assert missing_build_spec_status.stop_reason == "max_turns"
