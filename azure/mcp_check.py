"""Check that Jira and Confluence go through the Atlassian MCP server from inside the job. Sends nothing.

    az containerapp job start -n ops-native-ai-trigger -g ops-hub-rg --container-name engine \
        --image <image> --command python --args /app/azure/mcp_check.py
"""
import os
import sys

sys.path.insert(0, "/app/MultiAgent_Briefing")
import config  # noqa: E402,F401  (loads settings the same way a run does)
from agents import atlassian_mcp as m  # noqa: E402

print("MCPCHECK settings present:", {k: bool(os.getenv(k, "").strip()) for k in ("ATL_EMAIL", "ATL_TOKEN")})
print("MCPCHECK enabled:", m.enabled())
try:
    r = m.search_jira("project = OM ORDER BY updated DESC", ["summary", "updated"], max_results=3)
    issues = r.get("issues", [])
    print(f"MCPCHECK jira via MCP: OK, {len(issues)} issues, latest {issues[0].get('key') if issues else None}")
except Exception as exc:
    print(f"MCPCHECK jira via MCP: FAILED {type(exc).__name__}: {exc}")
    sys.exit(1)
