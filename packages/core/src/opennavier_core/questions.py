from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class QuestionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ClarifyingQuestion(QuestionModel):
    missing_field: str = Field(min_length=1)
    why_it_matters: str = Field(min_length=1)
    acceptable_answer_shape: str = Field(min_length=1)


class ClarifyingQuestionResult(QuestionModel):
    status: Literal["needs_answers", "ready", "complete_but_not_executable"]
    questions: list[ClarifyingQuestion] = Field(default_factory=list)
    capability_reasons: list[dict[str, str]] = Field(default_factory=list)


QUESTION_DEFINITIONS = {
    "geometry": ClarifyingQuestion(
        missing_field="geometry",
        why_it_matters="Geometry defines the domain and which deterministic writer can be used.",
        acceptable_answer_shape=(
            "Provide geometry.kind and geometry.dimensions with length, width, and height."
        ),
    ),
    "units": ClarifyingQuestion(
        missing_field="units",
        why_it_matters="Units make dimensions, velocity, pressure, and fluid properties auditable.",
        acceptable_answer_shape="Provide units such as length=m and velocity=m/s.",
    ),
    "fluid": ClarifyingQuestion(
        missing_field="fluid",
        why_it_matters="Fluid properties determine the Reynolds regime and dictionary values.",
        acceptable_answer_shape="Provide density and kinematic_viscosity as positive numbers.",
    ),
    "boundary_conditions": ClarifyingQuestion(
        missing_field="boundary_conditions",
        why_it_matters="Boundary conditions define inlet, outlet, wall, and field behavior.",
        acceptable_answer_shape="Provide patch, field, kind, and value where required.",
    ),
    "solver_family": ClarifyingQuestion(
        missing_field="solver_family",
        why_it_matters="The solver family gates deterministic compatibility checks.",
        acceptable_answer_shape="Provide a supported family such as incompressible_laminar.",
    ),
    "mesh": ClarifyingQuestion(
        missing_field="mesh",
        why_it_matters="Mesh intent determines whether a deterministic mesh writer can be used.",
        acceptable_answer_shape="Provide mesh.kind and mesh.cells with x, y, and z counts.",
    ),
    "objective": ClarifyingQuestion(
        missing_field="objective",
        why_it_matters="The objective determines what the report should evaluate.",
        acceptable_answer_shape=(
            "Provide a short objective such as pressure_drop or convergence_check."
        ),
    ),
    "output_expectations": ClarifyingQuestion(
        missing_field="output_expectations",
        why_it_matters="Expected outputs determine which artifacts and diagnostics are useful.",
        acceptable_answer_shape="Provide a list such as diagnostics, residuals, and report.",
    ),
}


def build_clarifying_questions(
    *,
    request_text: str,
    partial_spec: dict[str, object],
    capability_reasons: list[dict[str, str]] | None = None,
) -> ClarifyingQuestionResult:
    del request_text

    if capability_reasons:
        return ClarifyingQuestionResult(
            status="complete_but_not_executable",
            questions=[],
            capability_reasons=capability_reasons,
        )

    missing_fields = _missing_fields(partial_spec)
    if missing_fields:
        return ClarifyingQuestionResult(
            status="needs_answers",
            questions=[QUESTION_DEFINITIONS[field] for field in missing_fields],
        )

    return ClarifyingQuestionResult(status="ready", questions=[])


def _missing_fields(partial_spec: dict[str, object]) -> list[str]:
    return [
        field
        for field, predicate in (
            ("geometry", _has_geometry),
            ("units", _has_units),
            ("fluid", _has_fluid),
            ("boundary_conditions", _has_boundary_conditions),
            ("solver_family", _has_solver_family),
            ("mesh", _has_mesh),
            ("objective", _has_objective),
            ("output_expectations", _has_output_expectations),
        )
        if not predicate(partial_spec)
    ]


def _has_geometry(partial_spec: dict[str, object]) -> bool:
    geometry = partial_spec.get("geometry")
    return isinstance(geometry, dict) and bool(geometry.get("kind")) and "dimensions" in geometry


def _has_units(partial_spec: dict[str, object]) -> bool:
    units = partial_spec.get("units")
    return isinstance(units, dict) and bool(units.get("length"))


def _has_fluid(partial_spec: dict[str, object]) -> bool:
    fluid = partial_spec.get("fluid")
    return (
        isinstance(fluid, dict)
        and "density" in fluid
        and "kinematic_viscosity" in fluid
    )


def _has_boundary_conditions(partial_spec: dict[str, object]) -> bool:
    boundary_conditions = partial_spec.get("boundary_conditions")
    return isinstance(boundary_conditions, list) and bool(boundary_conditions)


def _has_solver_family(partial_spec: dict[str, object]) -> bool:
    return bool(partial_spec.get("solver_family"))


def _has_mesh(partial_spec: dict[str, object]) -> bool:
    mesh = partial_spec.get("mesh")
    return isinstance(mesh, dict) and bool(mesh.get("kind")) and "cells" in mesh


def _has_objective(partial_spec: dict[str, object]) -> bool:
    return bool(partial_spec.get("objective"))


def _has_output_expectations(partial_spec: dict[str, object]) -> bool:
    output_expectations = partial_spec.get("output_expectations")
    return isinstance(output_expectations, list) and bool(output_expectations)
