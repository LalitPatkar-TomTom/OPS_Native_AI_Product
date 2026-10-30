# Prototype: root-cause lead mail (28 Oct 2026)

The hand-built prototype shown to stakeholders on 28 Oct (RM Lanes, week 19–25 Oct): root causes and actions
instead of numbers. It led to the rule-based root causes in the product (`agents/root_cause.py`, ADR-008).

- `explore.py`, `explore3.py`: read-only Databricks extracts (run from `OPSHUB/`, output path as argument).
- `build_mail.py`: builds `mail.html` + charts from `data.json` / `data3.json` next to it; `--send` to the user only.
- `send_graph.py`, `send_graph_job.py`: send it from opsai@ (Graph), to the user only.

The data files and the built mail hold real editor data: they are git-ignored and must not be committed.
Run it in a working folder outside the repo, e.g. `Deployed/Prototype_LeadMail_2026-10-28/`.
