import json
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from opennavier_core.workspace_path import normalize_workspace_relative_path

SCHEMA_VERSION = "1.0"
SUPPORTED_WRITER_OPERATIONS = frozenset({"openfoam.write_case_tree"})
SUPPORTED_VALIDATORS = frozenset({"case_structure", "boundary_conditions"})
REQUIRED_CAVITY_VALIDATORS = frozenset({"case_structure", "boundary_conditions"})
SUPPORTED_CAVITY_CASE_FAMILY = "cavity"
SUPPORTED_CAVITY_SOLVER_FAMILY = "incompressible_laminar"
SUPPORTED_CAVITY_SOLVER = "icoFoam"
SUPPORTED_CAVITY_PHYSICS = "incompressible_laminar"
SUPPORTED_CAVITY_GEOMETRY = "cavity"
SUPPORTED_CAVITY_MESH = "structured"
SUPPORTED_CAVITY_WRITER_PARAMETERS = frozenset({"case_family"})
CAVITY_WRITER_ARTIFACTS = (
    ("openfoam_field", "0/U"),
    ("openfoam_field", "0/p"),
    ("openfoam_dictionary", "constant/transportProperties"),
    ("openfoam_dictionary", "system/blockMeshDict"),
    ("openfoam_dictionary", "system/controlDict"),
    ("openfoam_dictionary", "system/fvSchemes"),
    ("openfoam_dictionary", "system/fvSolution"),
)
RAW_DICTIONARY_PARAMETER_KEYS = frozenset(
    {
        "body",
        "content",
        "dictionary",
        "dictionary_text",
        "raw_dictionary",
        "raw_text",
        "text",
    }
)


class CaseBuildSpecModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CaseBuildCapabilityIssue(CaseBuildSpecModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    path: str = Field(min_length=1)


class CaseBuildCapabilityError(ValueError):
    def __init__(self, issues: list[CaseBuildCapabilityIssue]) -> None:
        self.issues = issues
        super().__init__("; ".join(issue.message for issue in issues))


class CaseBuildPhysics(CaseBuildSpecModel):
    kind: str = Field(min_length=1)


class CaseBuildGeometry(CaseBuildSpecModel):
    kind: str = Field(min_length=1)


class CaseBuildMesh(CaseBuildSpecModel):
    kind: str = Field(min_length=1)


class CaseBuildWriterOperation(CaseBuildSpecModel):
    id: str = Field(min_length=1)
    operation: str = Field(min_length=1)
    parameters: dict[str, str | int | float | bool] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_supported_typed_operation(self) -> Self:
        if self.operation not in SUPPORTED_WRITER_OPERATIONS:
            raise ValueError(
                f"Unsupported writer operation in writer_operations: {self.operation}"
            )

        for key, value in self.parameters.items():
            if key.lower() in RAW_DICTIONARY_PARAMETER_KEYS:
                raise ValueError("CaseBuildSpec rejects raw OpenFOAM dictionary text")
            if isinstance(value, str) and _looks_like_openfoam_dictionary(value):
                raise ValueError("CaseBuildSpec rejects raw OpenFOAM dictionary text")

        return self


class CaseBuildValidator(CaseBuildSpecModel):
    name: Literal["case_structure", "boundary_conditions"]


class CaseBuildArtifact(CaseBuildSpecModel):
    kind: str = Field(min_length=1)
    path: str = Field(min_length=1)

    @field_validator("path")
    @classmethod
    def validate_path_is_safe_relative(cls, value: str) -> str:
        return normalize_workspace_relative_path(
            value, field_name="expected_artifacts.path"
        )


class CaseBuildApproval(CaseBuildSpecModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)


class CaseBuildFileOperation(CaseBuildSpecModel):
    action: Literal["write"] = "write"
    path: str = Field(min_length=1)
    writer_operation_id: str = Field(min_length=1)


class CaseBuildDryRun(CaseBuildSpecModel):
    case_path: str = Field(min_length=1)
    file_operations: list[CaseBuildFileOperation] = Field(default_factory=list)
    writer_operations: list[CaseBuildWriterOperation] = Field(default_factory=list)
    validators: list[CaseBuildValidator] = Field(default_factory=list)
    expected_artifacts: list[CaseBuildArtifact] = Field(default_factory=list)
    approval_checkpoints: list[CaseBuildApproval] = Field(default_factory=list)


class CaseBuildSpec(CaseBuildSpecModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    artifact_type: Literal["case_build_spec"] = "case_build_spec"
    local_only: bool = True
    cloud_upload: bool = False
    case_name: str = Field(min_length=1)
    case_path: str = Field(min_length=1)
    solver_family: str = Field(min_length=1)
    solver: str = Field(min_length=1)
    physics: CaseBuildPhysics
    geometry: CaseBuildGeometry
    mesh: CaseBuildMesh
    writer_operations: list[CaseBuildWriterOperation] = Field(min_length=1)
    validators: list[CaseBuildValidator] = Field(min_length=1)
    expected_artifacts: list[CaseBuildArtifact] = Field(default_factory=list)
    approval_checkpoints: list[CaseBuildApproval] = Field(default_factory=list)

    @field_validator("case_path")
    @classmethod
    def validate_case_path_is_safe_relative(cls, value: str) -> str:
        return normalize_workspace_relative_path(value, field_name="case_path")

    @field_validator("validators", mode="before")
    @classmethod
    def coerce_validator_names(cls, value: object) -> object:
        if isinstance(value, list):
            return [{"name": item} if isinstance(item, str) else item for item in value]
        return value

    @model_validator(mode="after")
    def validate_case_build_spec(self) -> Self:
        if not self.local_only:
            raise ValueError("CaseBuildSpec must remain local-only")
        if self.cloud_upload:
            raise ValueError("CaseBuildSpec does not allow cloud upload")

        case_path = f"{self.case_path}/"
        for artifact in self.expected_artifacts:
            if not artifact.path.startswith(case_path):
                raise ValueError("expected_artifacts must stay under case_path")

        writer_artifacts = _expected_artifacts_for_declared_cavity_writer(
            self.case_path,
            self.writer_operations,
        )
        if writer_artifacts is not None and self.expected_artifacts:
            expected = _artifact_identity_set(writer_artifacts)
            declared = _artifact_identity_set(self.expected_artifacts)
            if declared != expected:
                raise ValueError(
                    "expected_artifacts must match deterministic writer outputs"
                )

        return self


def create_case_build_dry_run(spec: CaseBuildSpec) -> CaseBuildDryRun:
    artifacts = case_build_writer_expected_artifacts(spec)
    writer_operation_id = spec.writer_operations[0].id
    file_operations = [
        CaseBuildFileOperation(path=artifact.path, writer_operation_id=writer_operation_id)
        for artifact in artifacts
    ]
    return CaseBuildDryRun(
        case_path=spec.case_path,
        file_operations=file_operations,
        writer_operations=spec.writer_operations,
        validators=spec.validators,
        expected_artifacts=artifacts,
        approval_checkpoints=spec.approval_checkpoints,
    )


def case_build_writer_expected_artifacts(spec: CaseBuildSpec) -> list[CaseBuildArtifact]:
    issues = case_build_writer_capability_issues(spec)
    if issues:
        raise CaseBuildCapabilityError(issues)
    return _cavity_expected_artifacts(spec.case_path)


def case_build_writer_capability_issues(
    spec: CaseBuildSpec,
) -> list[CaseBuildCapabilityIssue]:
    issues: list[CaseBuildCapabilityIssue] = []

    if len(spec.writer_operations) != 1:
        issues.append(
            CaseBuildCapabilityIssue(
                code="case_build.unsupported_writer_operation_count",
                message="The current case-build writer supports exactly one writer operation.",
                path="writer_operations",
            )
        )
        return issues

    operation = spec.writer_operations[0]
    unknown_parameters = sorted(
        set(operation.parameters) - SUPPORTED_CAVITY_WRITER_PARAMETERS
    )
    if unknown_parameters:
        issues.append(
            CaseBuildCapabilityIssue(
                code="case_build.unsupported_writer_parameter",
                message="The current case-build writer does not support this parameter.",
                path=f"writer_operations.0.parameters.{unknown_parameters[0]}",
            )
        )

    case_family = operation.parameters.get("case_family")
    if case_family != SUPPORTED_CAVITY_CASE_FAMILY:
        issues.append(
            CaseBuildCapabilityIssue(
                code="case_build.unsupported_case_build_family",
                message="The current case-build writer only supports cavity cases.",
                path="writer_operations.0.parameters.case_family",
            )
        )

    if spec.solver_family != SUPPORTED_CAVITY_SOLVER_FAMILY:
        issues.append(
            CaseBuildCapabilityIssue(
                code="case_build.unsupported_solver_family",
                message="The current case-build writer only supports incompressible laminar cases.",
                path="solver_family",
            )
        )
    if spec.solver != SUPPORTED_CAVITY_SOLVER:
        issues.append(
            CaseBuildCapabilityIssue(
                code="case_build.unsupported_solver",
                message="The current case-build writer only supports icoFoam.",
                path="solver",
            )
        )
    if spec.physics.kind != SUPPORTED_CAVITY_PHYSICS:
        issues.append(
            CaseBuildCapabilityIssue(
                code="case_build.unsupported_physics",
                message=(
                    "The current case-build writer only supports "
                    "incompressible laminar physics."
                ),
                path="physics.kind",
            )
        )
    if spec.geometry.kind != SUPPORTED_CAVITY_GEOMETRY:
        issues.append(
            CaseBuildCapabilityIssue(
                code="case_build.unsupported_geometry",
                message="The current case-build writer only supports cavity geometry.",
                path="geometry.kind",
            )
        )
    if spec.mesh.kind != SUPPORTED_CAVITY_MESH:
        issues.append(
            CaseBuildCapabilityIssue(
                code="case_build.unsupported_mesh",
                message="The current case-build writer only supports structured meshes.",
                path="mesh.kind",
            )
        )

    declared_validators = {validator.name for validator in spec.validators}
    missing_validators = REQUIRED_CAVITY_VALIDATORS - declared_validators
    if missing_validators:
        issues.append(
            CaseBuildCapabilityIssue(
                code="case_build.missing_required_validator",
                message=(
                    "The current cavity writer requires the case_structure and "
                    "boundary_conditions validators."
                ),
                path="validators",
            )
        )

    return issues


def case_build_spec_to_json(spec: CaseBuildSpec) -> str:
    return json.dumps(spec.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def _looks_like_openfoam_dictionary(value: str) -> bool:
    return "FoamFile" in value or "boundaryField" in value or "dimensions" in value


def _expected_artifacts_for_declared_cavity_writer(
    case_path: str,
    writer_operations: list[CaseBuildWriterOperation],
) -> list[CaseBuildArtifact] | None:
    if len(writer_operations) != 1:
        return None
    if writer_operations[0].parameters.get("case_family") != SUPPORTED_CAVITY_CASE_FAMILY:
        return None
    return _cavity_expected_artifacts(case_path)


def _cavity_expected_artifacts(case_path: str) -> list[CaseBuildArtifact]:
    return [
        CaseBuildArtifact(kind=kind, path=f"{case_path}/{relative_path}")
        for kind, relative_path in CAVITY_WRITER_ARTIFACTS
    ]


def _artifact_identity_set(
    artifacts: list[CaseBuildArtifact],
) -> set[tuple[str, str]]:
    return {(artifact.kind, artifact.path) for artifact in artifacts}
