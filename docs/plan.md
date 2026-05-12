I am building this as an **open-source local engineering agent layer**, not as “another CFD SaaS.” The day-one wedge should be:

> **A local-first AI copilot that turns an engineering intent into a reproducible OpenFOAM case, runs checks, explains failures, generates reports, and never requires uploading CAD or simulation data to the cloud.**

The key market opening is that many AI/CAE players are moving cloud-first: SimScale positions itself as full-cloud CAE for CFD/FEA/thermal/EM, Navier AI is web-based and automates OpenFOAM workflows through agents, and Rescale/Navier’s partnership focuses on cloud HPC plus AI physics models. ([SimScale][1]) Your wedge should be the opposite: **privacy-first, local-first, open-source, solver-agnostic, and engineer-verifiable**.

---

# 0. Product thesis

## Product name placeholder

**OpenNavier**

## One-line positioning

**Cursor for OpenFOAM, FreeCAD, Gmsh, and ParaView — but local-first and open-source.**

Post-P3 positioning:

> **An open-source, AI-native simulation operating system: multi-solver over
> time, OpenFOAM-first in the first product slice, and always
> capability-gated.**

In this roadmap, "universal simulator" means unified orchestration,
validation, evidence, reports, and extension contracts over many specialized
solvers. It does not mean OpenNavier becomes one solver that can solve every
physics problem by itself.

## Initial user

Do **not** start with enterprise aerospace. Start with users who already feel pain but can adopt without procurement:

1. OpenFOAM learners and consultants
2. Mechanical / thermal engineers in small hardware teams
3. Electronics cooling / enclosure airflow engineers
4. University labs using OpenFOAM
5. Indie CAE consultants who want to deliver reports faster

## Initial beachhead

I would choose:

> **OpenFOAM case automation + verification assistant for simple external/internal flow and electronics cooling.**

Not full CAD/CAE democratization on day one. That is too broad.

The first product should help users avoid the top practical failures:

* wrong case folder structure
* wrong boundary conditions
* bad mesh quality
* solver divergence
* unclear residuals
* missing post-processing
* no reproducible report
* no audit trail

OpenFOAM is a strong foundation because it already exposes case setup, running, parallel execution, meshing, solving, and post-processing through files and command-line workflows. Its official docs cover case file structure, mesh generation, solving, monitoring, and post-processing. ([OpenFOAM][2]) OpenFOAM’s command-line interface is also described as a flexible way to control setup, execution, and result evaluation, which makes it suitable for agent orchestration. ([OpenFOAM][3])

---

# 1. Core product: what to build first

## MVP promise

The MVP should do this:

```text
User: "Simulate airflow through this simple duct at 10 m/s and estimate pressure drop."

Agent:
1. Creates an OpenFOAM case
2. Selects solver and validates a `CaseBuildSpec`
3. Generates or imports mesh
4. Writes boundary conditions
5. Runs pre-checks
6. Executes OpenFOAM locally
7. Watches logs
8. Diagnoses divergence or bad mesh
9. Runs post-processing
10. Generates a Markdown/PDF report
```

## What the first version should not do

Avoid these in v0:

* general CAD repair
* arbitrary industrial geometry
* fully autonomous turbulence model choice
* high-fidelity aerospace CFD
* surrogate model training
* cloud compute marketplace
* browser-based collaborative CAE
* “upload any CAD and get perfect answer” promise

Those are later.

---

# 2. Product architecture

## Local-first system design

```text
Desktop / CLI App
│
├── Agent Orchestrator
│   ├── Planner
│   ├── Tool router
│   ├── Safety / validation layer
│   └── Memory of previous runs
│
├── Engineering Tool Adapters
│   ├── OpenFOAM adapter
│   ├── Gmsh adapter
│   ├── FreeCAD adapter
│   ├── ParaView adapter
│   └── Python analysis adapter
│
├── Case Library
│   ├── incompressible/internal-flow
│   ├── external-flow/simple-object
│   ├── electronics-cooling/basic-enclosure
│   ├── pipe-flow/pressure-drop
│   └── heat-transfer/basic-conjugate
│
├── Verification Engine
│   ├── mesh quality checks
│   ├── boundary-condition checks
│   ├── dimensional sanity checks
│   ├── solver compatibility checks
│   ├── residual/convergence parser
│   └── post-processing validators
│
├── Report Generator
│   ├── Markdown
│   ├── PDF
│   ├── plots
│   ├── screenshots
│   └── reproducibility manifest
│
└── Optional Cloud Connectors
    ├── remote GPU/CPU runner
    ├── team dashboard
    └── private enterprise deployment
```

