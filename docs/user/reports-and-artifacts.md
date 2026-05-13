---
title: Reports And Artifacts
permalink: /reports-and-artifacts/
---

# Reports And Artifacts

OpenNavier produces local files that make a simulation workflow easier to audit.

## Diagnostics JSON

Diagnostics JSON is a durable machine-readable artifact. It contains stable
diagnostic records and status counts. Create one with:

```bash
uv run opennavier doctor ./examples/cavity --diagnostics-output diagnostics.json
```

or:

```bash
uv run opennavier report ./examples/cavity --output report.md --diagnostics-output diagnostics.json
```

Use this file when another tool, IDE agent, or future UI needs to inspect case
health without parsing terminal text.

## Markdown Report

Create a Markdown report with:

```bash
uv run opennavier report ./examples/cavity --output report.md
```

The report includes:

- generation timestamp
- inspected case path
- diagnostic summary
- failed checks
- visual asset references when supplied by a local integration
- assumptions
- reproducibility notes
- local-only/no-cloud notice
- optional mesh-quality and residual diagnostics when logs are present

## Visual Assets

Reports have a Visual Assets section. By default, the CLI does not run ParaView
or generate screenshots, so reports say that no visual assets were provided.

Package-level ParaView helpers can prepare deterministic screenshot artifact
paths, a pvpython script, and a ParaView log path for a local integration. Real
ParaView execution is still treated as integration-only and must be triggered
explicitly by that integration. Generated helper scripts may create a temporary
`.foam` reader marker while ParaView runs, then remove it afterward if the
marker did not already exist.

## Reproducibility Manifest

Create a manifest with:

```bash
uv run opennavier report ./examples/cavity --output report.md --manifest-output manifest.json
```

The manifest records:

- schema version
- generated timestamp
- resolved case path
- diagnostic counts
- diagnostic codes
- generated artifact references
- local-only flags

## Solver Logs

`opennavier run` writes an auditable solver log under the allowed case or run
directory:

```bash
uv run opennavier run ./examples/cavity --solver icoFoam
```

The printed `Log path` tells you where the command output was recorded.

## Path Safety

OpenNavier is intentionally strict about artifact paths. Runner logs must stay
inside the case path or an explicit run directory. Report, manifest, and
diagnostics output paths must be distinct.
