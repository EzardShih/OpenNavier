# OpenNavier CLI

The OpenNavier CLI is the first usable slice of the local-first OpenFOAM
automation workflow. It can create a deterministic starter cavity case, inspect
an existing case directory, report deterministic diagnostics, and write a
Markdown report. The OpenFOAM package also includes a tested local subprocess
runner API; a CLI command for solver execution is not wired yet.

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

For existing required system dictionaries, it also checks that the file contains
a minimal `FoamFile` header. Missing files are reported by the path check only,
without an additional dictionary-header diagnostic.

`doctor` also validates cavity-style boundary conditions when
`system/blockMeshDict`, `0/U`, and `0/p` are present. It compares patch names in
the mesh boundary section with the field `boundaryField` patches and reports
mismatches without modifying the case.

The validator only inspects paths and existing dictionary text. It does not
create missing folders, write dictionaries, run solvers, upload files, or modify
the case.

## Commands

### `opennavier init cavity <case_path>`

Creates a minimal OpenFOAM lid-driven cavity case.

```bash
uv run opennavier init cavity ./runs/cavity-001
```

By default, `init cavity` refuses to overwrite existing paths. Use `--force`
only to replace a previously generated cavity case or an empty target directory.
Protected paths such as the repository root, current working directory, drive
root, and home directory are refused.

### `opennavier check <case_path>`

Runs case-structure validation and prints each diagnostic.

```bash
uv run opennavier check ./examples/cavity
uv run opennavier check ./examples/cavity --format json
```

Exit codes:

- `0` when all checks pass
- `1` when one or more checks fail

### `opennavier doctor <case_path>`

Runs the same deterministic checks as `check`, then includes boundary-condition
validation and optional OpenFOAM log diagnostics when recognized logs are
present. It parses `checkMesh` logs for mesh-quality warnings and common solver
logs for residual warnings.

```bash
uv run opennavier doctor ./examples/cavity
uv run opennavier doctor ./examples/cavity --format json
```

Exit codes:

- `0` when no blocking case-structure issue is found
- `1` when the case structure is incomplete

For `check` and `doctor`, `--format json` prints the diagnostics as a JSON
array using the stable diagnostic fields: `status`, `code`, `message`, `path`,
and `details`. The default format remains human-readable text.

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
- optional mesh-quality and residual diagnostics when recognized logs are present

Use `--manifest-output` to also write a reproducibility manifest JSON file:

```bash
uv run opennavier report ./examples/cavity --output report.md --manifest-output manifest.json
```

The manifest includes:

- schema version and generation timestamp
- resolved case path
- diagnostic counts and diagnostic codes
- generated report artifact path
- deterministic flags showing no cloud upload occurred and OpenFOAM was not run

`--manifest-output` must point to a different path than `--output`.

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

If the default `uv` cache path cannot be initialized, point `UV_CACHE_DIR` at a
workspace-local directory:

```powershell
$env:UV_CACHE_DIR='.tmp\uv-cache'; uv run pytest
$env:UV_CACHE_DIR='.tmp\uv-cache'; uv run ruff check .
$env:UV_CACHE_DIR='.tmp\uv-cache'; uv run opennavier --help
```

The tests use small temporary case folders and do not require OpenFOAM.

## Current Scope

Implemented now:

- deterministic case-structure diagnostics
- deterministic `init cavity` case generation with overwrite guards
- JSON diagnostics output for `check` and `doctor`
- minimal `FoamFile` header checks for required system dictionaries
- cavity-style boundary-condition validation in `doctor`
- mesh quality parsing
- residual parsing
- optional `checkMesh` and solver log diagnostics in `doctor` and reports
- local subprocess runner API with deterministic fake-command tests
- CLI output for `check` and `doctor`
- Markdown report generation
- reproducibility manifest output for `report --manifest-output`
- committed `examples/cavity` case matching the deterministic template
- tests for valid and invalid case structures
- tests for CLI help, success, failure, doctor, and report behavior
- tests for JSON diagnostics output and exit codes
- tests for reproducibility manifest output
- tests for mesh quality and residual log parsing
- tests for cavity initialization, committed examples, runner behavior,
  boundary validation, and optional log diagnostics

Not implemented yet:

- CLI command for OpenFOAM solver execution
- Docker fallback execution
- AI planning or LLM-written dictionaries

Those features should be added after deterministic validators and tests define
their behavior.
