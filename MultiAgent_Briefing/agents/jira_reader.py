"""
Jira Reader  -  a generic query-and-extract engine.

Read-only. It knows how to build a JQL query from a filter list and pull named
values out of the issues that come back. It does not know what a CC rule is,
what OM-375717 is, or what any label means - all of that is handed to it by
the master agent, from the process spec.

Reads go out as the user identity, which has global read access, so a query
never fails for lack of permission. That is handled in lib/atlassian.py.

Extraction sources it understands:

    field           a Jira field, by id or name        summary, status, labels
    title_regex     a capture group from the summary   'CC Rule (\\d{4,6})'
    labels_match    which of a set of labels is present  verdict gates
    attachments     filenames, optionally filtered
    remote_links    linked URLs, optionally filtered
    comments        comment bodies, optionally by author

Anything it cannot resolve is reported in `warnings` rather than guessed at.
"""

from __future__ import annotations

import re
from typing import Any

from lib.atlassian import Client, JIRA

# Filter operators the spec may use, mapped to JQL.
OPERATORS = {
    "eq": "=",
    "ne": "!=",
    "in": "in",
    "not_in": "not in",
    "gt": ">",
    "lt": "<",
    "gte": ">=",
    "lte": "<=",
    "is": "is",
    "is_not": "is not",
}


def _quote(value: Any) -> str:
    """Render a value for JQL. Lists become parenthesised sets."""
    if isinstance(value, (list, tuple)):
        return "(" + ", ".join(_quote(v) for v in value) + ")"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text.upper() in ("EMPTY", "NULL"):
        return text.upper()
    return '"' + text.replace('"', '\\"') + '"'


def build_jql(source: dict, filters: list[dict] | None) -> str:
    """Turn a source plus filters into one JQL string.

    A raw `jql` in the source wins outright - filters are then ignored, which
    is deliberate: mixing a hand-written query with generated clauses produces
    surprises.
    """
    if source.get("jql"):
        return source["jql"]

    clauses: list[str] = []
    if source.get("project"):
        clauses.append(f'project = {_quote(source["project"])}')

    for f in filters or []:
        field = f["field"]
        # A custom field id is used bare; a name with spaces needs quoting.
        rendered = field if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", field) else f'"{field}"'

        # A cascading select needs cascadeOption(parent, child). Matching the
        # parent alone silently widens the result to every child under it -
        # on DOCMAN that is 773 tickets instead of 541, and the extra 232 are
        # other Orbis sub-components that have nothing to do with this process.
        if f.get("child_value") is not None:
            clauses.append(
                f"{rendered} in cascadeOption({_quote(f['value'])}, "
                f"{_quote(f['child_value'])})")
            continue

        op = OPERATORS.get(f.get("op", "eq"))
        if not op:
            raise ValueError(f"unknown filter operator: {f.get('op')!r}")
        clauses.append(f"{rendered} {op} {_quote(f['value'])}")

    if not clauses:
        raise ValueError("no project, jql or filters given - refusing to query all of Jira")

    return " AND ".join(clauses)


