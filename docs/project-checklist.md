# OpenNavier Project Checklist

This checklist tracks feature progress and matching test coverage. A feature is
only marked done when the behavior exists, has deterministic tests where
reasonable, and has current validation evidence.

## Product Direction

OpenNavier should become a local-first simulation AI agent that behaves like a
junior simulation engineer under review. Diagnostics, templates, runners, and
reports are not the product boundary; they are the toolbench the agent uses to
turn an engineering request into a verified local simulation workflow.

The final goal is an autonomous parametric design and simulation agent. A user
should be able to describe a design goal, constraints, and objective, then have
OpenNavier generate or modify topology, prepare CAD/mesh/simulation cases, run
local simulations, compare variants, and recommend the next design iteration
with visible engineering evidence.

The frontend should eventually package the CLI tool into an interactive
simulation workspace with a chat box. User messages in the chat box should be
wrapped into a structured local request and sent to the configured model
runner. The model runner layer should support Claude CLI, Codex CLI, and Gemini
CLI through explicit provider adapters, including a `claude -p` command bridge
when Claude CLI is selected and configurable command templates for Codex and
Gemini CLIs. The model response must still flow through typed specs, plans,
tool calls, diffs, and approval points instead of directly mutating CAD, mesh,
or OpenFOAM files.

The long-term CAD interaction goal is direct Three.js-based control of
parametric CAD and topology design in the frontend. Three.js should provide the
inspectable 3D design surface for sketching, constraints, topology operations,
variant comparison, and simulation result overlays, while durable geometry and
mesh artifacts remain exportable and reproducible through the backend adapters.

The agent should be able to:

1. Understand an engineering intent and ask for missing inputs when needed.
2. Convert the intent into a validated simulation specification.
3. Create a simulation plan with assumptions, solver choice, geometry/mesh
   approach, boundary conditions, run commands, expected outputs, and risk
   checks.
4. Generate or prepare the case through deterministic writers and adapters.
5. Run pre-flight validation, mesh commands, solver commands, and
   post-processing locally.
6. Watch logs and residuals, diagnose failures, propose bounded fixes, and
   rerun when the fix is deterministic and approved by policy.
7. Run parametric sweeps or design iterations against an explicit objective and
   compare variants using reproducible metrics.
8. Produce a report that explains inputs, assumptions, commands, checks,
   results, limitations, and next engineering recommendations.

The agent may use an LLM for intent extraction, planning, explanations, and
review-style reasoning. It must not hide solver behavior, upload user data by
default, or freely rewrite OpenFOAM dictionaries without schema validation,
deterministic generation, and inspectable diffs.

## Priority Context

The autonomous design-and-simulation agent is a compound goal, not a single
feature. Build it as infrastructure layers. Each lower layer must be useful and
testable without an LLM before a higher layer depends on it.

### Goal Breakdown

| Slice | Goal | Depends on | Description |
| --- | --- | --- | --- |
| 1 | Reliable local OpenFOAM automation | Existing package layout, examples, validators, runner API. | The user can initialize, check, run, diagnose, and report one supported case with visible commands and artifacts. |
| 2 | Agent-ready project memory | Session artifact, simulation plan artifact, diagnostics artifact, manifest references. | The system has a durable local record of intent, assumptions, commands, files, diagnostics, reports, and provenance. |
| 3 | Deterministic junior-engineer workflow | Planner, templates, validators, runner, diagnostics, reports, CLI/MCP contracts. | A no-LLM workflow can inspect a request, create a plan, prepare a case, run checks, and summarize evidence. |
| 4 | Optional model interface | Typed request/response models, provider adapters, schema validation, approval points. | Claude/Codex/Gemini CLI adapters can help draft specs, questions, plans, and explanations without bypassing deterministic tools. |
| 5 | Parametric design automation | Variant manifests, bounded parameters, metric extraction, comparison reports. | OpenNavier can generate controlled variants, compare reproducible metrics, and recommend the next bounded iteration. |
| 6 | Studio and 3D design workspace | Stable CLI/MCP runtime contracts, geometry operation schema, result artifact schema. | The frontend becomes an inspectable simulation workspace with chat, run status, reports, and later Three.js topology controls. |

### Priority Bands

