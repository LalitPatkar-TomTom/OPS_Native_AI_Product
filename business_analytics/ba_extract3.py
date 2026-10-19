"""OPS Hub usage per day from the Container App logs (Azure Log Analytics). Writes ba_data3.json.

Needs `az login` with read access to the ops-hub-rg Log Analytics workspace.
"""
import json
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).resolve().parent
WORKSPACE = "0dee71b1-5bb6-47a3-b997-22d1db955f7a"
SINCE = "2026-09-25"

Q_ENDPOINTS = rf"""ContainerAppConsoleLogs_CL
| where ContainerAppName_s == 'tomtom-ops-hub' and TimeGenerated > datetime({SINCE})
| extend ep = extract(@'"(?:GET|POST) (/api/[A-Za-z0-9_/-]+)', 1, Log_s), code = extract(@'HTTP/1.1" (\d{{3}})', 1, Log_s)
| where ep in ('/api/chat', '/api/onboarding/submit', '/api/sr/generate-job', '/api/sr/generate', '/api/sr/export/word', '/api/auth/me', '/api/feedback')
| summarize n=count(), ok=countif(code startswith '2') by day=format_datetime(TimeGenerated, 'yyyy-MM-dd'), ep
| order by day asc"""

Q_USERS = rf"""ContainerAppConsoleLogs_CL
| where ContainerAppName_s == 'tomtom-ops-hub' and TimeGenerated > datetime({SINCE}) and Log_s has 'numberOfUniqueAuthenticatedUsers'
| extend u = toint(extract(@'numberOfUniqueAuthenticatedUsers\\?":(\d+)', 1, Log_s))
| summarize peak_users_per_minute=max(u), active_minutes=countif(u > 0) by day=format_datetime(TimeGenerated, 'yyyy-MM-dd') | order by day asc"""


def run(query: str) -> list:
    with tempfile.TemporaryDirectory() as tmp:
        body, res = Path(tmp) / "q.json", Path(tmp) / "r.json"
        body.write_text(json.dumps({"query": query}), encoding="utf-8")
        subprocess.run(
            ["az", "rest", "--method", "post",
             "--url", f"https://api.loganalytics.io/v1/workspaces/{WORKSPACE}/query",
             "--resource", "https://api.loganalytics.io",
             "--body", f"@{body}", "--output-file", str(res)],
            check=True, shell=(sys.platform == "win32"))
        return json.loads(res.read_text(encoding="utf-8"))["tables"][0]["rows"]


by_day = defaultdict(dict)
for day, ep, n, ok in run(Q_ENDPOINTS):
    by_day[day][ep.replace("/api/", "")] = f"{ok}/{n}"
users = run(Q_USERS)

json.dump({"ops_hub_by_day": by_day, "ops_hub_users": users}, open(OUT / "ba_data3.json", "w"), indent=1)
for k in sorted(by_day):
    print(k, by_day[k])
print("--- unique signed-in users (peak per minute) ---")
for r in users:
    print(r)
