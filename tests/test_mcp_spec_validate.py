import json
from collections.abc import Generator
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

import pytest
from opennavier.mcp.spec_tools import spec_validate


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


@pytest.fixture
def workspace_tmp_path() -> Generator[Path, None, None]:
    path = Path(".tmp") / f"mcp-spec-validate-{uuid4().hex}"
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        rmtree(path, ignore_errors=True)


def test_spec_validate_accepts_payload_without_reading_workspace(
    workspace_tmp_path: Path,
) -> None:
    result = spec_validate(
        workspace_root=str(workspace_tmp_path / "missing-workspace"),
        spec=minimal_cavity_spec(),
    )

    assert result == {
        "valid": True,
        "spec": minimal_cavity_spec(),
        "errors": [],
        "source": "payload",
    }


def test_spec_validate_reads_json_spec_inside_workspace(workspace_tmp_path: Path) -> None:
    spec_path = workspace_tmp_path / "specs" / "simulation.json"
    spec_path.parent.mkdir()
    spec_path.write_text(json.dumps(minimal_cavity_spec()), encoding="utf-8")

    result = spec_validate(workspace_root=str(workspace_tmp_path))

    assert result == {
        "valid": True,
        "spec": minimal_cavity_spec(),
        "errors": [],
        "source": "specs/simulation.json",
    }


def test_spec_validate_reports_pydantic_errors(workspace_tmp_path: Path) -> None:
    payload = minimal_cavity_spec()
    payload["solver_family"] = "unsupported"

    result = spec_validate(workspace_root=str(workspace_tmp_path), spec=payload)

    assert result["valid"] is False
    assert result["spec"] is None
    assert result["source"] == "payload"
    assert result["errors"]
    assert result["errors"][0]["type"] == "literal_error"
    assert "solver_family" in result["errors"][0]["message"]


def test_spec_validate_reports_malformed_json(workspace_tmp_path: Path) -> None:
    spec_path = workspace_tmp_path / "specs" / "simulation.json"
    spec_path.parent.mkdir()
    spec_path.write_text("{", encoding="utf-8")

    result = spec_validate(workspace_root=str(workspace_tmp_path))

    assert result["valid"] is False
    assert result["spec"] is None
    assert result["source"] == "specs/simulation.json"
    assert result["errors"] == [
        {
            "type": "json_decode_error",
            "message": "Malformed JSON in specs/simulation.json",
        }
    ]


def test_spec_validate_reports_unreadable_file(workspace_tmp_path: Path) -> None:
    result = spec_validate(workspace_root=str(workspace_tmp_path))

    assert result["valid"] is False
    assert result["spec"] is None
    assert result["source"] == "specs/simulation.json"
    assert result["errors"]
    assert result["errors"][0]["type"] == "file_read_error"
    assert "specs/simulation.json" in result["errors"][0]["message"]


def test_spec_validate_reports_workspace_path_errors(workspace_tmp_path: Path) -> None:
    result = spec_validate(
        workspace_root=str(workspace_tmp_path), spec_path="../simulation.json"
    )

    assert result["valid"] is False
    assert result["spec"] is None
    assert result["source"] == "../simulation.json"
    assert result["errors"]
    assert result["errors"][0]["type"] == "workspace_path_error"
    assert "escapes workspace root" in result["errors"][0]["message"]
