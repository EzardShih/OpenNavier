# OpenNavier Evaluation Framework

This document defines how OpenNavier evaluates complete simulation workflows.
It complements `docs/project-checklist.md`, which tracks feature completion and
test coverage. The checklist asks "is this component implemented and tested?"
This framework asks "does the product help an engineer complete a simulation
workflow in a trustworthy, reproducible way?"

The north star is Pencil for simulation: a fast local workflow where an engineer
can express intent, generate or edit a case, run deterministic checks, execute
the solver, inspect results, and iterate without losing visibility into the
underlying engineering artifacts.

## Workflow Under Evaluation

The complete target workflow is:

```text
user intent or spec
-> structured simulation spec
-> deterministic planner
-> case generation
-> validation
-> execution
-> diagnostics
-> post-processing
-> report and manifest
-> review or edit loop
```

The current implemented slice is smaller:

```text
case template or existing case
-> case validation
-> optional log diagnostics
-> Markdown report
-> reproducibility manifest
```

Each new feature should make one part of the complete workflow more evaluable.
Do not add opaque intelligence before the deterministic workflow gates exist.

## Evaluation Principles

- Engineer-verifiable output matters more than plausible output.
- Every behavior-bearing feature needs a deterministic test first.
- Default tests must not require OpenFOAM, Gmsh, FreeCAD, ParaView, Docker, or
  network access.
- External-tool tests must be explicitly marked as integration tests.
- AI-generated content must be reduced to structured specs or plans before it
  can affect case files.
- Evaluation artifacts must remain local by default.
- Failures should produce stable diagnostic codes and human-readable guidance.
- Reports must disclose assumptions, inspected artifacts, and validation gaps.

## Evaluation Levels

| Level | Name | Scope | Default suite | Main evidence |
| --- | --- | --- | --- | --- |
| L0 | Unit evals | Parsers, validators, schemas, writers, adapters | Yes | `uv run pytest` |
| L1 | CLI contract evals | Commands, exit codes, JSON shape, report writing | Yes | `tests/test_cli.py` and related tests |
| L2 | Deterministic workflow evals | Case generation, validation, diagnostics, report, manifest | Yes | Temporary cases and committed examples |
| L3 | External-tool integration evals | Real OpenFOAM, Gmsh, FreeCAD, ParaView execution | No | Marked integration tests and saved artifacts |
| L4 | Product workflow evals | End-to-end engineer task completion | No | Demo script, artifacts, acceptance checklist |
| L5 | AI workflow evals | Prompt to validated spec or plan | No until enabled | Golden prompt set and schema validation |

L0 through L2 are required before a feature is marked done. L3 through L5 are
added when the relevant external dependency or product surface exists.

## Standard Gates

Each complete workflow should be evaluated through these gates. A gate may be
marked `not applicable` only when the workflow genuinely does not touch that
part of the product.

| Gate | Purpose | Required evidence |
| --- | --- | --- |
| G1 Intent and spec | User input becomes a validated structured intent | Pydantic validation, rejected invalid fields, assumptions listed |
| G2 Planning | Intent maps to a supported deterministic workflow | Template or adapter choice, solver family, unsupported cases rejected |
| G3 Case generation | Files are created predictably and safely | Expected file tree, overwrite guards, no protected path writes |
| G4 Static validation | The case is inspectable before execution | Case structure, dictionary headers, boundary consistency, solver compatibility when available |
| G5 Execution | The solver or external tool is invoked safely | Argument-list subprocess calls, captured logs, exit status, no shell-string execution |
| G6 Runtime diagnostics | Logs are parsed into actionable diagnostics | Residual, mesh, Courant, and failure-mode diagnostic codes |
| G7 Post-processing | Results become inspectable artifacts | Plots, screenshots, derived metrics, or clearly documented absence |
| G8 Report | The run is explainable to an engineer | Markdown report with status, assumptions, failures, and next steps |
| G9 Reproducibility | The workflow can be replayed or audited | Manifest with local paths, diagnostic codes, commands, versions when available |
| G10 Privacy and licensing | The workflow preserves local-first boundaries | No cloud upload by default, OpenFOAM remains an external dependency |
| G11 Edit loop | A parameter or setup change can be made safely | Changed spec or parameter, regenerated artifacts, comparison to previous run |

