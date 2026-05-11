import json
from pathlib import Path

from opennavier.mcp.paths import (
    WorkspacePathError,
    resolve_workspace_path,
    resolve_workspace_root,
)
from opennavier.openfoam.boundary_conditions import diagnose_boundary_conditions
from opennavier.openfoam.case_build_writer import CaseBuildWriteError, write_case_build_spec
from opennavier.openfoam.case_structure import validate_case_structure
from opennavier.openfoam.init_case import CasePathNotEmptyError
from opennavier_core.case_build_spec import (
    CaseBuildCapabilityError,
    CaseBuildSpec,
    case_build_spec_to_json,
    create_case_build_dry_run,
)
from opennavier_core.diagnostics import DiagnosticResult, DiagnosticStatus
from pydantic import ValidationError


def case_build_validate(
    workspace_root: str,
    build_spec_path: str = "specs/case-build.json",
    build_spec: dict[str, object] | None = None,
) -> dict[str, object]:
    validated = _validated_spec(
        workspace_root=workspace_root,
        build_spec_path=build_spec_path,
        build_spec=build_spec,
    )
    if validated["spec"] is None:
        return {
            "valid": False,
            "case_build_spec": None,
            "errors": validated["errors"],
            "source": validated["source"],
        }

    spec = validated["spec"]
    assert isinstance(spec, CaseBuildSpec)
    return {
        "valid": True,
        "case_build_spec": spec.model_dump(mode="json"),
        "errors": [],
        "source": validated["source"],
    }


def case_build_dry_run(
    workspace_root: str,
    build_spec_path: str = "specs/case-build.json",
    build_spec: dict[str, object] | None = None,
) -> dict[str, object]:
    validated = _validated_spec(
        workspace_root=workspace_root,
        build_spec_path=build_spec_path,
        build_spec=build_spec,
    )
    if validated["spec"] is None:
        return {
            "valid": False,
            "dry_run": None,
            "errors": validated["errors"],
            "source": validated["source"],
        }

    spec = validated["spec"]
    assert isinstance(spec, CaseBuildSpec)
    try:
        dry_run = create_case_build_dry_run(spec)
    except CaseBuildCapabilityError as error:
        return {
            "valid": False,
            "dry_run": None,
            "errors": [
                {
                    "type": "capability_error",
                    "message": _join_issue_messages(error.issues),
                }
            ],
            "source": validated["source"],
        }
    return {
        "valid": True,
        "dry_run": dry_run.model_dump(mode="json"),
        "errors": [],
        "source": validated["source"],
    }


def case_build_write(
    workspace_root: str,
    build_spec_path: str = "specs/case-build.json",
    build_spec: dict[str, object] | None = None,
    force: bool = False,
    persist_build_spec: bool = False,
) -> dict[str, object]:
    provenance = {"producer": "case_build_write", "inputs": []}
    next_actions = ["case_validate_structure", "diagnostics_residuals"]
    validated = _validated_spec(
        workspace_root=workspace_root,
        build_spec_path=build_spec_path,
        build_spec=build_spec,
    )
    source = str(validated["source"])
    provenance["inputs"] = [source]

    if validated["spec"] is None:
        return {
            "changed_paths": [],
            "diagnostics": [
                _failure_diagnostic(
                    code="mcp.case_build_spec.invalid",
                    message=_join_error_messages(validated["errors"]),
                    path=source,
                )
            ],
            "provenance": provenance,
            "next_actions": next_actions,
        }

    spec = validated["spec"]
    assert isinstance(spec, CaseBuildSpec)
    try:
        root = resolve_workspace_root(workspace_root)
        persist_target = _prepare_persisted_spec_target(
            root=root,
            build_spec_path=build_spec_path,
            spec=spec,
            persist_build_spec=persist_build_spec and build_spec is not None,
        )
        resolved_case_path = write_case_build_spec(spec, root, force=force)
    except WorkspacePathError as error:
        return _write_failure(
            code="mcp.workspace_path.invalid",
            message=str(error),
            path=str(workspace_root),
            provenance=provenance,
            next_actions=next_actions,
        )
    except (CasePathNotEmptyError, CaseBuildWriteError) as error:
        return _write_failure(
            code="mcp.case_build_write.refused",
            message=str(error),
            path=spec.case_path,
            provenance=provenance,
            next_actions=next_actions,
        )

    changed_paths = _case_file_paths(root=root, case_path=resolved_case_path)
    if persist_target is not None:
        persist_target.parent.mkdir(parents=True, exist_ok=True)
        persist_target.write_text(case_build_spec_to_json(spec), encoding="utf-8")
        changed_paths.append(persist_target.relative_to(root).as_posix())
        changed_paths = sorted(changed_paths)
    diagnostics = [
        diagnostic.model_dump(mode="json")
        for diagnostic in _run_declared_validators(spec, resolved_case_path)
    ]
    return {
        "changed_paths": changed_paths,
        "diagnostics": diagnostics,
        "provenance": provenance,
        "next_actions": next_actions,
    }


