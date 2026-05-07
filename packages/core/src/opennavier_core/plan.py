import json
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from opennavier_core.simulation_spec import SimulationSpec

SCHEMA_VERSION = "1.0"


class SimulationPlanModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PlanTool(SimulationPlanModel):
    name: str = Field(min_length=1)
    purpose: str = Field(min_length=1)


class PlanCommand(SimulationPlanModel):
    id: str = Field(min_length=1)
    argv: list[str] = Field(min_length=1)
    requires_approval: bool = False
    expected_log_path: str | None = None


class PlanArtifact(SimulationPlanModel):
    kind: str = Field(min_length=1)
    path: str = Field(min_length=1)


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
    template_id: str = Field(min_length=1)
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


def create_simulation_plan(spec: SimulationSpec) -> SimulationPlan:
    _require_supported_cavity_spec(spec)
    run_root = f"./runs/{spec.case_name}"
    case_path = f"{run_root}/case"
    diagnostics_path = f"{run_root}/diagnostics.json"
    report_path = f"{run_root}/reports/report.md"
    manifest_path = f"{run_root}/reports/manifest.json"

    return SimulationPlan(
        case_name=spec.case_name,
        solver="icoFoam",
        template_id="openfoam.cavity.icofoam.v1",
        assumptions=[
            "The cavity request maps to the deterministic lid-driven cavity template.",
            "The selected OpenFOAM solver family is incompressible laminar flow.",
            "Runtime artifacts remain under the generated run directory.",
        ],
        tools=[
            PlanTool(name="opennavier", purpose="Create, validate, diagnose, and report."),
            PlanTool(name="OpenFOAM", purpose="Generate mesh and execute icoFoam locally."),
        ],
        pre_flight_checks=sorted(
            [
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
                PlanCheck(
                    code="spec.matches_cavity_template",
                    message="Validated spec matches the supported cavity template.",
                ),
            ],
            key=lambda check: check.code,
        ),
        approval_checkpoints=[
            ApprovalCheckpoint(
                code="approve_case_initialization",
                message="Approve writing the deterministic starter case.",
            ),
            ApprovalCheckpoint(
                code="approve_mesh_generation",
                message="Approve local blockMesh execution.",
            ),
            ApprovalCheckpoint(
                code="approve_solver_execution",
                message="Approve local icoFoam execution.",
            ),
        ],
        commands=[
            PlanCommand(
                id="initialize_cavity_case",
                argv=["opennavier", "init", "cavity", case_path],
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
                argv=["icoFoam", "-case", case_path],
                requires_approval=True,
                expected_log_path=f"{case_path}/log.icoFoam",
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
            PlanArtifact(kind="openfoam_dictionary", path=f"{case_path}/system/blockMeshDict"),
            PlanArtifact(kind="solver_log", path=f"{case_path}/log.blockMesh"),
            PlanArtifact(kind="solver_log", path=f"{case_path}/log.checkMesh"),
            PlanArtifact(kind="solver_log", path=f"{case_path}/log.icoFoam"),
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
                code="template_scope_limited",
                message="Only the cavity template is supported in P0 planning.",
            ),
        ],
        report_outputs=[
            PlanArtifact(kind="report", path=report_path),
            PlanArtifact(kind="manifest", path=manifest_path),
        ],
    )


def simulation_plan_to_json(plan: SimulationPlan) -> str:
    return json.dumps(plan.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def _require_supported_cavity_spec(spec: SimulationSpec) -> None:
    if spec.solver_family != "incompressible_laminar":
        raise ValueError(f"Unsupported solver family: {spec.solver_family}")
    if spec.geometry.kind != "cavity":
        raise ValueError(f"Unsupported geometry kind: {spec.geometry.kind}")
    if spec.mesh.kind != "structured":
        raise ValueError(f"Unsupported mesh kind: {spec.mesh.kind}")
    supported_cells = {"x": 20, "y": 20, "z": 1}
    for axis, supported_value in supported_cells.items():
        received = getattr(spec.mesh.cells, axis)
        if received != supported_value:
            raise ValueError(
                f"Unsupported cavity template mesh.cells.{axis}: {received}"
            )
