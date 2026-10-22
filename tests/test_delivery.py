"""Who receives an email (MultiAgent_Briefing/delivery.py).

Rules under test: only the profile owner receives the email; EMAIL_CC=off (the Azure job) removes
every CC; a parallel run redirects to one address; any recipient that is not exactly one
@tomtom.com address is refused.
"""
import pytest

import audit_log
import delivery

OWNER = {"user": "jane.doe@tomtom.com"}


@pytest.fixture
def sent(monkeypatch):
    calls = []
    monkeypatch.setattr(delivery, "_send_email",
                        lambda to, subject, body, cc_emails=None, attachment_path=None:
                        (calls.append({"to": to, "subject": subject, "cc": cc_emails}) or True, "test"))
    monkeypatch.setattr(audit_log, "log_delivery", lambda **kw: None)
    return calls


def test_owner_only_when_cc_off(sent, monkeypatch):
    monkeypatch.setenv("EMAIL_CC", "off")
    r = delivery.deliver("c", OWNER, subject="S", html_body="<p>x</p>", cc_recipients=["x@tomtom.com"])
    assert r["email"] is True
    assert sent == [{"to": "jane.doe@tomtom.com", "subject": "S", "cc": []}]


def test_default_adds_profile_and_global_cc(sent, monkeypatch):
    monkeypatch.delenv("EMAIL_CC", raising=False)
    delivery.deliver("c", OWNER, subject="S", html_body="h", cc_recipients=["x@tomtom.com"])
    assert sent[0]["cc"] == ["x@tomtom.com"] + delivery.GLOBAL_CC


def test_parallel_run_redirects_to_one_address(sent, monkeypatch):
    monkeypatch.setenv("EMAIL_CC", "off")
    monkeypatch.setenv("EMAIL_PARALLEL_TO", "checker@tomtom.com")
    delivery.deliver("c", OWNER, subject="S", html_body="h")
    assert sent[0]["to"] == "checker@tomtom.com" and sent[0]["cc"] == []
    assert sent[0]["subject"] == "[AZURE PARALLEL → jane.doe@tomtom.com; no cc] S"


@pytest.mark.parametrize("owner", ["jane@tomtom.com;evil@example.com", "evil@example.com",
                                   "Jane <jane@tomtom.com>", "nobody", ""])
def test_invalid_owner_is_never_sent(sent, owner):
    r = delivery.deliver("c", {"user": owner}, subject="S", html_body="h")
    assert r["email"] is False and sent == []


def test_invalid_cc_is_dropped(sent, monkeypatch):
    monkeypatch.delenv("EMAIL_CC", raising=False)
    delivery.deliver("c", OWNER, subject="S", html_body="h",
                     cc_recipients=["ok@tomtom.com", "a@tomtom.com;b@x.com", "ext@gmail.com"])
    assert sent[0]["cc"] == ["ok@tomtom.com"] + delivery.GLOBAL_CC


@pytest.mark.parametrize("addr,ok", [("Kavita.Vajpai@tomtom.com", True), ("a.b@TomTom.com", True),
                                     ("a@tomtom.com.evil.io", False), ("a@b@tomtom.com", False)])
def test_is_valid_recipient(addr, ok):
    assert delivery.is_valid_recipient(addr) is ok
