from mcp.server.fastmcp import FastMCP

mcp = FastMCP("mongodb mcp")

# for test
@mcp.resource("config://server")
def get_app_config() -> str:
    return "server config here"

@mcp.tool()
def test_tool(a: int, b: int) -> int:
    return a + b

@mcp.prompt()
def test_prompt(prompt: str) -> str:
    return f"this is a prompt for test: \n{prompt}"