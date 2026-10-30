# Weekly "What's new" email (every Friday)

Every Friday after the 17:00 IST run, the Azure job sends **"What's new in OPS Native AI & OPS Hub"**
from opsai@tomtom.com to **all beta users** (the owner of every profile on the skills share, so new users
are included automatically) plus the stakeholders in `whats_new.py` (To: Ketki, Pratish, Vrushali;
CC: Peter Clarys, Seema Nayyar, Saurav Nanda). Like the Monday weekly analytics email, it runs from
`azure/entrypoint.sh`; there is no review step (user, 30 Oct 2026).

**Content = `notes.json`: functional, not technical.** At every release that changes what users see,
add one note per change, in plain words: what users can now see or do. No code, table or file names.
`highlight: true` puts a note in the box at the top. `coming_next` is the list at the end.
No AI model writes the email: the notes are written by a person (`tests/test_whats_new.py` checks the file).

Safe by design:
- only the notes dated after the last Friday's email (marker `native-ai/whats_new_sent.json` on the share);
- a week without notes sends nothing; a second run the same Friday sends nothing;
- `python send_weekly.py --dry-run --today YYYY-MM-DD` shows what would go out.

Local preview: `python whats_new.py <friday> --send-to-me` (writes the HTML to `Deployed/OPS_NativeAI_Docs/WhatsNew/`
and sends a copy to Lalit only from his Outlook).
