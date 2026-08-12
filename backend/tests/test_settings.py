"""Settings parsing, which is deployment-critical and easy to get wrong silently."""

from __future__ import annotations

from backend.app.config.settings import Settings


def test_defaults_allow_the_local_frontend():
    assert Settings().cors_origins == ["http://localhost:3000"]
    assert Settings().cors_origin_regex is None


def test_comma_separated_origins_are_split(monkeypatch):
    monkeypatch.setenv(
        "PRIVATEPERP_CORS_ORIGINS",
        "https://demo.vercel.app, https://example.com",
    )
    assert Settings().cors_origins == ["https://demo.vercel.app", "https://example.com"]


def test_json_origins_still_parse(monkeypatch):
    monkeypatch.setenv("PRIVATEPERP_CORS_ORIGINS", '["https://demo.vercel.app"]')
    assert Settings().cors_origins == ["https://demo.vercel.app"]


def test_a_single_origin_needs_no_delimiter(monkeypatch):
    monkeypatch.setenv("PRIVATEPERP_CORS_ORIGINS", "https://demo.vercel.app")
    assert Settings().cors_origins == ["https://demo.vercel.app"]


def test_an_empty_variable_falls_back_to_the_default(monkeypatch):
    """A blank dashboard field must not silently block every origin."""
    monkeypatch.setenv("PRIVATEPERP_CORS_ORIGINS", "")
    assert Settings().cors_origins == ["http://localhost:3000"]

    monkeypatch.setenv("PRIVATEPERP_CORS_ORIGINS", "   ")
    assert Settings().cors_origins == ["http://localhost:3000"]


def test_origin_regex_is_configurable(monkeypatch):
    """Vercel preview deployments get a fresh hostname on every push."""
    monkeypatch.setenv(
        "PRIVATEPERP_CORS_ORIGIN_REGEX", r"https://.*\.vercel\.app"
    )
    assert Settings().cors_origin_regex == r"https://.*\.vercel\.app"
