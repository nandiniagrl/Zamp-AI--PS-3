import pytest

from app.safety.sensitive import classify
from app.verification.credibility import assess, is_official, registrable


@pytest.mark.parametrize("domain, expected", [
    ("boards.greenhouse.io", "greenhouse.io"), ("news.bbc.co.uk", "bbc.co.uk"), ("www.stripe.com", "stripe.com"),
])
def test_registrable(domain, expected):
    assert registrable(domain) == expected


def test_official_domain_detection():
    assert is_official("stripe.com", "Stripe Inc.")
    assert is_official("www.acmeanalytics.com", "Acme Analytics")
    assert not is_official("techcrunch.com", "Acme Analytics")
    assert not is_official("st.com", "St")  # too short to trust


@pytest.mark.parametrize("domain, ctype, level", [
    ("stripe.com", "funding", "high"),
    ("techcrunch.com", "funding", "high"),
    ("businesswire.com", "funding", "medium"),
    ("boards.greenhouse.io", "hiring", "medium"),
    ("boards.greenhouse.io", "funding", "low"),
    ("instagram.com", "other", "low"),
    ("randomblog.example", "funding", "low"),
    ("economictimes.indiatimes.com", "expansion", "high"),   # full-host match (regression)
    ("timesofindia.indiatimes.com", "expansion", "low"),
])
def test_credibility_levels(domain, ctype, level):
    assert assess(domain, ctype, "Stripe")[0] == level


def test_sensitive_classification():
    assert classify("Acme lays off 12% of staff", "", "other", False) == (True, "layoffs")
    assert classify("x", "", "security_incident", False) == (True, "security incident")
    assert classify("Acme faces class action lawsuit", "", "other", False)[0]
    assert classify("Acme launches product", "", "product_launch", True) == (True, "flagged by model")
    assert classify("Acme launches product", "", "product_launch", False) == (False, None)
