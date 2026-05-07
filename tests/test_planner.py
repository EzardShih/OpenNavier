import json

import pytest
from opennavier_core.planner import PlanningRejected, plan_simulation, planning_rejection_to_json


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


def test_planner_accepts_cavity_payload_and_keeps_order_deterministic() -> None:
    plan = plan_simulation(minimal_cavity_payload())

    assert plan.case_name == "lid_driven_cavity"
    assert plan.solver == "icoFoam"
    assert [command.id for command in plan.commands] == [
        "initialize_cavity_case",
        "validate_case_structure",
        "generate_mesh",
        "check_mesh",
        "run_solver",
        "collect_diagnostics",
        "write_report",
    ]
    assert [check.code for check in plan.pre_flight_checks] == sorted(
        check.code for check in plan.pre_flight_checks
    )


@pytest.mark.parametrize(
    ("mutation", "expected_code", "expected_path"),
    [
        (
            lambda payload: payload.update({"physics": "compressible"}),
            "planner.unsupported_physics",
            "physics",
        ),
        (
            lambda payload: payload.update({"solver_family": "compressible_laminar"}),
            "planner.unsupported_solver_family",
            "solver_family",
        ),
        (
            lambda payload: payload.update({"geometry": {"kind": "pipe"}}),
            "planner.unsupported_geometry",
            "geometry.kind",
        ),
        (
            lambda payload: payload.update({"mesh": {"kind": "unstructured"}}),
            "planner.unsupported_mesh",
            "mesh.kind",
        ),
    ],
)
def test_planner_rejects_unsupported_specs_with_structured_reasons(
    mutation: object,
    expected_code: str,
    expected_path: str,
) -> None:
    payload = minimal_cavity_payload()
    mutation(payload)  # type: ignore[operator]

    with pytest.raises(PlanningRejected) as raised:
        plan_simulation(payload)

    rejection = raised.value.rejection
    assert rejection.status == "rejected"
    assert [(reason.code, reason.path) for reason in rejection.reasons] == [
        (expected_code, expected_path)
    ]
    assert not hasattr(rejection, "commands")


@pytest.mark.parametrize(
    ("field_name", "expected_path"),
    [
        ("geometry", "geometry"),
        ("mesh", "mesh"),
        ("fluid", "fluid"),
        ("boundary_conditions", "boundary_conditions"),
        ("run_control", "run_control"),
    ],
)
def test_planner_rejects_missing_inputs_without_partial_plan(
    field_name: str,
    expected_path: str,
) -> None:
    payload = minimal_cavity_payload()
    del payload[field_name]

    with pytest.raises(PlanningRejected) as raised:
        plan_simulation(payload)

    assert [(reason.code, reason.path) for reason in raised.value.rejection.reasons] == [
        ("planner.missing_input", expected_path)
    ]


def test_planner_rejects_cavity_specs_that_do_not_match_committed_template() -> None:
    payload = minimal_cavity_payload()
    mesh = payload["mesh"]
    assert isinstance(mesh, dict)
    cells = mesh["cells"]
    assert isinstance(cells, dict)
    cells["x"] = 40

    with pytest.raises(PlanningRejected) as raised:
        plan_simulation(payload)

    assert [
        (reason.code, reason.path, reason.metadata)
        for reason in raised.value.rejection.reasons
    ] == [
        (
            "planner.unsupported_template_parameter",
            "mesh.cells.x",
            {"received": "40", "supported": "20"},
        )
    ]


def test_planner_rejection_json_is_stable_and_sorted() -> None:
    payload = minimal_cavity_payload()
    del payload["boundary_conditions"]

    with pytest.raises(PlanningRejected) as raised:
        plan_simulation(payload)

    first = planning_rejection_to_json(raised.value.rejection)
    second = planning_rejection_to_json(raised.value.rejection)

    assert first == second
    assert first.endswith("\n")
    loaded = json.loads(first)
    assert list(loaded) == sorted(loaded)
    assert loaded["reasons"] == [
        {
            "code": "planner.missing_input",
            "message": "Required simulation input is missing.",
            "metadata": {},
            "path": "boundary_conditions",
        }
    ]
