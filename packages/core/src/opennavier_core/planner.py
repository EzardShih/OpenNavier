import json
from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from opennavier_core.plan import SimulationPlan, create_simulation_plan
from opennavier_core.simulation_spec import SimulationSpec


class PlanningModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PlanningRejectionReason(PlanningModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    path: str = Field(min_length=1)
    metadata: dict[str, str] = Field(default_factory=dict)


class PlanningRejection(PlanningModel):
    status: Literal["rejected"] = "rejected"
    reasons: list[PlanningRejectionReason] = Field(min_length=1)


class PlanningRejected(ValueError):
    def __init__(self, rejection: PlanningRejection) -> None:
        self.rejection = rejection
        super().__init__("Simulation planning was rejected")


def plan_simulation(payload: Mapping[str, object] | SimulationSpec) -> SimulationPlan:
    if isinstance(payload, SimulationSpec):
        return create_simulation_plan(payload)

    reasons = _prevalidate_supported_payload(payload)
    if reasons:
        raise PlanningRejected(PlanningRejection(reasons=reasons))

    try:
        spec = SimulationSpec.model_validate(payload)
    except ValidationError as error:
        raise PlanningRejected(
            PlanningRejection(reasons=_validation_reasons(error))
        ) from error

    return create_simulation_plan(spec)


def planning_rejection_to_json(rejection: PlanningRejection) -> str:
    return json.dumps(rejection.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def _prevalidate_supported_payload(
    payload: Mapping[str, object],
) -> list[PlanningRejectionReason]:
    required_fields = (
        "case_name",
        "solver_family",
        "geometry",
        "mesh",
        "fluid",
        "boundary_conditions",
        "run_control",
    )
    for field_name in required_fields:
        if field_name not in payload:
            return [_missing_input(field_name)]

    if "physics" in payload:
        return [
            PlanningRejectionReason(
                code="planner.unsupported_physics",
                message="Unsupported physics request.",
                path="physics",
            )
        ]

    if payload.get("solver_family") != "incompressible_laminar":
        return [
            PlanningRejectionReason(
                code="planner.unsupported_solver_family",
                message="Unsupported solver family.",
                path="solver_family",
            )
        ]

    geometry = payload.get("geometry")
    if isinstance(geometry, Mapping) and geometry.get("kind") != "cavity":
        return [
            PlanningRejectionReason(
                code="planner.unsupported_geometry",
                message="Unsupported geometry kind.",
                path="geometry.kind",
            )
        ]

    mesh = payload.get("mesh")
    if isinstance(mesh, Mapping) and mesh.get("kind") != "structured":
        return [
            PlanningRejectionReason(
                code="planner.unsupported_mesh",
                message="Unsupported mesh kind.",
                path="mesh.kind",
            )
        ]

    template_reason = _template_parameter_reason(payload)
    if template_reason is not None:
        return [template_reason]

    return []


def _validation_reasons(error: ValidationError) -> list[PlanningRejectionReason]:
    reasons: list[PlanningRejectionReason] = []
    for item in error.errors():
        path = ".".join(str(part) for part in item["loc"])
        if item["type"] == "missing":
            reasons.append(_missing_input(path))
        else:
            reasons.append(
                PlanningRejectionReason(
                    code="planner.invalid_input",
                    message=str(item["msg"]),
                    path=path or ".",
                    metadata={"type": str(item["type"])},
                )
            )
    return reasons or [_missing_input(".")]


def _missing_input(path: str) -> PlanningRejectionReason:
    return PlanningRejectionReason(
        code="planner.missing_input",
        message="Required simulation input is missing.",
        path=path,
    )


def _template_parameter_reason(
    payload: Mapping[str, object],
) -> PlanningRejectionReason | None:
    mesh = payload.get("mesh")
    if not isinstance(mesh, Mapping):
        return None
    cells = mesh.get("cells")
    if not isinstance(cells, Mapping):
        return None

    supported_cells = {"x": 20, "y": 20, "z": 1}
    for axis, supported_value in supported_cells.items():
        received = cells.get(axis)
        if received != supported_value:
            return PlanningRejectionReason(
                code="planner.unsupported_template_parameter",
                message="Cavity template parameter is not supported yet.",
                path=f"mesh.cells.{axis}",
                metadata={
                    "received": str(received),
                    "supported": str(supported_value),
                },
            )
    return None
