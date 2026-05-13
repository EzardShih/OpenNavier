from opennavier.mcp.paths import WorkspacePathError, resolve_workspace_path
from opennavier.openfoam.diagnostics import collect_case_diagnostics
from opennavier.openfoam.mesh_quality import diagnose_mesh_quality, parse_check_mesh
from opennavier.openfoam.residuals import diagnose_residuals, parse_residuals
from opennavier_core.diagnostic_artifact import write_diagnostics_artifact
from opennavier_core.diagnostics import DiagnosticResult, DiagnosticStatus
from opennavier_core.manifest import write_reproducibility_manifest
from opennavier_core.reporting import write_markdown_report


def diagnostics_residuals(workspace_root: str, log_path: str) -> dict[str, object]:
    try:
        resolved_log_path = resolve_workspace_path(workspace_root, log_path)
    except WorkspacePathError:
        return _diagnostics_result(
            log_path,
            [],
            DiagnosticResult(
                status=DiagnosticStatus.FAIL,
                code="mcp.workspace_path.invalid",
                message=f"Path must stay inside the workspace root: {log_path}",
                path=log_path,
                details={},
            ),
        )

    try:
        content = resolved_log_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        return _diagnostics_result(
            log_path,
            [],
            DiagnosticResult(
                status=DiagnosticStatus.FAIL,
                code="mcp.log.unreadable",
                message=f"Could not read solver log: {log_path}",
                path=log_path,
                details={"read_error": type(error).__name__},
            ),
        )

    records = parse_residuals(content)
    diagnostic = diagnose_residuals(records).model_copy(update={"path": log_path})
    return _diagnostics_result(log_path, records, diagnostic)


def diagnostics_mesh_quality(workspace_root: str, log_path: str) -> dict[str, object]:
    try:
        resolved_log_path = resolve_workspace_path(workspace_root, log_path)
    except WorkspacePathError:
        return {
            "log_path": log_path,
            "summary": None,
            "diagnostic": _workspace_path_failure(log_path).model_dump(mode="json"),
        }

    try:
        content = resolved_log_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        return {
            "log_path": log_path,
            "summary": None,
            "diagnostic": DiagnosticResult(
                status=DiagnosticStatus.FAIL,
                code="mcp.log.unreadable",
                message=f"Could not read checkMesh log: {log_path}",
                path=log_path,
                details={"read_error": type(error).__name__},
            ).model_dump(mode="json"),
        }

    summary = parse_check_mesh(content)
    diagnostic = diagnose_mesh_quality(summary).model_copy(update={"path": log_path})
    return {
        "log_path": log_path,
        "summary": summary.model_dump(mode="json"),
        "diagnostic": diagnostic.model_dump(mode="json"),
    }


def diagnostics_case(workspace_root: str, case_path: str) -> dict[str, object]:
    try:
        resolved_case_path = resolve_workspace_path(workspace_root, case_path)
    except WorkspacePathError:
        return {
            "case_path": case_path,
            "diagnostics": [_workspace_path_failure(case_path).model_dump(mode="json")],
        }

    return {
        "case_path": case_path,
        "diagnostics": [
            diagnostic.model_dump(mode="json")
            for diagnostic in collect_case_diagnostics(resolved_case_path)
        ],
    }


def diagnostics_artifact(
    workspace_root: str,
    case_path: str,
    diagnostics_output_path: str,
) -> dict[str, object]:
    try:
        resolved_case_path = resolve_workspace_path(workspace_root, case_path)
    except WorkspacePathError:
        return _diagnostics_artifact_failure(
            case_path=case_path,
            diagnostics_output_path=diagnostics_output_path,
            failure_path=case_path,
        )

    try:
        resolved_output_path = resolve_workspace_path(workspace_root, diagnostics_output_path)
    except WorkspacePathError:
        return _diagnostics_artifact_failure(
            case_path=case_path,
            diagnostics_output_path=diagnostics_output_path,
            failure_path=diagnostics_output_path,
        )

    diagnostics = collect_case_diagnostics(resolved_case_path)
    write_diagnostics_artifact(diagnostics, resolved_output_path)
    return {
        "case_path": case_path,
        "diagnostics_output": diagnostics_output_path,
        "diagnostics": [diagnostic.model_dump(mode="json") for diagnostic in diagnostics],
    }


