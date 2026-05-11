import json

import pytest
from opennavier_core.case_build_spec import CaseBuildCapabilityError, CaseBuildSpec
from opennavier_core.plan import create_simulation_plan, simulation_plan_to_json
from opennavier_core.simulation_spec import SimulationSpec
from pydantic import ValidationError
from test_case_build_spec import minimal_cavity_case_build_payload


def minimal_cavity_spec() -> SimulationSpec:
    return SimulationSpec.model_validate(
        {
            "case_name": "lid_driven_cavity",
            "solver_family": "incompressible_laminar",
            "geometry": {
                "kind": "cavity",
                "dimensions": {"length": 1.0, "width": 1.0, "height": 0.1},
            },
            "mesh": {
                "kind": "structured",
                "cells": {"x": 20, "y": 20, "z": 1},
            },
            "fluid": {
                "density": 1.0,
                "kinematic_viscosity": 0.01,
            },
            "boundary_conditions": [
                {
                    "patch": "movingWall",
                    "field": "U",
                    "kind": "fixedValue",
                    "value": [1.0, 0.0, 0.0],
                },
                {"patch": "fixedWalls", "field": "U", "kind": "noSlip"},
                {"patch": "frontAndBack", "field": "U", "kind": "empty"},
                {"patch": "movingWall", "field": "p", "kind": "zeroGradient"},
                {"patch": "fixedWalls", "field": "p", "kind": "zeroGradient"},
                {"patch": "frontAndBack", "field": "p", "kind": "empty"},
            ],
            "run_control": {
                "start_time": 0.0,
                "end_time": 0.5,
                "time_step": 0.005,
                "write_interval": 0.1,
            },
        }
    )


def test_cavity_spec_produces_serializable_auditable_plan_artifact() -> None:
    case_build_spec = CaseBuildSpec.model_validate(minimal_cavity_case_build_payload())
    plan = create_simulation_plan(minimal_cavity_spec(), case_build_spec)

    assert plan.schema_version == "1.0"
    assert plan.case_name == "lid_driven_cavity"
    assert plan.case_build_spec_ref.path == "./runs/lid_driven_cavity/case-build.json"
    assert plan.local_only is True
    assert plan.cloud_upload is False
    assert [tool.name for tool in plan.tools] == ["opennavier", "OpenFOAM"]
    case_build_call_names = [
        command.tool_call.name if command.tool_call else None
        for command in plan.commands[:3]
    ]
    assert case_build_call_names == [
        "case_build_validate",
        "case_build_dry_run",
        "case_build_write",
    ]
    for command in plan.commands[:3]:
        assert command.argv is None
        assert command.tool_call is not None
        assert command.tool_call.arguments["workspace_root"] == "."
        assert command.tool_call.arguments["build_spec_path"] == (
            "runs/lid_driven_cavity/case-build.json"
        )
        assert command.tool_call.arguments["build_spec"] == case_build_spec.model_dump(
            mode="json"
        )
    assert plan.commands[2].tool_call is not None
    assert plan.commands[2].tool_call.arguments["persist_build_spec"] is True
    assert [command.argv for command in plan.commands[3:]] == [
        ["opennavier", "check", "./runs/lid_driven_cavity/case", "--format", "json"],
        ["blockMesh", "-case", "./runs/lid_driven_cavity/case"],
        ["checkMesh", "-case", "./runs/lid_driven_cavity/case"],
        ["icoFoam", "-case", "./runs/lid_driven_cavity/case"],
        [
            "opennavier",
            "doctor",
            "./runs/lid_driven_cavity/case",
            "--format",
            "json",
            "--diagnostics-output",
            "./runs/lid_driven_cavity/diagnostics.json",
        ],
        [
            "opennavier",
            "report",
            "./runs/lid_driven_cavity/case",
            "--output",
            "./runs/lid_driven_cavity/reports/report.md",
            "--manifest-output",
            "./runs/lid_driven_cavity/reports/manifest.json",
        ],
    ]
    assert {check.code for check in plan.pre_flight_checks} == {
        "case_path.safe_relative",
        "case_path.not_existing_or_approved",
        "case_build_spec.valid",
        "case_build_spec.validators_available",
        "openfoam.tools.available",
    }
    assert [checkpoint.code for checkpoint in plan.approval_checkpoints] == [
        "approve_case_build_write",
        "approve_mesh_generation",
        "approve_solver_execution",
    ]
    assert plan.approval_checkpoints[0].message == (
        "Approve writing generated OpenFOAM case files and the validated case-build spec."
    )
    assert [artifact.path for artifact in plan.expected_artifacts] == [
        "./runs/lid_driven_cavity/case-build.json",
        "./runs/lid_driven_cavity/case/system/blockMeshDict",
        "./runs/lid_driven_cavity/case/log.blockMesh",
        "./runs/lid_driven_cavity/case/log.checkMesh",
        "./runs/lid_driven_cavity/case/log.icoFoam",
        "./runs/lid_driven_cavity/diagnostics.json",
        "./runs/lid_driven_cavity/reports/report.md",
        "./runs/lid_driven_cavity/reports/manifest.json",
    ]
    assert [output.path for output in plan.report_outputs] == [
        "./runs/lid_driven_cavity/reports/report.md",
        "./runs/lid_driven_cavity/reports/manifest.json",
    ]
    assert plan.assumptions
    assert plan.risks