# --------------------------------------------------------------------------
def _extract_one(issue: dict, rule: dict, client: Client,
                 warnings: list[str]) -> Any:
    """Pull one named value out of one issue."""
    fields = issue.get("fields", {})
    kind = rule.get("from", "field")
    spec = rule.get("spec")
    name = rule["name"]

    if kind == "field":
        if spec == "key":
            return issue.get("key")
        value = fields.get(spec)
        # Reduce the common Jira shapes to something a spec can compare.
        if isinstance(value, dict):
            return value.get("displayName") or value.get("name") or value.get("value")
        if isinstance(value, list):
            return [v.get("name") if isinstance(v, dict) else v for v in value]
        return value

    if kind == "title_regex":
        summary = fields.get("summary") or ""
        m = re.search(spec, summary)
        if not m:
            return None
        return m.group(1) if m.groups() else m.group(0)

    if kind == "labels_match":
        # Which of a known set of labels is present. Used for the decision
        # gates, where an exact match matters and a guess would be wrong.
        labels = set(fields.get("labels") or [])
        for candidate, result in (spec or {}).items():
            if candidate in labels:
                return result
        return None

    if kind == "attachments":
        # Author and timestamp are returned as well as the name, because
        # "has anyone filled this in?" is answered by who attached it - a file
        # the automation attached itself is not evidence of anything.
        items = fields.get("attachment") or []
        out = [{
            "filename": a.get("filename", ""),
            "author": ((a.get("author") or {}).get("emailAddress")
                       or (a.get("author") or {}).get("displayName") or ""),
            "created": a.get("created", ""),
            "size": a.get("size", 0),
        } for a in items]
        pattern = (spec or {}).get("pattern") if isinstance(spec, dict) else None
        if pattern:
            out = [a for a in out if re.search(pattern, a["filename"])]
        return out

    if kind == "remote_links":
        key = issue.get("key")
        try:
            links = client.request("GET", f"{JIRA}/issue/{key}/remotelink")
        except Exception as exc:                                # noqa: BLE001
            warnings.append(f"{key}: could not read remote links ({exc})")
            return []
        urls = [(l.get("object") or {}).get("url", "") for l in (links or [])]
        pattern = (spec or {}).get("pattern") if isinstance(spec, dict) else None
        if pattern:
            urls = [u for u in urls if re.search(pattern, u)]
        return urls

    if kind == "comments":
        comments = ((fields.get("comment") or {}).get("comments")) or []
        author = (spec or {}).get("author") if isinstance(spec, dict) else None
        out = []
        for c in comments:
            who = (c.get("author") or {}).get("emailAddress", "")
            if author and author.lower() not in who.lower():
                continue
            out.append({
                "author": who,
                "created": c.get("created"),
                "body": _adf_to_text(c.get("body")),
            })
        return out

    warnings.append(f"{name}: unknown extraction source {kind!r}")
    return None


def _adf_to_text(node: Any) -> str:
    """Flatten an Atlassian Document Format body to plain text.

    Only what is needed to recognise our own comments - not a full renderer.
    """
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(_adf_to_text(n) for n in node)
    if isinstance(node, dict):
        if node.get("type") == "text":
            return node.get("text", "")
        return _adf_to_text(node.get("content"))
    return ""


# --------------------------------------------------------------------------
def _fields_needed(extract: list[dict]) -> list[str]:
    """Which Jira fields to request, derived from the extraction rules."""
    needed = {"summary", "status", "labels"}
    for rule in extract:
        kind = rule.get("from", "field")
        spec = rule.get("spec")
        if kind == "field" and isinstance(spec, str) and spec != "key":
            needed.add(spec)
        elif kind == "attachments":
            needed.add("attachment")
        elif kind == "comments":
            needed.add("comment")
    return sorted(needed)


def run(task: dict) -> dict:
    """Agent entry point. Dict in, dict out.

    task = {
      client:   a lib.atlassian.Client
      source:   {project | board_id | jql}
      filters:  [{field, op, value}, ...]
      extract:  [{name, from, spec}, ...]
      scope:    optional single issue key, to re-read just one issue
    }
    """
    client: Client = task["client"]
    source = dict(task.get("source") or {})
    extract = task.get("extract") or []
    warnings: list[str] = []

    if task.get("scope"):
        source = {"jql": f'key = {_quote(task["scope"])}'}

    jql = build_jql(source, task.get("filters"))

    try:
        issues = client.search(jql, _fields_needed(extract))
    except Exception as exc:                                    # noqa: BLE001
        return {"rows": [], "count": 0, "jql": jql,
                "warnings": [f"query failed: {exc}"]}

    rows = []
    for issue in issues:
        row = {"key": issue.get("key")}
        for rule in extract:
            row[rule["name"]] = _extract_one(issue, rule, client, warnings)
        rows.append(row)

    return {"rows": rows, "count": len(rows), "jql": jql, "warnings": warnings}
