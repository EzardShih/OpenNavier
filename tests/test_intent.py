import json
from collections.abc import Sequence
from pathlib import Path

import pytest
from opennavier_core.intent import IntentRequest, ask_intent, build_intent_prompt
from opennavier_core.model_runner import ModelRunnerConfig, ModelRunnerExecutionError
from test_case_build_spec import minimal_cavity_case_build_payload
from test_planner import minimal_cavity_payload


class Completed:
    def __init__(self, stdout: str, returncode: int = 0) -> None:
        self.stdout = stdout
        self.stderr = ""
        self.returncode = returncode


def test_intent_prompt_keeps_model_inside_typed_local_contract() -> None:
    prompt = build_intent_prompt("Simulate the lid-driven cavity and report convergence.")

    assert "Simulate the lid-driven cavity and report convergence." in prompt
    assert "Return one JSON object" in prompt
    assert "simulation_spec" in prompt
    assert "case_build_spec" in prompt
    assert "Do not write OpenFOAM dictionaries" in prompt
    assert "local-only" in prompt


def test_ask_intent_returns_validated_simulation_spec_and_session_provenance(
    tmp_path: Path,
) -> None:
    def runner(command: Sequence[str]) -> Completed:
        assert command[:2] == ["codex", "exec"]
        assert "local-only" in command[-1]
        return Completed(
            json.dumps(
                {
                    "kind": "simulation_spec",
                    "payload": minimal_cavity_payload(),
                }
            )
        )

    result = ask_intent(
        IntentRequest(
            request_text="Create a cavity case.",
            workspace_root=str(tmp_path),
            session_id="intent-001",
            expected_response_kind="simulation_spec",
        ),
        ModelRunnerConfig(
            provider="codex",
            command_template=["codex", "exec", "{prompt}"],
        ),
        command_runner=runner,
    )

    assert result.status == "draft_simulation_spec"
    assert result.kind == "simulation_spec"
    assert result.payload["case_name"] == "lid_driven_cavity"
    assert result.session.session_id == "intent-001"
    assert result.session.engineering_intent == "Create a cavity case."
    assert result.session.provenance[0].tool == "model_runner.codex"
    assert result.session.provenance[0].action == "drafted simulation_spec"


def test_ask_intent_accepts_any_valid_typed_kind_without_callers_guessing(
    tmp_path: Path,
) -> None:
    def runner(command: Sequence[str]) -> Completed:
        return Completed(
            json.dumps(
                {
                    "kind": "clarifying_questions",
                    "payload": {
                        "status": "needs_answers",
                        "questions": [
                            {
                                "missing_field": "geometry",
                                "why_it_matters": "The domain is unknown.",
                                "acceptable_answer_shape": "Provide dimensions.",
                            }
                        ],
                    },
                }
            )
        )

    result = ask_intent(
        IntentRequest(
            request_text="Simulate airflow in a room.",
            workspace_root=str(tmp_path),
            session_id="intent-questions",
            expected_response_kind="simulation_spec",
        ),
        ModelRunnerConfig(provider="codex", command_template=["codex", "{prompt}"]),
        command_runner=runner,
    )

    assert result.status == "clarifying_questions"
    assert result.kind == "clarifying_questions"
    assert result.validation["clarifying_questions"]["questions"][0]["missing_field"] == "geometry"


def test_ask_intent_returns_case_build_dry_run_without_writing_files(
    tmp_path: Path,
) -> None:
    payload = minimal_cavity_case_build_payload()

    def runner(command: Sequence[str]) -> Completed:
        return Completed(json.dumps({"kind": "case_build_spec", "payload": payload}))

    result = ask_intent(
        IntentRequest(
            request_text="Draft a case build spec.",
            workspace_root=str(tmp_path),
            session_id="intent-002",
            expected_response_kind="case_build_spec",
        ),
        ModelRunnerConfig(provider="claude", command_template=["claude", "{prompt}"]),
        command_runner=runner,
    )

    assert result.status == "draft_case_build_spec"
    assert result.validation["dry_run"]["case_path"] == "runs/lid_driven_cavity/case"
    assert {
        operation["path"] for operation in result.validation["dry_run"]["file_operations"]
    } >= {"runs/lid_driven_cavity/case/system/controlDict"}
    assert not (tmp_path / "runs").exists()