## Why these tools

| Layer            | Recommended tool  | Why                                                                                                  |
| ---------------- | ----------------- | ---------------------------------------------------------------------------------------------------- |
| CFD solver       | **OpenFOAM**      | Open-source CFD foundation; GPL licensed. ([OpenFOAM][4])                                            |
| CAD scripting    | **FreeCAD**       | Open-source parametric CAD with Python scripting support. ([FreeCAD Wiki][5])                        |
| Mesh generation  | **Gmsh**          | Open-source mesh generator, distributed under GPL. ([gmsh.info][6])                                  |
| Visualization    | **ParaView**      | Open-source visualization tool with BSD 3-Clause license and Python/batch scripting. ([ParaView][7]) |
| Local automation | Python + Docker   | Easiest for subprocess control, case-build execution, parsing, and reports                           |
| Desktop later    | Tauri or Electron | Add UI after CLI proves usage                                                                        |

## Tech stack decision

Use a Python-first stack for v0.1. The first product is a local CLI and deterministic automation layer, so the stack should optimize for subprocess control, file generation, parsing, testability, and easy installation.

### v0.1 core stack

| Area | Decision | Notes |
| ---- | -------- | ----- |
| Language | **Python 3.11+** | Best fit for CLI tooling, OpenFOAM process control, parsers, reports, and scientific ecosystem access. |
| Packaging | **`pyproject.toml` + `uv`** | Use a modern Python project layout with fast dependency sync and reproducible lockfiles. |
| CLI framework | **Typer** | Clean command definitions for `opennavier doctor`, `opennavier report`, `opennavier init`, and future subcommands. |
| Data models | **Pydantic** | Validate simulation specs, manifests, diagnostics, and report inputs before writing files. |
| Dictionary writers | **Python structured writers** | Write OpenFOAM dictionaries, report Markdown, and later Gmsh/ParaView scripts from validated `CaseBuildSpec` data. |
| Testing | **pytest** | Unit-test parsers, validators, manifests, and CLI behavior without requiring OpenFOAM for every test. |
| Formatting/linting | **Ruff** | Single fast tool for linting and formatting Python code. |
| Local execution | **native subprocess + Docker fallback** | Run local OpenFOAM when installed; use Docker images for reproducible examples and CI-style validation. |
| Reports | **Markdown first** | Generate `report.md` and `manifest.json` before adding PDF export. |

### Engineering tool stack

| Tool | Phase | Role |
| ---- | ----- | ---- |
| **OpenFOAM** | v0.1 | Primary solver and case structure target. |
| **Gmsh** | v0.4 | Parametric mesh generation after case diagnostics are stable. |
| **FreeCAD** | v0.4 | Parametric geometry scripting; avoid arbitrary CAD healing early. |
| **ParaView / pvpython** | v0.5 | Batch post-processing, screenshots, and visualization presets. |

### Later stack decisions

Delay the desktop app until the CLI has real usage. Prefer **Tauri + TypeScript + React** for OpenNavier Studio because it fits a local-first desktop product with a smaller runtime than Electron. Keep the Python CLI as the automation engine behind the UI.

Delay LLM integration until deterministic commands work. When added, the LLM
should produce structured Pydantic simulation specs and schema-backed
`CaseBuildSpec` artifacts, not raw OpenFOAM dictionaries.

Important licensing note: OpenFOAM is GPL, Gmsh is GPL, FreeCAD is LGPL, and ParaView is BSD-licensed. ([OpenFOAM][4]) For the first commercial version, avoid modifying and redistributing solver internals unless you are ready to comply with GPL obligations. Keep your proprietary value in orchestration, case-build tooling, QA, reports, UI, and hosted services.

---

# 3. Day-one development plan

## Day 1 goal

By the end of day one, do **not** try to build an AI simulation platform.

Build this:

> A CLI that can create, run, check, and report one known OpenFOAM tutorial case reproducibly.

## Day 1 deliverables

```text
opennavier/
├── README.md
├── LICENSE
├── pyproject.toml
├── opennavier/
│   ├── cli.py
│   ├── runners/
│   │   └── openfoam_runner.py
│   ├── prompt_examples/
│   │   └── cavity/
│   ├── validators/
│   │   ├── case_structure.py
│   │   ├── mesh_quality.py
│   │   └── residuals.py
│   ├── reports/
│   │   └── markdown_report.py
│   └── logs/
├── examples/
│   └── cavity_demo.md
└── tests/
    └── test_case_structure.py
```

## Day 1 CLI commands

```bash
opennavier init cavity ./runs/cavity-001
opennavier check ./runs/cavity-001
opennavier run ./runs/cavity-001
opennavier diagnose ./runs/cavity-001
opennavier report ./runs/cavity-001
```

## Day 1 success metric

The product is successful on day one if you can record a demo:

```text
Prompt:
"Run the lid-driven cavity case and explain whether it converged."

Output:
- case generated
- OpenFOAM command executed
- log parsed
- residuals summarized
- basic report generated
```

Do not add LLM until this deterministic pipeline works.

---

# 4. 0-to-1 development roadmap

## Phase 1: Deterministic OpenFOAM automation

**Timeline:** Week 1–2
**Goal:** Build trust before intelligence.

### Build

* Case writer from validated `CaseBuildSpec` data
* OpenFOAM runner
* Log parser
* Mesh checker wrapper
* Residual parser
* Markdown report generator
* Reproducibility manifest

### Supported cases

Start with only three:

1. lid-driven cavity
2. pipe / duct pressure drop
3. external flow around simple object

### Output format

Every run should produce:

```text
run/
├── case/
├── logs/
├── plots/
├── report.md
├── manifest.json
└── diagnostics.json
```

### Why this matters

Most AI engineering products fail because they generate plausible-looking files without validation. Your advantage should be: **every agent action is checked by deterministic engineering rules.**

---

## Phase 2: Agent layer on top of deterministic tools

**Timeline:** Week 3–4
**Goal:** Natural-language interface through validated `CaseBuildSpec` data, not
fixed hardcoded case generators.

The concrete implementation contract for the "Pencil for simulation" direction
is documented in [`simulation-mcp-canvas.md`](simulation-mcp-canvas.md). It
defines the MCP canvas as the agent-access layer over the deterministic CLI and
package APIs, with repo-native `simulation.onv.json` manifests and validated
tools instead of free-form dictionary edits.

### Build

```text
User intent → structured simulation spec → validated CaseBuildSpec → MCP tool operations → validation → execution → diagnosis → report
```

Example structured spec:

```json
{
  "physics": "incompressible_flow",
  "case_type": "internal_duct",
  "velocity_inlet": "10 m/s",
  "outlet": "pressure_outlet",
  "fluid": "air",
  "objective": "pressure_drop"
}
```

### Agent rules

The LLM should **not directly write OpenFOAM files freely** in v1.

Instead:

1. LLM extracts intent
2. LLM may propose a one-off `CaseBuildSpec` as typed schema data
3. deterministic validators check the build spec, paths, writer operations, and required approvals
4. deterministic planner maps spec plus validated `CaseBuildSpec` to MCP/package tool operations
5. file generator writes OpenFOAM dictionaries through approved operations
6. checker rejects invalid setups
7. runner executes
8. LLM explains results

This is much safer than letting the LLM edit every file arbitrarily.

---

## Phase 3: Engineering QA moat

**Timeline:** Month 2
**Goal:** Become valuable even for people who already know OpenFOAM.

### Build checkers for

| Checker                      | What it catches                                  |
| ---------------------------- | ------------------------------------------------ |
| Case structure checker       | missing `0`, `constant`, `system` files          |
| Solver compatibility checker | wrong solver for physics                         |
| Boundary-condition checker   | inconsistent inlet/outlet/wall fields            |
| Mesh quality checker         | non-orthogonality, skewness, aspect ratio issues |
| Residual checker             | divergence, oscillation, false convergence       |
| Time-step checker            | Courant number risk                              |
| Units checker                | obvious magnitude errors                         |
| Report checker               | missing assumptions / missing validation         |

### Product insight

This is likely your first real moat.

A generic AI wrapper can generate OpenFOAM files. But a serious engineering tool needs a growing database of **simulation failure modes**.

---

## Phase 4: FreeCAD + Gmsh geometry pipeline

**Timeline:** Month 2–3
**Goal:** Move from tutorial cases to user-created parametric geometry.

FreeCAD has Python scripting support, and Gmsh provides a programmable mesh-generation path. ([FreeCAD Wiki][5]) Your first geometry flow should be parametric, not arbitrary CAD upload.

### Start with generated geometry

Examples:

```text
opennavier create-geometry duct --length 1m --width 0.1m --height 0.1m
opennavier create-geometry enclosure --fan 40mm --vent-pattern grid
opennavier create-geometry pipe-bend --diameter 30mm --angle 90
```

### Avoid at first

* messy STEP files
* complex assemblies
* CAD healing
* thin gaps
* moving parts
* conjugate heat transfer with many materials

### Why

Arbitrary CAD cleanup is a deep product by itself. Navier AI publicly emphasizes geometry cleanup and meshing as part of its agent-driven workflow, which shows the problem is commercially important but also hard. ([Y Combinator][8]) Do not start there.

---

## Phase 5: ParaView post-processing automation

**Timeline:** Month 3
**Goal:** Turn simulation output into human-readable evidence.

ParaView supports Python and batch execution through tools like `pvpython` and `pvbatch`, which makes automated visualization possible. ([ParaView Documentation][9])

### Build

* pressure contour image
* velocity slice
* streamline plot
* residual plot
* force / pressure-drop table
* comparison between runs
* report-ready screenshots

### CLI

```bash
opennavier visualize ./runs/duct-001 --preset pressure-drop
opennavier compare ./runs/duct-001 ./runs/duct-002
```

---

## Phase 6: Desktop UI

**Timeline:** Month 4–5
**Goal:** Expand beyond terminal users.

Only build UI after the CLI has users.

### UI screens

1. Project dashboard
2. New simulation wizard
3. Agent chat
4. Case file viewer
5. Run monitor
6. Diagnostics panel
7. Report viewer
8. Compare runs

### UI principle

The user should always see:

```text
What the agent changed
Why it changed it
Which command was executed
What files were generated
What assumptions were made
Whether checks passed or failed
```

This is how you build trust with engineers.

---

# 5. Product scope by version

## v0.1 — Open-source CLI

```text
Target: OpenFOAM users
Value: automate case setup, run, diagnose, report
Distribution: GitHub + Docker
Price: free
```

Features:

* `init`
* `check`
* `run`
* `diagnose`
* `report`
* 3 prompt examples and validated case-build paths
* Markdown reports
* local-only

## v0.2 — AI intent parser

```text
Target: technical users
Value: plain-English to validated simulation spec
Distribution: GitHub + CLI
Price: free open-source
```

Features:

* natural-language prompt
* schema-based spec generation
* schema-based `CaseBuildSpec` generation from prompt examples
* explanation of assumptions
* no arbitrary file editing yet

## v0.3 — Engineering QA engine

```text
Target: OpenFOAM consultants, labs
Value: catch mistakes faster
Distribution: GitHub + docs + examples
Price: free core, paid pro later
```

Features:

* mesh diagnostics
* residual diagnosis
* solver compatibility
* case-linting
* report quality checker

## v0.4 — Parametric geometry

```text
Target: small hardware teams
Value: run common geometry classes quickly
Distribution: CLI + Docker
Price: early paid pilots
```

Features:

* duct generator
* pipe generator
* electronics enclosure generator
* Gmsh integration
* FreeCAD integration

## v1.0 — OpenNavier Studio

```text
Target: engineering teams
Value: local-first engineering workflow
Distribution: desktop app + CLI
Price: open-core
```

Features:

* desktop UI
* project history
* run comparison
* report export
* team license
* optional private model / API support

---

## Post-P3 Simulation OS roadmap

After P0 to P3, OpenNavier should grow from an OpenFOAM-first copilot into a
multi-solver simulation OS. The order still follows the same trust rule:
capabilities become executable only when their physics, geometry, mesh, solver,
validators, benchmarks, artifacts, and reports are declared and tested.

