"""Drop-in helper: use MCP servers from the TomTom registry inside ANY orchestrator.

  async with RegistryTools() as rt:
      tools = rt.openai_tools()            # or rt.anthropic_tools() / rt.tools (neutral list)
      ...                                  # give `tools` to your LLM
      if rt.is_write(name): ...ask a human first...
      text = await rt.call(name, args)     # run the tool the LLM asked for

Needs:  pip install "mcp<2" httpx
Atlassian login (set in the environment / Azure Key Vault, never in code):
  MCP_AUTH   = full header value, e.g. "Basic <base64(email:token)>"
  or ATL_EMAIL + ATL_TOKEN (scoped API token) and this file builds the Basic header for you.
"""
import base64
import os
from contextlib import AsyncExitStack

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

REGISTRY = os.environ.get("MCP_REGISTRY", "https://mcp-registry.platform.ai.az.tt3.com/v0/servers")

# ALLOW-LIST: the agent may use ONLY these servers. Names are checked against the registry.
# url_override pins the address when the registry entry is stale (Atlassian's still says v1, which has only 4 tools).
ALLOWED = {
    "com.atlassian/atlassian-mcp-server": {
        "url_override": "https://mcp.atlassian.com/v2/mcp",
        "write_tools": {
            "createJiraIssue", "editJiraIssue", "transitionJiraIssue", "addOrEditJiraIssueComment",
            "createConfluenceContent", "updateConfluenceContent", "addGraphContext",
            "executeWrite", "executeDestructive",
        },
    },
}


def atlassian_auth_header():
    if os.environ.get("MCP_AUTH"):
        return os.environ["MCP_AUTH"].strip()
    email, token = os.environ.get("ATL_EMAIL", "").strip(), os.environ.get("ATL_TOKEN", "").strip()
    if not (email and token):
        raise RuntimeError("Set MCP_AUTH, or ATL_EMAIL and ATL_TOKEN, for Atlassian.")
    return "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode()


def registry_lookup(name):
    """Return the streamable-http remote for `name` from the registry, or None."""
    cursor = None
    for _ in range(20):
        r = httpx.get(REGISTRY, params={"cursor": cursor} if cursor else None, timeout=30)
        r.raise_for_status()
        data = r.json()
        for item in data.get("servers", []):
            s = item.get("server", item)
            if s.get("name") == name:
                for rem in s.get("remotes", []) or []:
                    if rem.get("type") == "streamable-http":
                        return rem
        cursor = (data.get("metadata") or {}).get("nextCursor")
        if not cursor:
            break
    return None


class RegistryTools:
    async def __aenter__(self):
        self._stack = AsyncExitStack()
        await self._stack.__aenter__()
        self.tools, self._owner, self._write = [], {}, set()
        for name, cfg in ALLOWED.items():
            remote = registry_lookup(name)
            if not remote:
                print(f"[registry] '{name}' not found in registry - skipped")
                continue
            url = cfg.get("url_override") or remote["url"]
            headers = {"Authorization": atlassian_auth_header()}
            r, w, _ = await self._stack.enter_async_context(streamablehttp_client(url, headers=headers))
            session = await self._stack.enter_async_context(ClientSession(r, w))
            await session.initialize()
            for t in (await session.list_tools()).tools:
                self.tools.append({"name": t.name, "description": t.description or "", "input_schema": t.inputSchema})
                self._owner[t.name] = session
                if t.name in cfg.get("write_tools", set()):
                    self._write.add(t.name)
            print(f"[registry] {name} -> {url} ({len(self._owner)} tools so far)")
        return self

    async def __aexit__(self, *exc):
        return await self._stack.__aexit__(*exc)

    def is_write(self, tool_name):
        return tool_name in self._write

    async def call(self, tool_name, args):
        if tool_name not in self._owner:
            return f"ERROR: tool '{tool_name}' is not available"
        res = await self._owner[tool_name].call_tool(tool_name, args or {})
        text = "\n".join(c.text for c in res.content if c.type == "text")
        return ("ERROR: " if res.isError else "") + text

    def openai_tools(self):
        return [{"type": "function", "function": {"name": t["name"], "description": t["description"],
                 "parameters": t["input_schema"]}} for t in self.tools]

    def anthropic_tools(self):
        return list(self.tools)
