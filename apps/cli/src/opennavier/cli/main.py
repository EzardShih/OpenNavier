import json
from pathlib import Path
from typing import Annotated, Literal

import typer
from opennavier.cli.reporting import write_markdown_report
from opennavier.openfoam.case_structure import validate_case_structure
from opennavier.openfoam.diagnostics import collect_case_diagnostics
from opennavier.openfoam.init_case import CasePathNotEmptyError, create_cavity_case
from opennavier_core.diagnostic_artifact import write_diagnostics_artifact
from opennavier_core.diagnostics import DiagnosticResult, has_failures
from opennavier_core.manifest import write_reproducibility_manifest

app = typer.Typer(
    help="Local-first OpenFOAM automation and diagnostics.",
    no_args_is_help=True,
)
init_app = typer.Typer(help="Create deterministic starter OpenFOAM cases.")
app.add_typer(init_app, name="init")


@init_app.command()
def cavity(
    case_path: Annotated[Path, typer.Argument(help="Case directory to create.")],
    force: Annotated[
        bool,
        typer.Option("--force", help="Overwrite an existing non-empty case path."),
    ] = False,
) -> None:
    """Create a minimal OpenFOAM lid-driven cavity case."""
    try:
        created_path = create_cavity_case(case_path, force=force)
    except CasePathNotEmptyError as error:
        typer.echo(str(error))
        raise typer.Exit(code=1) from error

    typer.echo(f"Created cavity case: {created_path}")


@app.command()
def check(
    case_path: Annotated[Path, typer.Argument(help="OpenFOAM case directory.")],
    output_format: Annotated[
        Literal["text", "json"],
        typer.Option("--format", help="Diagnostic output format."),
    ] = "text",
) -> None:
    """Validate required OpenFOAM case folders and dictionaries."""
    diagnostics = validate_case_structure(case_path)
    _print_diagnostics(diagnostics, output_format=output_format)

    if has_failures(diagnostics):
        raise typer.Exit(code=1)

    if output_format == "text":
        typer.echo("Case structure checks passed.")


@app.command()
def doctor(
    case_path: Annotated[Path, typer.Argument(help="OpenFOAM case directory.")],
    output_format: Annotated[
        Literal["text", "json"],
        typer.Option("--format", help="Diagnostic output format."),
    ] = "text",
    diagnostics_output: Annotated[
        Path | None,
        typer.Option("--diagnostics-output", help="Diagnostics artifact JSON path."),
    ] = None,
) -> None:
    """Inspect a case and summarize likely setup issues."""
    diagnostics = collect_case_diagnostics(case_path)
    _print_diagnostics(diagnostics, output_format=output_format)
    _write_optional_diagnostics_artifact(
        diagnostics,
        diagnostics_output=diagnostics_output,
        output_format=output_format,
    )

    if has_failures(diagnostics):
        if output_format == "text":
            typer.echo("")
            typer.echo("Likely issues:")
            typer.echo("- OpenFOAM case structure is incomplete.")
            typer.echo(
                "- Add missing required directories and system dictionaries before running solvers."
            )
        raise typer.Exit(code=1)

    if output_format == "text":
        typer.echo("")
        typer.echo("No blocking case-structure issues found.")


@app.command()
def report(
    case_path: Annotated[Path, typer.Argument(help="OpenFOAM case directory.")],
    output: Annotated[Path, typer.Option("--output", "-o", help="Markdown report path.")] = Path(
        "report.md"
    ),
    manifest_output: Annotated[
        Path | None,
        typer.Option("--manifest-output", help="Reproducibility manifest JSON path."),
    ] = None,
    diagnostics_output: Annotated[
        Path | None,
        typer.Option("--diagnostics-output", help="Diagnostics artifact JSON path."),
    ] = None,
) -> None:
    """Generate a deterministic Markdown report for a case inspection."""
    _validate_distinct_artifact_paths(
        output=output,
        manifest_output=manifest_output,
        diagnostics_output=diagnostics_output,
    )

    diagnostics = collect_case_diagnostics(case_path)
    report_path = write_markdown_report(
        case_path=case_path,
        diagnostics=diagnostics,
        output_path=output,
    )
    typer.echo(f"Wrote report: {report_path}")
    if manifest_output is not None:
        manifest_path = write_reproducibility_manifest(
            case_path=case_path,
            diagnostics=diagnostics,
            generated_artifacts=[report_path],
            output_path=manifest_output,
        )
        typer.echo(f"Wrote manifest: {manifest_path}")
    _write_optional_diagnostics_artifact(
        diagnostics,
        diagnostics_output=diagnostics_output,
        output_format="text",
    )

    if has_failures(diagnostics):
        raise typer.Exit(code=1)


def _validate_distinct_artifact_paths(
    *,
    output: Path,
    manifest_output: Path | None,
    diagnostics_output: Path | None,
) -> None:
    artifact_paths = [
        ("--output", output),
        *([] if manifest_output is None else [("--manifest-output", manifest_output)]),
        *([] if diagnostics_output is None else [("--diagnostics-output", diagnostics_output)]),
    ]
    resolved_paths: dict[Path, str] = {}
    for param_hint, path in artifact_paths:
        resolved = path.resolve()
        if resolved in resolved_paths:
            first_param_hint = resolved_paths[resolved]
            raise typer.BadParameter(
                f"{param_hint} must be different from {first_param_hint}.",
                param_hint=param_hint,
            )
        resolved_paths[resolved] = param_hint


def _write_optional_diagnostics_artifact(
    diagnostics: list[DiagnosticResult],
    *,
    diagnostics_output: Path | None,
    output_format: Literal["text", "json"],
) -> None:
    if diagnostics_output is None:
        return

    artifact_path = write_diagnostics_artifact(diagnostics, diagnostics_output)
    if output_format == "text":
        typer.echo(f"Wrote diagnostics: {artifact_path}")

def _print_diagnostics(
    diagnostics: list[DiagnosticResult], *, output_format: Literal["text", "json"] = "text"
) -> None:
    if output_format == "json":
        typer.echo(json.dumps([diagnostic.model_dump(mode="json") for diagnostic in diagnostics]))
        return

    for diagnostic in diagnostics:
        typer.echo(f"{diagnostic.status.value} {diagnostic.code} {diagnostic.message}")
