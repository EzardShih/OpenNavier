import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from opennavier_core.case_build_spec import (
    SUPPORTED_CAVITY_MESH,
    CaseBuildCapabilityIssue,
    CaseBuildSpec,
    case_build_writer_capability_issues,
)
from opennavier_core.plan import SimulationPlan, create_simulation_plan
from opennavier_core.simulation_spec import SimulationSpec


class PlanningModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PlanningReason(PlanningModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    path: str = Field(min_length=1)
    metadata: dict[str, str] = Field(default_factory=dict)


class PlannedSimulation(PlanningModel):
    status: Literal["planned"] = "planned"
    plan: SimulationPlan


class PlanningCapabilityResult(PlanningModel):
    status: Literal["not_executable"] = "not_executable"
    reasons: list[PlanningReason] = Field(min_length=1)


PlanningResult = PlannedSimulation | PlanningCapabilityResult


def plan_simulation(
    spec: SimulationSpec,
    case_build_spec: CaseBuildSpec,
) -> PlanningResult:
    reasons = _capability_reasons(spec, case_build_spec)
    if reasons:
        return PlanningCapabilityResult(reasons=reasons)

    return PlannedSimulation(plan=create_simulation_plan(spec, case_build_spec))


def planning_result_to_json(result: PlanningResult) -> str:
    return json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def _capability_reasons(
    spec: SimulationSpec,
    case_build_spec: CaseBuildSpec,
) -> list[PlanningReason]:
    reasons: list[PlanningReason] = []

    if spec.case_name != case_build_spec.case_name:
        reasons.append(
            PlanningReason(
                code="planner.case_name_mismatch",
                message="Simulation spec and case-build spec case names differ.",
                path="case_name",
            )
        )
    if spec.solver_family != case_build_spec.solver_family:
        reasons.append(
            PlanningReason(
                code="planner.solver_family_mismatch",
                message="Simulation spec and case-build spec solver families differ.",
                path="solver_family",
            )
        )
    if spec.geometry.kind != case_build_spec.geometry.kind:
        reasons.append(
            PlanningReason(
                code="planner.geometry_mismatch",
                message="Simulation spec and case-build spec geometry kinds differ.",
                path="geometry.kind",
            )
        )
    if spec.mesh.kind != case_build_spec.mesh.kind:
        reasons.append(
            PlanningReason(
                code="planner.mesh_mismatch",
                message="Simulation spec and case-build spec mesh kinds differ.",
                path="mesh.kind",
            )
        )

    if reasons:
        return reasons

    if spec.geometry.kind != "cavity":
        return [
            PlanningReason(
                code="planner.unsupported_geometry",
                message="No deterministic case-build writer currently supports this geometry.",
                path="geometry.kind",
            )
        ]

    reasons.extend(_simulation_spec_capability_reasons(spec))
    reasons.extend(_case_build_capability_reasons(case_build_spec))

    return _unique_reasons(reasons)


def _simulation_spec_capability_reasons(spec: SimulationSpec) -> list[PlanningReason]:
    reasons: list[PlanningReason] = []

    if spec.geometry.dimensions.model_dump(mode="json") != {
        "length": 1.0,
        "width": 1.0,
        "height": 0.1,
    }:
        reasons.append(
            PlanningReason(
                code="planner.unsupported_geometry_dimensions",
                message="The current cavity writer only supports a 1 x 1 x 0.1 cavity.",
                path="geometry.dimensions",
            )
        )

    if spec.mesh.kind != SUPPORTED_CAVITY_MESH:
        reasons.append(
            PlanningReason(
                code="planner.unsupported_mesh",
                message="The current cavity writer only supports structured meshes.",
                path="mesh.kind",
            )
        )
    if spec.mesh.cells.model_dump(mode="json") != {"x": 20, "y": 20, "z": 1}:
        reasons.append(
            PlanningReason(
                code="planner.unsupported_mesh_cells",
                message="The current cavity writer only supports a 20 x 20 x 1 mesh.",
                path="mesh.cells",
            )
        )

    if spec.fluid.kinematic_viscosity != 0.01:
        reasons.append(
            PlanningReason(
                code="planner.unsupported_kinematic_viscosity",
                message="The current cavity writer only supports nu = 0.01.",
                path="fluid.kinematic_viscosity",
            )
        )

    if spec.run_control.model_dump(mode="json") != {
        "start_time": 0.0,
        "end_time": 0.5,
        "time_step": 0.005,
        "write_interval": 0.1,
    }:
        reasons.append(
            PlanningReason(
                code="planner.unsupported_run_control",
                message="The current cavity writer only supports the checked-in run controls.",
                path="run_control",
            )
        )

    if _boundary_condition_fingerprint(spec) != _expected_cavity_boundary_conditions():
        reasons.append(
            PlanningReason(
                code="planner.unsupported_boundary_conditions",
                message="The current cavity writer only supports the reference cavity boundaries.",
                path="boundary_conditions",
            )
        )

    return reasons


def _case_build_capability_reasons(
    case_build_spec: CaseBuildSpec,
) -> list[PlanningReason]:
    return [
        PlanningReason(
            code=_planner_code(issue),
            message=issue.message,
            path=issue.path,
        )
        for issue in case_build_writer_capability_issues(case_build_spec)
    ]


def _planner_code(issue: CaseBuildCapabilityIssue) -> str:
    return f"planner.{issue.code.removeprefix('case_build.')}"


def _unique_reasons(reasons: list[PlanningReason]) -> list[PlanningReason]:
    unique: list[PlanningReason] = []
    seen: set[tuple[str, str]] = set()
    for reason in reasons:
        identity = (reason.code, reason.path)
        if identity in seen:
            continue
        seen.add(identity)
        unique.append(reason)
    return unique


def _boundary_condition_fingerprint(
    spec: SimulationSpec,
) -> list[tuple[str, str, str, str]]:
    return sorted(
        (
            condition.patch,
            condition.field,
            condition.kind,
            json.dumps(condition.value, sort_keys=True),
        )
        for condition in spec.boundary_conditions
    )


def _expected_cavity_boundary_conditions() -> list[tuple[str, str, str, str]]:
    return sorted(
        [
            ("movingWall", "U", "fixedValue", "[1.0, 0.0, 0.0]"),
            ("fixedWalls", "U", "noSlip", "null"),
            ("frontAndBack", "U", "empty", "null"),
            ("movingWall", "p", "zeroGradient", "null"),
            ("fixedWalls", "p", "zeroGradient", "null"),
            ("frontAndBack", "p", "empty", "null"),
        ]
    )