def test_create_simulation_plan_rejects_case_build_capability_gaps() -> None:
    payload = minimal_cavity_case_build_payload()
    payload["solver"] = "pimpleFoam"
    case_build_spec = CaseBuildSpec.model_validate(payload)

    with pytest.raises(CaseBuildCapabilityError, match="only supports icoFoam"):
        create_simulation_plan(minimal_cavity_spec(), case_build_spec)


def test_create_simulation_plan_rejects_spec_and_build_case_name_mismatch() -> None:
    payload = minimal_cavity_case_build_payload()
    payload["case_name"] = "different_case"
    case_build_spec = CaseBuildSpec.model_validate(payload)

    with pytest.raises(ValueError, match="case_name"):
        create_simulation_plan(minimal_cavity_spec(), case_build_spec)


def test_create_simulation_plan_rejects_spec_boundary_conditions_writer_cannot_honor(
) -> None:
    spec_payload = minimal_cavity_spec().model_dump(mode="json")
    spec_payload["boundary_conditions"][0]["value"] = [2.0, 0.0, 0.0]
    case_build_spec = CaseBuildSpec.model_validate(minimal_cavity_case_build_payload())

    with pytest.raises(ValueError, match="boundary_conditions"):
        create_simulation_plan(SimulationSpec.model_validate(spec_payload), case_build_spec)


def test_create_simulation_plan_rejects_unsafe_case_build_spec_path() -> None:
    case_build_spec = CaseBuildSpec.model_validate(minimal_cavity_case_build_payload())

    with pytest.raises(ValueError, match="case_build_spec_path"):
        create_simulation_plan(
            minimal_cavity_spec(),
            case_build_spec,
            case_build_spec_path="../outside/case-build.json",
        )


def test_simulation_plan_json_is_stable_and_sorted() -> None:
    case_build_spec = CaseBuildSpec.model_validate(minimal_cavity_case_build_payload())
    plan = create_simulation_plan(minimal_cavity_spec(), case_build_spec)

    first = simulation_plan_to_json(plan)
    second = simulation_plan_to_json(create_simulation_plan(minimal_cavity_spec(), case_build_spec))

    assert first == second
    assert first.endswith("\n")
    assert "generated_at" not in first
    loaded = json.loads(first)
    assert list(loaded) == sorted(loaded)
    assert [command["id"] for command in loaded["commands"]] == [
        "validate_case_build_spec",
        "dry_run_case_build",
        "write_case_build",
        "validate_case_structure",
        "generate_mesh",
        "check_mesh",
        "run_solver",
        "collect_diagnostics",
        "write_report",
    ]


def test_simulation_plan_schema_rejects_cloud_upload_opt_in() -> None:
    case_build_spec = CaseBuildSpec.model_validate(minimal_cavity_case_build_payload())
    payload = create_simulation_plan(minimal_cavity_spec(), case_build_spec).model_dump(
        mode="json"
    )
    payload["cloud_upload"] = True

    with pytest.raises(ValidationError, match="cloud upload"):
        create_simulation_plan(minimal_cavity_spec(), case_build_spec).__class__.model_validate(
            payload
        )