def _validated_spec(
    *,
    workspace_root: str,
    build_spec_path: str,
    build_spec: dict[str, object] | None,
) -> dict[str, object]:
    source = "payload" if build_spec is not None else build_spec_path
    try:
        root = resolve_workspace_root(workspace_root)
    except WorkspacePathError as error:
        return _invalid(source=source, error_type="workspace_path_error", message=str(error))

    if build_spec is None:
        try:
            resolved_spec_path = resolve_workspace_path(root, build_spec_path)
            payload = json.loads(resolved_spec_path.read_text(encoding="utf-8"))
        except WorkspacePathError as error:
            return _invalid(source=source, error_type="workspace_path_error", message=str(error))
        except json.JSONDecodeError:
            return _invalid(
                source=source,
                error_type="json_decode_error",
                message=f"Malformed JSON in {build_spec_path}",
            )
        except (OSError, UnicodeError) as error:
            return _invalid(
                source=source,
                error_type="file_read_error",
                message=f"Could not read case-build spec file {build_spec_path}: "
                f"{type(error).__name__}",
            )
    else:
        payload = build_spec

    try:
        spec = CaseBuildSpec.model_validate(payload)
        resolve_workspace_path(root, spec.case_path)
    except ValidationError as error:
        return {
            "spec": None,
            "errors": [
                {"type": "validation_error", "message": _validation_message(item)}
                for item in error.errors()
            ],
            "source": source,
        }
    except WorkspacePathError as error:
        return _invalid(source=source, error_type="workspace_path_error", message=str(error))

    return {"spec": spec, "errors": [], "source": source}


def _invalid(*, source: str, error_type: str, message: str) -> dict[str, object]:
    return {
        "spec": None,
        "errors": [{"type": error_type, "message": message}],
        "source": source,
    }


def _validation_message(error: dict[str, object]) -> str:
    location = ".".join(str(part) for part in error.get("loc", ()))
    message = str(error.get("msg", "Validation error"))
    if location:
        return f"{location}: {message}"
    return message


def _case_file_paths(*, root: Path, case_path: Path) -> list[str]:
    return sorted(
        path.relative_to(root).as_posix()
        for path in case_path.rglob("*")
        if path.is_file()
    )


