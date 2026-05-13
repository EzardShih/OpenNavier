from collections.abc import Callable

from opennavier.mcp.server import build_server


class FakeFastMCP:
    def __init__(self, name: str) -> None:
        self.name = name
        self.tool_names: list[str] = []

    def tool(self) -> Callable[[Callable[..., object]], Callable[..., object]]:
        def decorator(function: Callable[..., object]) -> Callable[..., object]:
            self.tool_names.append(function.__name__)
            return function

        return decorator


def test_build_server_registers_open_navier_mcp_tools() -> None:
    server = build_server(server_factory=FakeFastMCP)

    assert server.name == "OpenNavier"
    assert server.tool_names == [
        "workspace_inspect",
        "spec_validate",
        "case_build_validate",
        "case_build_dry_run",
        "case_build_write",
        "case_validate_structure",
        "diagnostics_residuals",
        "diagnostics_mesh_quality",
        "diagnostics_case",
        "diagnostics_artifact",
        "report_generate",
    ]
