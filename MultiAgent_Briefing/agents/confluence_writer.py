"""
Confluence Writer  -  the only door to Confluence writes.

Like the Jira writer, every guard sits here rather than in a caller, so no
agent can bypass them.

It renders a table of rows onto a page. It does not know what the rows mean -
the columns, their labels and which of them a human owns are handed to it by
the master agent, from the process spec.

The page is REGENERATED, never merged. That is deliberate: the summary page is
a projection of facts that live in Jira and Confluence, so rewriting it from
source is always correct, and a half-finished run leaves nothing inconsistent
behind. A person who edits an automation-owned cell will be overwritten on the
next run - which is right, because they edited a view rather than the data.

Columns marked as human-owned are the exception. Those values come from Jira
labels, so they survive a regeneration by being re-read, not by being left
alone.
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from datetime import datetime

from lib.atlassian import Client

STATE_COLOURS = {
    "READY": "blue",
    "SM_MISSING": "yellow",
    "SM_REQUESTED": "yellow",
    "ADP_CREATED": "yellow",
    "ADP_QUEUED": "yellow",
    "ADP_STALE": "red",
    "VERDICT_PENDING": "yellow",
    "BC_DUE": "purple",
    "JOINT_REVIEW": "purple",
    "APPROVED": "green",
    "SHARED_WITH_VALUE_STREAM": "green",
    "NOT_FEASIBLE": "neutral",
    "REVIEW_REJECTED": "neutral",
    "CLOSED_NO_ACTION": "neutral",
    "NEEDS_ATTENTION": "red",
}


def _e(value) -> str:
    return html.escape("" if value is None else str(value))


def status(text: str, colour: str = "neutral") -> str:
    return (f'<ac:structured-macro ac:name="status" ac:schema-version="1">'
            f'<ac:parameter ac:name="title">{_e(text)}</ac:parameter>'
            f'<ac:parameter ac:name="colour">{colour}</ac:parameter>'
            f'</ac:structured-macro>')


def link(url: str, label: str) -> str:
    if not url:
        return "&ndash;"
    return f'<a href="{_e(url)}">{_e(label or url)}</a>'


def panel(kind: str, body_html: str) -> str:
    return (f'<ac:structured-macro ac:name="{kind}" ac:schema-version="1">'
            f'<ac:rich-text-body>{body_html}</ac:rich-text-body>'
            f"</ac:structured-macro>")


@dataclass
class WriteOutcome:
    done: bool = False
    reason: str = ""
    page_id: str = ""
    version: int = 0
    rows: int = 0
    ran_as: str = ""

    def as_dict(self) -> dict:
        return vars(self)


def render_table(columns: list[dict], rows: list[dict]) -> str:
    """One HTML table, keyed by the spec's column definitions."""
    head = "".join(
        f"<th><p>{_e(c.get('label') or c['name'])}"
        + ("<br /><em>human</em>" if c.get("owner") == "HUMAN" else "")
        + "</p></th>"
        for c in columns)

    body = []
    for row in rows:
        cells = []
        for c in columns:
            name = c["name"]
            value = row.get(name)
            if name == "state":
                cell = status(str(value or "?"),
                              STATE_COLOURS.get(str(value), "neutral"))
            elif name == "sm_link":
                cell = link(str(value or ""), "solving method")
            elif name == "adp_key" and value:
                cell = link(f"https://tomtom.atlassian.net/browse/{value}",
                            str(value))
            elif name == "rule_id":
                cell = f"<strong>{_e(value)}</strong>"
            elif value in (None, "", False):
                cell = "&ndash;"
            elif value is True:
                cell = "Yes"
            else:
                cell = _e(value)
            cells.append(f"<td><p>{cell}</p></td>")
        body.append("<tr>" + "".join(cells) + "</tr>")

    return (f'<table data-layout="full-width"><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table>')


