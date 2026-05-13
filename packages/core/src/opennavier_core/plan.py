import json
from pathlib import PurePosixPath
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from opennavier_core.case_build_spec import (
    SUPPORTED_CAVITY_MESH,
    SUPPORTED_DUCT_MESH,
    CaseBuildCapabilityError,
    CaseBuildSpec,
    case_build_writer_capability_issues,
)
from opennavier_core.simulation_spec import SimulationSpec
from opennavier_core.workspace_path import normalize_workspace_relative_path

SCHEMA_VERSION = "1.0"


class SimulationPlanModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PlanTool(SimulationPlanModel):
    name: str = Field(min_length=1)
    purpose: str = Field(min_length=1)


class PlanToolCall(SimulationPlanModel):
    name: str = Field(min_length=1)
    arguments: dict[str, object] = Field(default_factory=dict)


class PlanCommand(SimulationPlanModel):
    id: str = Field(min_length=1)
    argv: list[str] | None = None
    tool_call: PlanToolCall | None = None
    requires_approval: bool = False
    expected_log_path: str | None = None

    @field_validator("expected_log_path")
    @classmethod
    def validate_expected_log_path(cls, value: str | None) -> str | None:
        if value is not None:
            normalize_workspace_relative_path(value, field_name="expected_log_path")
        return value

    @model_validator(mode="after")
    def validate_executable_call_shape(self) -> Self:
        if self.argv is None and self.tool_call is None:
            raise ValueError("PlanCommand requires argv or tool_call")
        if self.argv is not None and self.tool_call is not None:
            raise ValueError("PlanCommand cannot define both argv and tool_call")
        if self.argv is not None and not self.argv:
            raise ValueError("PlanCommand argv must not be empty")
        return self


class PlanArtifact(SimulationPlanModel):
    kind: str = Field(min_length=1)
    path: str = Field(min_length=1)

    @field_validator("path")
    @classmethod
    def validate_path_is_workspace_relative(cls, value: str) -> str:
        normalize_workspace_relative_path(value, field_name="path")
        return value


class PlanCheck(SimulationPlanModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)


class ApprovalCheckpoint(SimulationPlanModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)


class PlanRisk(SimulationPlanModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)


