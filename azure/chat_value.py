"""Time saved by OPS Hub chat answers, for the weekly analytics and the impact report.

Each usage_log.jsonl line written by OPS Hub since 21 Oct 2026 carries the work the answer
did and its estimate (category, minutes, minutes_low, minutes_high; see OPSHUB app/time_saved.py).
Older lines only have the first 90 characters of the question: those are estimated from the
text with the same minutes and counted as "estimated from question text".

Counted as 0: failed answers, the same question asked again by the same person within 30 min,
and answers the person rated 👎 in OPS Hub.
"""
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

# Same minutes as OPSHUB app/time_saved.py (point, low, high)
TABLE = {
    "reasoning":    (60, 60, 90),
    "cross_source": (45, 30, 60),
    "data_multi":   (30, 20, 45),
    "data_single":  (15, 10, 20),
    "jira_ticket":  (10, 5, 15),
    "lookup":       (5, 3, 10),
    "knowledge":    (5, 3, 10),
    "follow_up":    (1, 0, 2),
    "failed":       (0, 0, 0),
}
LABEL = {
    "reasoning":    "Analysis and reasoning (actions, risks, insights) on fetched data",
    "cross_source": "Data combined with Jira / Confluence",
    "data_multi":   "Several data queries or a chart",
    "data_single":  "One data query",
    "jira_ticket":  "Jira ticket drafted or created",
    "lookup":       "Jira / Confluence lookup",
    "knowledge":    "Explanation without data",
    "follow_up":    "Follow-up or clarification",
    "failed":       "Failed",
}
ORDER = list(TABLE)
REPEAT_WINDOW_S = 30 * 60

# Clarifications. Courtesy words only count when the message is short.
_CLARIFY = re.compile(r"^(which (table|data ?source|source)s?\b|how (do|did) (you|yo) calc|which jira\b|"
                      r"are you able|production or sandbox)", re.I)
_COURTESY = re.compile(r"^(hi|hello|yes|no|ok|okay|thanks?|thank you|great|check( it)? now|in tabular)\b", re.I)
_DATA_WORD = re.compile(r"\b(fta|coq|copq|eff\w*|quality|yield|volume|prod\w*|month|week|days?|users?|"
                        r"process|work ?units?|editors?|operators?|tasks?)\b", re.I)
# Synthesis for management, or judgement: actions, risks, insights
_REASON = re.compile(r"\b(insights?|risks?|actions?|recommend\w*|suggest\w*|why|root[ -]?cause|improve\w*|"
                     r"mitigat\w*|prioriti[sz]\w*|forecast\w*|predict\w*|when will|health report|analy[sz]\w*|"
                     r"assess\w*|what should|next steps?|executive|leadership|management|comprehensive|"
                     r"status report\w*)\b", re.I)
_JIRA_KEY = re.compile(r"\b(?!(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC|W|Q|FY)-)[A-Z][A-Z0-9]{1,9}-\d+\b")
_LOOKUP = re.compile(r"\b(jira|confluence|cofluence|tickets?|pages?)\b", re.I)
_TICKET = re.compile(r"\bcreate\b.*\b(ticket|jira)\b|\b(ticket|jira)\b.*\bcreate\b", re.I)
_MULTI = re.compile(r"\b(week[ -]?(on|wise)[ -]?week|week wise|unit wise|per (work ?unit|editor|process)|trend|"
                    r"compar\w*|cumulative|all process types|summar\w*|full \w+ report|every details?|"
                    r"in (a )?(single )?table)\b", re.I)


def from_text(msg: str) -> str:
    """Category for an old log line that only has the question text."""
    m = (msg or "").strip()
    lookup = bool(_JIRA_KEY.search(m) or _LOOKUP.search(m))
    if _CLARIFY.match(m) or (len(m) < 40 and _COURTESY.match(m)):
        return "follow_up"
    if len(m) < 25 and not lookup and not _DATA_WORD.search(m):
        return "follow_up"
    if _TICKET.search(m):
        return "jira_ticket"
    if _REASON.search(m):
        return "reasoning"
    if lookup:
        return "lookup"
    if _MULTI.search(m):
        return "data_multi"
    return "data_single"


def _ts(c: dict) -> float:
    d = datetime.fromisoformat(c["ts"].replace("Z", "+00:00"))
    return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).timestamp()


def value(chats: list, feedback: list | None = None) -> dict:
    """Time saved for a list of usage_log entries (already filtered to the period)."""
    disliked = {(f.get("email", "").lower(), (f.get("question") or "")[:90].strip().lower())
                for f in (feedback or []) if str(f.get("rating", "")).lower() in ("dislike", "down", "bad", "-1", "👎")}
    last_seen: dict = {}
    out = {"answered": 0, "failed": 0, "repeats": 0, "disliked": 0, "measured": 0, "estimated": 0,
           "minutes": 0.0, "low": 0.0, "high": 0.0, "by_cat": Counter(), "min_by_cat": defaultdict(float),
           "per_user": defaultdict(float)}
    for c in sorted(chats, key=_ts):
        email, msg = c.get("email", "").lower(), (c.get("msg") or "").strip()
        if c.get("ok") is False:
            out["failed"] += 1
            continue
        out["answered"] += 1
        key, t = (email, msg.lower()), _ts(c)
        repeat = key in last_seen and t - last_seen[key] <= REPEAT_WINDOW_S
        last_seen[key] = t
        if repeat:
            out["repeats"] += 1
            continue
        if key in disliked:
            out["disliked"] += 1
            continue
        if "minutes" in c:
            out["measured"] += 1
            cat, m, lo, hi = c.get("category", "data_single"), c["minutes"], c["minutes_low"], c["minutes_high"]
        else:
            out["estimated"] += 1
            cat = from_text(msg)
            m, lo, hi = TABLE[cat]
        out["by_cat"][cat] += 1
        out["min_by_cat"][cat] += m
        out["per_user"][email] += m
        out["minutes"] += m; out["low"] += lo; out["high"] += hi
    return out
