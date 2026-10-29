# Archive: retired code, kept for history (not shipped, not run)

Nothing in this folder is in the Docker image (`.dockerignore` excludes `_archive`), started by
`start.bat`, scheduled, or imported by the engine.

| Item | What it was | Replaced by | Archived |
|---|---|---|---|
| `Onboarding_Server/` | The first laptop onboarding server (`server.py` on `localhost:8010`, `watcher.py`). Its `merge_skills.py` called Claude Sonnet on Databricks Model Serving to merge a user's onboarding answers into their SKILL.md. Last changed 9 Oct 2026; its upload folder holds only one profile, from 8 Oct. | OPS Hub `/onboarding` (`OPSHUB/app/api/onboarding_routes.py`, `OPSHUB/app/merge_skills.py`), which saves profiles to the skills share the Azure job mounts. | 29 Oct 2026 |
| `UserOnboarding.HTML` | The laptop onboarding form that posted to that server. | The OPS Hub onboarding page. | 29 Oct 2026 |

Why archived rather than deleted: it is the history of how onboarding started. Why moved out of
`AI Architecture/`: it was the only code in this repo that called an AI model, and it made the
engine look as if it used one. The engine makes no LLM call (ADR-001); `tests/test_no_llm.py`
checks this. SECURITY.md listed this server (CORS `*`, local OAuth tokens) as "archive or delete".
