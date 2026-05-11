# OpenNavier MCP Simulation Canvas

This document defines the concrete implementation track for making OpenNavier a
"Pencil for simulation": a repo-native, MCP-accessible engineering canvas where
agents can create, inspect, validate, run, diagnose, and report simulation
workflows without hiding the generated artifacts from engineers.

The goal is not to turn OpenNavier into a cloud CAE platform or an opaque
solver-writing agent. The goal is to expose the deterministic OpenNavier
automation layer through a local MCP server so IDE agents can operate on
simulation state safely and engineers can inspect every file.

## Design Inputs

OpenNavier should borrow the useful workflow shape from Pencil without copying
its product domain. Pencil uses repo-native `.pen` files for design, exposes
MCP read/write tools to agents, supports a headless CLI, provides an interactive
tool shell, and can export visual outputs such as PNG/JPEG/WEBP/PDF files:

- Pencil product site: <https://pencil.dev/>
- Pencil `.pen` files: <https://docs.pencil.dev/core-concepts/pen-files>
- Pencil AI and MCP integration: <https://docs.pencil.dev/getting-started/ai-integration>
- Pencil CLI: <https://docs.pencil.dev/for-developers/pencil-cli>

OpenNavier should also use the public OpenFOAM MCP server below as a reference
for useful CFD-oriented tool categories. Its README describes a C++20,
OpenFOAM 12-oriented MCP server with tools for CFD assistance, OpenFOAM
execution, mesh quality, STL geometry analysis, turbulence analysis, and
educational guidance. OpenNavier should borrow the categories while keeping a
narrower local-first and test-driven scope:

- Reference OpenFOAM MCP server: <https://github.com/EzardShih/simulation-mcp-server/tree/main>

## Product Framing

"Pencil for simulation" means:

1. Simulation state lives in the repository.
2. Agents manipulate that state through deterministic MCP tools.
3. Every mutation is schema-validated before files are written.
4. Every generated artifact remains visible, editable, diffable, and reviewable.
5. Engineers can run the same workflow without AI through the CLI/packages.

The canvas is not necessarily a visual desktop surface in v0. It is a
structured workspace that an MCP client can inspect and modify. The later Studio
UI can render the same workspace visually, but the source of truth remains the
repo files.

## Core Workspace File

Each simulation workspace should have one manifest file:

```text
simulation.onv.json
```

This is analogous to Pencil's repo-native `.pen` files, but OpenNavier should
not pack every solver artifact into one document. `simulation.onv.json` is a
small index and provenance manifest for a file tree containing specs, geometry,
case dictionaries, logs, diagnostics, reports, and visual outputs.

Example workspace layout:

```text
simulation.onv.json
specs/
  simulation.json
geometry/
  source.step
  generated.geo
case/
  0/
  constant/
  system/
logs/
  blockMesh.log
  checkMesh.log
  simpleFoam.log
diagnostics/
  diagnostics.json
reports/
  report.md
exports/
  pressure-drop.png
```

Example manifest shape:

```json
{
  "schema_version": "0.1",
  "workspace_id": "duct-pressure-drop",
  "created_by": "opennavier",
  "simulation": {
    "name": "duct-pressure-drop",
    "case_type": "internal_duct",
    "solver_family": "incompressible_laminar"
  },
  "spec": {
    "path": "specs/simulation.json",
    "model": "SimulationSpec",
    "status": "valid"
  },
  "artifacts": [
    {
      "kind": "openfoam_case",
      "path": "case",
      "producer": "case_build_write",
      "inputs": ["specs/simulation.json", "specs/case-build.json"]
    },
    {
      "kind": "diagnostics",
      "path": "diagnostics/diagnostics.json",
      "producer": "diagnostics_run_all",
      "inputs": ["case", "logs/checkMesh.log", "logs/simpleFoam.log"]
    }
  ],
  "runs": [
    {
      "id": "run-001",
      "commands": ["blockMesh", "checkMesh", "simpleFoam"],
      "status": "completed",
      "logs": ["logs/blockMesh.log", "logs/checkMesh.log", "logs/simpleFoam.log"]
    }
  ]
}
```

Manifest rules:

- Paths are relative to the workspace directory.
- The manifest records artifact relationships and provenance; it does not hide
  generated OpenFOAM dictionaries or logs.
- Schema validation rejects unknown fields unless a versioned migration accepts
  them.
- All mutating tools update provenance in the manifest.
- Runtime outputs stay under ignored `runs/`, `logs/`, `diagnostics/`,
  `reports/`, or `exports/` locations, not under source packages.

## MCP Architecture

