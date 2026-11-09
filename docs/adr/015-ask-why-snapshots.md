# ADR-015: "Ask why" — each email's numbers saved as a snapshot, opened in OPS Hub

**Status:** Proposed (branch `ask-why`, not released) · **Date:** 9 Nov 2026 · **Issues:** OSI-039, OSI-045 ·
**OPS Hub side:** OPS Hub ADR-012

## Context
Users see a number in an email (FTA 91%, CoQ 8%) and ask "why?". The answer sits in breakdowns the engine already
computes — process types, work units, operators, the 8-week trend, root cause — but an email can only show a part.

## Decision
- Before an email is built, `ask_why.snapshot()` saves the parts of the analytics result the email is made from
  (a fixed list, `_KEEP`), the period exactly as the email header words it, and the email's judging rules (10 QC'd
  tasks to judge a sample, 8 production hours to judge an operator), as `<32 hex>.json` on the opshub-config share
  (`/data/config/drill`). The id comes from `secrets` and is never reused, so nothing is overwritten.
- The email links carry only that id and the metric: `<OPS Hub>/why?r=<id>&m=fta`. UC1 and UC3 get one
  "Ask why: FTA · Efficiency · CoQ · Yield" row under the KPI boxes, UC4 a "See why →" per alerting metric.
- OPS Hub opens its chat for the snapshot's owner (or an admin): the first question and answer are built from
  the snapshot without an LLM, so the chat starts with the email's exact numbers; deeper questions are normal chat
  turns in OPS Hub (tokens there, never here). People without OPS Hub access see no numbers (OPS Hub ADR-012).
- Rules only, no LLM (ADR-001; `test_no_llm.py` scans this module). Snapshots are never deleted (ADR-009).
- `ASK_WHY=1` switches it on; **off by default**, because an email must not link to a page that is not live yet.
  Release order: OPS Hub first, then `ASK_WHY=1` on the job. Off, every email is byte-identical to before
  (checked on 9 Nov for UC1 per process type, UC1 classic, UC3 and UC4).
- A save problem leaves the links out; the email is never held up.

## Consequences
- One small file per email with a link (83 KB for a 3-process-type scope with operator level, mostly operators).
- The share holds per-email numbers, including operator names when the profile has operator level, as the
  email does; only the owner and admins can open them.
- Not yet: links from single table cells, UC2 (Jira) numbers.
