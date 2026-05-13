---
title: MCP Tools
permalink: /mcp-tools/
---

# MCP Tools

OpenNavier exposes a local MCP stdio server for IDE agents and other local
automation clients.

Start the server with:

```bash
uv run opennavier-mcp
```

The MCP surface is deterministic and file-oriented. Tools operate inside an
explicit workspace root and call the same package APIs used by the CLI.

## Available Tool Areas

- Workspace inspection
- Simulation spec validation
- Case-build validation
- Case-build dry-runs
- Case-build writes
- Case structure validation
- Residual diagnostics
- Mesh-quality diagnostics
- Full case diagnostics
- Diagnostics artifact writing
- Report generation

Representative tools include:

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

## Safety Model

MCP tools are thin wrappers over deterministic local APIs. They are not a
separate execution path for arbitrary file edits or shell commands.

Important constraints:

- every tool is scoped to an explicit workspace root
- raw OpenFOAM dictionary blobs are rejected as case-build input
- case writes go through typed `CaseBuildSpec` validation
- dry-run output is available before writing files
- paths that escape the workspace are refused

## When To Use MCP Instead Of CLI

Use the CLI when you are running commands directly in a terminal.

Use MCP when an IDE agent or local automation client needs structured access to
OpenNavier capabilities, especially when you want typed results instead of
terminal text.