The MCP server should be a thin local tool surface over the deterministic
OpenNavier implementation layer.

```text
IDE agent
  |
  | MCP over stdio
  v
OpenNavier MCP server
  |
  v
OpenNavier CLI/services
  |
  +-- packages/core
  +-- packages/openfoam
  +-- packages/gmsh
  +-- packages/freecad
  +-- packages/paraview later
```

Implementation rules:

- Use stdio transport first so Claude Code, Codex, Cursor, and similar IDE
  agents can launch the server locally.
- Keep `packages/core`, `packages/openfoam`, `packages/gmsh`, and
  `packages/freecad` as the deterministic implementation layer.
- Put MCP-specific wiring in a separate package, for example `packages/mcp`.
- Do not let the MCP server bypass validators or write OpenFOAM dictionaries
  directly from LLM text.
- Every mutating tool returns `changed_paths`, `diagnostics`, `provenance`, and
  a short list of deterministic next actions.

## Tool Groups

The exact Python function names can evolve, but the MCP contract should be
organized around these stable tool groups.

### Workspace and Canvas Tools

These tools manage the repo-native workspace and its manifest.

| Tool | Mutates | Purpose |
| --- | --- | --- |
| `workspace_inspect` | No | Read `simulation.onv.json`, list known specs, cases, logs, diagnostics, reports, and exports. |
| `workspace_create_simulation` | Yes | Create a new workspace manifest and starter folder layout from validated inputs. |
| `workspace_list_artifacts` | No | Return artifact paths, types, producers, and stale/missing status. |
| `workspace_snapshot` | Yes | Write a timestamped manifest snapshot for review before or after a run. |

### Spec Tools

These tools work with validated `SimulationSpec` data.

| Tool | Mutates | Purpose |
| --- | --- | --- |
| `spec_read` | No | Read the current simulation spec and return the typed model. |
| `spec_write` | Yes | Write a spec only after Pydantic validation succeeds. |
| `spec_validate` | No | Validate schema, required fields, and supported enum values. |
| `spec_explain_assumptions` | No | Explain defaults and assumptions encoded in the spec. |
| `spec_validate_physical_bounds` | No | Check deterministic dimensional and physical sanity rules. |

### Case Tools

These tools validate, dry-run, write, and inspect OpenFOAM case files through
schema-backed `CaseBuildSpec` data and deterministic writer operations.

| Tool | Mutates | Purpose |
| --- | --- | --- |
| `case_build_validate` | No | Validate a user- or model-proposed `CaseBuildSpec` without writing files. |
| `case_build_dry_run` | No | Return planned writer operations, validators, expected artifacts, and approval points. |
| `case_build_write` | Yes | Write case files only through validated writer operations and path guards. |
| `case_inspect_dictionaries` | No | Read OpenFOAM dictionary summaries without modifying the case. |
| `case_validate_structure` | No | Run required directory and dictionary-header checks. |
| `case_validate_boundary_conditions` | No | Compare mesh patches with `0/U` and `0/p` boundary fields. |

### Execution Tools

These tools run local commands and collect logs. They should use an allow list
of known OpenFOAM executables and write logs under the workspace.

| Tool | Mutates | Purpose |
| --- | --- | --- |
| `execution_run_block_mesh` | Yes | Run `blockMesh` locally and capture stdout/stderr to a log. |
| `execution_run_check_mesh` | Yes | Run `checkMesh` locally and capture mesh diagnostics. |
| `execution_run_solver` | Yes | Run a supported solver command from the validated case metadata. |
| `execution_collect_logs` | Yes | Normalize discovered logs into the workspace manifest. |

### Diagnostics Tools

These tools convert case files and logs into structured diagnostic results.

| Tool | Mutates | Purpose |
| --- | --- | --- |
| `diagnostics_mesh_quality` | No | Parse `checkMesh` output and emit mesh quality warnings/failures. |
| `diagnostics_residuals` | No | Parse solver residuals and convergence signals. |
| `diagnostics_boundary_conditions` | No | Report boundary-condition mismatches and unsupported patch states. |
| `diagnostics_solver_compatibility` | No | Check that solver, physics, fields, and dictionaries are compatible. |
| `diagnostics_explain_failure` | No | Explain deterministic diagnostics in engineering language. |
| `diagnostics_run_all` | Yes | Write `diagnostics/diagnostics.json` and update the manifest. |

### Report and Export Tools

These tools turn validated state into reviewable outputs.

| Tool | Mutates | Purpose |
| --- | --- | --- |
| `report_generate_markdown` | Yes | Generate a deterministic Markdown report. |
| `report_generate_manifest` | Yes | Generate or refresh reproducibility metadata. |
| `report_list_outputs` | No | List reports, manifests, plots, and screenshots. |
| `report_export_visuals` | Yes | Later: call ParaView/pvpython to produce plots and screenshots. |