| Priority | Roadmap layer | Product meaning |
| --- | --- | --- |
| P4 | Capability registry and OS kernel | The planner, Studio, MCP tools, and LLM layer can only claim support through declared `CapabilityManifest` records. |
| P5 | Unified simulation ontology | CFD, FEA, thermal, and later domains share typed units, fields, materials, boundaries, objectives, and result artifacts. |
| P6 | Multi-solver adapter SDK | Solvers integrate through auditable local adapter contracts for discovery, input writing, execution, logs, diagnostics, results, and licensing. |
| P7 | FEA and thermal expansion | The first non-CFD capabilities prove the architecture with narrow linear elastic and thermal workflows. |
| P8 | Verification and evidence corpus | Benchmarks, analytical sanity checks, convergence evidence, and validation reports gate capability promotion. |
| P9 | Geometry and mesh preparation | CAD operations, semantic boundary tagging, mesh strategy, and model cleanup become reproducible local artifacts. |
| P10 | Coupled workflow graphs | Staged multi-solver workflows use explicit DAGs, unit-checked handoffs, approvals, retries, and partial-result handling. |
| P11 | Plugin ecosystem and certification | Community extensions contribute adapters and capabilities through manifests, sandbox rules, tests, benchmarks, and trust states. |
| P12 | AI-native capability authoring | Agents help draft capabilities, tests, schemas, examples, and docs, but humans and deterministic evidence control promotion. |

This long-term roadmap keeps the local-first promise intact:

* no cloud upload by default
* no hidden solver commands
* no LLM-authored raw solver files outside approved writers
* no executable claim without a capability manifest and benchmark evidence
* no broad domain promise until adapters, validators, and reports exist

---

# 6. Technical architecture: v1

```text
┌──────────────────────────────────────┐
│ OpenNavier CLI / Desktop UI             │
└──────────────────────────────────────┘
                  │
                  ▼
┌──────────────────────────────────────┐
│ Agent Orchestrator                    │
│ - intent parser                       │
│ - planner                             │
│ - tool caller                         │
│ - explanation layer                   │
└──────────────────────────────────────┘
                  │
                  ▼
┌──────────────────────────────────────┐
│ Simulation Spec Schema                │
│ - physics                             │
│ - geometry                            │
│ - mesh                                │
│ - solver                              │
│ - boundary conditions                 │
│ - outputs                             │
└──────────────────────────────────────┘
                  │
                  ▼
┌──────────────────────────────────────┐
│ Deterministic Generators              │
│ - OpenFOAM dictionary writer          │
│ - Gmsh script writer                  │
│ - FreeCAD script writer               │
│ - ParaView post-processing script     │
└──────────────────────────────────────┘
                  │
                  ▼
┌──────────────────────────────────────┐
│ Validators                            │
│ - schema validation                   │
│ - case linting                        │
│ - mesh checks                         │
│ - solver compatibility                │
│ - residual parser                     │
│ - units / magnitude checks            │
└──────────────────────────────────────┘
                  │
                  ▼
┌──────────────────────────────────────┐
│ Local Execution Layer                 │
│ - Docker runner                       │
│ - native OpenFOAM runner              │
│ - subprocess logs                     │
│ - resource monitor                    │
└──────────────────────────────────────┘
                  │
                  ▼
┌──────────────────────────────────────┐
│ Report + Artifact Layer               │
│ - report.md                           │
│ - report.pdf                          │
│ - plots                               │
│ - screenshots                         │
│ - manifest.json                       │
└──────────────────────────────────────┘
```

---

# 7. Repository structure

