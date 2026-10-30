"""Send the prototype mail from the automated sender (MAIL_SENDER via Graph), to the user only, charts inline.

Reuses OPS Native AI's delivery token helper read-only (nothing in the repo changes); delivery's own
_send_graph has no inline-image support, so the message is posted here with isInline attachments.
"""
import base64, os, sys
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, "/app/MultiAgent_Briefing")
import delivery  # noqa: E402  (loads the app's .env through its config)
import httpx  # noqa: E402

TO = "lalit.patkar@tomtom.com"
SUBJECT = "[PROTOTYPE] RM Lanes · root cause and actions · week 19–25 Oct (future-state mail)"
sender = os.getenv("MAIL_SENDER", "").strip()
assert sender and os.getenv("MAIL_CLIENT_SECRET", "").strip(), "Graph mail not configured"
html = (HERE / "mail.html").read_text(encoding="utf-8")
atts = [{"@odata.type": "#microsoft.graph.fileAttachment", "name": f, "contentType": "image/png", "isInline": True,
         "contentId": f, "contentBytes": base64.b64encode((HERE / f).read_bytes()).decode("ascii")}
        for f in ("coq.png", "eff.png", "fta.png")]
msg = {"subject": SUBJECT, "body": {"contentType": "HTML", "content": html},
       "toRecipients": [{"emailAddress": {"address": TO}}], "attachments": atts}
r = httpx.post(f"https://graph.microsoft.com/v1.0/users/{sender}/sendMail",
               headers={"Authorization": f"Bearer {delivery._graph_access_token()}"},
               json={"message": msg, "saveToSentItems": True}, timeout=60)
print("from", sender, "to", TO, "HTTP", r.status_code, "" if r.status_code == 202 else r.text[:200])
