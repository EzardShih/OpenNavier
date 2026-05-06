import json
from typing import Any

from opennavier.mcp.paths import WorkspacePathError, resolve_workspace_path
from opennavier_core.simulation_spec import SimulationSpec
from pydantic import ValidationError


def spec_validate(
    workspace_root: str,
    spec_path: str = "specs/simulation.json",
    spec: dict[str, object] | None = None,
) -> dict[str, object]:
    source = "payload" if spec is not None else spec_path

    if spec is not None:
        return _validate_payload(spec, source=source)

    try:
        resolved_spec_path = resolve_workspace_path(workspace_root, spec_path)
        content = resolved_spec_path.read_text(encoding="utf-8")
        payload = json.loads(content)
    except WorkspacePathError as error:
        return _invalid(source=source, error_type="workspace_path_error", message=str(error))
    except json.JSONDecodeError:
        return _invalid(
            source=source,
            error_type="json_decode_error",
            message=f"Malformed JSON in {spec_path}",
        )
    except (OSError, UnicodeError) as error:
        return _invalid(
            source=source,
            error_type="file_read_error",
            message=f"Could not read spec file {spec_path}: {type(error).__name__}",
        )

    return _validate_payload(payload, source=source)


def _validate_payload(payload: Any, *, source: str) -> dict[str, object]:
    try:
        spec = SimulationSpec.model_validate(payload)
    except ValidationError as error:
        return {
            "valid": False,
            "spec": None,
            "errors": [
                {
                    "type": str(item["type"]),
                    "message": _validation_message(item),
                }
                for item in error.errors()
            ],
            "source": source,
        }

    return {
        "valid": True,
        "spec": spec.model_dump(mode="json", exclude_none=True),
        "errors": [],
        "source": source,
    }


def _invalid(*, source: str, error_type: str, message: str) -> dict[str, object]:
    return {
        "valid": False,
        "spec": None,
        "errors": [{"type": error_type, "message": message}],
        "source": source,
    }


def _validation_message(error: dict[str, object]) -> str:
    location = ".".join(str(part) for part in error.get("loc", ()))
    message = str(error.get("msg", "Validation error"))
    if location:
        return f"{location}: {message}"
    return message
