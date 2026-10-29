"""Config for the Onboarding Server — loaded from .env."""
from pathlib import Path
from pydantic_settings import BaseSettings

_HERE = Path(__file__).parent


class Settings(BaseSettings):
    # ── Microsoft Graph OAuth (per-user delegated) ────────────────────────────
    graph_client_id: str = ""
    graph_client_secret: str = ""
    graph_tenant_id: str = ""
    graph_redirect_uri: str = "http://localhost:8000/auth/microsoft/callback"

    # ── Slack OAuth (per-user) ────────────────────────────────────────────────
    slack_oauth_client_id: str = ""
    slack_oauth_client_secret: str = ""
    slack_redirect_uri: str = "http://localhost:8000/auth/slack/callback"

    # ── Databricks LLM (used by the skill merger) ─────────────────────────────
    # Same workspace + same credentials as MultiTenantAgent_V3 — copy from its .env
    databricks_host: str = ""
    databricks_llm_model: str = "databricks-claude-sonnet-4-6"
    # Auth option 1 — PAT token (takes priority if set)
    databricks_pat_token: str = ""
    # Auth option 2 — Azure AD Service Principal (same as MultiTenantAgent_V3)
    databricks_client_id: str = ""
    databricks_client_secret: str = ""
    databricks_azure_tenant_id: str = ""

    # ── Databricks SQL (used by scope-options endpoint for onboarding form) ──
    databricks_sql_warehouse_id: str = ""
    databricks_combined_table: str = "mo_occ_reporting.manual_efficiency.manual_efficiency_quality_all_weekly_tbl"

    # ── Skills directories ────────────────────────────────────────────────────
    # _HERE = AI Architecture/Onboarding_Server/
    # _HERE.parent = AI Architecture/  (all skill data lives here)
    skills_uploads_dir: str  = str(_HERE.parent / "skills" / "uploads")
    skills_combined_dir: str = str(_HERE.parent / "skills" / "Personal Skills")
    skills_domains_dir: str  = str(_HERE.parent / "skills")

    # ── Server ────────────────────────────────────────────────────────────────
    port: int = 8010
    log_level: str = "INFO"

    # ── Token storage ─────────────────────────────────────────────────────────
    tokens_dir: str = str(_HERE.parent / "skills" / "tokens")

    model_config = {
        # .env is two levels up: AI Architecture/Onboarding_Server/ -> OPS_Native_AI/
        "env_file": str(Path(__file__).resolve().parent.parent.parent / ".env"),
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }
