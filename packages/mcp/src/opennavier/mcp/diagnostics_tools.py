from opennavier.mcp.paths import WorkspacePathError, resolve_workspace_path
from opennavier.openfoam.residuals import diagnose_residuals, parse_residuals
from opennavier_core.diagnostics import DiagnosticResult, DiagnosticStatus


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


def _json_dump(record: object) -> dict[str, object]:
    return record.model_dump(mode="json")
