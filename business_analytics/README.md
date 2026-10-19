# Business value analytics (OPS Native AI + OPS Hub)

Rebuilds the *OPS_NativeAI_OPSHub_Business_Value_Report* (Word + PDF). All reads are read-only.

| Step | Script | Source | Output |
|---|---|---|---|
| 1 | `ba_extract.py` | `MultiAgent_Briefing/output/trigger_audit.db` (events from 9 Oct, runs/emails from 13 Oct), profile skill files | `ba_data.json` |
| 2 | `ba_extract2.py` | `MultiAgent_Briefing/output/task_scheduler.log` (from 1 Oct) | `ba_data2.json` |
| 3 | `ba_extract3.py` | OPS Hub Container App logs in Log Analytics (needs `az login`) | `ba_data3.json` |
| 4 | `ba_report.py` | the three JSON files | charts (`c_*.png`) + `.docx` in `Deployed\` |
| 5 | `to_pdf.ps1` | latest report `.docx` | `.pdf` next to it |

```
python ba_extract.py
python ba_extract2.py
python ba_extract3.py
python ba_report.py
powershell -File to_pdf.ps1
```

Needs `python-docx` and `matplotlib`. The JSON files here are the 19 Oct 2026 snapshot.

**Not final:** the report date/cut-off, some narrative text and the minutes-per-item
assumptions (`ba_report.py`) are hard-coded for the 19 Oct edition; the productivity
numbers are to be revisited (e.g. UC4 counts alert emails from 1 Oct, distinct breaches
are only tracked from 9 Oct). Planned replacement: Databricks Delta tables + a dashboard
(section 9 of the report).