| Priority | Meaning | Should exist before |
| --- | --- | --- |
| P0 | Foundational local contracts and safety controls. These define where the agent works, what it is allowed to write, and how simulations are represented. | Agent orchestration, model calls, frontend runtime workflows, and automatic reruns. |
| P1 | Deterministic engineering workflow infrastructure. These connect existing validators, templates, runners, diagnostics, and reports into repeatable commands and tools. | Natural-language planning, Studio chat workflows, and design optimization. |
| P2 | Model-assisted and interactive workflows. These add optional LLM intent parsing, model runner bridges, bounded fix proposals, and Studio runtime integration on top of deterministic contracts. | Autonomous parametric design loops and advanced 3D topology editing. |
| P3 | Advanced design workspace and optimization capabilities. These are valuable later, but they should not block the first useful local OpenFOAM automation product. | Full autonomous CAD/topology generation and result-overlay UX. |

### Infrastructure Build Order

| Order | Infrastructure layer | Build first | Build later | Context |
| --- | --- | --- | --- | --- |
| 1 | Local workspace and artifact contracts | Session artifact, manifest fields, diagnostics artifact, path safety, no-cloud defaults. | Project history, artifact migrations, team sharing, and branded reports. | The agent needs a durable local notebook before it can safely plan, run, or explain work. |
| 2 | Typed engineering contracts | `SimulationSpec`, simulation plan model, command records, expected artifacts, approval checkpoints. | Rich objective models, multi-physics specs, and optimization-specific schemas. | Model output and UI input must enter through typed contracts instead of direct file edits. |
| 3 | Deterministic OpenFOAM automation | Template initialization, case checks, explicit solver execution, log capture, overwrite guards. | Automatic solver selection, auto-remediation, parallel execution, and remote execution options. | This is the first product-grade path: create, check, run, diagnose, and report a known case locally. |
| 4 | Diagnostics and report artifacts | Structured diagnostic records, mesh and residual parsing, Markdown report, reproducibility manifest. | PDF export, ParaView screenshots, plots, and report quality scoring. | Every workflow needs inspectable evidence before it can claim engineering usefulness. |
| 5 | CLI and MCP tool contracts | Stable CLI commands and thin MCP tools over package APIs. | Studio runtime calls, agent tool routing, and external integrations. | The frontend and agent should consume the same deterministic contracts that tests already cover. |
| 6 | Agent orchestration | No-LLM inspect, validate, plan, initialize, run, diagnose, summarize workflow. | Model-guided planning, automatic fix proposals, and bounded rerun policies. | Prove the tool loop with deterministic inputs before adding reasoning variability. |
| 7 | Model runner bridge | Provider abstraction, command construction, mocked Claude/Codex/Gemini CLI adapters, schema validation of responses. | Streaming chat UX, provider-specific prompt tuning, and user-configurable model workflows. | A model can suggest specs, plans, and explanations, but it must not bypass validation or mutate solver files directly. |
| 8 | Parametric geometry and design loop | Pipe/duct/enclosure parameters, variant manifests, bounded sweep creation, metric extraction. | Three.js topology editing, arbitrary CAD cleanup, optimization loops, and simulation result overlays. | Design automation becomes credible only after the local simulation pipeline is reproducible. |

## Validation Status

Last checked: 2026-05-06

| Command | Status | Notes |
| --- | --- | --- |
| `.venv\Scripts\python.exe -m pytest` | Not rechecked | Superseded by workspace-local `uv run pytest` validation. |
| `.venv\Scripts\python.exe -m ruff check .` | Not rechecked | Superseded by workspace-local `uv run ruff check .` validation. |
| `uv run pytest` | Done | 149 tests passed on 2026-05-06. |
| `.venv\Scripts\uv.exe run pytest` | Not rechecked | Superseded by workspace-local `uv run pytest` validation. |
| `$env:UV_CACHE_DIR='.tmp\uv-cache'; uv run pytest` | Done | 149 tests passed. |
| `uv run ruff check .` | Not rechecked | Use a workspace-local cache in this environment. |
| `$env:UV_CACHE_DIR='.tmp\uv-cache'; uv run ruff check .` | Done | Ruff reported all checks passed. |
| `$env:UV_CACHE_DIR='.tmp\uv-cache'; uv lock --check` | Done | Lock file is current. |
| `uv run opennavier --help` | Done | CLI help rendered successfully on 2026-05-06. |
| `$env:UV_CACHE_DIR='.tmp\uv-cache'; uv run opennavier --help` | Done | CLI help rendered successfully. |