## Safety Model

OpenNavier MCP tools must preserve the same trust boundary as the CLI.

- No cloud upload by default.
- No free-form LLM writes to OpenFOAM dictionaries.
- No mutation outside the declared workspace root.
- No solver command outside an explicit allow list.
- No hidden generated files; every artifact path is returned to the client.
- All specs and manifests are schema-validated before writing.
- All generated artifacts record producer, inputs, command, timestamp, and
  OpenNavier version when available.
- Read-only tools must not create missing folders or normalize files as a side
  effect.
- Destructive overwrite behavior requires an explicit `force` or replacement
  option and must preserve the same path guards as the CLI.

The agent can propose changes, but OpenNavier decides whether those changes are
valid engineering state.

## v0 Implementation Path

Build the MCP server in Python first. The current product is file-oriented and
subprocess-oriented, so a Python MCP package can reuse the existing validated
packages without linking against OpenFOAM internals.

Recommended sequence:

1. Add `packages/mcp` with a stdio server and no solver execution.
2. Add tests for loading, validating, and saving `simulation.onv.json`.
3. Expose read-only workspace tools first.
4. Expose `spec_read`, `spec_write`, and `spec_validate` using the existing
   `SimulationSpec` model.
5. Expose `case_build_validate`, `case_build_dry_run`, `case_build_write`,
   `case_validate_structure`, and `case_validate_boundary_conditions` through
   existing core/OpenFOAM package APIs.
6. Expose diagnostics tools for mesh quality and residual parsing.
7. Add local execution tools only after subprocess behavior and log paths are
   covered by focused tests.
8. Add report/export tools after manifest provenance is stable.

Avoid a C++ OpenFOAM-linked MCP server until direct solver API integration is
necessary. Shelling out to known OpenFOAM executables and parsing deterministic
files is easier to test, easier to install, and better aligned with the
local-first v0 scope.

## Contrast With the Reference MCP Server

The reference OpenFOAM MCP server is useful because it points to CFD-specific
tool categories that generic file tools miss: OpenFOAM execution, mesh/STL
analysis, turbulence guidance, and educational explanations.

OpenNavier should borrow those categories, but keep different constraints:

| Concern | Reference direction to borrow | OpenNavier constraint |
| --- | --- | --- |
| CFD assistance | Help users understand OpenFOAM concepts and failures. | Explanations must be grounded in deterministic diagnostics and visible files. |
| Execution | Provide tools that can run OpenFOAM commands. | Use local subprocess wrappers, allow-listed commands, and captured logs. |
| Mesh/STL analysis | Inspect geometry and mesh quality. | Start with parsed `checkMesh` evidence; add STL/Gmsh/FreeCAD analysis incrementally. |
| Turbulence guidance | Help choose and interpret models. | Keep v0 narrow; reject unsupported physics instead of inventing dictionaries. |
| Educational mode | Teach users why a setup fails. | Teach from validators, assumptions, and report evidence, not from hidden solver edits. |
| Implementation language | C++20/OpenFOAM-linked server can be valuable near solver internals. | Use Python first; move lower only when direct OpenFOAM APIs are required. |

## Non-Goals for This Contract

- Implementing the MCP server in this documentation pass.
- Replacing the CLI with MCP tools.
- Adding cloud compute or remote upload paths.
- Allowing LLMs to write arbitrary OpenFOAM dictionaries.
- Supporting arbitrary industrial CAD cleanup in v0.
- Hiding generated artifacts inside an opaque binary workspace.

## Example Agent Workflow

```text
User: Create a duct pressure-drop simulation for air at 10 m/s.

Agent:
1. Calls workspace_create_simulation.
2. Calls spec_write with a candidate SimulationSpec.
3. Calls spec_validate and spec_validate_physical_bounds.
4. Proposes a typed `CaseBuildSpec`, then calls case_build_validate,
   case_build_dry_run, and case_build_write when deterministic support exists.
5. Calls case_validate_structure and case_validate_boundary_conditions.
6. Calls execution_run_block_mesh, execution_run_check_mesh, and execution_run_solver.
7. Calls diagnostics_run_all.
8. Calls report_generate_markdown and report_generate_manifest.
9. Shows changed paths, diagnostics, and report path to the engineer.
```

Every step is reproducible through repo files and deterministic OpenNavier
commands. The MCP server is the agent-access layer; the engineering contract
remains the files, validators, runners, diagnostics, and reports.
