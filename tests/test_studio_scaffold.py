from __future__ import annotations

import json
from pathlib import Path

STUDIO_ROOT = Path("apps/studio")


def read_text(relative_path: str) -> str:
    return (STUDIO_ROOT / relative_path).read_text(encoding="utf-8")


def test_studio_scaffold_declares_tauri_react_project_files() -> None:
    expected_files = {
        "index.html",
        "package.json",
        "tsconfig.json",
        "vite.config.ts",
        "src/App.tsx",
        "src/contracts.ts",
        "src/main.tsx",
        "src/styles.css",
        "src-tauri/Cargo.toml",
        "src-tauri/build.rs",
        "src-tauri/src/main.rs",
        "src-tauri/tauri.conf.json",
    }

    for relative_path in expected_files:
        assert (STUDIO_ROOT / relative_path).is_file(), relative_path

    package_json = json.loads(read_text("package.json"))
    assert package_json["name"] == "@opennavier/studio"
    assert package_json["private"] is True
    assert package_json["scripts"]["dev"] == "tauri dev"
    assert package_json["scripts"]["web:dev"] == "vite --host 127.0.0.1"
    assert package_json["scripts"]["build"] == "tauri build"
    assert package_json["scripts"]["web:build"] == "vite build"
    assert package_json["scripts"]["preview"] == "vite preview"
    assert package_json["scripts"]["typecheck"] == "tsc --noEmit"
    assert package_json["dependencies"]["@tauri-apps/api"]
    assert package_json["dependencies"]["react"]
    assert package_json["dependencies"]["react-dom"]
    assert package_json["devDependencies"]["@tauri-apps/cli"]
    assert package_json["devDependencies"]["@vitejs/plugin-react"]
    assert package_json["devDependencies"]["@types/react"]
    assert package_json["devDependencies"]["@types/react-dom"]
    assert package_json["devDependencies"]["vite"]
    assert package_json["devDependencies"]["typescript"]

    tauri_config = json.loads(read_text("src-tauri/tauri.conf.json"))
    assert tauri_config["productName"] == "OpenNavier Studio"
    assert tauri_config["identifier"] == "dev.opennavier.studio"
    assert tauri_config["build"]["beforeDevCommand"] == "npm run web:dev"
    assert tauri_config["build"]["beforeBuildCommand"] == "npm run web:build"
    assert tauri_config["build"]["frontendDist"] == "../dist"
    assert tauri_config["build"]["devUrl"] == "http://localhost:5173"


def test_studio_typescript_config_uses_modern_vite_resolution() -> None:
    tsconfig = json.loads(read_text("tsconfig.json"))
    compiler_options = tsconfig["compilerOptions"]

    assert compiler_options["module"] == "ESNext"
    assert compiler_options["moduleResolution"] == "Bundler"
    assert "ignoreDeprecations" not in compiler_options


def test_studio_app_shows_local_engineering_tool_surface_first() -> None:
    app_source = read_text("src/App.tsx")

    expected_surface_labels = [
        "Project Dashboard",
        "Run Monitor",
        "Diagnostics",
        "Report Viewer",
        "Visible Commands",
        "Case Files",
        "Assumptions",
        "Check Status",
    ]
    for label in expected_surface_labels:
        assert label in app_source

    assert "No cloud upload" in app_source
    assert "Local OpenFOAM command" in app_source
    assert "opennavier doctor ./examples/cavity --diagnostics-output diagnostics.json" in app_source
    assert (
        "opennavier report ./examples/cavity --output report.md --manifest-output manifest.json"
        in app_source
    )
    assert "blockMeshDict" in app_source
    assert "controlDict" in app_source
    assert "fvSchemes" in app_source
    assert "fvSolution" in app_source


def test_studio_scaffold_avoids_cloud_and_marketing_language() -> None:
    combined_source = "\n".join(
        read_text(relative_path)
        for relative_path in [
            "package.json",
            "src/App.tsx",
            "src/main.tsx",
            "src/styles.css",
            "src-tauri/tauri.conf.json",
        ]
    ).lower()

    forbidden_terms = [
        "upload endpoint",
        "upload queue",
        "cloud sync",
        "saas",
        "landing page",
        "hero",
        "get started today",
    ]
    for term in forbidden_terms:
        assert term not in combined_source

    assert "local-first" in combined_source
    assert "engineer-verifiable" in combined_source


def test_studio_chat_request_bridge_uses_local_typed_contract() -> None:
    contracts_source = read_text("src/contracts.ts")
    app_source = read_text("src/App.tsx")

    for expected in [
        "StudioChatRequest",
        "buildStudioChatRequest",
        "requestText",
        "workspaceRoot",
        "selectedProvider",
        "localOnly: true",
        "approvalRequired: true",
        'source: "studio.chat"',
    ]:
        assert expected in contracts_source

    for expected in [
        "Engineering Request",
        "Provider",
        "Approval Prompts",
        "Structured Next Actions",
        "Validation Errors",
        "Clarifying Questions",
    ]:
        assert expected in app_source


def test_studio_runtime_contract_surfaces_local_evidence() -> None:
    contracts_source = read_text("src/contracts.ts")
    app_source = read_text("src/App.tsx")

    for expected in [
        "StudioRuntimeState",
        "workspaceRoot",
        "selectedCasePath",
        "visibleCommands",
        "diagnosticsArtifactPath",
        "reportPath",
        "manifestPath",
        "logPath",
        "runStatus",
    ]:
        assert expected in contracts_source

    for expected in [
        "Run Status",
        "Log Path",
        "diagnostics.json",
        "manifest.json",
        "Explicit approval required before writes or reruns",
    ]:
        assert expected in app_source

    assert 'workspaceRoot: "C:/OpenNavier"' not in app_source
    assert "workspaceRoot: runtime.workspaceRoot" in app_source