When direct `uv run ...` commands are blocked by the default cache path, use a
workspace-local cache:

```powershell
$env:UV_CACHE_DIR='.tmp\uv-cache'; uv run pytest
$env:UV_CACHE_DIR='.tmp\uv-cache'; uv run ruff check .
$env:UV_CACHE_DIR='.tmp\uv-cache'; uv run opennavier --help
```

## Near-Term Development Queue

This queue is ordered by dependency, not by excitement. Finish the P0 local
contracts before building model or frontend workflows that depend on them. Each
item should land with a failing test first, a focused green test run, and a full
available validation run.

The first complete slice should be: local session artifact, explicit simulation
plan, safe `run` command, diagnostics artifact, and report manifest. That slice
creates the minimum inspectable infrastructure for later agent and Studio work.

| Priority | Track | Target behavior | Acceptance signal | Dependency context |
| --- | --- | --- | --- | --- |
| P0 | Agent session model | Create a local simulation workspace/session artifact that stores intent, spec, plan, commands, diagnostics, reports, artifacts, and provenance. | Tests cover schema validation, path safety, manifest loading, artifact references, and no-cloud defaults. | Build this first because every future agent action needs one durable local audit trail. |
| P0 | Simulation plan artifact | Convert a validated `SimulationSpec` into an explicit plan with assumptions, required tools, commands, expected artifacts, pre-flight checks, and approval checkpoints. | Planner tests cover accepted cavity/duct specs, unsupported specs, missing inputs, approval points, and stable JSON output. | The plan is the bridge between engineering intent and deterministic tools. |
| P0 | Run safety | Run commands refuse unsafe or missing case paths and keep generated artifacts under the case or run directory. | Path-safety tests prove no writes occur outside the intended target. | Safety must precede any command runner, agent loop, or UI-triggered execution. |
| P0 | CLI run workflow | `opennavier run <case_path>` executes an explicit solver command through the existing runner API and writes a visible log. | CLI tests cover success, command-not-found failure, nonzero return codes, selected runner, and log output. | Start with explicit solver commands; defer solver auto-selection until planner rules exist. |
| P0 | Diagnostics artifacts | `doctor` or `report` can write `diagnostics.json` with stable diagnostic records. | JSON artifact tests cover schema, counts, diagnostic codes, paths, and no-cloud flags. | This gives CLI, MCP, Studio, and reports one shared evidence contract. |
| P0 | Deterministic planner baseline | Map supported specs to known templates, validation steps, run commands, expected logs, and report outputs without using a model. | Tests cover cavity and first duct/pipe planning, unsupported physics, and deterministic ordering. | Build the planner before `ask`; the model should request a plan, not invent one. |
| P1 | Agent tool loop | Add an agent-facing workflow that can inspect a workspace, validate a spec, create a plan, initialize a case, run checks, and summarize next actions. | MCP or CLI tests cover tool ordering, failure handling, skipped steps, and stable summaries without requiring an LLM. | This proves the junior-engineer workflow with deterministic inputs before model calls are introduced. |
| P1 | Clarifying questions | Detect missing or ambiguous simulation inputs and return concrete questions instead of guessing. | Tests cover missing geometry, fluid properties, boundary conditions, objective, units, and unsupported case classes. | This belongs before natural-language execution because the agent should ask before creating a misleading case. |
| P1 | Pipe and duct templates | Add deterministic `init pipe-flow` or `init duct-pressure-drop` templates. | Template tests compare generated files, overwrite guards, validation results, and committed examples. | These expand the useful case library after the session, planner, and run contracts are stable. |
| P1 | Solver compatibility checks | Validate that selected solver family, dictionaries, fields, and template assumptions agree for supported templates. | Unit tests cover valid cavity/duct cases and known incompatible solver/dictionary combinations. | Keep this deterministic and separate from LLM planning. |
| P1 | MCP diagnostics expansion | Expose mesh-quality, full case diagnostics, report generation, and diagnostics artifact tools through MCP. | MCP tests prove workspace scoping, output shape, path safety, and parity with package APIs. | MCP should stay thin over core/OpenFOAM APIs and should not create a second behavior path. |
| P1 | Model runner adapter contract | Add provider-neutral request/response models and mocked subprocess adapters for Claude CLI, Codex CLI, and Gemini CLI. | Tests cover provider selection, command construction, missing CLI handling, response parsing, and no direct file mutation from model text. | Define the model boundary before wiring chat UI; all model output must pass through typed contracts. |
| P2 | LLM intent interface | Add `opennavier ask` or equivalent MCP flow that turns natural language into a draft spec, clarifying questions, or a plan. | Tests use mocked model responses and verify schema validation, rejection handling, provenance, and no direct dictionary writes. | LLM output must enter through `SimulationSpec`, question, or plan artifacts. |
| P2 | Frontend chat request bridge | Package chat-box messages into structured local requests that can be sent to the selected model runner. | Frontend/backend tests cover request payload shape, provider configuration, local-only defaults, failure states, and approval prompts. | The chat box should drive the agent workflow after CLI/MCP contracts exist, not bypass them. |
| P2 | Agent iteration policy | Allow bounded fix suggestions and rerun plans when diagnostics fail. | Tests cover fix proposals, required approval points, changed files, rerun limits, and stop conditions. | The first version can propose fixes before it automatically applies them. |
| P2 | ParaView report assets | Generate report-ready screenshots from an existing case using the ParaView adapter. | Adapter and report tests cover script generation, log paths, artifact naming, and optional screenshot inclusion. | Real ParaView execution should stay integration-marked. |
| P2 | Studio runtime workflow | Connect the Studio scaffold to local CLI/MCP diagnostics, run logs, and reports. | Frontend or scaffold tests cover visible commands, diagnostics states, report links, and local-only messaging. | Do not expand UI runtime before CLI/MCP contracts are stable. |
| P3 | Parametric design loop | Generate and compare bounded design variants from parameters, constraints, and objective metrics. | Tests cover variant manifests, parameter bounds, run queue creation, metric extraction, and ranking behavior. | Start with small deterministic sweeps before optimization or model-guided design. |
| P3 | Three.js topology workspace | Add a frontend 3D topology/CAD interaction surface backed by explicit geometry operations. | Frontend tests cover command serialization, selection state, topology operation payloads, undo/redo state, and export handoff to adapters. | Three.js controls the design surface later; backend artifacts remain the source of reproducibility. |