```text
opennavier/
├── apps/
│   ├── cli/
│   └── studio/                  # later desktop app
│
├── packages/
│   ├── core/
│   │   ├── specs/
│   │   ├── planner/
│   │   ├── validators/
│   │   └── reports/
│   │
│   ├── openfoam/
│   │   ├── case_build/
│   │   ├── dictionary_writer/
│   │   ├── runner/
│   │   ├── log_parser/
│   │   └── diagnostics/
│   │
│   ├── gmsh/
│   │   ├── script_generator/
│   │   └── mesh_converter/
│   │
│   ├── freecad/
│   │   ├── geometry_generator/
│   │   └── step_exporter/
│   │
│   ├── paraview/
│   │   ├── pvpython_scripts/
│   │   └── screenshot_exporter/
│   │
│   └── agent/
│       ├── llm_client/
│       ├── prompt_examples/
│       ├── tool_registry/
│       └── guardrails/
│
├── examples/
│   ├── cavity/
│   ├── pipe-flow/
│   ├── duct-pressure-drop/
│   └── electronics-enclosure/
│
├── docs/
│   ├── getting-started.md
│   ├── architecture.md
│   ├── validation-philosophy.md
│   └── commercial-license.md
│
├── docker/
│   ├── openfoam.Dockerfile
│   └── devcontainer.json
│
└── tests/
```

---

# 8. Moat strategy

## Bad moat

“LLM writes OpenFOAM files.”

This is easy to copy.

## Real moat

### 1. Simulation failure database

Every failed run becomes structured knowledge:

```json
{
  "symptom": "residual diverges after 200 iterations",
  "case_type": "internal_flow",
  "solver": "simpleFoam",
  "possible_causes": [
    "bad inlet velocity magnitude",
    "poor mesh non-orthogonality",
    "incompatible turbulence settings",
    "wrong pressure outlet condition"
  ],
  "recommended_checks": [
    "checkMesh",
    "Courant number",
    "boundary condition consistency"
  ]
}
```

### 2. Prompt Example Library

Provide strong non-executable prompt examples for common use cases:

* duct pressure drop
* fan enclosure airflow
* electronics cooling
* pipe bend loss
* external drag
* heat sink airflow
* cleanroom airflow
* hood / exhaust ventilation

### 3. Reproducibility layer

Every run generates a manifest:

```json
{
  "solver": "simpleFoam",
  "openfoam_version": "v2412",
  "mesh_tool": "gmsh",
  "case_build_spec": "case-builds/duct-pressure-drop.json",
  "created_by": "opennavier",
  "assumptions": [
    "incompressible flow",
    "steady-state",
    "air at room temperature"
  ]
}
```

### 4. Local-first trust

This is the big wedge against cloud-first competitors.

Engineers in semiconductor, defense, hardware, industrial equipment, and labs often dislike uploading sensitive geometry. Your local-first promise should be simple:

```text
Your geometry, mesh, logs, and results stay on your machine by default.
```

---

# 9. GTM from day one

## Day-one GTM principle

Do not launch as:

> “AI CAE platform.”

Launch as:

> “Open-source OpenFOAM copilot that helps you run and debug cases locally.”

This is more believable and more searchable.

---

## Week 1: Build in public

### Channels

* GitHub
* X / Twitter
* LinkedIn
* Reddit: r/CFD, r/OpenFOAM, r/MechanicalEngineering
* CFD Online forum, carefully and respectfully
* YouTube short demos
* Hacker News when demo is strong enough

### First post

```text
I’m building an open-source local-first engineering agent for OpenFOAM.

Goal:
- no cloud upload
- no black-box CFD
- generate cases
- run locally
- diagnose logs
- produce reports

Starting with cavity, duct flow, and pipe pressure drop.

Looking for OpenFOAM users who hate debugging case setup.
```

### First demo

A 60-second video:

```text
1. User types plain-English simulation request
2. CLI creates OpenFOAM case
3. Runs checkMesh
4. Runs solver
5. Parses residuals
6. Generates report.md
```

---

## Week 2–3: Target OpenFOAM pain communities

Your best early users are not enterprise buyers. They are:

* graduate students
* CFD consultants
* OpenFOAM learners
* hardware engineers without CFD specialists
* CAE freelancers

### Offer

```text
Send me one broken OpenFOAM case.
I’ll use OpenNavier to diagnose it and turn the diagnosis into an open-source checker.
```

This gives you real data, real failure modes, and community goodwill.

---

## Month 1: Create SEO assets

You should publish pages targeting painful search queries:

