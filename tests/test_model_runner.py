import json

import pytest
from opennavier_core.model_runner import (
    ModelRunnerConfig,
    ModelRunnerExecutionError,
    ModelRunnerRequest,
    build_model_command,
    run_model_request,
)


class Completed:
    def __init__(self, stdout: str, returncode: int = 0) -> None:
        self.stdout = stdout
        self.stderr = ""
        self.returncode = returncode


def test_model_runner_builds_provider_command_from_template() -> None:
    command = build_model_command(
        ModelRunnerConfig(
            provider="codex",
            command_template=["codex", "exec", "--json", "{prompt}"],
        ),
        ModelRunnerRequest(prompt="Draft a spec", response_kind="simulation_spec"),
    )

    assert command == ["codex", "exec", "--json", "Draft a spec"]


def test_model_runner_parses_only_typed_json_responses() -> None:
    def runner(command: list[str]) -> Completed:
        assert command[0] == "claude"
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
                        ]
                    },
                }
            )
        )

    response = run_model_request(
        ModelRunnerRequest(prompt="simulate airflow", response_kind="clarifying_questions"),
        ModelRunnerConfig(provider="claude", command_template=["claude", "-p", "{prompt}"]),
        command_runner=runner,
    )

    assert response.kind == "clarifying_questions"
    assert response.payload["questions"][0]["missing_field"] == "geometry"


def test_model_runner_rejects_payload_that_does_not_match_response_kind() -> None:
    def runner(command: list[str]) -> Completed:
        return Completed(
            json.dumps(
                {
                    "kind": "simulation_spec",
                    "payload": {"case_name": "missing_required_fields"},
                }
            )
        )

    with pytest.raises(ModelRunnerExecutionError, match="payload"):
        run_model_request(
            ModelRunnerRequest(prompt="draft a simulation spec", response_kind="simulation_spec"),
            ModelRunnerConfig(provider="codex", command_template=["codex", "{prompt}"]),
            command_runner=runner,
        )


def test_model_runner_rejects_direct_file_mutation_or_raw_dictionary_text() -> None:
    def runner(command: list[str]) -> Completed:
        return Completed(
            json.dumps(
                {
                    "kind": "case_build_spec",
                    "payload": {
                        "instructions": "write file system/controlDict with FoamFile {}",
                    },
                }
            )
        )

    with pytest.raises(ModelRunnerExecutionError, match="direct file mutation"):
        run_model_request(
            ModelRunnerRequest(prompt="write an OpenFOAM file", response_kind="case_build_spec"),
            ModelRunnerConfig(provider="gemini", command_template=["gemini", "{prompt}"]),
            command_runner=runner,
        )


def test_model_runner_reports_missing_cli_without_shell_fallback() -> None:
    def runner(command: list[str]) -> Completed:
        raise FileNotFoundError(command[0])

    with pytest.raises(ModelRunnerExecutionError, match="Model CLI not found"):
        run_model_request(
            ModelRunnerRequest(prompt="draft", response_kind="simulation_spec"),
            ModelRunnerConfig(provider="codex", command_template=["missing-codex", "{prompt}"]),
            command_runner=runner,
        )
