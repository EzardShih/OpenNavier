import json

import pytest
from opennavier_core.case_build_spec import (
    CaseBuildCapabilityError,
    CaseBuildCapabilityIssue,
    CaseBuildSpec,
    case_build_spec_to_json,
    case_build_writer_capability_issues,
    create_case_build_dry_run,
)
from pydantic import ValidationError


def minimal_cavity_case_build_payload() -> dict[str, object]:
    case_path = "runs/lid_driven_cavity/case"
    return {
        "case_name": "lid_driven_cavity",
        "case_path": case_path,
        "solver_family": "incompressible_laminar",
        "solver": "icoFoam",
        "physics": {"kind": "incompressible_laminar"},
        "geometry": {"kind": "cavity"},
        "mesh": {"kind": "structured"},
        "writer_operations": [
            {
                "id": "write_case_tree",
                "operation": "openfoam.write_case_tree",
                "parameters": {"case_family": "cavity"},
            }
        ],
        "validators": ["case_structure", "boundary_conditions"],
        "expected_artifacts": [
            {"kind": "openfoam_field", "path": f"{case_path}/0/U"},
            {"kind": "openfoam_field", "path": f"{case_path}/0/p"},
            {
                "kind": "openfoam_dictionary",
                "path": f"{case_path}/constant/transportProperties",
            },
            {"kind": "openfoam_dictionary", "path": f"{case_path}/system/blockMeshDict"},
            {"kind": "openfoam_dictionary", "path": f"{case_path}/system/controlDict"},
            {"kind": "openfoam_dictionary", "path": f"{case_path}/system/fvSchemes"},
            {"kind": "openfoam_dictionary", "path": f"{case_path}/system/fvSolution"},
        ],
        "approval_checkpoints": [
            {
                "code": "approve_case_build_write",
                "message": "Approve writing the validated case-build spec.",
            },
            {
                "code": "approve_solver_execution",
                "message": "Approve local icoFoam execution.",
            },
        ],
    }


def minimal_duct_case_build_payload() -> dict[str, object]:
    case_path = "runs/duct_pressure_drop/case"
    return {
        "case_name": "duct_pressure_drop",
        "case_path": case_path,
        "solver_family": "incompressible_laminar",
        "solver": "simpleFoam",
        "physics": {"kind": "incompressible_laminar"},
        "geometry": {"kind": "duct"},
        "mesh": {"kind": "structured"},
        "writer_operations": [
            {
                "id": "write_case_tree",
                "operation": "openfoam.write_case_tree",
                "parameters": {"case_family": "duct"},
            }
        ],
        "validators": ["case_structure", "boundary_conditions"],
        "expected_artifacts": [
            {"kind": "openfoam_field", "path": f"{case_path}/0/U"},
            {"kind": "openfoam_field", "path": f"{case_path}/0/p"},
            {
                "kind": "openfoam_dictionary",
                "path": f"{case_path}/constant/transportProperties",
            },
            {
                "kind": "openfoam_dictionary",
                "path": f"{case_path}/constant/turbulenceProperties",
            },
            {"kind": "openfoam_dictionary", "path": f"{case_path}/system/blockMeshDict"},
            {"kind": "openfoam_dictionary", "path": f"{case_path}/system/controlDict"},
            {"kind": "openfoam_dictionary", "path": f"{case_path}/system/fvSchemes"},
            {"kind": "openfoam_dictionary", "path": f"{case_path}/system/fvSolution"},
        ],
        "approval_checkpoints": [
            {
                "code": "approve_case_build_write",
                "message": "Approve writing the validated duct case-build spec.",
            },
            {
                "code": "approve_solver_execution",
                "message": "Approve local simpleFoam execution.",
            },
        ],
    }


def test_case_build_spec_accepts_schema_backed_cavity_reference() -> None:
    spec = CaseBuildSpec.model_validate(minimal_cavity_case_build_payload())

    assert spec.schema_version == "1.0"
    assert spec.artifact_type == "case_build_spec"
    assert spec.local_only is True
    assert spec.cloud_upload is False
    assert spec.case_path == "runs/lid_driven_cavity/case"
    assert spec.writer_operations[0].operation == "openfoam.write_case_tree"
    assert [validator.name for validator in spec.validators] == [
        "case_structure",
        "boundary_conditions",
    ]