def report_generate(
    workspace_root: str,
    case_path: str,
    report_output_path: str,
    manifest_output_path: str | None = None,
) -> dict[str, object]:
    try:
        resolved_case_path = resolve_workspace_path(workspace_root, case_path)
    except WorkspacePathError:
        return _report_generate_failure(
            case_path=case_path,
            report_output_path=report_output_path,
            manifest_output_path=manifest_output_path,
            failure_path=case_path,
        )

    try:
        resolved_report_path = resolve_workspace_path(workspace_root, report_output_path)
    except WorkspacePathError:
        return _report_generate_failure(
            case_path=case_path,
            report_output_path=report_output_path,
            manifest_output_path=manifest_output_path,
            failure_path=report_output_path,
        )

    try:
        resolved_manifest_path = (
            None
            if manifest_output_path is None
            else resolve_workspace_path(workspace_root, manifest_output_path)
        )
    except WorkspacePathError:
        return _report_generate_failure(
            case_path=case_path,
            report_output_path=report_output_path,
            manifest_output_path=manifest_output_path,
            failure_path=str(manifest_output_path),
        )

    if resolved_manifest_path is not None and resolved_report_path == resolved_manifest_path:
        return _report_generate_path_conflict_failure(
            case_path=case_path,
            report_output_path=report_output_path,
            manifest_output_path=manifest_output_path,
        )

    diagnostics = collect_case_diagnostics(resolved_case_path)
    write_markdown_report(
        case_path=resolved_case_path,
        diagnostics=diagnostics,
        output_path=resolved_report_path,
    )
    if resolved_manifest_path is not None:
        write_reproducibility_manifest(
            case_path=resolved_case_path,
            diagnostics=diagnostics,
            generated_artifacts=[resolved_report_path],
            output_path=resolved_manifest_path,
        )

    return {
        "case_path": case_path,
        "report_path": report_output_path,
        "manifest_path": manifest_output_path,
        "diagnostics": [diagnostic.model_dump(mode="json") for diagnostic in diagnostics],
    }


def _diagnostics_result(
    log_path: str,
    records: list[object],
    diagnostic: DiagnosticResult,
) -> dict[str, object]:
    return {
        "log_path": log_path,
        "records": [_json_dump(record) for record in records],
        "diagnostic": diagnostic.model_dump(mode="json"),
    }


def _diagnostics_artifact_failure(
    *,
    case_path: str,
    diagnostics_output_path: str,
    failure_path: str,
) -> dict[str, object]:
    diagnostic = _workspace_path_failure(failure_path)
    return {
        "case_path": case_path,
        "diagnostics_output": diagnostics_output_path,
        "diagnostics": [diagnostic.model_dump(mode="json")],
    }


def _report_generate_failure(
    *,
    case_path: str,
    report_output_path: str,
    manifest_output_path: str | None,
    failure_path: str,
) -> dict[str, object]:
    diagnostic = _workspace_path_failure(failure_path)
    return {
        "case_path": case_path,
        "report_path": report_output_path,
        "manifest_path": manifest_output_path,
        "diagnostics": [diagnostic.model_dump(mode="json")],
    }


def _report_generate_path_conflict_failure(
    *,
    case_path: str,
    report_output_path: str,
    manifest_output_path: str,
) -> dict[str, object]:
    diagnostic = DiagnosticResult(
        status=DiagnosticStatus.FAIL,
        code="mcp.artifact_path.conflict",
        message=(
            "report_output_path and manifest_output_path must be different: "
            f"{report_output_path}"
        ),
        path=report_output_path,
        details={},
    )
    return {
        "case_path": case_path,
        "report_path": report_output_path,
        "manifest_path": manifest_output_path,
        "diagnostics": [diagnostic.model_dump(mode="json")],
    }


def _json_dump(record: object) -> dict[str, object]:
    return record.model_dump(mode="json")


def _workspace_path_failure(path: str) -> DiagnosticResult:
    return DiagnosticResult(
        status=DiagnosticStatus.FAIL,
        code="mcp.workspace_path.invalid",
        message=f"Path must stay inside the workspace root: {path}",
        path=path,
        details={},
    )
