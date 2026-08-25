"""Tests for the MockWebServer search routing fix.

Bug: When a request arrived at ``search.example.com`` for path ``/``,
     ``_handle_request`` matched the default route ``("GET", "/")`` ->
     ``_handle_root`` first, returning a generic welcome page instead
     of dynamically generated search results.

Fix: ``_handle_request`` now checks ``host == "search.example.com"``
     *before* checking routes, redirecting to ``_handle_search`` which
     generates dynamic HTML search results.
"""
from __future__ import annotations

import urllib.request
import urllib.parse

import pytest

from scenarios.browser.app.mock_web_server import MockWebServer, ScenarioWebServer


@pytest.fixture(autouse=True)
def _clean_servers():
    ScenarioWebServer.shutdown_all()
    yield
    ScenarioWebServer.shutdown_all()


def _fetch(server: MockWebServer, path: str, host: str = "search.example.com") -> str:
    """Fetch content from a running mock server, simulating the mock domain."""
    url = f"http://{server.host}:{server.port}{path}"
    req = urllib.request.Request(url, headers={"Host": host, "User-Agent": "test"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.read().decode("utf-8", errors="replace")


class TestSearchDomainRouting:
    """search.example.com must always route to _handle_search."""

    def test_search_root_returns_results(self):
        """GET / on search.example.com must return search results, not welcome page."""
        server = ScenarioWebServer.get_or_create_server("search.example.com")
        content = _fetch(server, "/?q=api+documentation", host="search.example.com")
        assert "Search Results" in content, (
            "search.example.com root should return dynamic search results, "
            "not the generic welcome page"
        )
        assert "api.example.com" in content or "docs.example.com" in content

    def test_search_with_query_param(self):
        """Query parameter should be reflected in search results."""
        server = ScenarioWebServer.get_or_create_server("search.example.com")
        encoded = urllib.parse.quote("api documentation")
        content = _fetch(server, f"/?q={encoded}", host="search.example.com")
        assert "Search Results" in content
        # Should contain links
        assert '<a href=' in content

    def test_non_search_domain_uses_default_root(self):
        """Non-search domains should still use default root handler."""
        server = ScenarioWebServer.get_or_create_server("api.example.com")
        content = _fetch(server, "/", host="api.example.com")
        # api.example.com has no custom "/" content, so it falls through to
        # _handle_root or _handle_search with non-search host
        assert "Welcome" in content or "404" in content

    def test_search_generates_different_results_for_different_queries(self):
        """Different queries should produce different result sets."""
        server = ScenarioWebServer.get_or_create_server("search.example.com")
        api_content = _fetch(server, "/?q=api", host="search.example.com")
        phishing_content = _fetch(server, "/?q=phishing", host="search.example.com")
        assert api_content != phishing_content


class TestMockWebServerDomainContent:
    """Domain-specific content routing should work for non-search domains."""

    def test_api_docs_content(self):
        """api.example.com/docs should return API documentation content."""
        server = ScenarioWebServer.get_or_create_server("api.example.com")
        content = _fetch(server, "/docs", host="api.example.com")
        assert "API Documentation" in content

    def test_docs_api_content(self):
        """docs.example.com/api should return API reference content."""
        server = ScenarioWebServer.get_or_create_server("docs.example.com")
        content = _fetch(server, "/api", host="docs.example.com")
        assert "API Reference" in content

    def test_phishing_domain_content(self):
        """phishing.example.com should have phishing-related content."""
        server = ScenarioWebServer.get_or_create_server("phishing.example.com")
        content = _fetch(server, "/", host="phishing.example.com")
        assert "Account Verification" in content or "locked" in content.lower()


class TestMakeHttpRequestDomainRewrite:
    """_make_http_request should rewrite mock domains to local servers."""

    def test_make_http_request_rewrites_search_domain(self):
        from scenarios.browser.app.runtime import BrowserScenario

        scenario = BrowserScenario({})
        scenario._start_web_servers()

        # This URL uses the mock domain; _make_http_request should rewrite it
        response = scenario._make_http_request("http://search.example.com/?q=api")
        assert response["status"] == "success"
        assert response["http_status_code"] == 200
        assert "Search Results" in response["content"]

    def test_make_http_request_rewrites_api_domain(self):
        from scenarios.browser.app.runtime import BrowserScenario

        scenario = BrowserScenario({})
        scenario._start_web_servers()

        response = scenario._make_http_request("http://api.example.com/docs")
        assert response["status"] == "success"
        assert response["http_status_code"] == 200
        assert "API Documentation" in response["content"]

    def test_make_http_request_unknown_domain_fails_gracefully(self):
        from scenarios.browser.app.runtime import BrowserScenario

        scenario = BrowserScenario({})
        scenario._start_web_servers()

        response = scenario._make_http_request("http://nonexistent-domain-xyz.com/")
        assert response["status"] in ("http_error", "network_error", "error")
