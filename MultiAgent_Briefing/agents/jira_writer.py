"""
Jira Writer  -  the only door to Jira writes, and where every guard lives.

Because any agent may call this one, the safety checks cannot sit in a central
router - they sit here, so no caller can bypass them. A new agent added later
inherits every protection for free.

Guards, applied to every call regardless of who made it:

  kill switch      writes disabled outright
  dry run          plan the call, log it, execute nothing
  duplicate        a ticket already exists for this key
  cooldown         we already said this to this person, recently enough
  budget           this run has made its maximum tickets or comments
  forbidden        closing, deleting and transitioning are refused, always

Cooldowns need no stored state. Every comment this agent posts carries a
marker naming its purpose and subject; "have we said this already, and when"
is answered by reading our own comments back. Nothing to corrupt, nothing to
restore, and it survives a redeploy.

Actions it will perform:  create, comment, attach, edit_fields
Actions it refuses:       transition, close, delete
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from lib.adf import markdown_to_adf, text_to_adf
from lib.atlassian import Client, JIRA

FORBIDDEN = ("transition", "close", "delete", "resolve")

# Appended to every comment we post, so a later run can recognise its own
# work. It doubles as the sign-off a reader sees, so there is one line at the
# bottom of a comment rather than a friendly line plus a machine tag.
MARKER = "cc-autosolve"


def comment_marker(purpose: str, subject: str) -> str:
    return f"Posted by the {MARKER} assistant - ref {purpose}/{subject}"


@dataclass
class Budget:
    """Per-run write caps. Exceeding one halts rather than trimming quietly."""
    max_creates: int = 10
    max_comments: int = 15
    max_attachments: int = 40
    creates: int = 0
    comments: int = 0
    attachments: int = 0

    def room_for(self, kind: str) -> bool:
        return {
            "create": self.creates < self.max_creates,
            "comment": self.comments < self.max_comments,
            "attach": self.attachments < self.max_attachments,
        }.get(kind, True)

    def spend(self, kind: str) -> None:
        if kind == "create":
            self.creates += 1
        elif kind == "comment":
            self.comments += 1
        elif kind == "attach":
            self.attachments += 1


@dataclass
class WriterContext:
    """Everything the guards need, gathered once per run by the caller."""
    client: Client
    budget: Budget = field(default_factory=Budget)
    kill_switch: bool = False
    # rule_id -> existing issue key, for the duplicate guard
    existing_by_key: dict[str, str] = field(default_factory=dict)
    # issue key -> [{"body":..., "created":...}] of OUR comments
    our_comments: dict[str, list[dict]] = field(default_factory=dict)
    performed: list[dict] = field(default_factory=list)
    refused: list[dict] = field(default_factory=list)

    def record(self, action: str, target: str, detail: str, done: bool,
               reason: str = "") -> dict:
        entry = {"action": action, "target": target, "detail": detail,
                 "done": done, "reason": reason}
        (self.performed if done else self.refused).append(entry)
        return entry


# --------------------------------------------------------------------------
def _working_days_between(then: datetime, now: datetime) -> int:
    days = 0
    cursor = then
    while cursor.date() < now.date():
        cursor += timedelta(days=1)
        if cursor.weekday() < 5:
            days += 1
    return days


def _parse_jira_time(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f%z")
    except (ValueError, TypeError):
        return None


def cooldown_blocks(ctx: WriterContext, issue_key: str, purpose: str,
                    subject: str, cooldown_working_days: int) -> str | None:
    """Have we already said this, recently enough that saying it again is noise?

    Returns a reason string when the comment should be withheld, else None.
    """
    marker = comment_marker(purpose, subject)
    now = datetime.now(timezone.utc)
    for comment in ctx.our_comments.get(issue_key, []):
        if marker not in (comment.get("body") or ""):
            continue
        when = _parse_jira_time(comment.get("created", ""))
        if when is None:
            return f"already commented for '{purpose}' (timestamp unreadable)"
        elapsed = _working_days_between(when, now)
        if elapsed < cooldown_working_days:
            return (f"already commented for '{purpose}' {elapsed} working "
                    f"day(s) ago; cooldown is {cooldown_working_days}")
    return None


# --------------------------------------------------------------------------
def _guard(ctx: WriterContext, action: str, kind: str, target: str) -> str | None:
    if action in FORBIDDEN:
        return f"'{action}' is never permitted by this agent"
    if ctx.kill_switch:
        return "kill switch is on"
    if not ctx.budget.room_for(kind):
        return (f"run budget for {kind} is spent "
                f"({getattr(ctx.budget, kind + 's')} used)")
    return None


def create_subtask(ctx: WriterContext, spec_target: dict, values: dict,
                   description_markdown: str) -> dict:
    """Create one sub-task. Refuses if one already exists for this key."""
    key = str(values.get("rule_id", ""))
    summary = spec_target["summary_pattern"].format(**values)

    if key and key in ctx.existing_by_key:
        return ctx.record("create", key, summary, False,
                          f"already exists as {ctx.existing_by_key[key]}")

    blocked = _guard(ctx, "create", "create", key)
    if blocked:
        return ctx.record("create", key, summary, False, blocked)

    labels = [l.format(**values) for l in spec_target.get("labels", [])]
    fields = {
        "project": {"key": spec_target["project"]},
        "issuetype": {"name": spec_target["issue_type"]},
        "parent": {"key": spec_target["parent"]},
        "summary": summary,
        "description": markdown_to_adf(description_markdown),
        "labels": [l for l in labels if l and "{" not in l],
    }
    for name, value in (spec_target.get("fields") or {}).items():
        if value is not None and not str(value).startswith("TODO:"):
            fields[name] = value

    # Planning ID is enforced on the create screen but not on edit. A
    # placeholder satisfies the screen and is cleared straight afterwards, so
    # the sub-task ends up consistent with its parent, which has none.
    workaround = spec_target.get("planning_id_workaround") or {}
    planning_field = workaround.get("field")
    if workaround.get("enabled") is True and planning_field:
        fields[planning_field] = workaround.get("set_value", "placeholder")

    if ctx.client.dry_run:
        return ctx.record("create", key, summary, False, "dry run")

    # Last look before committing. The context was gathered when the run
    # started, and a run can be busy for minutes fetching data - long enough
    # for another run, or a person, to have raised this ticket meanwhile. Two
    # duplicates were created exactly this way before the check existed.
    if key:
        try:
            found = ctx.client.search(
                f'parent = {spec_target["parent"]} AND summary ~ "\\\\[CC {key}\\\\]"',
                ["summary"])
            for issue in found:
                if f"[CC {key}]" in (issue.get("fields", {}).get("summary") or ""):
                    existing = issue.get("key", "")
                    ctx.existing_by_key[key] = existing
                    return ctx.record("create", key, summary, False,
                                      f"already exists as {existing} "
                                      f"(found on the final check)")
        except Exception as exc:                                # noqa: BLE001
            # A failed check must not silently permit a duplicate.
            return ctx.record("create", key, summary, False,
                              f"could not verify uniqueness: {exc}")

    created = ctx.client.create_issue(fields)
    issue_key = created.get("key", "")
    ctx.budget.spend("create")
    ctx.existing_by_key[key] = issue_key

    if (workaround.get("enabled") is True and planning_field
            and workaround.get("clear_after_create")):
        try:
            ctx.client.update_issue(issue_key, {planning_field: None})
        except Exception as exc:                                # noqa: BLE001
            ctx.record("edit_fields", issue_key,
                       f"clear {planning_field}", False, str(exc))

    return ctx.record("create", key, f"{issue_key}  {summary}", True)


def post_comment(ctx: WriterContext, issue_key: str, body: str, *,
                 purpose: str, subject: str, cooldown_working_days: int = 0,
                 mention_account_id: str | None = None) -> dict:
    """Post a comment, subject to the cooldown for this purpose and subject."""
    blocked = _guard(ctx, "comment", "comment", issue_key)
    if blocked:
        return ctx.record("comment", issue_key, purpose, False, blocked)

    if cooldown_working_days:
        reason = cooldown_blocks(ctx, issue_key, purpose, subject,
                                 cooldown_working_days)
        if reason:
            return ctx.record("comment", issue_key, purpose, False, reason)

    text = body.rstrip() + "\n\n" + comment_marker(purpose, subject)
    doc = text_to_adf(text)

    # A mention only makes sense when there is somebody to mention. An
    # unassigned ticket gets the comment plain rather than addressed to nobody.
    if mention_account_id:
        doc["content"].insert(0, {
            "type": "paragraph",
            "content": [{"type": "mention",
                         "attrs": {"id": mention_account_id}},
                        {"type": "text", "text": " "}],
        })

    if ctx.client.dry_run:
        return ctx.record("comment", issue_key, purpose, False, "dry run")

    ctx.client.add_comment(issue_key, doc)
    ctx.budget.spend("comment")
    return ctx.record("comment", issue_key, purpose, True)


def attach_file(ctx: WriterContext, issue_key: str, path: str | Path) -> dict:
    """Attach one file, skipping it if a file of that name is already there."""
    path = Path(path)
    if not path.exists():
        return ctx.record("attach", issue_key, path.name, False, "file not found")

    blocked = _guard(ctx, "attach", "attach", issue_key)
    if blocked:
        return ctx.record("attach", issue_key, path.name, False, blocked)

    if ctx.client.dry_run:
        return ctx.record("attach", issue_key, path.name, False, "dry run")

    existing = ctx.client.get_issue(issue_key, "attachment")
    names = {a.get("filename") for a in
             (existing.get("fields", {}).get("attachment") or [])}
    if path.name in names:
        return ctx.record("attach", issue_key, path.name, False,
                          "already attached")

    ctx.client.add_attachment(issue_key, path.name, path.read_bytes())
    ctx.budget.spend("attach")
    return ctx.record("attach", issue_key, path.name, True)


# --------------------------------------------------------------------------
def load_our_comments(client: Client, parent_jql: str,
                      our_emails: list[str]) -> dict[str, list[dict]]:
    """Read back our own comments under a parent, for the cooldown guard."""
    from agents.jira_reader import _adf_to_text

    issues = client.search(parent_jql, ["comment"])
    out: dict[str, list[dict]] = {}
    lowered = [e.lower() for e in our_emails if e]
    for issue in issues:
        key = issue.get("key")
        rows = []
        for c in (issue.get("fields", {}).get("comment", {}).get("comments") or []):
            who = ((c.get("author") or {}).get("emailAddress") or "").lower()
            body = _adf_to_text(c.get("body"))
            if (lowered and who and any(e in who for e in lowered)) or MARKER in body:
                rows.append({"body": body, "created": c.get("created", "")})
        if rows:
            out[key] = rows
    return out


def run(task: dict) -> dict:
    """Agent entry point. Dict in, dict out."""
    ctx: WriterContext = task["context"]
    action = task["action"]

    if action in FORBIDDEN:
        return ctx.record(action, task.get("target", ""), "", False,
                          f"'{action}' is never permitted by this agent")

    if action == "create":
        return create_subtask(ctx, task["target_spec"], task["values"],
                              task["description"])
    if action == "comment":
        return post_comment(
            ctx, task["target"], task["body"],
            purpose=task["purpose"], subject=task.get("subject", ""),
            cooldown_working_days=task.get("cooldown_working_days", 0),
            mention_account_id=task.get("mention_account_id"),
        )
    if action == "attach":
        return attach_file(ctx, task["target"], task["path"])

    return ctx.record(action, task.get("target", ""), "", False,
                      f"unknown action {action!r}")
