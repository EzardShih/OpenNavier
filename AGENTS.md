# Repository Guidelines

## Project Structure & Module Organization

This repository is currently in planning stage. The only committed material is under `docs/`, with `docs/plan.md` describing the intended local-first OpenFOAM automation product.

The planned implementation should follow this layout:

- `apps/cli/` for the command-line interface.
- `apps/studio/` for a later desktop UI.
- `packages/core/` for specs, planners, validators, and reports.
- `packages/openfoam/` for templates, dictionary writers, runners, logs, and diagnostics.
- `packages/gmsh/`, `packages/freecad/`, and `packages/paraview/` for tool adapters.
- `examples/` for reproducible demo cases such as `cavity/`, `pipe-flow/`, and `duct-pressure-drop/`.
- `tests/` for automated tests matching the package structure.

## Build, Test, and Development Commands

No build system is checked in yet. Until code is added, use documentation review as the main validation step:

```bash
rg "TODO|TBD|FIXME" docs
```

When the Python CLI is introduced, use the decided `pyproject.toml` + `uv` workflow:

```bash
uv sync
uv run pytest
uv run ruff check .
uv run python -m opennavier.cli --help
opennavier doctor ./examples/cavity
```

Document any new setup, lint, or test commands in `README.md` when those files are added.

## Coding Style & Naming Conventions

Use Python 3.11+ for orchestration, validators, runners, and report generation unless a package has a clear reason to use another language. Prefer Typer for CLI commands, Pydantic for validated specs, Jinja2 for templates, pytest for tests, and Ruff for formatting/linting. Use `snake_case` for modules, functions, fixtures, and CLI command names.

Keep generated simulation artifacts out of source packages. Store reusable templates under package template directories and runtime outputs under ignored `runs/` or `examples/*/run/` paths.

## Testing Guidelines

Follow strict test-driven development for every behavior change. Write or update the failing test first, run the focused test to confirm it fails for the expected reason, implement the smallest production change that makes it pass, then refactor while keeping tests green. Do not add behavior-bearing code before the corresponding test exists.

Every bug fix must start with a regression test that reproduces the bug. Every new feature must start with tests that define the intended external behavior and important edge cases. If a change cannot reasonably be tested, document the reason in the PR and keep the implementation isolated.

Add tests with each behavior-bearing module. Place tests in `tests/` using names like `test_case_structure.py` and `test_residuals.py`. Focus early coverage on deterministic checks: case folder validation, OpenFOAM log parsing, mesh-quality parsing, report manifests, CLI argument handling, dictionary generation, and adapter error handling.

Tests should not require OpenFOAM unless explicitly marked as integration tests. Use small fixture cases and captured logs for fast unit tests.

Before considering work complete, run the narrow test target added or changed for the task, then run the full available test suite. If the full suite cannot be run, state the blocker clearly with the exact command that should be run later.

## Commit & Pull Request Guidelines

This directory is not currently a Git repository, so no local commit convention is available. Use concise, imperative commit messages such as `Add case structure validator` or `Document OpenFOAM doctor workflow`.

Pull requests should include a short problem statement, implemented change, validation commands, and any screenshots or report samples for user-facing output. Link issues when available and call out solver, licensing, or local-data privacy implications.

## Agent-Specific Instructions

Preserve the local-first, engineer-verifiable product direction from `docs/plan.md`. Do not add cloud upload paths, opaque solver behavior, or LLM-written OpenFOAM dictionaries without deterministic validation.

Agents must follow TDD exactly: red, green, refactor. For implementation tasks, first inspect the relevant behavior, add or update tests, verify the new test fails, implement the minimal fix, verify the new test passes, then run broader validation. Do not skip the red step unless the user explicitly asks for documentation-only or exploratory work.
