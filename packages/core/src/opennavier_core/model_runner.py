import json
import re
import subprocess
from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from opennavier_core.case_build_spec import CaseBuildSpec
from opennavier_core.questions import ClarifyingQuestionResult
from opennavier_core.simulation_spec import SimulationSpec

ProviderName = Literal["claude", "codex", "gemini"]
ResponseKind = Literal[
    "simulation_spec",
    "clarifying_questions",
    "case_build_spec",
    "plan_request",
]

DEFAULT_COMMAND_TEMPLATES: dict[ProviderName, list[str]] = {
    "claude": ["claude", "-p", "{prompt}"],
    "codex": ["codex", "exec", "--json", "{prompt}"],
    "gemini": ["gemini", "{prompt}"],
}
FORBIDDEN_RESPONSE_MARKERS = (
    "FoamFile",
    "boundaryField",
    "write file",
    "overwrite file",
    "edit file",
)
FORBIDDEN_RESPONSE_PATTERNS = (
    re.compile(
        r"\b(?:write|overwrite|edit|modify|mutate)\b"
        r"[^{}\r\n]{0,120}"
        r"\bsystem[\\/](?:controlDict|fvSchemes|fvSolution)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bdimensions\s*\[[^\]]+\]", re.IGNORECASE),
)


class ModelRunnerExecutionError(RuntimeError):
    """Raised when a configured model adapter cannot return a typed response."""


class ModelRunnerModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ModelRunnerRequest(ModelRunnerModel):
    prompt: str = Field(min_length=1)
    response_kind: ResponseKind | None = None


class ModelRunnerConfig(ModelRunnerModel):
    provider: ProviderName
    command_template: list[str] | None = None

    @field_validator("command_template")
    @classmethod
    def validate_command_template(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        if not value:
            raise ValueError("command_template must include an executable")
        for part in value:
            if any(marker in part for marker in ("&&", "||", ";", "|")):
                raise ValueError("command_template must be an argument sequence")
        return value


class ModelRunnerResponse(ModelRunnerModel):
    kind: ResponseKind
    payload: dict[str, object] = Field(default_factory=dict)
    raw_text: str = ""


CommandRunner = Callable[[list[str]], object]


def build_model_command(
    config: ModelRunnerConfig,
    request: ModelRunnerRequest,
) -> list[str]:
    template = config.command_template or DEFAULT_COMMAND_TEMPLATES[config.provider]
    return [part.replace("{prompt}", request.prompt) for part in template]


def run_model_request(
    request: ModelRunnerRequest,
    config: ModelRunnerConfig,
    *,
    command_runner: CommandRunner | None = None,
) -> ModelRunnerResponse:
    command = build_model_command(config, request)
    runner = command_runner or _run_subprocess
    try:
        completed = runner(command)
    except FileNotFoundError as error:
        raise ModelRunnerExecutionError(f"Model CLI not found: {command[0]}") from error

    return_code = int(getattr(completed, "returncode", 1))
    stdout = str(getattr(completed, "stdout", ""))
    stderr = str(getattr(completed, "stderr", ""))
    if return_code != 0:
        raise ModelRunnerExecutionError(
            f"Model CLI exited with {return_code}: {stderr.strip()}"
        )

    response = _parse_typed_response(stdout)
    if request.response_kind is not None and response.kind != request.response_kind:
        raise ModelRunnerExecutionError(
            f"Model returned {response.kind}, expected {request.response_kind}"
        )
    if _contains_forbidden_mutation_text(stdout):
        raise ModelRunnerExecutionError(
            "Model response attempted direct file mutation or raw OpenFOAM dictionary text."
        )
    _validate_response_payload(response)
    return response


def _run_subprocess(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True)


def _parse_typed_response(stdout: str) -> ModelRunnerResponse:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as error:
        raise ModelRunnerExecutionError("Model output was not valid JSON.") from error
    try:
        response = ModelRunnerResponse.model_validate({**payload, "raw_text": stdout})
    except (TypeError, ValueError) as error:
        raise ModelRunnerExecutionError(
            "Model output did not match the response schema."
        ) from error
    return response


def _contains_forbidden_mutation_text(value: object) -> bool:
    text = json.dumps(value, sort_keys=True) if not isinstance(value, str) else value
    lower_text = text.lower()
    marker_found = any(
        marker.lower() in lower_text
        for marker in FORBIDDEN_RESPONSE_MARKERS
    )
    return marker_found or any(pattern.search(text) for pattern in FORBIDDEN_RESPONSE_PATTERNS)


def _validate_response_payload(response: ModelRunnerResponse) -> None:
    validators = {
        "simulation_spec": SimulationSpec,
        "clarifying_questions": ClarifyingQuestionResult,
        "case_build_spec": CaseBuildSpec,
    }
    validator = validators.get(response.kind)
    if validator is None:
        return

    try:
        validator.model_validate(response.payload)
    except ValueError as error:
        raise ModelRunnerExecutionError(
            f"Model response payload did not match the {response.kind} schema."
        ) from error
