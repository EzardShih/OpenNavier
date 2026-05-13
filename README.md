# OpenNavier

OpenNavier is a local-first OpenFOAM automation and diagnostics CLI. The P1
slice connects the P0 contracts into a deterministic no-LLM workflow: validate
specs, plan from schema-backed `CaseBuildSpec` data, write supported cases,
run checks or explicit solver commands, collect diagnostics, and write report
artifacts. The legacy cavity starter remains available as a reference workflow,
and P1 adds a second duct pressure-drop build-spec path.

Your geometry, mesh, logs, and results stay on your machine by default. The CLI
does not upload case data to a cloud service.

## Development

Install dependencies with `uv`:

```bash
uv sync
```

Run validation:

```bash
uv run pytest
uv run ruff check .
uv run opennavier --help
```

The `apps/studio` directory is a Tauri + React scaffold. Install its Node
dependencies before running frontend checks:

```powershell
cd apps/studio
npm.cmd install
npm.cmd run check
```

The Studio `check` gate runs TypeScript, ESLint, and Prettier:

```powershell
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run format:check
```

GitHub Actions runs both the Python gate and the Studio gate on pushes and pull
requests. To run the same guardrails locally before pushing, install
`pre-commit` and enable both hook types:

```bash
pre-commit install
pre-commit install --hook-type pre-push
```

If `uv` cannot initialize its default cache directory on Windows or in a
sandboxed environment, use a workspace-local cache:

```powershell
$env:UV_CACHE_DIR='.tmp\uv-cache'; uv run pytest
$env:UV_CACHE_DIR='.tmp\uv-cache'; uv run ruff check .
$env:UV_CACHE_DIR='.tmp\uv-cache'; uv run opennavier --help
```

## MCP server

OpenNavier also exposes a local MCP stdio server for IDE agents:

```bash
uv run opennavier-mcp
```

The first MCP tool surface is deterministic and file-oriented:

- `workspace_inspect`
- `spec_validate`
- `case_build_validate`
- `case_build_dry_run`
- `case_build_write`
- `case_validate_structure`
- `diagnostics_residuals`
- `diagnostics_mesh_quality`
- `diagnostics_case`
- `diagnostics_artifact`
- `report_generate`

Tools operate inside an explicit workspace root and use the same validated core
and OpenFOAM package APIs as the CLI.

## CLI

Create a reference lid-driven cavity case with the legacy starter command:

```bash
opennavier init cavity ./runs/cavity-001
```

Validate a case structure:

```bash
opennavier check ./examples/cavity
```

Run the same deterministic checks with troubleshooting-oriented output:

```bash
opennavier doctor ./examples/cavity
```

Write durable diagnostics JSON from `doctor`:

```bash
opennavier doctor ./examples/cavity --diagnostics-output diagnostics.json
```

Run an explicit local solver command and write an auditable solver log:

```bash
opennavier run ./examples/cavity --solver icoFoam
```

Run through Docker only when explicitly selected:

```bash
opennavier run ./examples/cavity --runner docker --docker-image openfoam/openfoam-run:latest --solver icoFoam
```

Generate a Markdown report:

```bash
opennavier report ./examples/cavity --output report.md
```

Generate the report with a reproducibility manifest:

```bash
opennavier report ./examples/cavity --output report.md --manifest-output manifest.json
```

Generate the report with a diagnostics artifact:

```bash
opennavier report ./examples/cavity --output report.md --diagnostics-output diagnostics.json
```

The first validator checks for required OpenFOAM case paths:

- `0`
- `constant`
- `system`
- `system/controlDict`
- `system/fvSchemes`
- `system/fvSolution`

For existing required system dictionaries, it also checks for a minimal
`FoamFile` header. It reports missing paths and malformed dictionaries without
modifying the case.

`doctor` also validates cavity-style boundary conditions when the relevant
dictionaries are present. `doctor` and `report` parse recognized optional
`checkMesh` and solver logs when they are present, without requiring OpenFOAM to
be installed.

## P1 package contracts

P1 adds package-level contracts that future CLI, MCP, and Studio surfaces can
call without invoking an LLM:

- `opennavier_core.workflow.run_no_llm_workflow` runs the deterministic
  inspect, validate, plan, initialize, check, optional solver, diagnose, report,
  manifest, and summary sequence through an explicit operations adapter such as
  `opennavier.openfoam.workflow_operations.openfoam_workflow_operations`.
- `opennavier_core.questions` and `opennavier_core.clarification_loop` return
  structured missing-input questions and stop at ready-to-plan,
  complete-but-not-executable, max-turn, declined-info, or cancellation states.
- `opennavier.openfoam.solver_compatibility.check_solver_compatibility` keeps
  solver-family, `controlDict`, required-field, and algorithm checks separate
  from basic case-structure validation.
- `opennavier_core.model_runner` defines provider-neutral Claude, Codex, and
  Gemini CLI adapter contracts, but model output still has to parse into typed
  response models and cannot directly mutate files or include raw OpenFOAM
  dictionaries.

The core package also includes local-only simulation plan and planner contracts
that map a validated `SimulationSpec` plus validated `CaseBuildSpec` to
deterministic case-build operations, commands, approval checkpoints, expected
artifacts, diagnostics, and reports. Missing or ambiguous simulation intake is
left for the clarification loop; the planner reports complete-but-not-executable
capabilities without creating partial plans.

## User documentation

User-facing documentation lives in `docs/user/`. It is written as plain
Markdown so it can be published first through GitBook or GitHub Pages and later
moved into an Astro documentation site.

Start with:

- `docs/user/index.md`
- `docs/user/quick-start.md`
- `docs/user/SUMMARY.md` for GitBook-style navigation