```text
"OpenFOAM residuals not converging"
"OpenFOAM checkMesh failed"
"OpenFOAM pressure outlet boundary condition"
"simpleFoam divergence"
"OpenFOAM Courant number too high"
"OpenFOAM mesh non orthogonality"
"OpenFOAM tutorial report generator"
"OpenFOAM AI assistant"
"OpenFOAM local copilot"
```

Each article should include:

* explanation
* example failure
* command-line diagnosis
* how OpenNavier checks it
* reproducible example repo

This is perfect for your skillset: SEO + technical product + open-source distribution.

---

## Month 2: Launch “case doctor”

This could become the viral feature.

```bash
opennavier doctor ./my-broken-openfoam-case
```

Output:

```text
Diagnosis:
1. Mesh has high non-orthogonality near outlet.
2. U boundary condition is inconsistent with selected solver.
3. Pressure field is missing outlet reference.
4. Residuals diverge after 120 iterations.

Suggested fix:
- reduce relaxation factor
- refine mesh near outlet
- change outlet pressure condition
- rerun checkMesh
```

This is more immediately useful than “generate a case from prompt.”

---

## Month 3: First paid pilots

Do not sell SaaS first. Sell **workflow acceleration**.

### Pilot offer

```text
$500–$2,000 fixed-price pilot

We help your team automate one recurring OpenFOAM workflow locally:
- case-build spec
- validation rules
- run script
- report generator
- comparison dashboard
```

### Target customers

* CAE consultants
* university labs
* small hardware startups
* industrial design firms
* electronics cooling teams
* HVAC / ventilation consultants

### Why they buy

They do not buy because “AI is cool.”

They buy because:

```text
You reduce 2 days of repeated simulation setup/reporting into 30 minutes.
```

---

## Month 4–6: Open-core monetization

## Free open-source core

```text
- CLI
- OpenFOAM runner
- prompt examples
- basic diagnostics
- Markdown reports
- local LLM support
```

## Paid Pro

```text
$19–$49/month individual
- desktop UI
- advanced reports
- run comparison
- private prompt example library
- advanced diagnostics
- PDF export
- parametric sweeps
```

## Team license

```text
$199–$999/month/team
- shared local project format
- internal prompt example registry
- audit trail
- team report branding
- private model config
- license management
```

## Enterprise

```text
$10k–$100k/year
- on-prem deployment
- custom solver adapters
- private workflow automation
- compliance support
- dedicated support
```

The cloud should be optional, not required.

---

# 10. Pricing model

## Best initial pricing

Start with services + open source:

```text
Open-source CLI: free
Custom workflow pilot: $500–$2,000
Team deployment: $5k–$20k
Annual enterprise support: $10k+
```

Then add product pricing after usage patterns are clear.

## Why not usage-based first?

For local-first products, usage-based pricing is harder because compute happens on the user’s machine. Better monetization:

* support
* prompt examples
* QA rules
* desktop UI
* team workflows
* private deployment
* report automation
* solver adapters
* vertical packages

---

# 11. Product wedge options

## Best wedge: OpenFOAM doctor

**Why:** easiest to adopt, high pain, clear value.

```text
opennavier doctor ./case
```

## Second wedge: report generator

**Why:** consultants and students need this.

```text
opennavier report ./case --format pdf
```

## Third wedge: case-build generator

**Why:** makes new users productive.

```text
opennavier init duct-pressure-drop
```

## Fourth wedge: AI simulation planner

**Why:** impressive, but only after deterministic tools work.

```text
opennavier ask "simulate pressure drop in a 1m duct at 10 m/s"
```

---

# 12. First 30 days execution plan

## Day 1

Build deterministic CLI skeleton.

```text
Goal:
- run one OpenFOAM case
- parse log
- generate report
```

## Day 2–3

Add case checker.

```text
Checks:
- required folders
- required dictionaries
- solver exists
- boundary files exist
```

## Day 4–5

Add residual parser.

```text
Output:
- initial residual
- final residual
- convergence trend
- warning if diverging
```

## Day 6–7

Publish GitHub repo and demo video.

```text
CTA:
"Send me a broken OpenFOAM case."
```

## Week 2

Add `opennavier doctor`.

```text
Focus:
- case linting
- checkMesh parsing
- common error explanations
```

## Week 3

Add case-build generator.

```text
Prompt examples:
- cavity
- pipe flow
- duct pressure drop
```