class SimulationPlan(SimulationPlanModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    artifact_type: Literal["simulation_plan"] = "simulation_plan"
    local_only: bool = True
    cloud_upload: bool = False
    case_name: str = Field(min_length=1)
    solver: str = Field(min_length=1)
    case_build_spec_ref: PlanArtifact
    assumptions: list[str] = Field(default_factory=list)
    tools: list[PlanTool] = Field(default_factory=list)
    commands: list[PlanCommand] = Field(default_factory=list)
    expected_artifacts: list[PlanArtifact] = Field(default_factory=list)
    pre_flight_checks: list[PlanCheck] = Field(default_factory=list)
    approval_checkpoints: list[ApprovalCheckpoint] = Field(default_factory=list)
    risks: list[PlanRisk] = Field(default_factory=list)
    report_outputs: list[PlanArtifact] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_local_only_policy(self) -> Self:
        if not self.local_only:
            raise ValueError("Simulation plans must remain local-only")
        if self.cloud_upload:
            raise ValueError("Simulation plans do not allow cloud upload")
        return self


def create_simulation_plan(
    spec: SimulationSpec,
    case_build_spec: CaseBuildSpec,
    *,
    case_build_spec_path: str | None = None,
    workspace_root: str = ".",
) -> SimulationPlan:
    _validate_plan_inputs(spec, case_build_spec)
    capability_issues = case_build_writer_capability_issues(case_build_spec)
    if capability_issues:
        raise CaseBuildCapabilityError(capability_issues)

    run_root = _display_path(_parent_path(case_build_spec.case_path))
    case_path = _display_path(case_build_spec.case_path)
    case_build_ref_path = _display_path(
        _normalize_case_build_spec_path(
            case_build_spec_path
            or f"{_parent_path(case_build_spec.case_path)}/case-build.json"
        )
    )
    case_build_tool_arguments = {
        "workspace_root": workspace_root,
        "build_spec_path": _workspace_path(case_build_ref_path),
        "build_spec": case_build_spec.model_dump(mode="json"),
    }
    diagnostics_path = f"{run_root}/diagnostics.json"
    report_path = f"{run_root}/reports/report.md"
    manifest_path = f"{run_root}/reports/manifest.json"
    solver = case_build_spec.solver

    return SimulationPlan(
        case_name=spec.case_name,
        solver=solver,
        case_build_spec_ref=PlanArtifact(kind="case_build_spec", path=case_build_ref_path),
        assumptions=[
            "The validated simulation request is paired with a schema-backed CaseBuildSpec.",
            "Case files are written only through deterministic case-build writer operations.",
            "Runtime artifacts remain under the generated run directory.",
        ],
        tools=[
            PlanTool(name="opennavier", purpose="Create, validate, diagnose, and report."),
            PlanTool(name="OpenFOAM", purpose=f"Generate mesh and execute {solver} locally."),
        ],
        pre_flight_checks=sorted(
            [
                PlanCheck(
                    code="case_build_spec.valid",
                    message="Case-build spec has passed schema validation.",
                ),
                PlanCheck(
                    code="case_build_spec.validators_available",
                    message="Required case-build validators are available.",
                ),
                PlanCheck(
                    code="case_path.safe_relative",
                    message="Generated case path is relative to the workspace.",
                ),
                PlanCheck(
                    code="case_path.not_existing_or_approved",
                    message="Existing case output requires explicit overwrite approval.",
                ),
                PlanCheck(
                    code="openfoam.tools.available",
                    message="OpenFOAM commands are available before solver execution.",
                ),
            ],
            key=lambda check: check.code,
        ),
        approval_checkpoints=[
            ApprovalCheckpoint(
                code="approve_case_build_write",
                message=(
                    "Approve writing generated OpenFOAM case files and the validated "
                    "case-build spec."
                ),
            ),
            ApprovalCheckpoint(
                code="approve_mesh_generation",
                message="Approve local blockMesh execution.",
            ),
            ApprovalCheckpoint(
                code="approve_solver_execution",
                message=f"Approve local {solver} execution.",
            ),
        ],
        commands=[
            PlanCommand(
                id="validate_case_build_spec",
                tool_call=PlanToolCall(
                    name="case_build_validate",
                    arguments=case_build_tool_arguments,
                ),
            ),
            PlanCommand(
                id="dry_run_case_build",
                tool_call=PlanToolCall(
                    name="case_build_dry_run",
                    arguments=case_build_tool_arguments,
                ),
            ),
            PlanCommand(
                id="write_case_build",
                tool_call=PlanToolCall(
                    name="case_build_write",
                    arguments={**case_build_tool_arguments, "persist_build_spec": True},
                ),
                requires_approval=True,
            ),
            PlanCommand(
                id="validate_case_structure",
                argv=["opennavier", "check", case_path, "--format", "json"],
            ),
            PlanCommand(
                id="generate_mesh",
                argv=["blockMesh", "-case", case_path],
                requires_approval=True,
                expected_log_path=f"{case_path}/log.blockMesh",
            ),
            PlanCommand(
                id="check_mesh",
                argv=["checkMesh", "-case", case_path],
                expected_log_path=f"{case_path}/log.checkMesh",
            ),
            PlanCommand(
                id="run_solver",
                argv=[solver, "-case", case_path],
                requires_approval=True,
                expected_log_path=f"{case_path}/log.{solver}",
            ),
            PlanCommand(
                id="collect_diagnostics",
                argv=[
                    "opennavier",
                    "doctor",
                    case_path,
                    "--format",
                    "json",
                    "--diagnostics-output",
                    diagnostics_path,
                ],
            ),
            PlanCommand(
                id="write_report",
                argv=[
                    "opennavier",
                    "report",
                    case_path,
                    "--output",
                    report_path,
                    "--manifest-output",
                    manifest_path,
                ],
            ),
        ],
        expected_artifacts=[
            PlanArtifact(kind="case_build_spec", path=case_build_ref_path),
            PlanArtifact(kind="openfoam_dictionary", path=f"{case_path}/system/blockMeshDict"),
            PlanArtifact(kind="solver_log", path=f"{case_path}/log.blockMesh"),
            PlanArtifact(kind="solver_log", path=f"{case_path}/log.checkMesh"),
            PlanArtifact(kind="solver_log", path=f"{case_path}/log.{solver}"),
            PlanArtifact(kind="diagnostics", path=diagnostics_path),
            PlanArtifact(kind="report", path=report_path),
            PlanArtifact(kind="manifest", path=manifest_path),
        ],
        risks=[
            PlanRisk(
                code="openfoam_not_installed",
                message="Local solver commands may be unavailable on this machine.",
            ),
            PlanRisk(
                code="case_build_scope_limited",
                message="Only schema-backed case-build operations can write solver files.",
            ),
        ],
        report_outputs=[
            PlanArtifact(kind="report", path=report_path),
            PlanArtifact(kind="manifest", path=manifest_path),
        ],
    )


def simulation_plan_to_json(plan: SimulationPlan) -> str:
    return json.dumps(plan.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def _validate_plan_inputs(spec: SimulationSpec, case_build_spec: CaseBuildSpec) -> None:
    if spec.case_name != case_build_spec.case_name:
        raise ValueError("case_name must match between SimulationSpec and CaseBuildSpec")
    if spec.solver_family != case_build_spec.solver_family:
        raise ValueError(
            "solver_family must match between SimulationSpec and CaseBuildSpec"
        )
    if spec.geometry.kind != case_build_spec.geometry.kind:
        raise ValueError("geometry.kind must match between SimulationSpec and CaseBuildSpec")
    if spec.mesh.kind != case_build_spec.mesh.kind:
        raise ValueError("mesh.kind must match between SimulationSpec and CaseBuildSpec")
    if spec.geometry.kind == "cavity":
        _validate_supported_cavity_spec(spec)
    elif spec.geometry.kind == "duct":
        _validate_supported_duct_spec(spec)


def _validate_supported_cavity_spec(spec: SimulationSpec) -> None:
    if spec.geometry.dimensions.model_dump(mode="json") != {
        "length": 1.0,
        "width": 1.0,
        "height": 0.1,
    }:
        raise ValueError("geometry.dimensions are not supported by the cavity writer")
    if spec.mesh.kind != SUPPORTED_CAVITY_MESH:
        raise ValueError("mesh.kind is not supported by the cavity writer")
    if spec.mesh.cells.model_dump(mode="json") != {"x": 20, "y": 20, "z": 1}:
        raise ValueError("mesh.cells are not supported by the cavity writer")
    if spec.fluid.kinematic_viscosity != 0.01:
        raise ValueError("fluid.kinematic_viscosity is not supported by the cavity writer")
    if spec.run_control.model_dump(mode="json") != {
        "start_time": 0.0,
        "end_time": 0.5,
        "time_step": 0.005,
        "write_interval": 0.1,
    }:
        raise ValueError("run_control is not supported by the cavity writer")
    if _boundary_condition_fingerprint(spec) != _expected_cavity_boundary_conditions():
        raise ValueError("boundary_conditions are not supported by the cavity writer")


def _normalize_case_build_spec_path(path: str) -> str:
    return normalize_workspace_relative_path(
        path,
        field_name="case_build_spec_path",
    )


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


def _validate_supported_duct_spec(spec: SimulationSpec) -> None:
    if spec.geometry.dimensions.model_dump(mode="json") != {
        "length": 1.0,
        "width": 0.1,
        "height": 0.1,
    }:
        raise ValueError("geometry.dimensions are not supported by the duct writer")
    if spec.mesh.kind != SUPPORTED_DUCT_MESH:
        raise ValueError("mesh.kind is not supported by the duct writer")
    if spec.mesh.cells.model_dump(mode="json") != {"x": 40, "y": 4, "z": 4}:
        raise ValueError("mesh.cells are not supported by the duct writer")
    if spec.fluid.kinematic_viscosity != 1.5e-5:
        raise ValueError("fluid.kinematic_viscosity is not supported by the duct writer")
    if spec.run_control.model_dump(mode="json") != {
        "start_time": 0.0,
        "end_time": 1000.0,
        "time_step": 1.0,
        "write_interval": 100.0,
    }:
        raise ValueError("run_control is not supported by the duct writer")
    if _boundary_condition_fingerprint(spec) != _expected_duct_boundary_conditions():
        raise ValueError("boundary_conditions are not supported by the duct writer")


def _expected_duct_boundary_conditions() -> list[tuple[str, str, str, str]]:
    return sorted(
        [
            ("inlet", "U", "fixedValue", "[10.0, 0.0, 0.0]"),
            ("outlet", "U", "zeroGradient", "null"),
            ("walls", "U", "noSlip", "null"),
            ("inlet", "p", "zeroGradient", "null"),
            ("outlet", "p", "fixedValue", "0.0"),
            ("walls", "p", "zeroGradient", "null"),
        ]
    )


def _parent_path(path: str) -> str:
    parent = PurePosixPath(path).parent.as_posix()
    return "." if parent == "." else parent


def _display_path(path: str) -> str:
    if path.startswith("./"):
        return path
    if path == ".":
        return "."
    return f"./{path}"


def _workspace_path(path: str) -> str:
    if path.startswith("./"):
        return path[2:]
    return path
