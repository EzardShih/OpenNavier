---
title: Troubleshooting
permalink: /troubleshooting/
---

# Troubleshooting

## `uv` Cannot Use Its Cache Directory

Use a workspace-local cache:

```powershell
$env:UV_CACHE_DIR='.tmp\uv-cache'; uv run opennavier --help
```

The same pattern works for tests and lint checks:

```powershell
$env:UV_CACHE_DIR='.tmp\uv-cache'; uv run pytest
$env:UV_CACHE_DIR='.tmp\uv-cache'; uv run ruff check .
```

## `check` Or `doctor` Reports Missing Case Paths

OpenNavier expects the basic OpenFOAM case structure:

```text
0/
constant/
system/
system/controlDict
system/fvSchemes
system/fvSolution
```

Add the missing files or start from a supported example case.

## Dictionary Header Warnings Or Failures

Required system dictionaries should contain a minimal `FoamFile` header. If a
file exists but does not look like an OpenFOAM dictionary, OpenNavier reports it
without modifying the file.

## `run` Reports A Missing Executable

Confirm the selected solver is available on your `PATH`:

```bash
uv run opennavier run ./examples/cavity --solver icoFoam
```

If you want to run through Docker, select Docker explicitly and provide an
image:

```bash
uv run opennavier run ./examples/cavity --runner docker --docker-image openfoam/openfoam-run:latest --solver icoFoam
```

## Report, Manifest, Or Diagnostics Paths Are Rejected

Artifact output paths must be distinct. This is rejected:

```bash
uv run opennavier report ./examples/cavity --output report.md --manifest-output report.md
```

Use separate paths:

```bash
uv run opennavier report ./examples/cavity --output report.md --manifest-output manifest.json
```

## Optional Log Diagnostics Do Not Appear

Mesh-quality and residual diagnostics appear only when recognized OpenFOAM logs
are present. `doctor` and `report` do not require those logs, and they do not
run OpenFOAM automatically.