## Canonical Workflow Evals

### EVAL-CAVITY-STATIC: Starter Cavity Static Workflow

Goal: prove that OpenNavier can create and inspect a deterministic tutorial case
without requiring OpenFOAM.

Input:

```bash
uv run opennavier init cavity ./runs/eval-cavity-static
uv run opennavier doctor ./runs/eval-cavity-static
uv run opennavier report ./runs/eval-cavity-static --output ./runs/eval-cavity-static/report.md --manifest-output ./runs/eval-cavity-static/manifest.json
```

Pass criteria:

- The generated case contains `0`, `constant`, and `system`.
- Required system dictionaries contain `FoamFile` headers.
- Boundary-condition validation passes for the generated cavity case.
- `doctor` exits with `0`.
- `report.md` and `manifest.json` are created.
- The manifest records diagnostic counts and no cloud upload.
- Running the same workflow twice is deterministic except for timestamps and
  absolute paths.

Current status: partially covered by unit and CLI tests. A single named
workflow test or scripted eval should be added when `runs/eval-*` conventions
exist.

### EVAL-CAVITY-RUN: Day 1 Run And Convergence Workflow

Goal: prove the first complete simulation loop:

```text
generate case -> validate -> run OpenFOAM -> parse log -> summarize convergence -> report
```

Prompt:

```text
Run the lid-driven cavity case and explain whether it converged.
```

Pass criteria:

- The case is generated or selected deterministically.
- The run command executes OpenFOAM through an argument-list subprocess call.
- Solver logs are captured under a predictable logs directory.
- Residual diagnostics identify convergence, divergence, or uncertainty.
- The final report includes the solver command, exit code, residual summary,
  assumptions, and validation gaps.
- If OpenFOAM is unavailable, the workflow fails with a clear diagnostic rather
  than pretending results exist.

Current status: blocked on CLI solver execution wiring and real or fake
end-to-end run artifacts.

### EVAL-BROKEN-CASE-DOCTOR: Broken Case Diagnostics

Goal: prove that OpenNavier is useful on cases it did not generate.

Fixture classes:

- Missing required directories or dictionaries.
- Malformed or missing `FoamFile` headers.
- Boundary patches present in `blockMeshDict` but missing from field files.
- `checkMesh` logs with high skewness or non-orthogonality.
- Solver logs with divergence, oscillation, or stalled residuals.

Pass criteria:

- Each issue produces a stable diagnostic code.
- Blocking issues result in a non-zero CLI exit where documented.
- Warnings do not hide blocking failures.
- JSON output remains machine-readable and stable.
- Human text explains what was inspected and what was not inspected.

Current status: substantially covered by current tests. Expand by adding new
captured-log fixtures as real user cases are collected.

### EVAL-DUCT-PRESSURE-DROP: Parametric Duct Workflow

Goal: prove OpenNavier can move beyond tutorial cases into a common engineering
workflow.

Input spec:

```json
{
  "case_name": "duct_pressure_drop",
  "solver_family": "incompressible_laminar",
  "geometry": {
    "kind": "duct",
    "length": 1.0,
    "width": 0.1,
    "height": 0.05
  },
  "fluid": {
    "kinematic_viscosity": 1.5e-5
  },
  "objective": "pressure_drop"
}
```

Pass criteria:

- Unsupported geometry or missing physical parameters are rejected at spec
  validation time.
- Geometry and mesh generation produce deterministic local artifacts.
- Mesh quality diagnostics pass or produce actionable warnings.
- Solver selection matches the physics and run control.
- Reported pressure drop is compared against an analytical or reference value
  with a documented tolerance when such a comparison is valid.
- The report states when the comparison is not physically appropriate.

Current status: future eval. The Gmsh and FreeCAD adapters exist, but the
planner, duct template, solver execution, and pressure-drop comparison do not.

### EVAL-AI-SPEC: Prompt To Validated Simulation Spec

Goal: evaluate AI only as a structured intent layer.

Example prompts:

