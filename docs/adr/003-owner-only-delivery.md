# ADR-003: Owner-only delivery through Microsoft Graph from a shared mailbox

**Status:** Accepted (19 Oct 2026, the product owner's rule for going live from Azure).

## Context
In the pilot, Outlook on the laptop sent the emails, with CCs to leads. From Azure there is no
Outlook, and emails about one person's projects should not reach others by default.

## Decision
- **Sender:** email goes through Microsoft Graph `sendMail` from the dedicated mailbox
  `opsai@tomtom.com`, with `saveToSentItems`.
- **Recipient:** the only recipient is the profile owner. That is the profile's file name, and it must
  be exactly one `@tomtom.com` address.
- **No CC:** `EMAIL_CC=off` removes all CCs.
- **Exceptions:** two operational mails are deliberate exceptions: the profile-check email (the OPS
  Native AI team is in CC) and the weekly analytics report (a fixed list of readers).
- **Recorded:** every delivery is recorded, with to, cc, intended owner and transport.
- **Parallel mode:** `EMAIL_PARALLEL_TO` sends everything to one checker address during a cut-over.

## Consequences
- **Privacy:** a user's operational data reaches only that user, and the recipient rule is enforced
  in code and tested.
- **Visible in the analytics:** reach and value can be measured per person.
- **Shared app registration:** Mail.Send is granted on the OPS Hub sign-in app for now. A dedicated
  sender app (OSI-021) would separate the duties.

## Revisit when
Teams need shared digests, for example one per project for a whole team. That would be a new use case
with its own list of recipients, not a CC on personal mails.
