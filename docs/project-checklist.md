# OpenNavier Project Checklist

This checklist tracks feature progress and matching test coverage. A feature is
only marked done when the behavior exists, has deterministic tests where
reasonable, and has current validation evidence.

## Validation Status

Last checked: 2026-05-05

| Command | Status | Notes |
| --- | --- | --- |
| `.venv\Scripts\python.exe -m pytest` | Done | 71 tests passed in an earlier validation pass. |
| `.venv\Scripts\python.exe -m ruff check .` | Done | Ruff reported all checks passed. |
| `uv run pytest` | Done | 105 tests passed. |
| `.venv\Scripts\uv.exe run pytest` | Blocked | Not rechecked in this pass. |
| `$env:UV_CACHE_DIR='.tmp\uv-cache'; uv run pytest` | Not rechecked | Direct `uv run pytest` succeeded in this pass. |
| `uv run ruff check .` | Done | Ruff reported all checks passed. |
| `$env:UV_CACHE_DIR='.tmp\uv-cache'; uv run ruff check .` | Not rechecked | Direct `uv run ruff check .` succeeded in this pass. |
| `uv lock --check` | Done | Lock file is current. |
| `uv run opennavier --help` | Done | CLI help rendered successfully. |
| `$env:UV_CACHE_DIR='.tmp\uv-cache'; uv run opennavier --help` | Not rechecked | Direct `uv run opennavier --help` succeeded in this pass. |

When direct `uv run ...` commands are blocked by the default cache path, use a
workspace-local cache:

```powershell
$env:UV_CACHE_DIR='.tmp\uv-cache'; uv run pytest
$env:UV_CACHE_DIR='.tmp\uv-cache'; uv run ruff check .
$env:UV_CACHE_DIR='.tmp\uv-cache'; uv run opennavier --help
```

## Feature and Test Matrix

