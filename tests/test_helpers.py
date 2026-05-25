"""Tests for _helpers — proposal_reply factory and helpers."""
import json
import pytest
from tools._helpers import proposal_reply, err_json, unwrap


class TestProposalReply:
    def test_basic_error(self):
        r = proposal_reply(False, "something went wrong", error="read failed")
        assert r["ok"] is False
        assert r["proposal"] == "something went wrong"
        assert r["error"] == "read failed"
        assert "evidence" not in r
        assert "options" not in r

    def test_with_evidence_and_options(self):
        r = proposal_reply(False, "port not listening",
                           error="connection refused",
                           evidence={"host": "127.0.0.1", "port": 7860},
                           options=["check service", "verify port"])
        assert r["evidence"] == {"host": "127.0.0.1", "port": 7860}
        assert r["options"] == ["check service", "verify port"]

    def test_with_next_call(self):
        r = proposal_reply(False, "es not found",
                           error="es.exe missing",
                           next_call={"tool": "dir_list", "params": {"path": "."}})
        assert r["next_call"]["tool"] == "dir_list"

    def test_extra_kwargs_flattened(self):
        r = proposal_reply(True, "found 3 issues",
                           language="python", errors=[{"msg": "x"}])
        assert r["language"] == "python"
        assert r["errors"] == [{"msg": "x"}]

    def test_falsy_options_not_added(self):
        r = proposal_reply(True, "all ok", options=[])
        assert "options" not in r

    def test_empty_evidence_not_added(self):
        r = proposal_reply(True, "ok", evidence={})
        assert "evidence" not in r

    def test_ok_true_no_error_field(self):
        r = proposal_reply(True, "ok")
        assert "error" not in r


class TestHelpers:
    def test_err_json(self):
        result = err_json("test error")
        data = json.loads(result)
        assert data["ok"] is False
        assert data["error"] == "test error"

    def test_unwrap_nested_error(self):
        result = unwrap({"ok": False, "error": "inner error"})
        data = json.loads(result)
        assert data["ok"] is False
        assert data["error"] == "inner error"

    def test_unwrap_success(self):
        result = unwrap({"ok": True, "data": [1, 2, 3]})
        data = json.loads(result)
        assert data["ok"] is True
        assert data["data"] == {"ok": True, "data": [1, 2, 3]}

    def test_unwrap_non_dict(self):
        result = unwrap("not a dict")
        data = json.loads(result)
        assert data["ok"] is False
        assert "非预期类型" in data["error"]
