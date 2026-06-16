"""
Unit tests for the router module.
Tests the routing logic that determines which agents to invoke.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from router import route


class TestRouter:
    """Tests for router.route() function."""

    def test_news_keywords_detected(self):
        """Questions with news-related keywords route to news."""
        result = route("Should I invest in steel this month?")
        assert result["news"] is True

    def test_theory_keywords_detected(self):
        """Questions with theory-related keywords route to theory."""
        result = route("Explain P/E ratio and valuation")
        assert result["theory"] is True

    def test_both_news_and_theory(self):
        """Questions with both news and theory keywords set both flags."""
        result = route("Why is the stock market price falling today?")
        assert result["news"] is True
        assert result["theory"] is True

    def test_neither_flag(self):
        """Questions with no matching keywords set neither flag."""
        result = route("Hello, how are you?")
        assert result["news"] is False
        assert result["theory"] is False

    def test_company_keyword(self):
        """'company' keyword triggers news routing."""
        result = route("Tell me about this company")
        assert result["news"] is True

    def test_risk_keyword(self):
        """'risk' keyword triggers theory routing."""
        result = route("What is the risk of investing?")
        assert result["theory"] is True

    def test_case_insensitive(self):
        """Routing works regardless of case."""
        result = route("SHOULD I INVEST IN STOCKS?")
        assert result["news"] is True

    def test_empty_string(self):
        """Empty question returns both flags as False."""
        result = route("")
        assert result["news"] is False
        assert result["theory"] is False


if __name__ == "__main__":
    # Simple test runner for environments without pytest
    tests = TestRouter()
    test_methods = [m for m in dir(tests) if m.startswith("test_")]
    passed = 0
    failed = 0
    for method_name in test_methods:
        try:
            getattr(tests, method_name)()
            print(f"  ✅ {method_name}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {method_name}: {e}")
            failed += 1
    print(f"\n{passed}/{len(test_methods)} tests passed")
    if failed:
        exit(1)
