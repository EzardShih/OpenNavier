---
title: CLI Reference
permalink: /cli/
---

# CLI Reference

Run commands from the repository root with `uv run`.

## Help

```bash
uv run opennavier --help
```

## `init cavity`

Create a minimal lid-driven cavity reference case:

```bash
uv run opennavier init cavity ./runs/cavity-001
```

Use `--force` only when you intentionally want to replace a previously generated
case or an empty target directory:

```bash
uv run opennavier init cavity ./runs/cavity-001 --force
```

Protected paths such as the repository root, current working directory, drive
root, and home directory are refused.

## `check`

Validate the required OpenFOAM case structure:

```bash
uv run opennavier check ./examples/cavity
```

Print structured JSON:

```bash
uv run opennavier check ./examples/cavity --format json
```

Exit codes:

- `0`: all checks pass
- `1`: one or more checks fail

## `doctor`

Run deterministic diagnostics:

```bash
uv run opennavier doctor ./examples/cavity
```

Print structured JSON:

```bash
uv run opennavier doctor ./examples/cavity --format json
```

Write a diagnostics artifact:

```bash
uv run opennavier doctor ./examples/cavity --diagnostics-output diagnostics.json
```

`doctor` includes case structure, cavity-style boundary validation when relevant
files are present, and optional mesh-quality or residual diagnostics when
recognized logs exist.

## `run`

Run an explicit local solver command:

```bash
uv run opennavier run ./examples/cavity --solver icoFoam
```

Pass solver arguments:

```bash
uv run opennavier run ./examples/cavity --solver simpleFoam --solver-arg -postProcess
```

Write run artifacts to an explicit directory:

```bash
uv run opennavier run ./examples/cavity --solver icoFoam --run-directory ./runs/cavity-001
```

Use Docker explicitly:

```bash
uv run opennavier run ./examples/cavity --runner docker --docker-image openfoam/openfoam-run:latest --solver icoFoam
```

The command prints:

- runner backend
- command
- return code
- log path

Exit codes:

- `0`: solver command completed successfully
- `1`: executable was missing or the solver returned a nonzero code

## `report`

Write a Markdown report:

```bash
uv run opennavier report ./examples/cavity --output report.md
```

Write a reproducibility manifest:

```bash
uv run opennavier report ./examples/cavity --output report.md --manifest-output manifest.json
```

Write diagnostics JSON at the same time:

```bash
uv run opennavier report ./examples/cavity --output report.md --diagnostics-output diagnostics.json
```

Artifact paths must be distinct. For example, `--output report.md` and
`--manifest-output report.md` is rejected.
