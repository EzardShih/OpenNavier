# OpenNavier Project Checklist

This checklist tracks feature progress and matching test coverage. A feature is
only marked done when the behavior exists, has deterministic tests where
reasonable, and has current validation evidence.

## Validation Status

Last checked: 2026-05-04

| Command | Status | Notes |
| --- | --- | --- |
| `.venv\Scripts\python.exe -m pytest` | Done | 8 tests passed. |
| `.venv\Scripts\python.exe -m ruff check .` | Done | Ruff reported all checks passed. |
| `uv run pytest` | Blocked | `uv` is installed, but the default cache path `C:\Users\User\AppData\Local\uv\cache` cannot be initialized because access is denied. |
| `.venv\Scripts\uv.exe run pytest` | Blocked | Same default uv cache permission issue as above. |
| `$env:UV_CACHE_DIR='.tmp\uv-cache'; uv run pytest` | Done | 25 tests passed with a workspace-local uv cache. |
| `uv run ruff check .` | Blocked | Same default uv cache permission issue as above. |
| `$env:UV_CACHE_DIR='.tmp\uv-cache'; uv run ruff check .` | Done | Ruff reported all checks passed with a workspace-local uv cache. |
| `uv run opennavier --help` | Blocked | Same default uv cache permission issue as above. |
| `$env:UV_CACHE_DIR='.tmp\uv-cache'; uv run opennavier --help` | Done | CLI help rendered successfully with a workspace-local uv cache. |

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
| CLI | `opennavier doctor <case_path>` | Done | Done | `tests/test_cli.py::test_doctor_returns_nonzero_for_invalid_case` | Add specific issue explanations as new diagnostics are introduced. |
| CLI | `opennavier report <case_path> --output <path>` | Done | Done | `tests/test_cli.py::test_report_writes_markdown_report` | Add manifest or JSON output tests before implementing those formats. |
| Core diagnostics | Structured diagnostic result model with `PASS`, `FAIL`, and `WARN` | Done | Covered through consumers | `packages/core/src/opennavier_core/diagnostics.py`; CLI and validator tests | Add direct model tests if validation rules or serialization behavior expands. |
| Core diagnostics | Failure aggregation helper | Done | Covered through consumers | `opennavier_core.diagnostics.has_failures`; CLI exit-code tests | Keep exit-code tests as the public behavior contract. |
| OpenFOAM validation | Required case directory checks for `0`, `constant`, and `system` | Done | Done | `tests/test_case_structure.py` | Add more OpenFOAM checks as separate validators. |
| OpenFOAM validation | Required `system/controlDict`, `system/fvSchemes`, and `system/fvSolution` checks | Done | Done | `tests/test_case_structure.py` | Add dictionary-content validation separately. |
| OpenFOAM validation | Minimal `FoamFile` header checks for existing required system dictionaries | Done | Done | `tests/test_case_structure.py`; `tests/test_cli.py` | Add full dictionary parsing only when a concrete validation rule needs it. |
| OpenFOAM validation | Validation does not create or modify missing case paths | Done | Done | `tests/test_case_structure.py::test_missing_openfoam_case_paths_are_reported_without_creating_them` | Preserve read-only behavior for diagnostic commands. |
| Reporting | Deterministic Markdown report generation | Done | Done | `apps/cli/src/opennavier/cli/reporting.py`; report CLI test | Add golden-file or snapshot-style coverage if report formatting becomes more complex. |
| Documentation | README development and CLI usage notes | Done | Not applicable | `README.md`; `docs/cli.md` | Update whenever setup, commands, or scope changes. |
| Documentation | Project-management checklist | Done | Not applicable | `docs/project-checklist.md` | Update after each feature lands or validation status changes. |
| Examples | Reproducible `examples/cavity` case | Not Started | Missing | Planned in `docs/plan.md` | Add fixture-style example after template or init behavior is specified. |
| CLI | `opennavier init` case/template creation | Not Started | Missing | Planned in `docs/plan.md` | Define external behavior with tests before writing files. |
| CLI | JSON output for diagnostics | Not Started | Missing | Implied by stable diagnostics contract in `docs/cli.md` | Add CLI contract tests for JSON schema and exit codes. |
| Reporting | Reproducibility manifest output | Not Started | Missing | Planned in `docs/plan.md` | Define manifest fields and add tests before implementation. |
| OpenFOAM runner | Local solver execution | Not Started | Missing | Out of current scope in `docs/cli.md` | Start with subprocess wrapper tests using fake commands; mark real OpenFOAM tests as integration. |
| OpenFOAM runner | Docker fallback execution | Not Started | Missing | Planned in `docs/plan.md` | Add only after native runner behavior is stable. |
| OpenFOAM parsing | Mesh quality parsing | Done | Done | `tests/test_mesh_quality.py` | Integrate mesh-quality diagnostics into `doctor` and reports after parser behavior stabilizes. |
| OpenFOAM parsing | Residual parsing | Not Started | Missing | Planned in `docs/plan.md`; listed as not implemented in `docs/cli.md` | Use captured solver logs for deterministic parser tests. |
| OpenFOAM validation | Boundary-condition validation | Not Started | Missing | Planned in `docs/plan.md`; listed as not implemented in `docs/cli.md` | Define supported boundary checks before implementation. |
| OpenFOAM templates | Case template generation | Not Started | Missing | Planned in `docs/plan.md`; listed as not implemented in `docs/cli.md` | Add tests for generated file tree and dictionary contents first. |
| Gmsh adapter | Mesh generation adapter | Not Started | Missing | Planned for a later phase in `docs/plan.md` | Delay until case diagnostics and templates are stable. |
| FreeCAD adapter | Parametric geometry scripting adapter | Not Started | Missing | Planned for a later phase in `docs/plan.md` | Delay until the first OpenFOAM workflow is useful. |
| ParaView adapter | Batch post-processing and screenshots | Not Started | Missing | Planned for a later phase in `docs/plan.md` | Delay until solver logs and result layout are available. |
| Studio | Desktop UI | Not Started | Missing | Planned for later in `docs/plan.md` | Start only after CLI usage validates workflows. |
| AI planning | Pydantic simulation specs from LLM output | Not Started | Missing | Planned later in `docs/plan.md`; explicitly not implemented in `docs/cli.md` | Keep blocked until deterministic commands and validators are mature. |
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
