"""Tests for regex_tester — nested quantifier rejection (ReDoS)."""
import pytest
from tools.regex_tester import test as regex_test


class TestRegexTester:
    def test_basic_match(self):
        result = regex_test("hello", "hello world")
        assert result["ok"] is True
        assert result["has_match"] is True

    def test_no_match(self):
        result = regex_test("xyz99", "hello world")
        assert result["ok"] is True
        assert result["has_match"] is False

    def test_rejects_nested_quantifier(self):
        result = regex_test("(a+)+", "aaaaaaaaaaab")
        assert result["ok"] is False
        assert "嵌套" in result["error"] or "回溯" in result["error"]

    def test_rejects_nested_star(self):
        result = regex_test("(.*)+", "any text")
        assert result["ok"] is False

    def test_rejects_long_pattern(self):
        long_pattern = "a" * 2001
        result = regex_test(long_pattern, "test")
        assert result["ok"] is False
        assert "过长" in result["error"]

    def test_rejects_long_text(self):
        result = regex_test("hello", "x" * 100001)
        assert result["ok"] is False
        assert "过长" in result["error"]

    def test_invalid_syntax(self):
        result = regex_test("[unclosed", "test")
        assert result["ok"] is False
        assert "语法" in result["error"]

    def test_flag_ignorecase(self):
        result = regex_test("HELLO", "hello world", flags="i")
        assert result["ok"] is True
        assert result["has_match"] is True

    def test_groups(self):
        result = regex_test("(\\d+)", "abc 123 def 456")
        assert result["ok"] is True
        assert result["count"] == 2
        assert "groups" in result["matches"][0]