def _prepare_persisted_spec_target(
    *,
    root: Path,
    build_spec_path: str,
    spec: CaseBuildSpec,
    persist_build_spec: bool,
) -> Path | None:
    if not persist_build_spec:
        return None

    target = resolve_workspace_path(root, build_spec_path)
    if target.exists() and target.is_dir():
        raise CaseBuildWriteError(f"Refusing to overwrite directory: {build_spec_path}")

    generated_case_files = _planned_generated_case_files(root=root, spec=spec)
    if target in generated_case_files:
        relative_target = target.relative_to(root).as_posix()
        raise CaseBuildWriteError(
            "Refusing to persist case-build spec over generated case file: "
            f"{relative_target}"
        )

    generated_case_directories = _planned_generated_case_directories(
        root=root,
        generated_case_files=generated_case_files,
    )
    if target in generated_case_directories:
        relative_target = target.relative_to(root).as_posix()
        raise CaseBuildWriteError(
            "Refusing to persist case-build spec over generated case directory: "
            f"{relative_target}"
        )

    for parent in _workspace_parent_chain(root=root, path=target.parent):
        if parent in generated_case_files:
            relative_parent = parent.relative_to(root).as_posix()
            raise CaseBuildWriteError(
                "Refusing to persist case-build spec under generated case file: "
                f"{relative_parent}"
            )
        if parent.exists() and not parent.is_dir():
            relative_parent = parent.relative_to(root).as_posix()
            raise CaseBuildWriteError(
                "Refusing to persist case-build spec because parent is not a "
                f"directory: {relative_parent}"
            )

    desired = case_build_spec_to_json(spec)
    if target.exists():
        try:
            existing = target.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise CaseBuildWriteError(
                f"Could not inspect existing case-build spec: {build_spec_path}"
            ) from error
        if existing != desired:
            raise CaseBuildWriteError(
                f"Refusing to overwrite existing case-build spec: {build_spec_path}"
            )
        return None

    return target


def _planned_generated_case_directories(
    *,
    root: Path,
    generated_case_files: set[Path],
) -> set[Path]:
    directories: set[Path] = set()
    for path in generated_case_files:
        for parent in _workspace_parent_chain(root=root, path=path.parent):
            if parent == root:
                continue
            directories.add(parent)
    return directories


def _workspace_parent_chain(*, root: Path, path: Path) -> list[Path]:
    parents: list[Path] = []
    current = path
    while True:
        current.relative_to(root)
        parents.append(current)
        if current == root:
            return parents
        current = current.parent


def _planned_generated_case_files(*, root: Path, spec: CaseBuildSpec) -> set[Path]:
    try:
        dry_run = create_case_build_dry_run(spec)
    except CaseBuildCapabilityError as error:
        raise CaseBuildWriteError(_join_issue_messages(error.issues)) from error

    return {
        resolve_workspace_path(root, operation.path)
        for operation in dry_run.file_operations
    }


def _run_declared_validators(spec: CaseBuildSpec, case_path: Path) -> list[DiagnosticResult]:
    diagnostics: list[DiagnosticResult] = []
    for validator in spec.validators:
        if validator.name == "case_structure":
            diagnostics.extend(validate_case_structure(case_path))
        elif validator.name == "boundary_conditions":
            diagnostics.extend(diagnose_boundary_conditions(case_path))
        else:
            raise CaseBuildWriteError(
                f"Unsupported case-build validator: {validator.name}"
            )
    return diagnostics


def _failure_diagnostic(*, code: str, message: str, path: str) -> dict[str, object]:
    return DiagnosticResult(
        status=DiagnosticStatus.FAIL,
        code=code,
        message=message,
        path=path,
    ).model_dump(mode="json")


def _write_failure(
    *,
    code: str,
    message: str,
    path: str,
    provenance: dict[str, object],
    next_actions: list[str],
) -> dict[str, object]:
    return {
        "changed_paths": [],
        "diagnostics": [_failure_diagnostic(code=code, message=message, path=path)],
        "provenance": provenance,
        "next_actions": next_actions,
    }


def _join_error_messages(errors: object) -> str:
    if not isinstance(errors, list):
        return "Invalid case-build spec."
    messages: list[str] = []
    for error in errors:
        if isinstance(error, dict) and "message" in error:
            messages.append(str(error["message"]))
    return "; ".join(messages) or "Invalid case-build spec."


def _join_issue_messages(issues: object) -> str:
    if not isinstance(issues, list):
        return "Unsupported case-build capability."
    messages: list[str] = []
    for issue in issues:
        if hasattr(issue, "message"):
            messages.append(str(issue.message))
    return "; ".join(messages) or "Unsupported case-build capability."