## Week 4

Add LLM intent parser.

```text
But only output structured simulation specs or `CaseBuildSpec` artifacts.
Do not let it freely write case files.
```

---

# 13. First 90 days roadmap

| Time      | Product milestone                  | GTM milestone                    | Success metric      |
| --------- | ---------------------------------- | -------------------------------- | ------------------- |
| Day 1     | Run + report one case              | Start build-in-public thread     | 1 working demo      |
| Week 1    | CLI + residual parser              | GitHub repo public               | 20 GitHub stars     |
| Week 2    | `opennavier doctor`                  | Ask users for broken cases       | 5 real cases tested |
| Week 3    | 3 prompt examples + build specs    | Publish OpenFOAM debugging posts | 100 stars           |
| Week 4    | LLM intent → validated spec        | YouTube demo                     | 10 active users     |
| Month 2   | mesh + BC + residual diagnostics   | CFD community launch             | 25 real user cases  |
| Month 3   | parametric duct/enclosure workflow | paid pilot outreach              | 3 paid pilots       |
| Month 4–6 | desktop alpha                      | team pilots                      | $5k–$20k revenue    |

---

# 14. The first homepage

## Hero

```text
Local-first AI copilot for OpenFOAM.

Generate, run, debug, and report CFD cases on your own machine.
No cloud upload. No black-box solver. Fully reproducible.
```

## Subheading

```text
OpenNavier helps engineers automate OpenFOAM workflows using open-source tools like OpenFOAM, Gmsh, FreeCAD, and ParaView.
```

## CTA

```text
Install CLI
View GitHub
Submit a broken case
```

## Feature sections

```text
1. Diagnose broken OpenFOAM cases
2. Generate validated case-build specs
3. Run simulations locally
4. Parse residuals and mesh quality
5. Generate engineering reports
6. Bring your own LLM or run without AI
```

## Trust section

```text
Your CAD and simulation data stay local by default.
Every file generated by the agent is visible, editable, and reproducible.
```

---

# 15. The most important product principle

Do not market it as replacing engineers.

Market it as:

```text
A local automation layer for engineers who already care about verification.
```

Engineers do not trust magic. They trust:

* visible files
* reproducible commands
* logs
* assumptions
* validation checks
* comparison reports
* ability to override

So your product should never hide the OpenFOAM workflow. It should make the workflow easier to inspect.

---

# 16. What I would build first, literally

The first serious feature should be this:

```bash
opennavier doctor ./case
```

Because it has the clearest value.

Then:

```bash
opennavier report ./case
```

Then:

```bash
opennavier init duct-pressure-drop
```

Then:

```bash
opennavier ask "Create a duct pressure drop simulation for air at 10 m/s"
```

That sequence gives you the best 0-to-1 path:

```text
debug existing pain → generate trust → automate repeat work → add AI interface
```

My recommendation: build the **OpenFOAM Doctor + Report Generator** first, not the full AI-native CAE platform. This gives you a real open-source wedge, a credible GTM story, and a path toward paid local-first engineering automation.

[1]: https://www.simscale.com/?utm_source=chatgpt.com "SimScale: Simulation Software | Engineering AI in the Cloud"
[2]: https://www.openfoam.com/documentation/user-guide?utm_source=chatgpt.com "User Guide"
[3]: https://doc.openfoam.com/2212/getting-started/command-line/?utm_source=chatgpt.com "Command line"
[4]: https://openfoam.org/licence/?utm_source=chatgpt.com "Free Software Licence"
[5]: https://wiki.freecad.org/Python_scripting_tutorial?utm_source=chatgpt.com "Python scripting tutorial"
[6]: https://gmsh.info/LICENSE.txt?utm_source=chatgpt.com "GNU General Public License (GPL)"
[7]: https://www.paraview.org/license/?utm_source=chatgpt.com "ParaView License"
[8]: https://www.ycombinator.com/companies/navier-ai?utm_source=chatgpt.com "Navier AI: Agent-Driven Engineering"
[9]: https://docs.paraview.org/en/latest/Tutorials/ClassroomTutorials/pythonAndBatchPvpythonAndPvbatch.html?utm_source=chatgpt.com "14. Python & Batch: pvpython and pvbatch"