def test_case_build_spec_accepts_schema_backed_duct_reference() -> None:
    spec = CaseBuildSpec.model_validate(minimal_duct_case_build_payload())

    assert spec.case_name == "duct_pressure_drop"
    assert spec.solver == "simpleFoam"
    assert spec.geometry.kind == "duct"
    assert spec.writer_operations[0].parameters == {"case_family": "duct"}


def test_case_build_dry_run_reports_duct_file_operations() -> None:
    spec = CaseBuildSpec.model_validate(minimal_duct_case_build_payload())

    dry_run = create_case_build_dry_run(spec)

    assert dry_run.case_path == "runs/duct_pressure_drop/case"
    assert [operation.path for operation in dry_run.file_operations] == [
        "runs/duct_pressure_drop/case/0/U",
        "runs/duct_pressure_drop/case/0/p",
        "runs/duct_pressure_drop/case/constant/transportProperties",
        "runs/duct_pressure_drop/case/constant/turbulenceProperties",
        "runs/duct_pressure_drop/case/system/blockMeshDict",
        "runs/duct_pressure_drop/case/system/controlDict",
        "runs/duct_pressure_drop/case/system/fvSchemes",
        "runs/duct_pressure_drop/case/system/fvSolution",
    ]
    assert [command.id for command in dry_run.commands] == [
        "write_case_tree",
        "validate_case_structure",
        "validate_boundary_conditions",
    ]


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        (
            lambda payload: payload.update({"case_path": "../outside/case"}),
            "case_path",
        ),
        (
            lambda payload: payload.update({"case_path": "C:case"}),
            "case_path",
        ),
        (
            lambda payload: payload["expected_artifacts"].append(  # type: ignore[index,union-attr]
                {"kind": "report", "path": "runs/lid_driven_cavity/report.md"}
            ),
            "expected_artifacts",
        ),
        (
            lambda payload: payload["writer_operations"].append(  # type: ignore[index,union-attr]
                {
                    "id": "raw_dictionary",
                    "operation": "openfoam.write_case_tree",
                    "parameters": {"content": "FoamFile\n{\n}\n"},
                }
            ),
            "raw OpenFOAM dictionary text",
        ),
        (
            lambda payload: payload["writer_operations"].append(  # type: ignore[index,union-attr]
                {"id": "shell", "operation": "shell.command", "parameters": {}}
            ),
            "writer_operations",
        ),
        (
            lambda payload: payload["validators"].append("mesh_quality"),  # type: ignore[index,union-attr]
            "validators",
        ),
    ],
)
def test_case_build_spec_rejects_unsafe_or_unavailable_operations(
    mutation: object,
    match: str,
) -> None:
    payload = minimal_cavity_case_build_payload()
    mutation(payload)  # type: ignore[operator]

    with pytest.raises(ValidationError, match=match):
        CaseBuildSpec.model_validate(payload)


def test_case_build_dry_run_reports_deterministic_file_operations() -> None:
    spec = CaseBuildSpec.model_validate(minimal_cavity_case_build_payload())

    dry_run = create_case_build_dry_run(spec)

    assert dry_run.case_path == "runs/lid_driven_cavity/case"
    assert [operation.path for operation in dry_run.file_operations] == [
        "runs/lid_driven_cavity/case/0/U",
        "runs/lid_driven_cavity/case/0/p",
        "runs/lid_driven_cavity/case/constant/transportProperties",
        "runs/lid_driven_cavity/case/system/blockMeshDict",
        "runs/lid_driven_cavity/case/system/controlDict",
        "runs/lid_driven_cavity/case/system/fvSchemes",
        "runs/lid_driven_cavity/case/system/fvSolution",
    ]
    assert [validator.name for validator in dry_run.validators] == [
        "case_structure",
        "boundary_conditions",
    ]
    assert [artifact.path for artifact in dry_run.expected_artifacts] == [
        "runs/lid_driven_cavity/case/0/U",
        "runs/lid_driven_cavity/case/0/p",
        "runs/lid_driven_cavity/case/constant/transportProperties",
        "runs/lid_driven_cavity/case/system/blockMeshDict",
        "runs/lid_driven_cavity/case/system/controlDict",
        "runs/lid_driven_cavity/case/system/fvSchemes",
        "runs/lid_driven_cavity/case/system/fvSolution",
    ]


