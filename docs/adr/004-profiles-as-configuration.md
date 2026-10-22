# ADR-004: A personal SKILL.md profile per user is the configuration

**Status:** Accepted.

## Context
What matters differs between users:
- **Scope:** each user has their own projects, Jira keys, Databricks process types and planning IDs.
- **Metrics:** each user follows different metrics, with their own alert levels and directions.
- **Timing:** each user has their own quiet hours and active use cases.

Users had to be able to change these without a developer or a deploy.

## Decision
- **One profile per user:** each user has one Markdown profile, `<email>_skill.md`, created and
  updated through OPS Hub onboarding.
- **Merge:** the form answers are merged with the user's domain SKILL.md by the LLM, once.
- **Profile storage:** the profile is stored on the shared `opshub-skills` share, and the job reads it
  at every run.
- **Parsing:** `skill_registry.py` parses the profile with tolerant rules (tables or prose) into
  typed settings.
- **Feedback to the user:** `profile_check.py` emails the user what the engine understood, and what
  to fix, whenever the profile changes.

## Consequences
- **Self-service:** a user's change applies at the next run, with no deploy. The engine has no
  per-user code.
- **Human-readable:** profiles can be reviewed and versioned like documents.
- **Tolerant parsing:** a badly written profile can parse wrongly. That is mitigated by:
  - the parser tests;
  - the profile-check email;
  - `scripts/check_profiles.py`, part of every release check;
  - the onboarding form structure.

## Revisit when
The number of users makes Markdown review impractical. Store the parsed settings as structured data
(JSON) next to the Markdown, and validate it against a schema when it is saved.