- "Run a lid-driven cavity with a 20 by 20 mesh and end time 0.5."
- "Estimate pressure drop through a 1 meter duct with air at 10 m/s."
- "Use a turbulent external-airfoil case." This should be rejected until that
  workflow is supported.

Pass criteria:

- The model emits only the allowed structured spec shape.
- Unsupported physics, fields, or geometry classes are rejected.
- Units and magnitudes are normalized or flagged before case generation.
- The deterministic planner can consume the accepted spec.
- The AI layer never writes OpenFOAM dictionaries directly.

Current status: schema validation exists. Prompt evals are future work and
should not be introduced until deterministic spec-to-case behavior exists.

### EVAL-STUDIO-EDIT-LOOP: Pencil-Like Edit Loop

Goal: evaluate the interactive product feel once Studio exists.

Task:

```text
Open a simulation, change one physical or geometric parameter, rerun checks,
compare the new result to the previous result, and export a report.
```

Pass criteria:

- The first viewport is the working simulation, not a marketing page.
- The user can see case status, diagnostics, and key artifacts without opening
  raw folders manually.
- Parameter changes are visible as structured changes, not hidden file edits.
- Regeneration does not overwrite unrelated user changes silently.
- The UI shows running, failed, passed, and warning states clearly.
- The exported report and manifest match the final visible state.

Current status: future eval. Studio is not started.

## Metrics

Use exact matches for deterministic structure and schema behavior. Use
tolerances only for floating-point physics results or external solver output.

| Area | Metric | Target |
| --- | --- | --- |
| Determinism | Same input produces same file tree and diagnostics | Exact match except timestamps and absolute paths |
| Safety | Protected paths and shell-string solver commands are rejected | 100 percent |
| Diagnostic stability | Diagnostic codes stay stable across releases | 100 percent unless intentionally versioned |
| Report quality | Reports include assumptions, failures, validation gaps, and local-only note | 100 percent |
| Solver handling | Missing external tools produce explicit diagnostics | 100 percent |
| AI schema adherence | Accepted AI output validates against Pydantic models | 100 percent |
| Unsupported request handling | Unsupported workflows are rejected before file generation | 100 percent |
| Physical sanity | Derived metrics match reference or analytical expectations | Case-specific tolerance |

## Artifact Conventions

Default unit and CLI tests should use temporary directories. Manual and
integration evals may write under ignored runtime directories such as:

```text
runs/evals/<eval-id>/
```

A complete workflow artifact directory should eventually contain:

```text
case/
logs/
plots/
diagnostics.json
report.md
manifest.json
```

Until the run directory convention is implemented, tests should keep using
temporary directories and committed minimal examples.

## Regression Policy

When a workflow bug is found:

1. Add a failing regression test or captured fixture first.
2. Confirm the test fails for the expected reason.
3. Implement the smallest fix.
4. Run the focused test.
5. Run `uv run pytest` and `uv run ruff check .`.
6. Update `docs/project-checklist.md` and this file if the workflow contract or
   pass criteria changed.

If the bug requires an external dependency, add a deterministic unit or fake
subprocess test first, then add an explicitly marked integration test if needed.

## Release Readiness Gates

Before a release or public demo, the following must be true:

- `uv run pytest` passes.
- `uv run ruff check .` passes.
- `uv run opennavier --help` renders.
- The currently supported canonical workflow evals are run or explicitly marked
  blocked with the reason.
- Documentation states which parts of the complete workflow are implemented and
  which are not.
- Any screenshots, reports, or benchmark outputs were produced locally and can
  be regenerated.

## Current Gaps

The main gaps between the current codebase and this evaluation framework are:

- No named workflow eval command or script exists yet.
- No CLI command wires the local runner into `opennavier run`.
- No canonical run artifact directory convention exists yet.
- No real OpenFOAM integration eval is defined or marked.
- No ParaView or post-processing eval exists.
- No spec-to-case planner eval exists.
- No AI prompt eval set exists.
- No Studio edit-loop eval exists.

The next high-leverage evaluation milestone is EVAL-CAVITY-RUN: one complete
local cavity workflow that produces logs, diagnostics, a report, and a manifest.
