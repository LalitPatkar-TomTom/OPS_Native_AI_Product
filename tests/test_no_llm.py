"""ADR-001 guard (29 Oct 2026): the engine and the job scripts make no LLM call and carry no model setting.

Scans everything that goes into the image (MultiAgent_Briefing, azure) for AI-model libraries and for the
Databricks Model Serving path, so a model call cannot slip in unnoticed; the AI model belongs to OPS Hub.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHIPPED = [ROOT / "MultiAgent_Briefing", ROOT / "azure"]
AI_IMPORT = re.compile(r"^\s*(import|from)\s+(openai|anthropic|langchain\w*|transformers|litellm|google\.generativeai|"
                       r"mlflow\.deployments|databricks_genai)\b", re.M)
MODEL_CALL = re.compile(r"serving-endpoints|/invocations\b|chat\.completions|messages\.create\(")


def _files():
    for base in SHIPPED:
        for p in base.rglob("*.py"):
            if "output" not in p.parts and "__pycache__" not in p.parts:
                yield p


def test_no_ai_model_library_or_model_call_in_shipped_code():
    hits = []
    for p in _files():
        t = p.read_text(encoding="utf-8", errors="ignore")
        hits += [f"{p.relative_to(ROOT)}: {m.group(0).strip()}" for m in AI_IMPORT.finditer(t)]
        hits += [f"{p.relative_to(ROOT)}: {m.group(0)}" for m in MODEL_CALL.finditer(t)]
    assert not hits, "LLM use in the engine needs a new ADR first:\n" + "\n".join(hits)


def test_no_ai_library_in_the_image_requirements():
    req = (ROOT / "azure" / "requirements-azure.txt").read_text(encoding="utf-8").lower()
    assert not re.search(r"^(openai|anthropic|langchain|transformers|litellm)\b", req, re.M)


def test_job_gets_no_model_setting():
    import deploy_job
    assert "DATABRICKS_LLM_MODEL" not in deploy_job.PLAIN
    assert deploy_job.SKIP.match("DATABRICKS_LLM_MODEL")          # dropped, not turned into a secret


def test_retired_onboarding_server_is_archived_and_not_shipped():
    assert not (ROOT / "AI Architecture" / "Onboarding_Server").exists()
    assert (ROOT / "_archive" / "Onboarding_Server" / "merge_skills.py").exists()
    assert "_archive" in (ROOT / ".dockerignore").read_text(encoding="utf-8").split()
