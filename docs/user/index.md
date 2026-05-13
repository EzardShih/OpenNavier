---
title: OpenNavier User Guide
permalink: /
---

# OpenNavier User Guide

OpenNavier is a local-first OpenFOAM automation and diagnostics toolkit. It helps
you inspect OpenFOAM cases, generate supported starter cases, run explicit solver
commands, parse logs, and produce auditable local reports.

The current product is an early developer-facing CLI and MCP tool surface. It is
not yet a full desktop simulation workspace, and it does not run an autonomous
AI agent over your files. The useful path today is deterministic and local:
prepare a supported case, validate it, run checks or a solver command, collect
diagnostics, and write reproducibility artifacts.

## What You Can Do Now

- Create a reference lid-driven cavity case.
- Validate required OpenFOAM case folders and dictionaries.
- Diagnose case structure, cavity boundary fields, mesh-quality logs, and solver
  residual logs.
- Run an explicit local or Docker-based solver command.
- Generate Markdown reports, diagnostics JSON, and reproducibility manifests.
- Use local MCP tools from IDE agents for workspace inspection, spec validation,
  case-build validation, dry-runs, writes, diagnostics, and report generation.

## Local-First By Default

OpenNavier is designed around inspectable local engineering work. Case files,
logs, reports, manifests, and diagnostics stay on your machine by default.
OpenNavier does not upload simulation geometry, mesh data, solver logs, or
results to a cloud service.

## Documentation Hosting

These pages are plain Markdown by design. They can be published directly with
GitBook, GitHub Pages, or later imported into an Astro-powered documentation
site.

Recommended first publishing targets:

- GitBook: use `docs/user/SUMMARY.md` as the navigation source.
- GitHub Pages: publish the `docs/user/` directory as Markdown pages.
- Astro later: import each file as a documentation content entry and preserve
  the same page order.
