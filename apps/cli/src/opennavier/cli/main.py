import json
from pathlib import Path
from typing import Annotated, Literal

import typer
from opennavier.cli.reporting import write_markdown_report
from opennavier.openfoam.case_structure import validate_case_structure
from opennavier_core.diagnostics import DiagnosticResult, has_failures

app = typer.Typer(
    help="Local-first OpenFOAM automation and diagnostics.",
    no_args_is_help=True,
)


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
) -> None:
    """Inspect a case and summarize likely setup issues."""
    diagnostics = validate_case_structure(case_path)
    _print_diagnostics(diagnostics, output_format=output_format)

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
) -> None:
    """Generate a deterministic Markdown report for a case inspection."""
    diagnostics = validate_case_structure(case_path)
    report_path = write_markdown_report(
        case_path=case_path,
        diagnostics=diagnostics,
        output_path=output,
    )
    typer.echo(f"Wrote report: {report_path}")

    if has_failures(diagnostics):
        raise typer.Exit(code=1)


def _print_diagnostics(
    diagnostics: list[DiagnosticResult], *, output_format: Literal["text", "json"] = "text"
) -> None:
    if output_format == "json":
        typer.echo(json.dumps([diagnostic.model_dump(mode="json") for diagnostic in diagnostics]))
        return

    for diagnostic in diagnostics:
        typer.echo(f"{diagnostic.status.value} {diagnostic.code} {diagnostic.message}")
