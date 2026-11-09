# DECISIONS

- Repo lives in subfolder `issue-tracker-quality-lab` because the parent folder holds unrelated projects.
- Local tools: Python 3.11, Java 21, Chrome present. Maven and Swift missing -> Java/Swift run only in CI.
- GitHub user: Naysrania18.
- MCP SDK installed is 2.x: uses mcp.server.mcpserver.MCPServer (renamed from FastMCP). requirements pin mcp>=2 to match.
