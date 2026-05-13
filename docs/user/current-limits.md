---
title: Current Limits
permalink: /current-limits/
---

# Current Limits

OpenNavier is under active development. The current version is useful for local
deterministic OpenFOAM automation, but several larger product goals are not yet
available as end-user workflows.

## Available Today

- CLI-based case checks, diagnostics, reports, and explicit solver runs.
- Legacy `init cavity` reference case generation.
- Schema-backed build-spec validation and deterministic case-build tool
  contracts.
- A second duct pressure-drop example path in the repository.
- Local MCP tools for IDE agents.
- Early Tauri + React Studio scaffold.
- Package-level report visual asset hooks and ParaView script helpers for local
  integrations.

## Not Yet Available As A User Workflow

- A packaged desktop Studio app.
- A full chat-driven simulation workflow.
- Natural-language request parsing through a model.
- LLM-generated `CaseBuildSpec` intake.
- Automatic fix-and-rerun loops.
- CLI or Studio-driven ParaView screenshot execution.
- Parametric design optimization.
- Three.js CAD/topology editing.
- Simulation result overlays in the desktop UI.
- PDF reports.

## OpenFOAM Dependency Expectations

Most tests and diagnostics do not require OpenFOAM to be installed. Running a
real solver command with `opennavier run` requires the selected solver
executable to be available locally or through the explicitly selected Docker
image.

## Engineering Trust Boundary

OpenNavier is meant to assist engineering work, not hide it. Solver commands,
generated artifacts, diagnostics, and reports are kept visible. Future model
features must still pass through typed schemas, deterministic validation, and
approval checkpoints.