def render_page(ledger: dict, rows: list[dict], *, counts: dict,
                notes: list[str] | None = None) -> str:
    """The whole summary page, rebuilt from scratch."""
    columns = ledger.get("columns", [])
    stamp = datetime.now().strftime("%d %b %Y at %H:%M")

    intro = panel("info",
        "<p><strong>This page is maintained automatically.</strong> It is "
        "rebuilt from Jira and the source pages each time the process runs, so "
        "editing a cell here has no lasting effect - the next run will "
        "overwrite it. The two columns marked <em>human</em> are read from "
        "labels on the ADP ticket, which is where those decisions belong.</p>")

    warn = panel("note",
        "<p>Automation never closes, deletes or transitions a ticket, and never "
        "decides either gate. It creates, comments and keeps this page "
        "current.</p>")

    tally = " &middot; ".join(
        f"<strong>{v}</strong> {k.replace('_', ' ')}"
        for k, v in counts.items() if v)

    note_html = ""
    if notes:
        items = "".join(f"<li><p>{_e(n)}</p></li>" for n in notes)
        note_html = f"<h2>Notes from the last run</h2><ul>{items}</ul>"

    return (
        f"{intro}"
        f"<p>Last updated {_e(stamp)} &middot; {tally}</p>"
        f"<h2>Rules</h2>"
        f"{render_table(columns, rows)}"
        f"{note_html}"
        f"{warn}"
    )


# --------------------------------------------------------------------------
def write_page(client: Client, page_id: str, title: str, body_html: str,
               *, kill_switch: bool = False) -> WriteOutcome:
    """Replace a page's content. Guards first, exactly like the Jira writer."""
    if kill_switch:
        return WriteOutcome(reason="kill switch is on", page_id=page_id)
    if client.dry_run:
        return WriteOutcome(reason="dry run", page_id=page_id)

    try:
        current = client.get_page(page_id, "version")
        version = int(((current.get("version") or {}).get("number")) or 0)
    except Exception as exc:                                    # noqa: BLE001
        return WriteOutcome(reason=f"could not read the page: {exc}",
                            page_id=page_id)

    try:
        updated = client.update_page(
            page_id, title, body_html, version,
            message="Updated by the cc-autosolve assistant")
    except Exception as exc:                                    # noqa: BLE001
        return WriteOutcome(reason=f"write failed: {exc}", page_id=page_id)

    ran_as = "write role"
    if client.write_fallback_uses:
        ran_as = "read role (the write role was denied)"

    return WriteOutcome(
        done=True, page_id=page_id, ran_as=ran_as,
        version=int(((updated.get("version") or {}).get("number")) or version + 1),
    )


def publish_child(client: Client, parent_id: str, space_key: str,
                  title: str, body_html: str,
                  *, kill_switch: bool = False) -> WriteOutcome:
    """Create a child page, or update it if one with that title already exists.

    Titled by rule, so a rerun revises the same page rather than leaving a
    second copy beside it. That matters for a proposal under review: the panel
    should be commenting on one page whose history shows what changed, not
    choosing between near-identical siblings.
    """
    if kill_switch:
        return WriteOutcome(reason="kill switch is on")
    if client.dry_run:
        return WriteOutcome(reason="dry run")

    try:
        existing = client.child_by_title(parent_id, title)
    except Exception as exc:                                    # noqa: BLE001
        return WriteOutcome(reason=f"could not list child pages: {exc}")

    ran_as_note = lambda: ("read role (the write role was denied)"
                           if client.write_fallback_uses else "write role")

    if existing:
        page_id = str(existing.get("id"))
        try:
            version = int(((existing.get("version") or {}).get("number")) or 0)
            if not version:
                version = int(((client.get_page(page_id, "version")
                                .get("version") or {}).get("number")) or 0)
            updated = client.update_page(
                page_id, title, body_html, version,
                message="Revised by the cc-autosolve assistant")
        except Exception as exc:                                # noqa: BLE001
            return WriteOutcome(reason=f"update failed: {exc}", page_id=page_id)
        return WriteOutcome(
            done=True, page_id=page_id, ran_as=ran_as_note(),
            version=int(((updated.get("version") or {}).get("number")) or version + 1),
            reason="revised the existing page")

    try:
        created = client.create_page(space_key, parent_id, title, body_html)
    except Exception as exc:                                    # noqa: BLE001
        return WriteOutcome(reason=f"create failed: {exc}")

    return WriteOutcome(done=True, page_id=str(created.get("id")),
                        version=1, ran_as=ran_as_note(),
                        reason="created a new page")


def run(task: dict) -> dict:
    """Agent entry point. Dict in, dict out."""
    client: Client = task["client"]
    ledger = task["ledger"]
    rows = task.get("rows") or []

    body = render_page(ledger, rows,
                       counts=task.get("counts") or {},
                       notes=task.get("notes"))

    outcome = write_page(
        client,
        str(ledger["page_id"]),
        str(ledger.get("page_title") or "Summary"),
        body,
        kill_switch=bool(task.get("kill_switch")),
    )
    outcome.rows = len(rows)
    return outcome.as_dict()