| Area | Feature or behavior | Feature status | Test status | Evidence | Next action |
| --- | --- | --- | --- | --- | --- |
| Repository | Python workspace with CLI, core, and OpenFOAM packages | Done | Done | `pyproject.toml`; `.venv\Scripts\python.exe -m pytest` | Keep package boundaries stable as features are added. |
| CLI | Typer application entrypoint | Done | Done | `tests/test_cli.py::test_help_shows_core_commands` | Add tests with each new command. |
| CLI | `opennavier check <case_path>` | Done | Done | `tests/test_cli.py::test_check_returns_success_for_valid_case`; `tests/test_cli.py::test_check_returns_failure_for_invalid_case` | Expand beyond case structure only after new validators are tested. |
| CLI | `opennavier doctor <case_path>` | Done | Done | `tests/test_cli.py::test_doctor_returns_nonzero_for_invalid_case`; `tests/test_doctor_logs.py` | Add more solver log patterns only after parser behavior is tested. |
| CLI | `opennavier report <case_path> --output <path>` | Done | Done | `tests/test_cli.py::test_report_writes_markdown_report`; `tests/test_manifest.py::test_report_manifest_output_writes_reproducibility_manifest_for_invalid_case` | Keep report and manifest artifact paths distinct. |
| Core diagnostics | Structured diagnostic result model with `PASS`, `FAIL`, and `WARN` | Done | Covered through consumers | `packages/core/src/opennavier_core/diagnostics.py`; CLI and validator tests | Add direct model tests if validation rules or serialization behavior expands. |
| Core diagnostics | Failure aggregation helper | Done | Covered through consumers | `opennavier_core.diagnostics.has_failures`; CLI exit-code tests | Keep exit-code tests as the public behavior contract. |
| OpenFOAM validation | Required case directory checks for `0`, `constant`, and `system` | Done | Done | `tests/test_case_structure.py` | Add more OpenFOAM checks as separate validators. |
| OpenFOAM validation | Required `system/controlDict`, `system/fvSchemes`, and `system/fvSolution` checks | Done | Done | `tests/test_case_structure.py` | Add dictionary-content validation separately. |
| OpenFOAM validation | Minimal `FoamFile` header checks for existing required system dictionaries | Done | Done | `tests/test_case_structure.py`; `tests/test_cli.py` | Add full dictionary parsing only when a concrete validation rule needs it. |
| OpenFOAM validation | Validation does not create or modify missing case paths | Done | Done | `tests/test_case_structure.py::test_missing_openfoam_case_paths_are_reported_without_creating_them` | Preserve read-only behavior for diagnostic commands. |
| Reporting | Deterministic Markdown report generation | Done | Done | `apps/cli/src/opennavier/cli/reporting.py`; report CLI test | Add golden-file or snapshot-style coverage if report formatting becomes more complex. |
| Documentation | README development and CLI usage notes | Done | Not applicable | `README.md`; `docs/cli.md` | Update whenever setup, commands, or scope changes. |
| Documentation | Project-management checklist | Done | Not applicable | `docs/project-checklist.md` | Update after each feature lands or validation status changes. |
| Examples | Reproducible `examples/cavity` case | Done | Done | `examples/cavity`; `tests/test_examples.py::test_committed_cavity_example_matches_template_and_validates_read_only` | Keep committed examples exact matches for deterministic templates and free of runtime artifacts. |
| CLI | `opennavier init cavity <case_path>` case creation | Done | Done | `tests/test_init.py` | Add more templates only after each command's generated file tree and overwrite behavior are tested. |
| CLI | JSON output for diagnostics | Done | Done | `tests/test_cli.py::test_check_json_returns_diagnostics_for_valid_case`; `tests/test_cli.py::test_doctor_json_returns_diagnostics_without_text_summary` | Keep JSON schema stable when new diagnostics are added. |
| Reporting | Reproducibility manifest output | Done | Done | `packages/core/src/opennavier_core/manifest.py`; `tests/test_manifest.py` | Keep manifest fields deterministic and update docs when the schema changes. |
| OpenFOAM runner | Local solver execution | Done | Done | `packages/openfoam/src/opennavier/openfoam/runner.py`; `tests/test_runner.py` | Add CLI wiring or real OpenFOAM integration tests only after the subprocess wrapper API is consumed. |
| OpenFOAM runner | Docker fallback execution | Not Started | Missing | Planned in `docs/plan.md` | Add only after native runner behavior is stable. |
| OpenFOAM diagnostics | Optional `checkMesh` and solver log diagnostics in `doctor` and reports | Done | Done | `tests/test_doctor_logs.py` | Keep optional logs non-blocking when absent and add new log locations through regression tests. |
| OpenFOAM parsing | Mesh quality parsing | Done | Done | `tests/test_mesh_quality.py`; `tests/test_doctor_logs.py::test_doctor_includes_mesh_warnings_from_check_mesh_log` | Expand thresholds only with deterministic fixtures. |
| OpenFOAM parsing | Residual parsing | Done | Done | `tests/test_residuals.py`; `tests/test_doctor_logs.py::test_doctor_includes_residual_warnings_from_solver_log` | Add solver variants only with captured-log fixtures. |
| OpenFOAM validation | Boundary-condition validation | Done | Done | `tests/test_boundary_conditions.py`; `.venv\Scripts\python.exe -m pytest tests/test_boundary_conditions.py` | Extend only with deterministic fixtures for additional generated case styles. |
| OpenFOAM templates | Deterministic lid-driven cavity case template generation | Done | Done | `packages/openfoam/src/opennavier/openfoam/init_case.py`; `tests/test_init.py` | Add templates for pipe or duct cases only after generated dictionaries and overwrite guards are specified in tests. |
| Gmsh adapter | Mesh generation adapter | Done | Done | `packages/gmsh/src/opennavier/gmsh/adapter.py`; `tests/test_gmsh_adapter.py` | Add real Gmsh integration tests only when the executable is an explicit test dependency. |
| FreeCAD adapter | Parametric geometry scripting adapter | Done | Done | `packages/freecad/src/opennavier/freecad/adapter.py`; `tests/test_freecad_adapter.py` | Add real FreeCAD integration tests only when the executable is an explicit test dependency. |
| ParaView adapter | Batch post-processing and screenshots | Not Started | Missing | Planned for a later phase in `docs/plan.md` | Delay until solver logs and result layout are available. |
| Studio | Desktop UI | Not Started | Missing | Planned for later in `docs/plan.md` | Start only after CLI usage validates workflows. |
| AI planning | Pydantic simulation specs from LLM output | Done | Done | `packages/core/src/opennavier_core/simulation_spec.py`; `tests/test_simulation_specs.py` | Keep specs as validated intent and add deterministic planner wiring only after external behavior is tested. |
| AI planning | LLM-written OpenFOAM dictionaries | Out of Scope | Not applicable | `docs/plan.md` says LLM should not directly write OpenFOAM files freely in v1. | Preserve deterministic dictionary generation and validation instead. |

## TDD Completion Rule

For every behavior-bearing change:

1. Add or update the failing test first.
2. Run the focused test and confirm it fails for the expected reason.
3. Implement the smallest production change that passes the test.
4. Run the focused test again.
5. Run the full available test suite.
6. Update this checklist with the new feature status, test status, evidence, and next action.

## Status Definitions

- Done: implemented, tested where reasonable, and recently validated.
- Partial: behavior exists but coverage, docs, or validation evidence is incomplete.
- Not Started: no behavior-bearing implementation exists yet.
- Blocked: cannot currently be validated or completed because of an environment or dependency issue.
- Out of Scope: intentionally excluded from the current product direction.
