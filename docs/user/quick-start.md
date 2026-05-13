---
title: Quick Start
permalink: /quick-start/
---

# Quick Start

This guide assumes you are running OpenNavier from the repository checkout.

## 1. Install Dependencies

Install Python dependencies with `uv`:

```bash
uv sync
```

Check that the CLI is available:

```bash
uv run opennavier --help
```

On Windows or sandboxed environments, if the default `uv` cache cannot be used,
run commands with a workspace-local cache:

```powershell
$env:UV_CACHE_DIR='.tmp\uv-cache'; uv run opennavier --help
```

## 2. Inspect An Example Case

Validate the committed cavity example:

```bash
uv run opennavier check ./examples/cavity
```

Run the broader diagnostic command:

```bash
uv run opennavier doctor ./examples/cavity
```

`doctor` reports blocking case-structure issues and also reads recognized
optional OpenFOAM logs when they are present.

## 3. Create A Starter Case

Create a local lid-driven cavity case:

```bash
uv run opennavier init cavity ./runs/cavity-001
```

The command refuses to overwrite existing non-empty directories unless you pass
`--force`.

## 4. Run A Solver Command

Run an explicit local solver command:

```bash
uv run opennavier run ./examples/cavity --solver icoFoam
```

OpenNavier prints the selected runner, command, return code, and solver log
path. It does not choose or invent solver commands silently.

Use Docker only when you explicitly select it:

```bash
uv run opennavier run ./examples/cavity --runner docker --docker-image openfoam/openfoam-run:latest --solver icoFoam
```

## 5. Generate Evidence Artifacts

Write a Markdown report:

```bash
uv run opennavier report ./examples/cavity --output report.md
```

Write a report plus reproducibility manifest:

```bash
uv run opennavier report ./examples/cavity --output report.md --manifest-output manifest.json
```

Write diagnostics JSON from `doctor`:

```bash
uv run opennavier doctor ./examples/cavity --diagnostics-output diagnostics.json
```
