# OpenNavier

OpenNavier is a local-first OpenFOAM automation and diagnostics CLI. The initial
slice focuses on deterministic case inspection and Markdown reports before any
solver execution, generated dictionaries, desktop UI, or AI planning is added.

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

## CLI

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

The first validator checks for required OpenFOAM case paths:

- `0`
- `constant`
- `system`
- `system/controlDict`
- `system/fvSchemes`
- `system/fvSolution`

It reports missing paths without modifying the case.
