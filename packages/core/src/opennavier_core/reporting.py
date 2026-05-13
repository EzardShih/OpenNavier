from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Template

from opennavier_core.diagnostics import DiagnosticResult, DiagnosticStatus


@dataclass(frozen=True)
class ReportVisualAsset:
    label: str
    screenshot_path: Path | str | None = None
    script_path: Path | str | None = None
    log_path: Path | str | None = None


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

## Visual Assets

{% if visual_assets -%}
{% for asset in visual_assets -%}
### {{ asset.label }}

{% if asset.screenshot_exists -%}
![{{ asset.label }}]({{ asset.screenshot_path }})
{% elif asset.screenshot_path -%}
Screenshot not available: `{{ asset.screenshot_path }}`
{% else -%}
Screenshot not requested.
{% endif %}
{% if asset.script_path -%}
- ParaView script: `{{ asset.script_path }}`
{% endif -%}
{% if asset.log_path %}
- ParaView log: `{{ asset.log_path }}`
{% endif %}
{% endfor %}
{% else -%}
No visual assets were provided.
{% endif %}

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
    visual_assets: list[ReportVisualAsset] | None = None,
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
        visual_assets=_visual_asset_context(visual_assets or []),
        passed_count=sum(
            diagnostic.status is DiagnosticStatus.PASS for diagnostic in diagnostics
        ),
        warning_count=len(warnings),
        failed_count=len(failures),
    )
    output.write_text(content, encoding="utf-8")
    return output


def _visual_asset_context(
    visual_assets: list[ReportVisualAsset],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for asset in visual_assets:
        screenshot_path = _optional_path(asset.screenshot_path)
        rows.append(
            {
                "label": asset.label,
                "screenshot_path": None if screenshot_path is None else str(screenshot_path),
                "screenshot_exists": (
                    False if screenshot_path is None else screenshot_path.is_file()
                ),
                "script_path": _optional_path_string(asset.script_path),
                "log_path": _optional_path_string(asset.log_path),
            }
        )
    return rows


def _optional_path(value: Path | str | None) -> Path | None:
    if value is None:
        return None
    return Path(value)


def _optional_path_string(value: Path | str | None) -> str | None:
    path = _optional_path(value)
    return None if path is None else str(path)
