# OpenNavier CLI

The OpenNavier CLI is the first usable slice of the local-first OpenFOAM
automation workflow. It does not run OpenFOAM yet. It inspects an existing case
directory, reports deterministic diagnostics, and can write a Markdown report.

## Install

From the repository root:

```bash
uv sync
```

Run the CLI through `uv`:

```bash
uv run opennavier --help
```

## Package Layout

The current CLI is split across three workspace packages:

- `apps/cli` contains the Typer command-line app.
- `packages/core` contains shared diagnostic result models.
- `packages/openfoam` contains OpenFOAM-specific validators.

The CLI entry point is:

```text
opennavier.cli.main:app
```

## Diagnostics Model

Every check returns a structured diagnostic with:

- `status`: `PASS`, `FAIL`, or `WARN`
- `code`: stable machine-readable diagnostic code
- `message`: human-readable explanation
- `path`: inspected file or directory path
- `details`: optional structured metadata

This keeps output deterministic and gives later report, JSON, and UI layers a
stable contract.

## Case Structure Checks

The first validator checks for the minimum OpenFOAM case structure:

```text
0/
constant/
system/
system/controlDict
system/fvSchemes
system/fvSolution
```

The validator only inspects paths. It does not create missing folders, write
dictionaries, run solvers, upload files, or modify the case.

## Commands

### `opennavier check <case_path>`

Runs case-structure validation and prints each diagnostic.

```bash
uv run opennavier check ./examples/cavity
```

Exit codes:

- `0` when all checks pass
- `1` when one or more checks fail

### `opennavier doctor <case_path>`

Runs the same deterministic checks as `check`, then adds a short likely-issues
summary for failed diagnostics.

```bash
uv run opennavier doctor ./examples/cavity
```

Exit codes:

- `0` when no blocking case-structure issue is found
- `1` when the case structure is incomplete

### `opennavier report <case_path> --output report.md`

Runs validation and writes a Markdown report.

```bash
uv run opennavier report ./examples/cavity --output report.md
```

The report includes:

- timestamp
- inspected case path
- passed and failed check counts
- all diagnostic results
- failed checks section
- assumptions
- reproducibility notes
- explicit note that no cloud upload occurred

Exit codes:

- `0` when the report is written and all checks pass
- `1` when the report is written but one or more checks fail

## Validation

Run the current test and lint suite:

```bash
uv run pytest
uv run ruff check .
uv run opennavier --help
```

The tests use small temporary case folders and do not require OpenFOAM.

## Current Scope

Implemented now:

- deterministic case-structure diagnostics
- CLI output for `check` and `doctor`
- Markdown report generation
- tests for valid and invalid case structures
- tests for CLI help, success, failure, doctor, and report behavior

Not implemented yet:

- OpenFOAM solver execution
- mesh quality parsing
- residual parsing
- boundary-condition validation
- case template generation
- AI planning or LLM-written dictionaries

Those features should be added after deterministic validators and tests define
their behavior.
