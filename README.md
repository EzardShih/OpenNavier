# OpenNavier

OpenNavier is a local-first OpenFOAM automation and diagnostics CLI. The initial
slice focuses on deterministic starter cases, case inspection, Markdown reports,
tested local runner building blocks, tool adapters, and an initial desktop
scaffold before a full solver CLI workflow or AI planning is added.

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

The `apps/studio` directory is a Tauri + React scaffold. The Python validation
suite inspects its deterministic project files; it does not install npm
dependencies or build the desktop app yet.

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
- `case_init_cavity`
- `case_validate_structure`
- `diagnostics_residuals`

Tools operate inside an explicit workspace root and use the same validated core
and OpenFOAM package APIs as the CLI.

## CLI

Create a starter lid-driven cavity case:

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

Generate a Markdown report:

```bash
opennavier report ./examples/cavity --output report.md
```

Generate the report with a reproducibility manifest:

```bash
opennavier report ./examples/cavity --output report.md --manifest-output manifest.json
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