def test_ask_intent_rejects_case_build_specs_without_deterministic_writer(
    tmp_path: Path,
) -> None:
    payload = minimal_cavity_case_build_payload()
    payload["writer_operations"][0]["parameters"]["case_family"] = "electronics"

    def runner(command: Sequence[str]) -> Completed:
        return Completed(json.dumps({"kind": "case_build_spec", "payload": payload}))

    result = ask_intent(
        IntentRequest(
            request_text="Draft an unsupported case.",
            workspace_root=str(tmp_path),
            session_id="intent-003",
            expected_response_kind="case_build_spec",
        ),
        ModelRunnerConfig(provider="gemini", command_template=["gemini", "{prompt}"]),
        command_runner=runner,
    )

    assert result.status == "rejected"
    assert result.issues[0]["code"] == "case_build.unsupported_case_build_family"
    assert result.session.provenance[0].action == "rejected case_build_spec"


def test_ask_intent_rejects_plan_request_that_disables_approval(
    tmp_path: Path,
) -> None:
    payload = {
        "simulation_spec": minimal_cavity_payload(),
        "approval_required": False,
    }

    def runner(command: Sequence[str]) -> Completed:
        return Completed(json.dumps({"kind": "plan_request", "payload": payload}))

    result = ask_intent(
        IntentRequest(
            request_text="Plan the cavity without approval.",
            workspace_root=str(tmp_path),
            session_id="intent-approval",
            expected_response_kind="plan_request",
        ),
        ModelRunnerConfig(provider="codex", command_template=["codex", "{prompt}"]),
        command_runner=runner,
    )

    assert result.status == "rejected"
    assert result.issues[0]["code"] == "intent.schema_validation_failed"
    assert "approval" in result.issues[0]["message"]


def test_ask_intent_rejects_plan_request_with_unsupported_case_build_spec(
    tmp_path: Path,
) -> None:
    case_build_spec = minimal_cavity_case_build_payload()
    case_build_spec["writer_operations"][0]["parameters"]["case_family"] = "electronics"
    payload = {
        "case_build_spec": case_build_spec,
    }

    def runner(command: Sequence[str]) -> Completed:
        return Completed(json.dumps({"kind": "plan_request", "payload": payload}))

    result = ask_intent(
        IntentRequest(
            request_text="Plan an unsupported electronics case.",
            workspace_root=str(tmp_path),
            session_id="intent-plan-case-build",
            expected_response_kind="plan_request",
        ),
        ModelRunnerConfig(provider="codex", command_template=["codex", "{prompt}"]),
        command_runner=runner,
    )

    assert result.status == "rejected"
    assert result.issues[0]["code"] == "case_build.unsupported_case_build_family"
    assert result.session.provenance[0].action == "rejected plan_request"


def test_ask_intent_rejects_model_text_that_attempts_direct_file_mutation(
    tmp_path: Path,
) -> None:
    def runner(command: Sequence[str]) -> Completed:
        return Completed(
            json.dumps(
                {
                    "kind": "plan_request",
                    "payload": {"instruction": "write system/controlDict directly"},
                }
            )
        )

    with pytest.raises(ModelRunnerExecutionError, match="direct file mutation"):
        ask_intent(
            IntentRequest(
                request_text="Patch the case directly.",
                workspace_root=str(tmp_path),
                session_id="intent-004",
                expected_response_kind="plan_request",
            ),
            ModelRunnerConfig(provider="codex", command_template=["codex", "{prompt}"]),
            command_runner=runner,
        )
