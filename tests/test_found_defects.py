"""Defects found by exploratory testing (not planted). Strict xfail, same convention as the planted ones."""
import pytest


@pytest.mark.xfail(strict=True, reason="BUG-006 docs/bugs/BUG-006.md: whitespace-only title accepted")
@pytest.mark.parametrize("title", ["     ", "  ab  "])
def test_bug006_title_must_have_enough_real_characters(client, reporter, title):
    r = client.post("/api/issues", json={"title": title, "component": "Mail"}, headers=reporter)
    assert r.status_code == 422


def test_second_login_replaces_the_first_token(client):
    """Documents current behaviour (one token per user). Raised as a question in the testability review."""
    login = {"username": "rita", "password": "test-pass"}
    first = client.post("/api/auth/login", json=login).json()["token"]
    second = client.post("/api/auth/login", json=login).json()["token"]
    assert client.get("/api/issues", headers={"Authorization": f"Bearer {first}"}).status_code == 401
    assert client.get("/api/issues", headers={"Authorization": f"Bearer {second}"}).status_code == 200
