from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Template

from opennavier_core.diagnostics import DiagnosticResult, DiagnosticStatus

REPORT_TEMPLATE = Template(
    """# OpenNavier Case Report

Generated at: `{{ generated_at }}`

Inspected case: `{{ case_path }}`

## Validation Summary

- Passed checks: {{ passed_count }}
- Warning checks: {{ warning_count }}
- Failed checks: {{ failed_count }}

## Checks

{% for diagnostic in diagnostics -%}
- **{{ diagnostic.status.value }}** `{{ diagnostic.code }}`: {{ diagnostic.message }}
  - Path: `{{ diagnostic.path }}`
{% endfor %}

## Failed Checks

{% if failures -%}
{% for diagnostic in failures -%}
- `{{ diagnostic.code }}`: {{ diagnostic.message }}
{% endfor %}
{% else -%}
No failed checks.
{% endif %}

## Assumptions

- This report validates deterministic OpenFOAM case structure checks.
- Boundary-condition consistency is inspected when relevant dictionaries are present.
- Present optional OpenFOAM logs are parsed for mesh quality and residual diagnostics.
{% if openfoam_executed -%}
- OpenFOAM was executed locally.
{% else -%}
- OpenFOAM was not executed.
{% endif %}

## Reproducibility

- No cloud upload occurred.
- The inspected files stayed on the local machine.
- The validator reports missing paths without modifying the case.
"""
)


def write_markdown_report(
    *,
    case_path: Path | str,
    diagnostics: list[DiagnosticResult],
    output_path: Path | str,
    openfoam_executed: bool = False,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    failures = [
        diagnostic for diagnostic in diagnostics if diagnostic.status is DiagnosticStatus.FAIL
    ]
    warnings = [
        diagnostic for diagnostic in diagnostics if diagnostic.status is DiagnosticStatus.WARN
    ]
    content = REPORT_TEMPLATE.render(
        generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
        case_path=Path(case_path).resolve(),
        diagnostics=diagnostics,
        failures=failures,
        openfoam_executed=openfoam_executed,
        passed_count=sum(
            diagnostic.status is DiagnosticStatus.PASS for diagnostic in diagnostics
        ),
        warning_count=len(warnings),
        failed_count=len(failures),
    )
    output.write_text(content, encoding="utf-8")
    return output
