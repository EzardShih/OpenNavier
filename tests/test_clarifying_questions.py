from opennavier_core.questions import (
    ClarifyingQuestion,
    ClarifyingQuestionResult,
    build_clarifying_questions,
)


def test_clarifying_questions_cover_missing_engineering_inputs() -> None:
    result = build_clarifying_questions(
        request_text="simulate airflow through this part",
        partial_spec={"case_name": "airflow"},
    )

    assert result.status == "needs_answers"
    assert [question.missing_field for question in result.questions] == [
        "geometry",
        "units",
        "fluid",
        "boundary_conditions",
        "solver_family",
        "mesh",
        "objective",
        "output_expectations",
    ]
    assert result.questions[0] == ClarifyingQuestion(
        missing_field="geometry",
        why_it_matters="Geometry defines the domain and which deterministic writer can be used.",
        acceptable_answer_shape=(
            "Provide geometry.kind and geometry.dimensions with length, width, and height."
        ),
    )


def test_clarifying_questions_distinguish_complete_unsupported_capability() -> None:
    result = build_clarifying_questions(
        request_text="simulate compressible hypersonic flow over a wing",
        partial_spec={
            "case_name": "wing",
            "geometry": {"kind": "external_wing"},
            "units": {"length": "m", "velocity": "m/s"},
            "fluid": {"density": 1.2, "kinematic_viscosity": 1.5e-5},
            "boundary_conditions": [{"patch": "inlet"}],
            "solver_family": "compressible_turbulent",
            "mesh": {"kind": "unstructured"},
            "objective": "drag",
            "output_expectations": ["forces", "residuals"],
        },
        capability_reasons=[
            {
                "code": "planner.unsupported_geometry",
                "message": "No deterministic writer supports external wings yet.",
                "path": "geometry.kind",
            }
        ],
    )

    assert result == ClarifyingQuestionResult(
        status="complete_but_not_executable",
        questions=[],
        capability_reasons=[
            {
                "code": "planner.unsupported_geometry",
                "message": "No deterministic writer supports external wings yet.",
                "path": "geometry.kind",
            }
        ],
    )


def test_clarifying_questions_distinguish_not_yet_executable_physics() -> None:
    result = build_clarifying_questions(
        request_text="simulate compressible cavity flow",
        partial_spec={
            "case_name": "compressible_cavity",
            "geometry": {"kind": "cavity"},
            "units": {"length": "m"},
            "fluid": {"density": 1.2, "kinematic_viscosity": 1.5e-5},
            "boundary_conditions": [{"patch": "inlet"}],
            "solver_family": "compressible_laminar",
            "mesh": {"kind": "structured"},
            "objective": "convergence",
            "output_expectations": ["report"],
        },
        capability_reasons=[
            {
                "code": "planner.unsupported_physics",
                "message": "Compressible physics is not executable yet.",
                "path": "physics.kind",
            }
        ],
    )

    assert result.status == "complete_but_not_executable"
    assert result.capability_reasons[0]["code"] == "planner.unsupported_physics"
