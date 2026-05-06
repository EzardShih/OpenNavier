from collections.abc import Callable
from typing import Any

from opennavier.mcp.case_init_tools import case_init_cavity
from opennavier.mcp.case_validation_tools import case_validate_structure
from opennavier.mcp.diagnostics_tools import diagnostics_residuals
from opennavier.mcp.spec_tools import spec_validate
from opennavier.mcp.workspace_tools import workspace_inspect

TOOL_FUNCTIONS = (
    workspace_inspect,
    spec_validate,
    case_init_cavity,
    case_validate_structure,
    diagnostics_residuals,
)


def build_server(server_factory: Callable[[str], Any] | None = None) -> Any:
    if server_factory is None:
        from mcp.server.fastmcp import FastMCP

        server_factory = FastMCP

    server = server_factory("OpenNavier")
    for tool_function in TOOL_FUNCTIONS:
        server.tool()(tool_function)

    return server


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