def test_case_build_spec_rejects_declared_artifacts_the_writer_will_not_create() -> None:
    payload = minimal_cavity_case_build_payload()
    payload["expected_artifacts"].append(  # type: ignore[index,union-attr]
        {
            "kind": "openfoam_dictionary",
            "path": "runs/lid_driven_cavity/case/system/customDict",
        }
    )

    with pytest.raises(ValidationError, match="deterministic writer outputs"):
        CaseBuildSpec.model_validate(payload)


def test_case_build_spec_rejects_windows_drive_relative_case_path() -> None:
    payload = minimal_cavity_case_build_payload()
    payload["case_path"] = "C:case"
    payload["expected_artifacts"] = [
        {"kind": "openfoam_field", "path": "C:case/0/U"},
        {"kind": "openfoam_field", "path": "C:case/0/p"},
        {
            "kind": "openfoam_dictionary",
            "path": "C:case/constant/transportProperties",
        },
        {"kind": "openfoam_dictionary", "path": "C:case/system/blockMeshDict"},
        {"kind": "openfoam_dictionary", "path": "C:case/system/controlDict"},
        {"kind": "openfoam_dictionary", "path": "C:case/system/fvSchemes"},
        {"kind": "openfoam_dictionary", "path": "C:case/system/fvSolution"},
    ]

    with pytest.raises(ValidationError, match="case_path"):
        CaseBuildSpec.model_validate(payload)


def test_case_build_capability_requires_declared_baseline_validators() -> None:
    payload = minimal_cavity_case_build_payload()
    payload["validators"] = ["case_structure"]
    spec = CaseBuildSpec.model_validate(payload)

    issues = case_build_writer_capability_issues(spec)

    assert issues == [
        CaseBuildCapabilityIssue(
            code="case_build.missing_required_validator",
            message=(
                "The current cavity writer requires the case_structure and "
                "boundary_conditions validators."
            ),
            path="validators",
        )
    ]


def test_case_build_capability_reports_unsupported_parameters_for_supported_family() -> None:
    payload = minimal_duct_case_build_payload()
    payload["writer_operations"][0]["parameters"]["unexpected"] = "ignored"  # type: ignore[index]
    spec = CaseBuildSpec.model_validate(payload)

    issues = case_build_writer_capability_issues(spec)

    assert issues == [
        CaseBuildCapabilityIssue(
            code="case_build.unsupported_writer_parameter",
            message="The current case-build writer does not support this parameter.",
            path="writer_operations.0.parameters.unexpected",
        )
    ]
    with pytest.raises(CaseBuildCapabilityError, match="does not support this parameter"):
        create_case_build_dry_run(spec)


def test_case_build_capability_reports_missing_openfoam_writer() -> None:
    payload = minimal_cavity_case_build_payload()
    payload["writer_operations"][0]["operation"] = "openfoam.write_unknown_case"  # type: ignore[index]
    spec = CaseBuildSpec.model_validate(payload)

    issues = case_build_writer_capability_issues(spec)

    assert issues == [
        CaseBuildCapabilityIssue(
            code="case_build.missing_writer",
            message="No deterministic case-build writer is available for this operation.",
            path="writer_operations.0.operation",
        )
    ]


def test_case_build_spec_json_is_stable_and_sorted() -> None:
    spec = CaseBuildSpec.model_validate(minimal_cavity_case_build_payload())

    first = case_build_spec_to_json(spec)
    second = case_build_spec_to_json(
        CaseBuildSpec.model_validate(minimal_cavity_case_build_payload())
    )

    assert first == second
    assert first.endswith("\n")
    loaded = json.loads(first)
    assert list(loaded) == sorted(loaded)
