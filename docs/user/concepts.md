---
title: Core Concepts
permalink: /concepts/
---

# Core Concepts

## Case

A case is an OpenFOAM case directory. The minimum structure OpenNavier checks
today is:

```text
0/
constant/
system/
system/controlDict
system/fvSchemes
system/fvSolution
```

OpenNavier validates existing case files without modifying them during
diagnostic commands.

## Diagnostic

A diagnostic is a structured result with:

- `status`: `PASS`, `FAIL`, or `WARN`
- `code`: stable machine-readable identifier
- `message`: human-readable explanation
- `path`: inspected file or directory
- `details`: optional structured metadata

The same diagnostic shape is used by CLI output, JSON artifacts, reports, and
MCP tools.

## Report

A report is a Markdown summary of the inspected case. It includes diagnostic
counts, failed checks, assumptions, reproducibility notes, and a local-only
notice. If recognized `checkMesh` or solver logs are present, their diagnostics
can appear in the report.

## Manifest

A manifest is a JSON reproducibility record. It captures the inspected case path,
diagnostic counts, diagnostic codes, generated report artifact paths, and flags
that make local-only behavior explicit.

## CaseBuildSpec

A `CaseBuildSpec` is typed data that describes deterministic case-build
operations. It is the safe path for future generated OpenFOAM cases. OpenNavier
rejects raw unvalidated OpenFOAM dictionary blobs as a planning or generation
shortcut.

## SimulationSpec And Plan

A `SimulationSpec` captures validated simulation intent. A simulation plan maps
a supported spec plus a validated build spec into deterministic steps, expected
artifacts, commands, checks, risks, and approval points.

Today, these contracts are most useful to developers, MCP tools, and future
agent workflows. They are intentionally stricter than free-form text.
