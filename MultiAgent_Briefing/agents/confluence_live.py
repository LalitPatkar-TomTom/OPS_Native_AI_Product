"""
Live Confluence reads, driven by the process spec.

The pieces below join the three parts that already exist:

    lib/atlassian.py        fetches the page
    confluence_fetch.py     adapts storage format to parsable text
    confluence_reader.py    extracts sections and the behaviour badge

Nothing here knows what a CC rule is. It is told the space, the title pattern
and the columns by whoever calls it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agents.confluence_fetch import parse_table, storage_to_text
from agents.confluence_reader import parse_solving_method
from lib.atlassian import Client


@dataclass
class TableRead:
    rows: list[dict] = field(default_factory=list)
    matched: list[dict] = field(default_factory=list)
    excluded: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def read_table_source(client: Client, source: dict) -> TableRead:
    """Read the table on each configured page and apply the spec's filters.

    Rows that fail a filter are kept in `excluded` with the reason, so the
    handoff plan can explain what was left out rather than silently dropping
    it - a rule vanishing without explanation is worse than one held back.
    """
    out = TableRead()
    filters = source.get("filters") or []
    extract = {e["spec"]: e["name"] for e in source.get("extract", [])
               if e.get("from") == "table_column"}
    required = [f["column"] for f in filters] + list(extract)

    for page in source.get("pages", []):
        page_id = page["page_id"]
        try:
            raw = client.get_page(page_id, "body.storage,version")
            storage = raw["body"]["storage"]["value"]
        except Exception as exc:                                # noqa: BLE001
            out.warnings.append(f"page {page_id}: could not be read ({exc})")
            continue

        rows, warns = parse_table(storage, required_columns=required)
        out.warnings.extend(f"page {page_id}: {w}" for w in warns)

        for row in rows:
            record = {name: (row.get(col) or "").strip()
                      for col, name in extract.items()}
            record["domain"] = page.get("domain", "")
            record["origin"] = "CONFLUENCE_ANALYSIS"
            record["source_page"] = page_id
            if not record.get("rule_id"):
                continue

            reason = None
            for f in filters:
                actual = (row.get(f["column"]) or "").strip()
                expected = str(f["value"]).strip()
                if f.get("op", "eq") == "eq" and actual.lower() != expected.lower():
                    reason = f'{f["column"]} is "{actual or "(empty)"}", not "{expected}"'
                    break

            out.rows.append(record)
            if reason:
                out.excluded.append({**record, "reason": reason})
            else:
                out.matched.append(record)

    return out


def find_solving_method(client: Client, rule_id: str, source: dict) -> dict:
    """Locate and parse one rule's solving method page.

    The query comes from the spec, so this function has no idea it is looking
    at CC rules - only that a page is titled with a key.
    """
    query = source["query"].replace("{rule_id}", str(rule_id))
    try:
        found = client.cql(query, limit=5)
    except Exception as exc:                                    # noqa: BLE001
        return {"rule_id": rule_id, "found": False,
                "warnings": [f"lookup failed: {exc}"]}

    results = found.get("results") or []
    if not results:
        return {"rule_id": rule_id, "found": False,
                "warnings": ["no page found for this rule"]}

    warnings: list[str] = []
    if len(results) > 1:
        warnings.append(f"{len(results)} pages matched; using the first")

    content = results[0].get("content") or results[0]
    page_id = content.get("id")

    try:
        page = client.get_page(page_id, "body.storage,version,history")
        storage = page["body"]["storage"]["value"]
    except Exception as exc:                                    # noqa: BLE001
        return {"rule_id": rule_id, "found": False,
                "warnings": [f"page {page_id} could not be read ({exc})"]}

    parsed = parse_solving_method(
        str(rule_id),
        storage_to_text(storage),
        f"https://tomtom.atlassian.net/wiki/spaces/"
        f"{(page.get('space') or {}).get('key', 'CPPSM')}/pages/{page_id}/{rule_id}",
    )
    parsed["found"] = True
    parsed["page_id"] = page_id
    parsed["sm_author"] = (
        ((page.get("history") or {}).get("createdBy") or {}).get("displayName", "")
    )
    parsed["warnings"] = warnings + parsed.get("warnings", [])
    return parsed
