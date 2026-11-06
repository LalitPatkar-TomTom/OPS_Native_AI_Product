"""Shared test setup for the OPS Native AI engine.

Before any engine module imports, every output, DB and switch is pointed at a temporary folder
or cleared, so a test run never reads the laptop .env switches, never writes the real analytics
DB and never sends email (delivery is replaced by a recorder in the tests that need it).
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TMP = Path(tempfile.mkdtemp(prefix="nativeai-tests-"))

os.environ["OPS_OUTPUT_DIR"] = str(TMP / "output")
os.environ["OPS_BACKUP_DIR"] = str(TMP / "backups")
# Set (empty) before config.py loads .env, so load_dotenv(override=False) keeps them empty
for key in ("TEST_RECIPIENT_OVERRIDE", "PREVIEW_MODE", "FORCE_UC4_ALERT", "OPS_AUDIT_TEST",
            "EMAIL_PARALLEL_TO", "EMAIL_CC", "EMAIL_TRANSPORT", "MAIL_SENDER", "MAIL_CLIENT_SECRET",
            "TEAMS_WEBHOOK_URL", "JIRA_API_TOKEN", "ATL_TOKEN", "DATABRICKS_PAT_TOKEN"):
    os.environ[key] = ""
os.environ["ATLASSIAN_VIA_MCP"] = "0"

sys.path.insert(0, str(ROOT / "MultiAgent_Briefing"))
sys.path.insert(0, str(ROOT / "MultiAgent_Briefing" / "agents"))
sys.path.insert(0, str(ROOT / "azure"))


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _no_jira_project_lookup(request, monkeypatch):
    """Tests never call Jira: the project-exists lookup (jira_agent.project_missing) answers "exists" unless a
    test is marked real_project_lookup and stubs httpx itself."""
    if request.node.get_closest_marker("real_project_lookup"):
        return
    from agents import jira_agent
    monkeypatch.setattr(jira_agent, "project_missing", lambda key: False)
    # the per-key lookup for profiles with several keys (OSI-061) also never reaches Jira in tests
    monkeypatch.setattr(jira_agent, "project_status", lambda key: "ok")
