import json

from opennavier_core.case_build_spec import CaseBuildSpec
from opennavier_core.planner import plan_simulation, planning_result_to_json
from opennavier_core.simulation_spec import SimulationSpec
from test_case_build_spec import (
    minimal_cavity_case_build_payload,
    minimal_duct_case_build_payload,
)


def minimal_cavity_payload() -> dict[str, object]:
    return {
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


def minimal_duct_payload() -> dict[str, object]:
    return {
        "case_name": "duct_pressure_drop",
        "solver_family": "incompressible_laminar",
        "geometry": {
            "kind": "duct",
            "dimensions": {"length": 1.0, "width": 0.1, "height": 0.1},
        },
        "mesh": {
            "kind": "structured",
            "cells": {"x": 40, "y": 4, "z": 4},
        },
        "fluid": {
            "density": 1.225,
            "kinematic_viscosity": 1.5e-5,
        },
        "boundary_conditions": [
            {
                "patch": "inlet",
                "field": "U",
                "kind": "fixedValue",
                "value": [10.0, 0.0, 0.0],
            },
            {"patch": "outlet", "field": "U", "kind": "zeroGradient"},
            {"patch": "walls", "field": "U", "kind": "noSlip"},
            {"patch": "inlet", "field": "p", "kind": "zeroGradient"},
            {"patch": "outlet", "field": "p", "kind": "fixedValue", "value": 0.0},
            {"patch": "walls", "field": "p", "kind": "zeroGradient"},
        ],
        "run_control": {
            "start_time": 0.0,
            "end_time": 1000.0,
            "time_step": 1.0,
            "write_interval": 100.0,
        },
    }


def test_planner_accepts_cavity_payload_and_keeps_order_deterministic() -> None:
    spec = SimulationSpec.model_validate(minimal_cavity_payload())
    case_build_spec = CaseBuildSpec.model_validate(minimal_cavity_case_build_payload())

    result = plan_simulation(spec, case_build_spec)

    assert result.status == "planned"
    assert result.plan.case_name == "lid_driven_cavity"
    assert result.plan.solver == "icoFoam"
    assert [command.id for command in result.plan.commands] == [
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
    assert [check.code for check in result.plan.pre_flight_checks] == sorted(
        check.code for check in result.plan.pre_flight_checks
    )


def test_planner_accepts_duct_payload_as_second_executable_path() -> None:
    spec = SimulationSpec.model_validate(minimal_duct_payload())
    case_build_spec = CaseBuildSpec.model_validate(minimal_duct_case_build_payload())

    result = plan_simulation(spec, case_build_spec)

    assert result.status == "planned"
    assert result.plan.case_name == "duct_pressure_drop"
    assert result.plan.solver == "simpleFoam"
    assert result.plan.expected_artifacts[1].path == (
        "./runs/duct_pressure_drop/case/system/blockMeshDict"
    )


def test_planner_returns_capability_result_for_complete_unsupported_geometry(
) -> None:
    payload = minimal_cavity_payload()
    payload["geometry"] = {
        "kind": "pipe",
        "dimensions": {"length": 2.0, "width": 0.5, "height": 0.5},
    }
    build_payload = minimal_cavity_case_build_payload()
    build_payload["geometry"] = {"kind": "pipe"}
    build_payload["writer_operations"] = [
        {
            "id": "write_case_tree",
            "operation": "openfoam.write_case_tree",
            "parameters": {"case_family": "pipe"},
        }
    ]

    result = plan_simulation(
        SimulationSpec.model_validate(payload),
        CaseBuildSpec.model_validate(build_payload),
    )

    assert result.status == "not_executable"
    assert [(reason.code, reason.path) for reason in result.reasons] == [
        ("planner.unsupported_geometry", "geometry.kind")
    ]


def test_planner_returns_capability_result_for_spec_and_build_mismatch(
) -> None:
    build_payload = minimal_cavity_case_build_payload()
    build_payload["case_name"] = "different_case"

    result = plan_simulation(
        SimulationSpec.model_validate(minimal_cavity_payload()),
        CaseBuildSpec.model_validate(build_payload),
    )

    assert result.status == "not_executable"
    assert [(reason.code, reason.path) for reason in result.reasons] == [
        ("planner.case_name_mismatch", "case_name")
    ]


def test_planner_rejects_cavity_mesh_values_the_writer_cannot_honor() -> None:
    payload = minimal_cavity_payload()
    payload["mesh"] = {"kind": "structured", "cells": {"x": 40, "y": 30, "z": 1}}

    result = plan_simulation(
        SimulationSpec.model_validate(payload),
        CaseBuildSpec.model_validate(minimal_cavity_case_build_payload()),
    )

    assert result.status == "not_executable"
    assert [(reason.code, reason.path) for reason in result.reasons] == [
        ("planner.unsupported_mesh_cells", "mesh.cells")
    ]


def test_planner_returns_capability_result_for_complete_unsupported_solver_family(
) -> None:
    payload = minimal_cavity_payload()
    payload["solver_family"] = "compressible_laminar"
    build_payload = minimal_cavity_case_build_payload()
    build_payload["solver_family"] = "compressible_laminar"

    result = plan_simulation(
        SimulationSpec.model_validate(payload),
        CaseBuildSpec.model_validate(build_payload),
    )

    assert result.status == "not_executable"
    assert [(reason.code, reason.path) for reason in result.reasons] == [
        ("planner.unsupported_solver_family", "solver_family")
    ]


def test_planner_returns_capability_result_for_complete_unsupported_mesh() -> None:
    payload = minimal_cavity_payload()
    payload["mesh"] = {
        "kind": "unstructured",
        "cells": {"x": 20, "y": 20, "z": 1},
    }
    build_payload = minimal_cavity_case_build_payload()
    build_payload["mesh"] = {"kind": "unstructured"}

    result = plan_simulation(
        SimulationSpec.model_validate(payload),
        CaseBuildSpec.model_validate(build_payload),
    )

    assert result.status == "not_executable"
    assert [(reason.code, reason.path) for reason in result.reasons] == [
        ("planner.unsupported_mesh", "mesh.kind")
    ]


def test_planner_returns_capability_result_for_unsupported_case_build_physics() -> None:
    build_payload = minimal_cavity_case_build_payload()
    build_payload["physics"] = {"kind": "compressible_laminar"}

    result = plan_simulation(
        SimulationSpec.model_validate(minimal_cavity_payload()),
        CaseBuildSpec.model_validate(build_payload),
    )

    assert result.status == "not_executable"
    assert [(reason.code, reason.path) for reason in result.reasons] == [
        ("planner.unsupported_physics", "physics.kind")
    ]


def test_planner_rejects_case_build_writer_family_the_writer_cannot_execute() -> None:
    build_payload = minimal_cavity_case_build_payload()
    build_payload["writer_operations"] = [
        {
            "id": "write_case_tree",
            "operation": "openfoam.write_case_tree",
            "parameters": {"case_family": "pipe"},
        }
    ]

    result = plan_simulation(
        SimulationSpec.model_validate(minimal_cavity_payload()),
        CaseBuildSpec.model_validate(build_payload),
    )

    assert result.status == "not_executable"
    assert [(reason.code, reason.path) for reason in result.reasons] == [
        (
            "planner.unsupported_case_build_family",
            "writer_operations.0.parameters.case_family",
        )
    ]


def test_planner_rejects_solvers_the_writer_cannot_execute_consistently() -> None:
    build_payload = minimal_cavity_case_build_payload()
    build_payload["solver"] = "pimpleFoam"

    result = plan_simulation(
        SimulationSpec.model_validate(minimal_cavity_payload()),
        CaseBuildSpec.model_validate(build_payload),
    )

    assert result.status == "not_executable"
    assert [(reason.code, reason.path) for reason in result.reasons] == [
        ("planner.unsupported_solver", "solver")
    ]


def test_planner_rejects_case_build_specs_missing_required_validators() -> None:
    build_payload = minimal_cavity_case_build_payload()
    build_payload["validators"] = ["case_structure"]

    result = plan_simulation(
        SimulationSpec.model_validate(minimal_cavity_payload()),
        CaseBuildSpec.model_validate(build_payload),
    )

    assert result.status == "not_executable"
    assert [(reason.code, reason.path) for reason in result.reasons] == [
        ("planner.missing_required_validator", "validators")
    ]


def test_planning_result_json_is_stable_and_sorted() -> None:
    build_payload = minimal_cavity_case_build_payload()
    build_payload["case_name"] = "different_case"
    result = plan_simulation(
        SimulationSpec.model_validate(minimal_cavity_payload()),
        CaseBuildSpec.model_validate(build_payload),
    )

    first = planning_result_to_json(result)
    second = planning_result_to_json(result)

    assert first == second
    assert first.endswith("\n")
    loaded = json.loads(first)
    assert list(loaded) == sorted(loaded)
    assert loaded["reasons"] == [
        {
            "code": "planner.case_name_mismatch",
            "message": "Simulation spec and case-build spec case names differ.",
            "metadata": {},
            "path": "case_name",
        }
    ]
