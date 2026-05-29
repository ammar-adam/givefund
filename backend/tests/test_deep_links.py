"""Unit tests for checkout deep links and donor prefill."""

from deep_links import build_donate_url, checkout_assist


def test_gofundme_donate_path():
    url = build_donate_url(
        platform="gofundme",
        campaign_url="https://www.gofundme.com/f/help-maria",
        campaign_id=42,
        donor_email="donor@example.com",
    )
    assert "/donate" in url
    assert "utm_source=givefund" in url
    assert "utm_content=42" in url


def test_givebutter_email_prefill():
    url = build_donate_url(
        platform="givebutter",
        campaign_url="https://givebutter.com/c/example",
        donor_email="donor@example.com",
        donor_name="Jane Doe",
    )
    assert "email=donor%40example.com" in url or "email=donor@example.com" in url
    assert "fname=Jane" in url
    assert "lname=Doe" in url


def test_checkout_assist_wallet_saved():
    data = checkout_assist(
        platform="givebutter",
        campaign_url="https://givebutter.com/c/example",
        campaign_id=1,
        title="Test",
        donor_email="a@b.com",
        donor_name="A B",
        wallet_saved=True,
    )
    assert data["wallet_saved"] is True
    assert data["link_likely"] is True
    assert "email" in data["prefill_fields"]
    assert "name" in data["prefill_fields"]
