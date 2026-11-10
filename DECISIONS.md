# DECISIONS

- Repo lives in subfolder `issue-tracker-quality-lab` because the parent folder holds unrelated projects.
- Local tools: Python 3.11, Java 21, Chrome present. Maven and Swift missing -> Java/Swift run only in CI.
- GitHub user: Naysrania18.
- MCP SDK installed is 2.x: uses mcp.server.mcpserver.MCPServer (renamed from FastMCP). requirements pin mcp>=2 to match.
- Local Maven: portable Maven 3.9.9 unzipped to S:/Git Hub Clone project/_tools (outside repo, cache on S:). Java suite verified locally: 66 pass, 4 known-defect tests fail as designed. Allure runs without AspectJ agent (results + REST attachments only).