## Feature and Test Matrix

| Area | Feature or behavior | Feature status | Test status | Evidence | Next action |
| --- | --- | --- | --- | --- | --- |
| Repository | Python workspace with CLI, core, OpenFOAM, ParaView, and MCP packages | Done | Done | `pyproject.toml`; `$env:UV_CACHE_DIR='.tmp\uv-cache'; uv run pytest` | Keep package boundaries stable as features are added. |
| CLI | Typer application entrypoint | Done | Done | `tests/test_cli.py::test_help_shows_core_commands` | Add tests with each new command. |
| CLI | `opennavier check <case_path>` | Done | Done | `tests/test_cli.py::test_check_returns_success_for_valid_case`; `tests/test_cli.py::test_check_returns_failure_for_invalid_case` | Expand beyond case structure only after new validators are tested. |
| CLI | `opennavier doctor <case_path>` | Done | Done | `tests/test_cli.py::test_doctor_returns_nonzero_for_invalid_case`; `tests/test_doctor_logs.py` | Add more solver log patterns only after parser behavior is tested. |
| CLI | `opennavier report <case_path> --output <path>` | Done | Done | `tests/test_cli.py::test_report_writes_markdown_report`; `tests/test_manifest.py::test_report_manifest_output_writes_reproducibility_manifest_for_invalid_case` | Keep report and manifest artifact paths distinct. |
| Core diagnostics | Structured diagnostic result model with `PASS`, `FAIL`, and `WARN` | Done | Covered through consumers | `packages/core/src/opennavier_core/diagnostics.py`; CLI and validator tests | Add direct model tests if validation rules or serialization behavior expands. |
| Core diagnostics | Failure aggregation helper | Done | Covered through consumers | `opennavier_core.diagnostics.has_failures`; CLI exit-code tests | Keep exit-code tests as the public behavior contract. |
| OpenFOAM validation | Required case directory checks for `0`, `constant`, and `system` | Done | Done | `tests/test_case_structure.py` | Add more OpenFOAM checks as separate validators. |
| OpenFOAM validation | Required `system/controlDict`, `system/fvSchemes`, and `system/fvSolution` checks | Done | Done | `tests/test_case_structure.py` | Add dictionary-content validation separately. |
| OpenFOAM validation | Minimal `FoamFile` header checks for existing required system dictionaries | Done | Done | `tests/test_case_structure.py`; `tests/test_cli.py` | Add full dictionary parsing only when a concrete validation rule needs it. |
| OpenFOAM validation | Validation does not create or modify missing case paths | Done | Done | `tests/test_case_structure.py::test_missing_openfoam_case_paths_are_reported_without_creating_them` | Preserve read-only behavior for diagnostic commands. |
| Reporting | Deterministic Markdown report generation | Done | Done | `apps/cli/src/opennavier/cli/reporting.py`; report CLI test | Add golden-file or snapshot-style coverage if report formatting becomes more complex. |
| Documentation | README development, CLI, and MCP usage notes | Done | Not applicable | `README.md`; `docs/cli.md` | Update whenever setup, commands, or scope changes. |
| Documentation | Project-management checklist | Done | Not applicable | `docs/project-checklist.md` | Update after each feature lands or validation status changes. |
| Documentation | MCP simulation canvas design | Done | Not applicable | `docs/simulation-mcp-canvas.md` | Use as the implementation contract for the MCP package. |
| Examples | Reproducible `examples/cavity` case | Done | Done | `examples/cavity`; `tests/test_examples.py::test_committed_cavity_example_matches_template_and_validates_read_only` | Keep committed examples exact matches for deterministic templates and free of runtime artifacts. |
| CLI | `opennavier init cavity <case_path>` case creation | Done | Done | `tests/test_init.py` | Add more templates only after each command's generated file tree and overwrite behavior are tested. |
| CLI | `opennavier run <case_path>` solver execution command | Not Started | Not Started | Existing runner API only; no CLI command is wired yet. | Add CLI tests for explicit solver commands, log writing, failures, and Docker selection before implementation. |
| CLI | JSON output for diagnostics | Done | Done | `tests/test_cli.py::test_check_json_returns_diagnostics_for_valid_case`; `tests/test_cli.py::test_doctor_json_returns_diagnostics_without_text_summary` | Keep JSON schema stable when new diagnostics are added. |
| CLI | Diagnostics JSON artifact output | Not Started | Not Started | Current JSON diagnostics print to stdout only. | Add `diagnostics.json` artifact tests for `doctor` or `report` before adding the option. |
| Reporting | Reproducibility manifest output | Done | Done | `packages/core/src/opennavier_core/manifest.py`; `tests/test_manifest.py` | Keep manifest fields deterministic and update docs when the schema changes. |
| Reporting | PDF report export | Not Started | Not Started | Markdown reporting is implemented; no PDF writer exists. | Defer until Markdown structure and report assets stabilize. |
| Agent workspace | Simulation session or project artifact | Not Started | Not Started | Current MCP workspace inspection reads known folders and `simulation.onv.json`, but no full agent session contract exists. | Add a typed local artifact for intent, spec, plan, commands, diagnostics, artifacts, and provenance. |
| Agent planning | Simulation plan artifact | Not Started | Not Started | Specs validate intent, but no plan model captures assumptions, commands, expected outputs, or review checkpoints. | Add plan model tests before adding natural-language or autonomous execution flows. |
| Agent planning | Clarifying question generation | Not Started | Not Started | Invalid specs currently return validation errors only. | Add deterministic question generation for missing or ambiguous engineering inputs. |
| Agent execution | Tool loop for inspect-plan-create-check-run-report | Not Started | Not Started | Current tools exist separately; no orchestrated agent workflow exists. | Add a no-LLM orchestrator test that calls existing package APIs in a stable order. |
| Agent execution | Bounded fix-and-rerun workflow | Not Started | Not Started | Diagnostics report issues but do not create remediation plans. | Add failure-mode tests that produce fix proposals and require explicit approval before file changes or reruns. |
| Agent execution | Autonomous parametric design and simulation loop | Not Started | Not Started | No workflow generates variants, runs simulations, compares metrics, and recommends a next design. | Add deterministic sweep tests before adding model-guided optimization. |
| Agent review | Engineering explanation and recommendation layer | Not Started | Not Started | Reports list diagnostics, but do not yet provide junior-engineer-style interpretation and next simulation recommendations. | Start with deterministic explanations for known diagnostic codes, then allow LLM summarization over structured evidence. |
| OpenFOAM runner | Local solver execution | Done | Done | `packages/openfoam/src/opennavier/openfoam/runner.py`; `tests/test_runner.py` | Add CLI wiring or real OpenFOAM integration tests only after the subprocess wrapper API is consumed. |
| OpenFOAM runner | Docker fallback execution | Done | Done | `packages/openfoam/src/opennavier/openfoam/runner.py`; `tests/test_runner.py::test_run_docker_solver_mounts_case_sets_workdir_appends_solver_and_writes_log` | Wire into CLI only after runner-selection behavior is tested. |
| OpenFOAM runner | `checkMesh` command wrapper | Not Started | Not Started | Current implementation parses existing `checkMesh` logs only. | Add fake-command tests for execution, log writing, and parser handoff before real integration tests. |
| OpenFOAM diagnostics | Optional `checkMesh` and solver log diagnostics in `doctor` and reports | Done | Done | `tests/test_doctor_logs.py` | Keep optional logs non-blocking when absent and add new log locations through regression tests. |
| OpenFOAM parsing | Mesh quality parsing | Done | Done | `tests/test_mesh_quality.py`; `tests/test_doctor_logs.py::test_doctor_includes_mesh_warnings_from_check_mesh_log` | Expand thresholds only with deterministic fixtures. |
| OpenFOAM parsing | Residual parsing | Done | Done | `tests/test_residuals.py`; `tests/test_doctor_logs.py::test_doctor_includes_residual_warnings_from_solver_log` | Add solver variants only with captured-log fixtures. |
| OpenFOAM parsing | Residual trend and divergence diagnosis | Not Started | Not Started | Current residual diagnosis checks latest final residual threshold only. | Add captured-log fixtures for rising residuals, oscillation, missing fields, and false convergence. |
| OpenFOAM validation | Boundary-condition validation | Done | Done | `tests/test_boundary_conditions.py`; `.venv\Scripts\python.exe -m pytest tests/test_boundary_conditions.py` | Extend only with deterministic fixtures for additional generated case styles. |
| OpenFOAM validation | Solver compatibility validation | Not Started | Not Started | No solver-family-to-dictionary compatibility validator exists yet. | Add tests for supported solver/template pairs and known incompatible dictionaries. |
| OpenFOAM templates | Deterministic lid-driven cavity case template generation | Done | Done | `packages/openfoam/src/opennavier/openfoam/init_case.py`; `tests/test_init.py` | Add templates for pipe or duct cases only after generated dictionaries and overwrite guards are specified in tests. |
| OpenFOAM templates | Pipe-flow or duct-pressure-drop template generation | Not Started | Not Started | `docs/plan.md` identifies these as next supported cases. | Start with one template and add committed example coverage matching the generated tree. |
| Gmsh adapter | Mesh generation adapter | Done | Done | `packages/gmsh/src/opennavier/gmsh/adapter.py`; `tests/test_gmsh_adapter.py` | Add real Gmsh integration tests only when the executable is an explicit test dependency. |
| FreeCAD adapter | Parametric geometry scripting adapter | Done | Done | `packages/freecad/src/opennavier/freecad/adapter.py`; `tests/test_freecad_adapter.py` | Add real FreeCAD integration tests only when the executable is an explicit test dependency. |
| ParaView adapter | Batch post-processing and screenshots | Done | Done | `packages/paraview/src/opennavier/paraview/adapter.py`; `tests/test_paraview_adapter.py` | Add real ParaView integration tests only when the executable is an explicit test dependency. |
| ParaView reports | Report screenshot inclusion | Not Started | Not Started | ParaView adapter can create scripts, but reports do not consume screenshot artifacts. | Add report tests for optional screenshot references after artifact naming is specified. |
| Studio | Initial local desktop UI scaffold | Done | Done | `apps/studio`; `tests/test_studio_scaffold.py` | Expand from scaffold to runtime UI workflows after CLI usage validates the interaction model. |
| Studio | Runtime diagnostics and report workflow | Not Started | Not Started | Studio is currently a static scaffold inspected by Python tests. | Define a stable CLI or MCP contract before wiring frontend runtime behavior. |
| Studio | Chat box to model CLI request packaging | Not Started | Not Started | No frontend chat workflow or Claude/Codex/Gemini CLI bridge exists. | Add frontend/backend tests for request packaging, provider selection, command construction, model-runner configuration, and failure states. |
| Studio | Three.js CAD and topology design surface | Not Started | Not Started | Studio has no 3D viewport or topology operation model. | Add a Three.js workspace with serialized operations before connecting to FreeCAD/Gmsh/OpenFOAM generation. |
| Studio | Simulation result overlays in 3D view | Not Started | Not Started | ParaView screenshots exist only as adapter scripts; no frontend overlay workflow exists. | Define result artifact formats before adding contour, vector, or variant-comparison overlays. |
| MCP | MCP server package | Done | Done | `packages/mcp/pyproject.toml`; `packages/mcp/src/opennavier/mcp/server.py`; `tests/test_mcp_server.py` | Keep the MCP layer thin over deterministic package APIs. |
| MCP | MCP workspace inspection tool | Done | Done | `packages/mcp/src/opennavier/mcp/workspace_tools.py`; `tests/test_mcp_workspace_inspect.py` | Add manifest mutations only after behavior is specified with tests. |
| MCP | MCP workspace path safety | Done | Done | `packages/mcp/src/opennavier/mcp/paths.py`; `tests/test_mcp_paths.py` | Keep every tool scoped to explicit workspace roots. |
| MCP | MCP spec validation tool | Done | Done | `packages/mcp/src/opennavier/mcp/spec_tools.py`; `tests/test_mcp_spec_validate.py` | Add spec read/write and physical-bounds tools only after tests. |
| MCP | MCP cavity case initialization and structure validation tools | Done | Done | `packages/mcp/src/opennavier/mcp/case_init_tools.py`; `packages/mcp/src/opennavier/mcp/case_validation_tools.py`; `tests/test_mcp_case_init_cavity.py`; `tests/test_mcp_case_validate_structure.py` | Add duct and pipe init tools only after templates are specified. |
| MCP | MCP residual diagnostics tool | Done | Done | `packages/mcp/src/opennavier/mcp/diagnostics_tools.py`; `tests/test_mcp_diagnostics_residuals.py` | Expose mesh-quality and run-all diagnostics through tests before adding solver execution tools. |
| MCP | MCP full case diagnostics and report tools | Not Started | Not Started | Current MCP diagnostics surface only residual parsing directly. | Add tools after package-level diagnostics artifact behavior is stable. |
| AI planning | Pydantic simulation specs from LLM output | Done | Done | `packages/core/src/opennavier_core/simulation_spec.py`; `tests/test_simulation_specs.py` | Keep specs as validated intent and add deterministic planner wiring only after external behavior is tested. |
| AI planning | Deterministic spec-to-template planner | Not Started | Not Started | Specs validate intent, but no planner maps them to templates or commands. | Add planner tests before adding `ask` or natural-language workflows. |
| AI planning | Natural-language intent parser | Not Started | Not Started | No model-backed or mocked LLM intent parsing exists. | Add mocked-provider tests that transform user requests into draft specs or clarifying questions. |
| AI planning | Junior simulation engineer agent | Not Started | Not Started | No end-to-end agent can plan, execute tools, inspect results, and recommend next actions. | Build this incrementally from the session artifact, planner, tool loop, and review layer. |
| AI planning | Model runner bridges for Claude, Codex, and Gemini CLIs | Not Started | Not Started | No model CLI provider abstraction exists yet. | Add provider adapters with mocked subprocess tests before invoking real model commands; keep command templates configurable and auditable. |
| AI planning | LLM-written OpenFOAM dictionaries | Out of Scope | Not applicable | `docs/plan.md` says LLM should not directly write OpenFOAM files freely in v1. | Preserve deterministic dictionary generation and validation instead. |

## TDD Completion Rule

For every behavior-bearing change:

1. Add or update the failing test first.
2. Run the focused test and confirm it fails for the expected reason.
3. Implement the smallest production change that passes the test.
4. Run the focused test again.
5. Run the full available test suite.
6. Update this checklist with the new feature status, test status, evidence, and next action.

## Status Definitions

- Done: implemented, tested where reasonable, and recently validated.
- Partial: behavior exists but coverage, docs, or validation evidence is incomplete.
- Not Started: no behavior-bearing implementation exists yet.
- Blocked: cannot currently be validated or completed because of an environment or dependency issue.
- Out of Scope: intentionally excluded from the current product direction.
