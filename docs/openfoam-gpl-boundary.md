# OpenFOAM GPL Boundary Policy

This document is an engineering and packaging policy for keeping OpenNavier
separate from OpenFOAM's GPL-covered code. It is not legal advice. Before a
commercial release, binary distribution, appliance image, hosted runner, or
enterprise deployment, review the exact package with counsel.

## Product Position

OpenNavier is an orchestration, validation, reporting, and user-interface layer
for simulation workflows. OpenFOAM is an external solver that users install,
select, and run locally. OpenNavier must not be described, packaged, or built as
a modified OpenFOAM distribution unless the release is intentionally GPL
compliant.

The safe default architecture is:

```text
OpenNavier process
  -> writes user-owned case files and logs
  -> invokes OpenFOAM command-line tools by subprocess
  -> parses files, logs, and reports
  -> never links to OpenFOAM libraries
```

## Baseline Facts

- The OpenFOAM Foundation says OpenFOAM is licensed under the GNU General Public
  Licence and that GPL-covered source included in another software product can
  cause GPL inheritance for that included code path.
- GPLv3 permits running unmodified GPL programs. Obligations become much more
  important when conveying or distributing GPL-covered source or object code.
- The FSF GPL FAQ treats command-line arguments, pipes, and sockets as normal
  communication mechanisms between separate programs, while linking modules in a
  shared executable or shared address space is much more likely to create one
  combined program.
- Containers do not automatically solve this. The FSF FAQ says the analysis of
  whether something is one work or an aggregate is unchanged by putting software
  in containers.
- OpenFOAM is also a trademark. Use the name descriptively, such as "works with
  OpenFOAM", not as if OpenNavier is an official OpenFOAM product.

Sources:

- https://openfoam.org/licence/
- https://www.gnu.org/licenses/gpl-3.0.en.html
- https://www.gnu.org/licenses/gpl-faq.html#MereAggregation
- https://www.gnu.org/licenses/gpl-faq.html#GPLPlugins
- https://www.gnu.org/licenses/gpl-faq.html#AggregateContainers
- https://cfd.direct/openfoam/about/

## Allowed Default Integration

Use OpenFOAM only through stable external process boundaries:

- Detect a user-installed OpenFOAM executable with `PATH`, environment variables,
  or explicit configuration.
- Invoke tools such as `blockMesh`, `checkMesh`, `simpleFoam`, `foamRun`,
  `postProcess`, and `foamToVTK` by subprocess.
- Pass ordinary command-line arguments, environment variables, and file paths.
- Write OpenFOAM case files that OpenNavier generated from original templates.
- Read and parse OpenFOAM dictionaries, logs, residual files, VTK files, and
  reports from the user's working directory.
- Store solver version, command, working directory, and exit code in manifests.
- Support multiple OpenFOAM variants through configuration instead of compiling
  against one specific source tree.

Implementation rule:

```python
subprocess.run(["checkMesh", "-case", str(case_path)], check=False)
```

is the preferred boundary.

Avoid turning OpenFOAM into an in-process dependency:

```text
OpenNavier -> OpenFOAM executable   OK default
OpenNavier -> libOpenFOAM.so        Not allowed without legal review
OpenNavier + copied OpenFOAM source Not allowed without GPL release review
```

## Prohibited Without Legal Review

Do not do these in normal OpenNavier development:

- Copy OpenFOAM source code, headers, solvers, utilities, or tutorial files into
  this repository.
- Translate OpenFOAM source code into Python, TypeScript, or another language.
- Link OpenNavier binaries against OpenFOAM libraries, including dynamic linking.
- Build a Python extension, C++ plugin, Rust crate, or Node native addon that
  includes OpenFOAM headers or links to OpenFOAM libraries.
- Patch OpenFOAM source and ship the patched solver as part of an OpenNavier
  release.
- Bundle OpenFOAM binaries inside the OpenNavier wheel, desktop app, installer,
  or proprietary distribution.
- Ship a Docker image, VM image, installer, or appliance containing OpenFOAM
  without a GPL compliance plan.
- Use the OpenFOAM logo or imply endorsement by the OpenFOAM Foundation,
  OpenCFD, CFD Direct, or Keysight/OpenCFD.
- Import license text or notices in a way that suggests OpenNavier itself is
  licensed under GPL unless that is an intentional project decision.

## Case Templates and Examples

OpenFOAM case dictionaries are text artifacts, but they can still be copyrighted
if copied from OpenFOAM tutorials or third-party examples. OpenNavier templates
must therefore be original works.

Template rules:

- Write templates from first principles based on OpenFOAM's public file formats
  and documented behavior.
- Keep generated dictionaries small, explicit, and traceable to OpenNavier
  simulation specs.
- Do not copy tutorial case files from an OpenFOAM installation.
- Do not copy comments, banners, long file headers, or exact tutorial structure
  unless the source license is reviewed and accepted.
- If a template is adapted from a GPL example, mark that template as GPL-derived
  and keep it out of proprietary packages.
- Prefer tests that assert behavior and required fields, not byte-for-byte copies
  of upstream OpenFOAM examples.

For current examples such as `examples/cavity`, keep the files original,
minimal, and generated by OpenNavier code. If we discover that any example was
copied from OpenFOAM tutorials, replace it with an original template or move it
into a clearly GPL-compatible example set.

