# ADR-001: Deterministic engine, no LLM in the decision or send path

**Status:** Accepted.

## Context
The engine sends emails to many people, four times a day, with no person reviewing each one first.
An alert that fires wrongly, a number that is made up, or text an LLM invented would go straight to
users' inboxes.

## Decision
- **Rules decide:** whether to send, to whom, and which numbers to show are decided by code, from the
  user's profile and the source data:
  - SLA hours;
  - the user's own alert level and direction for each metric;
  - quiet hours;
  - one alert per day.
- **Templates format:** emails and Word reports are rendered from fixed templates.
- **Priorities by rule:** recommended actions (P0, P1, P2) come from rules over that data.
- **The LLM's place:** the LLM is used only where a person reads the output before it matters. That
  is the OPS Hub chat, the Status Report text, and the one-off merge of a user's onboarding answers
  into their profile.

## Consequences
- **Reproducible:** every email can be explained and re-created from the data and the profile, and
  the unit tests can pin the behaviour.
- **No prompt injection:** text in Jira or Confluence cannot change what is sent. It is HTML-escaped
  into the email as plain text.
- **Less flexible wording:** narrative is template-based, so it is less flexible than LLM prose.

## Revisit when
Users ask for a narrative summary in the briefing. Add it as a clearly labelled, optional section,
and keep the decision logic deterministic.
- **Enforced (29 Oct 2026):** `tests/test_no_llm.py` fails the build if an AI-model library or a Databricks
  Model Serving call appears in the shipped code, or if the job is given a model setting. The retired laptop
  onboarding server, the only code here that called a model, is in `_archive/`. Using an LLM in the engine
  later (e.g. wording on top of rule-based facts) needs a new ADR that replaces this one.
