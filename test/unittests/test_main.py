"""Tests for the __main__ CLI entry."""
import sys
from unittest.mock import patch

import pytest


def test_main_requires_engine():
    from ovos_stt_http_server import __main__
    with patch.object(sys, "argv", ["ovos-stt-server"]):
        with pytest.raises(SystemExit):
            __main__.main()


def test_main_runs(monkeypatch):
    from ovos_stt_http_server import __main__
    calls = {}

    def fake_start(engine, lang_engine=None, multi=False, translate_plugin=None):
        calls["start"] = (engine, lang_engine, multi, translate_plugin)
        return ("app-obj", "model-obj")

    def fake_run(server, host, port):
        calls["run"] = (server, host, port)

    monkeypatch.setattr(__main__, "start_stt_server", fake_start)
    monkeypatch.setattr(__main__.uvicorn, "run", fake_run)
    monkeypatch.setattr(
        sys, "argv",
        ["ovos-stt-server", "--engine", "fake", "--port", "1234", "--multi"],
    )
    __main__.main()
    assert calls["start"] == ("fake", None, True, "ovos-translate-plugin-server")
    assert calls["run"] == ("app-obj", "0.0.0.0", 1234)