## Packaging Policy

### Python Package or CLI

Recommended default:

- Publish OpenNavier as a Python package with no OpenFOAM binaries included.
- Declare OpenFOAM as an optional external system dependency.
- Provide `opennavier doctor` or `opennavier system-check` to detect solver
  availability and explain installation steps.
- Store all generated case and run artifacts outside source packages, for
  example under `runs/` or a user-selected workspace.

Do not package:

- OpenFOAM executables.
- OpenFOAM shared libraries.
- OpenFOAM source trees.
- Copied OpenFOAM tutorial cases.

### Desktop Application

Recommended default:

- Ship the desktop UI and Python orchestration engine only.
- Let users configure an existing OpenFOAM installation path.
- On first launch, show supported solver discovery paths and a link to upstream
  OpenFOAM installation docs.
- If the app can launch OpenFOAM commands, log the command and path clearly.

Do not embed OpenFOAM into the desktop installer unless the entire installer has
been reviewed for GPL compliance.

### Docker and Dev Containers

Lowest-risk default:

- Provide a Dockerfile or devcontainer recipe that users build themselves.
- Use upstream package repositories or upstream images during build.
- Keep OpenNavier and OpenFOAM as visibly separate components.

Higher-risk distribution:

- Publishing a prebuilt image containing OpenFOAM is distribution of GPL-covered
  object code. Before doing this, prepare source availability, license notices,
  version records, build scripts, and offer text required for GPL compliance.
- Do not assume "it is only a container" changes the GPL analysis.

### Cloud or Hosted Execution

OpenNavier's product direction is local-first. If a hosted runner is ever added:

- Treat hosted execution as a separate product review.
- Confirm whether users receive copies of GPL-covered binaries or only access a
  service.
- Keep OpenFOAM modifications isolated and documented.
- Do not upload CAD, mesh, logs, or results by default.
- Preserve user-visible solver version, command, input, and output manifests.

## Source and Dependency Hygiene

Every dependency added to OpenNavier must have a license review before release.

Allowed by default:

- Permissive Python dependencies such as MIT, BSD, Apache-2.0.
- LGPL libraries used through normal dynamic linking, only after review.
- External command-line tools invoked by subprocess.

Needs review:

- GPL, AGPL, SSPL, BUSL, PolyForm, Commons Clause, or custom licenses.
- Native extensions that link to GPL or LGPL libraries.
- SDKs that require cloud upload or telemetry.
- Example assets copied from upstream solver projects.

Repository rules:

- Keep a dependency license inventory before each release.
- Do not vendor source code unless its license is reviewed.
- Keep third-party notices in a dedicated file when distribution starts.
- Make generated artifacts easy to identify and keep them out of source packages.

## Practical Architecture Decisions

### Keep

- `packages/openfoam` as a subprocess, file-generation, parsing, diagnostics, and
  reporting package.
- Pydantic simulation specs as the canonical OpenNavier-owned API.
- Original Jinja2 templates or Python dictionary writers.
- CLI commands that make all solver actions visible.
- Manifests that record `openfoam_invocation`, `openfoam_version`, and
  `openfoam_installation_path` when known.

### Avoid

- A native C++ "OpenFOAM SDK" package inside OpenNavier.
- In-process solver APIs.
- Monkeypatching or modifying OpenFOAM installations.
- Hidden solver commands.
- LLM-generated raw dictionaries without deterministic validation.

## Distribution Checklist

Before any public release:

- [ ] Confirm no OpenFOAM source, headers, binaries, or copied tutorials are in
      the release artifact.
- [ ] Confirm OpenFOAM is documented as an external dependency.
- [ ] Confirm solver integration uses subprocess boundaries.
- [ ] Confirm installers do not bundle OpenFOAM.
- [ ] Confirm examples and templates are original or have reviewed provenance.
- [ ] Confirm `README.md` does not imply OpenNavier is endorsed by OpenFOAM.
- [ ] Confirm third-party dependency licenses are inventoried.
- [ ] Confirm generated reports and manifests identify solver versions without
      copying upstream source.
- [ ] If distributing Docker/VM images with OpenFOAM, complete GPL source,
      notices, and build-script compliance before publishing.

## Wording to Use

Good:

```text
OpenNavier is a local-first automation layer for OpenFOAM workflows.
OpenFOAM is installed separately and invoked through command-line tools.
```

Good:

```text
Works with user-installed OpenFOAM distributions.
```

Avoid:

```text
OpenNavier includes OpenFOAM.
```

Avoid:

```text
OpenNavier is an OpenFOAM distribution.
```

Avoid:

```text
Official OpenFOAM desktop app.
```

## If We Intentionally Ship OpenFOAM Later

Sometimes GPL compliance may be acceptable. If OpenNavier intentionally ships a
GPL-covered OpenFOAM component, do it explicitly:

- Separate the GPL-covered component in the repository and package layout.
- Include the GPL license text and upstream notices.
- Publish corresponding source for all GPL-covered binaries we convey.
- Publish build scripts and exact source revisions.
- Preserve user rights to inspect, modify, and rebuild the GPL-covered part.
- Do not mix proprietary OpenNavier code into the same linked work.
- Have counsel review whether the whole distributed artifact must be GPL.

This is not the default path. The default path is to keep OpenFOAM external and
interact with it through documented command-line boundaries.
