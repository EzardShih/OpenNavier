import pytest
from opennavier_core.simulation_spec import SimulationSpec
from pydantic import ValidationError


def minimal_cavity_spec() -> dict[str, object]:
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
            {
                "patch": "fixedWalls",
                "field": "U",
                "kind": "noSlip",
            },
            {
                "patch": "frontAndBack",
                "field": "U",
                "kind": "empty",
            },
            {
                "patch": "movingWall",
                "field": "p",
                "kind": "zeroGradient",
            },
            {
                "patch": "fixedWalls",
                "field": "p",
                "kind": "zeroGradient",
            },
            {
                "patch": "frontAndBack",
                "field": "p",
                "kind": "empty",
            },
        ],
        "run_control": {
            "start_time": 0.0,
            "end_time": 0.5,
            "time_step": 0.005,
            "write_interval": 0.1,
        },
    }


def test_simulation_spec_parses_valid_minimal_cavity_llm_output() -> None:
    spec = SimulationSpec.model_validate(minimal_cavity_spec())

    assert spec.case_name == "lid_driven_cavity"
    assert spec.solver_family == "incompressible_laminar"
    assert spec.geometry.kind == "cavity"
    assert spec.mesh.cells.x == 20
    assert spec.fluid.kinematic_viscosity == 0.01
    assert spec.boundary_conditions[0].patch == "movingWall"
    assert spec.run_control.end_time == 0.5


def test_simulation_spec_accepts_json_like_llm_output() -> None:
    json_payload = SimulationSpec.model_validate(minimal_cavity_spec()).model_dump_json()

    spec = SimulationSpec.model_validate_json(json_payload)

    assert spec.case_name == "lid_driven_cavity"
    assert spec.boundary_conditions[-1].kind == "empty"


def test_simulation_spec_rejects_unknown_solver_family() -> None:
    payload = minimal_cavity_spec()
    payload["solver_family"] = "llm_generated_magic_solver"

    with pytest.raises(ValidationError, match="solver_family"):
        SimulationSpec.model_validate(payload)


def test_simulation_spec_rejects_missing_boundary_conditions() -> None:
    payload = minimal_cavity_spec()
    payload["boundary_conditions"] = []

    with pytest.raises(ValidationError, match="boundary_conditions"):
        SimulationSpec.model_validate(payload)


@pytest.mark.parametrize(
    "path",
    [
        ("mesh", "cells", "grading"),
        ("run_control", "write_control"),
    ],
)
def test_simulation_spec_rejects_unsupported_fields(path: tuple[str, ...]) -> None:
    payload = minimal_cavity_spec()
    target = payload
    for key in path[:-1]:
        target = target[key]  # type: ignore[index,assignment]
    target[path[-1]] = "unsupported"  # type: ignore[index]

    with pytest.raises(ValidationError, match=path[-1]):
        SimulationSpec.model_validate(payload)


@pytest.mark.parametrize(
    ("path", "invalid_value"),
    [
        (("mesh", "cells", "x"), 0),
        (("mesh", "cells", "y"), -2),
        (("fluid", "density"), 0.0),
        (("fluid", "kinematic_viscosity"), -0.01),
        (("run_control", "end_time"), 0.0),
        (("run_control", "time_step"), 0.0),
        (("run_control", "write_interval"), -1.0),
    ],
)
def test_simulation_spec_rejects_non_positive_mesh_fluid_and_run_values(
    path: tuple[str, ...],
    invalid_value: object,
) -> None:
    payload = minimal_cavity_spec()
    target = payload
    for key in path[:-1]:
        target = target[key]  # type: ignore[index,assignment]
    target[path[-1]] = invalid_value  # type: ignore[index]

    with pytest.raises(ValidationError, match=path[-1]):
        SimulationSpec.model_validate(payload)


@pytest.mark.parametrize(
    "boundary_condition",
    [
        {"patch": "movingWall", "field": "p", "kind": "noSlip"},
        {"patch": "movingWall", "field": "U", "kind": "fixedValue"},
        {
            "patch": "movingWall",
            "field": "U",
            "kind": "fixedValue",
            "value": [1.0, 0.0],
        },
        {
            "patch": "fixedWalls",
            "field": "U",
            "kind": "noSlip",
            "value": [0.0, 0.0, 0.0],
        },
    ],
)
def test_simulation_spec_rejects_invalid_boundary_condition_combinations(
    boundary_condition: dict[str, object],
) -> None:
    payload = minimal_cavity_spec()
    payload["boundary_conditions"] = [boundary_condition]

    with pytest.raises(ValidationError, match="boundary_conditions"):
        SimulationSpec.model_validate(payload)


@pytest.mark.parametrize(
    ("start_time", "end_time"),
    [
        (0.5, 0.5),
        (1.0, 0.5),
    ],
)
def test_simulation_spec_rejects_run_controls_that_end_before_they_start(
    start_time: float,
    end_time: float,
) -> None:
    payload = minimal_cavity_spec()
    payload["run_control"]["start_time"] = start_time  # type: ignore[index]
    payload["run_control"]["end_time"] = end_time  # type: ignore[index]

    with pytest.raises(ValidationError, match="end_time"):
        SimulationSpec.model_validate(payload)


def test_simulation_spec_is_structured_intent_not_dictionary_writer() -> None:
    spec = SimulationSpec.model_validate(minimal_cavity_spec())

    assert not hasattr(spec, "write_openfoam_dictionaries")
    assert not hasattr(spec, "to_openfoam_dict")
    assert spec.model_dump()["geometry"]["kind"] == "cavity"
