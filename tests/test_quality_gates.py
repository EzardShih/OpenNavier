import json
from pathlib import Path

ROOT = Path(".")


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_studio_package_exposes_single_check_gate() -> None:
    package_json = json.loads(read_text("apps/studio/package.json"))

    assert package_json["scripts"]["check"] == (
        "npm run typecheck && npm run lint && npm run format:check"
    )


def test_studio_typescript_config_uses_modern_vite_resolution() -> None:
    tsconfig = json.loads(read_text("apps/studio/tsconfig.json"))
    compiler_options = tsconfig["compilerOptions"]

    assert compiler_options["module"] == "ESNext"
    assert compiler_options["moduleResolution"] == "Bundler"
    assert "ignoreDeprecations" not in compiler_options


def test_ci_runs_python_and_studio_quality_gates() -> None:
    workflow = read_text(".github/workflows/checks.yml")

    for expected in [
        "actions/checkout@v6",
        "actions/setup-python@v6",
        "actions/setup-node@v6",
        "astral-sh/setup-uv@",
        "uv run ruff check . --no-cache",
        "uv run pytest",
        "npm --prefix apps/studio ci",
        "npm --prefix apps/studio run check",
    ]:
        assert expected in workflow


def test_pre_commit_config_exposes_local_quality_hooks() -> None:
    config = read_text(".pre-commit-config.yaml")

    for expected in [
        "id: python-ruff",
        "entry: uv run ruff check . --no-cache",
        "id: python-tests",
        "entry: uv run pytest",
        "id: studio-check",
        "entry: npm --prefix apps/studio run check",
        "stages: [pre-push]",
    ]:
        assert expected in config


def test_agent_and_readme_document_quality_gates() -> None:
    agents = read_text("AGENTS.md")
    readme = read_text("README.md")

    for expected in [
        "npm.cmd run check",
        "npm.cmd run typecheck",
        "npm.cmd run lint",
        "npm.cmd run format:check",
    ]:
        assert expected in agents

    for expected in [
        "npm.cmd install",
        "npm.cmd run check",
        "pre-commit install",
        "pre-commit install --hook-type pre-push",
    ]:
        assert expected in readme
