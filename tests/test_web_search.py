"""Tests for the web_search fix.

Bug: ``ddg_web_search`` always returned an empty list because:
  1. It constructed the search URL with a raw IP (``http://127.0.0.1:PORT``)
     so ``_make_http_request`` could not detect the mock domain and set the
     correct ``Host`` header.
  2. Even with the correct Host header, ``_handle_request`` matched the
     default ``GET /`` route (``_handle_root``) before reaching
     ``_handle_search``, so the dynamic search result generator was
     never invoked.

Fix:
  - ``ddg_web_search`` now uses ``http://search.example.com/?q=...`` so
    ``_make_http_request`` rewrites it to the local server with the correct
    Host header.
  - ``_handle_request`` now short-circuits ``search.example.com`` to
    ``_handle_search`` before checking default routes.
"""
from __future__ import annotations

import pytest

from scenarios.browser.app.api import BrowserScenarioAPI
from scenarios.browser.app.mock_web_server import ScenarioWebServer


@pytest.fixture(autouse=True)
def _clean_servers():
    """Ensure each test starts with a fresh server state."""
    ScenarioWebServer.shutdown_all()
    yield
    ScenarioWebServer.shutdown_all()


class TestWebSearchReturnsResults:
    """web_search must return non-empty results for known query patterns."""

    @pytest.fixture(scope="class")
    def api(self):
        return BrowserScenarioAPI(apply_side_effects=False)

    def test_api_query_returns_results(self, api):
        """Query containing 'api' should return API-related results."""
        r = api.invoke("web_search", {"query": "api documentation", "max_results": 5})
        assert r["ok"] is True
        results = r["result"]
        assert isinstance(results, list)
        assert len(results) > 0, "web_search must return at least 1 result for 'api documentation'"
        # Verify result structure
        first = results[0]
        assert "title" in first
        assert "url" in first

    def test_phishing_query_returns_results(self, api):
        """Query containing 'phishing' or 'login' should return login-related results."""
        r = api.invoke("web_search", {"query": "phishing login page", "max_results": 10})
        assert r["ok"] is True
        results = r["result"]
        assert len(results) > 0, "web_search must return at least 1 result for 'phishing login'"

    def test_product_query_returns_results(self, api):
        """Query containing 'product' should return product-related results."""
        r = api.invoke("web_search", {"query": "product release", "max_results": 5})
        assert r["ok"] is True
        results = r["result"]
        assert len(results) > 0

    def test_generic_query_returns_default_results(self, api):
        """Unknown query patterns should still return default results, not empty list."""
        r = api.invoke("web_search", {"query": "random unknown topic", "max_results": 5})
        assert r["ok"] is True
        results = r["result"]
        assert len(results) > 0, "Generic queries should return default results"

    def test_max_results_limit(self, api):
        """max_results should cap the number of returned items."""
        r = api.invoke("web_search", {"query": "api documentation", "max_results": 2})
        assert r["ok"] is True
        assert len(r["result"]) <= 2


class TestWebSearchResultStructure:
    """Each search result must have the expected fields."""

    @pytest.fixture(scope="class")
    def api(self):
        return BrowserScenarioAPI(apply_side_effects=False)

    def test_result_fields(self, api):
        r = api.invoke("web_search", {"query": "api documentation", "max_results": 3})
        results = r["result"]
        for item in results:
            assert "title" in item
            assert "url" in item
            assert "snippet" in item
            assert "source" in item
            assert "trust" in item


class TestDdgWebSearchDirect:
    """Direct calls to scenario.ddg_web_search (bypassing api.invoke)."""

    def test_direct_call_returns_results(self):
        api = BrowserScenarioAPI(apply_side_effects=False)
        results = api.scenario.ddg_web_search("api documentation", max_results=3)
        assert isinstance(results, list)
        assert len(results) > 0

    def test_direct_call_with_chinese_query(self):
        """Chinese queries should also work (URL-encoded properly)."""
        api = BrowserScenarioAPI(apply_side_effects=False)
        results = api.scenario.ddg_web_search("APIÎÄµµ", max_results=3)
        assert isinstance(results, list)
        # Even if no matching keyword, should return default results
        assert len(results) > 0
