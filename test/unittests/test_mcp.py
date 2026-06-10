# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for the MCP server integration.

All tests mock the STT engine so no real model is required.
The ``mcp`` package itself is required (pip install 'ovos-stt-http-server[mcp]').
"""
import asyncio
import base64
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_model(transcription: str = "hello world", detected_lang: str = "en-us"):
    """Return a minimal mock that quacks like ModelContainer."""
    model = MagicMock()
    model.process_audio.return_value = transcription
    model.detect_language.return_value = (detected_lang, 0.99)
    return model


def _get_tools(mcp):
    return asyncio.get_event_loop().run_until_complete(mcp.list_tools())


def _call_tool(mcp, name, kwargs):
    content_list, _structured = asyncio.get_event_loop().run_until_complete(
        mcp.call_tool(name, kwargs)
    )
    return content_list


def _extract_text(content_list) -> str:
    """Extract plain text from a FastMCP content list."""
    parts = []
    for block in content_list:
        if isinstance(block, str):
            parts.append(block)
        elif hasattr(block, "text"):
            parts.append(block.text)
        elif isinstance(block, dict):
            parts.append(block.get("text", ""))
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# build_mcp_server
# ---------------------------------------------------------------------------

class TestBuildMcpServer:
    @pytest.fixture(autouse=True)
    def _check_mcp(self):
        pytest.importorskip("mcp", reason="mcp extra not installed")

    def test_returns_fastmcp_instance(self):
        from mcp.server.fastmcp import FastMCP
        from ovos_stt_http_server.mcp_server import build_mcp_server
        mcp = build_mcp_server(_make_model())
        assert isinstance(mcp, FastMCP)

    def test_transcribe_tool_registered(self):
        from ovos_stt_http_server.mcp_server import build_mcp_server
        mcp = build_mcp_server(_make_model())
        tool_names = [t.name for t in _get_tools(mcp)]
        assert "transcribe" in tool_names

    def test_transcribe_tool_has_description(self):
        from ovos_stt_http_server.mcp_server import build_mcp_server
        mcp = build_mcp_server(_make_model())
        transcribe = next(t for t in _get_tools(mcp) if t.name == "transcribe")
        assert transcribe.description

    def test_transcribe_tool_input_schema_has_audio_fields(self):
        from ovos_stt_http_server.mcp_server import build_mcp_server
        mcp = build_mcp_server(_make_model())
        transcribe = next(t for t in _get_tools(mcp) if t.name == "transcribe")
        props = transcribe.inputSchema.get("properties", {})
        # at least one of the two audio input fields must be present
        assert "audio_b64" in props or "audio_path" in props

    def test_transcribe_tool_has_lang_param(self):
        from ovos_stt_http_server.mcp_server import build_mcp_server
        mcp = build_mcp_server(_make_model())
        transcribe = next(t for t in _get_tools(mcp) if t.name == "transcribe")
        props = transcribe.inputSchema.get("properties", {})
        assert "lang" in props

    def test_custom_server_name_accepted(self):
        from mcp.server.fastmcp import FastMCP
        from ovos_stt_http_server.mcp_server import build_mcp_server
        mcp = build_mcp_server(_make_model(), server_name="my-stt")
        assert isinstance(mcp, FastMCP)


# ---------------------------------------------------------------------------
# transcribe tool execution (mocked AudioData)
# ---------------------------------------------------------------------------

class TestTranscribeTool:
    @pytest.fixture(autouse=True)
    def _check_mcp(self):
        pytest.importorskip("mcp", reason="mcp extra not installed")

    def _call(self, model, **kwargs):
        from ovos_stt_http_server.mcp_server import build_mcp_server
        mcp = build_mcp_server(model)
        content_list, _ = asyncio.get_event_loop().run_until_complete(
            mcp.call_tool("transcribe", kwargs)
        )
        return _extract_text(content_list)

    def test_transcribe_with_audio_b64(self):
        model = _make_model("hello world")
        raw = b"\x00" * 100
        audio_b64 = base64.b64encode(raw).decode()
        text = self._call(model, audio_b64=audio_b64, lang="en-us")
        assert "hello world" in text

    def test_transcribe_with_audio_path(self, tmp_path):
        model = _make_model("path transcription")
        audio_file = tmp_path / "test.pcm"
        audio_file.write_bytes(b"\x00" * 200)
        text = self._call(model, audio_path=str(audio_file), lang="en-us")
        assert "path transcription" in text

    def test_transcribe_auto_lang_calls_detect_language(self):
        model = _make_model("auto result", detected_lang="pt-pt")
        raw = b"\x00" * 50
        audio_b64 = base64.b64encode(raw).decode()
        self._call(model, audio_b64=audio_b64, lang="auto")
        model.detect_language.assert_called_once()

    def test_transcribe_explicit_lang_skips_detection(self):
        model = _make_model("explicit lang result")
        raw = b"\x00" * 50
        audio_b64 = base64.b64encode(raw).decode()
        self._call(model, audio_b64=audio_b64, lang="de-de")
        model.detect_language.assert_not_called()

    def test_transcribe_no_audio_raises(self):
        from ovos_stt_http_server.mcp_server import build_mcp_server
        model = _make_model()
        mcp = build_mcp_server(model)
        # Calling with neither audio_b64 nor audio_path should raise
        with pytest.raises(Exception):
            asyncio.get_event_loop().run_until_complete(
                mcp.call_tool("transcribe", {})
            )

    def test_transcribe_empty_result_returns_empty_string(self):
        model = _make_model("")
        model.process_audio.return_value = None  # simulate None return
        raw = b"\x00" * 50
        audio_b64 = base64.b64encode(raw).decode()
        text = self._call(model, audio_b64=audio_b64, lang="en-us")
        assert text == ""

    def test_transcribe_both_inputs_given_audio_path_wins(self, tmp_path):
        """When both audio_b64 and audio_path are supplied, audio_path takes priority.

        The source reads ``if audio_path is not None`` first, so the file is
        used and the b64 string is ignored.
        """
        model = _make_model("from file")
        audio_file = tmp_path / "both.pcm"
        audio_file.write_bytes(b"\x01" * 100)
        # audio_b64 contains different data — if it were used the test would
        # still pass (same model mock), but we verify process_audio is called
        # with bytes matching the file content, not the b64.
        b64_data = base64.b64encode(b"\x02" * 100).decode()
        from ovos_stt_http_server.mcp_server import build_mcp_server
        from ovos_plugin_manager.utils.audio import AudioData
        mcp = build_mcp_server(model)
        asyncio.get_event_loop().run_until_complete(
            mcp.call_tool("transcribe", {
                "audio_b64": b64_data,
                "audio_path": str(audio_file),
                "lang": "en-us",
            })
        )
        call_audio: AudioData = model.process_audio.call_args[0][0]
        assert call_audio.frame_data == b"\x01" * 100

    def test_transcribe_invalid_base64_raises(self):
        """Passing a non-base64 string for audio_b64 raises an exception."""
        from ovos_stt_http_server.mcp_server import build_mcp_server
        model = _make_model()
        mcp = build_mcp_server(model)
        with pytest.raises(Exception):
            asyncio.get_event_loop().run_until_complete(
                mcp.call_tool("transcribe", {
                    "audio_b64": "!!!not-valid-base64!!!",
                    "lang": "en-us",
                })
            )

    def test_transcribe_audio_path_not_found_raises(self):
        """A non-existent audio_path must raise FileNotFoundError (or similar)."""
        from ovos_stt_http_server.mcp_server import build_mcp_server
        model = _make_model()
        mcp = build_mcp_server(model)
        with pytest.raises(Exception):
            asyncio.get_event_loop().run_until_complete(
                mcp.call_tool("transcribe", {
                    "audio_path": "/tmp/__nonexistent_ovos_test_file__.pcm",
                    "lang": "en-us",
                })
            )

    def test_transcribe_detect_language_failure_propagates(self):
        """If detect_language raises, the exception propagates from transcribe."""
        from ovos_stt_http_server.mcp_server import build_mcp_server
        model = _make_model()
        model.detect_language.side_effect = RuntimeError("lang detect exploded")
        mcp = build_mcp_server(model)
        raw = b"\x00" * 50
        audio_b64 = base64.b64encode(raw).decode()
        with pytest.raises(Exception, match="lang detect exploded"):
            asyncio.get_event_loop().run_until_complete(
                mcp.call_tool("transcribe", {
                    "audio_b64": audio_b64,
                    "lang": "auto",
                })
            )

    def test_transcribe_returns_detected_lang_text(self):
        """When lang=auto, process_audio is called with the detected language."""
        model = _make_model("olá mundo", detected_lang="pt-pt")
        raw = b"\x00" * 50
        audio_b64 = base64.b64encode(raw).decode()
        text = self._call(model, audio_b64=audio_b64, lang="auto")
        assert "olá mundo" in text
        # Verify process_audio was called with the detected lang
        call_args = model.process_audio.call_args
        assert call_args[1].get("lang") == "pt-pt" or (
            len(call_args[0]) > 1 and call_args[0][1] == "pt-pt"
        )


# ---------------------------------------------------------------------------
# mount_mcp_on_fastapi
# ---------------------------------------------------------------------------

class TestMountMcpOnFastapi:
    @pytest.fixture(autouse=True)
    def _check_mcp(self):
        pytest.importorskip("mcp", reason="mcp extra not installed")

    def test_mount_does_not_raise(self):
        from fastapi import FastAPI
        from ovos_stt_http_server.mcp_server import mount_mcp_on_fastapi
        app = FastAPI()
        model = _make_model()
        mount_mcp_on_fastapi(app, model, path="/mcp")

    def test_import_error_without_mcp(self, monkeypatch):
        """When mcp is not installed, _require_mcp() raises ImportError."""
        import ovos_stt_http_server.mcp_server as mod
        monkeypatch.setattr(mod, "_MCP_AVAILABLE", False)
        with pytest.raises(ImportError, match="FastMCP"):
            mod._require_mcp()

    def test_build_mcp_server_raises_when_mcp_unavailable(self, monkeypatch):
        """build_mcp_server() raises ImportError when _MCP_AVAILABLE is False."""
        import ovos_stt_http_server.mcp_server as mod
        monkeypatch.setattr(mod, "_MCP_AVAILABLE", False)
        with pytest.raises(ImportError):
            mod.build_mcp_server(_make_model())

    def test_mount_mcp_on_fastapi_raises_when_mcp_unavailable(self, monkeypatch):
        """mount_mcp_on_fastapi() raises ImportError when _MCP_AVAILABLE is False."""
        from fastapi import FastAPI
        import ovos_stt_http_server.mcp_server as mod
        monkeypatch.setattr(mod, "_MCP_AVAILABLE", False)
        app = FastAPI()
        with pytest.raises(ImportError):
            mod.mount_mcp_on_fastapi(app, _make_model())


# ---------------------------------------------------------------------------
# MCP module import-time graceful degradation (sys.modules blocking)
# ---------------------------------------------------------------------------

class TestMcpModuleImportDegradation:
    """Verify the except-ImportError branch at module level (lines 38-39).

    When ``mcp`` is not on sys.path at import time, the module must still load
    with ``_MCP_AVAILABLE = False`` rather than raising.
    """

    def test_module_loads_without_mcp_package(self):
        """Force a fresh import of mcp_server with mcp blocked in sys.modules."""
        import sys
        import importlib

        # Block the mcp package by inserting a sentinel that raises ImportError.
        sentinel = object()  # not a real module
        blocked_keys = [k for k in list(sys.modules) if k == "mcp" or k.startswith("mcp.")]
        saved = {k: sys.modules.pop(k) for k in blocked_keys}
        # Use a fake module that raises on attribute access is complex;
        # simpler: set the key to None which causes ImportError on `import mcp`.
        sys.modules["mcp"] = None  # type: ignore
        sys.modules["mcp.server"] = None  # type: ignore
        sys.modules["mcp.server.fastmcp"] = None  # type: ignore

        # Remove the already-cached mcp_server module so it re-executes.
        mcp_server_saved = sys.modules.pop("ovos_stt_http_server.mcp_server", None)
        try:
            import ovos_stt_http_server.mcp_server as fresh_mod
            assert fresh_mod._MCP_AVAILABLE is False
        finally:
            # Restore everything.
            for k in ["mcp", "mcp.server", "mcp.server.fastmcp"]:
                sys.modules.pop(k, None)
            sys.modules.update(saved)
            if mcp_server_saved is not None:
                sys.modules["ovos_stt_http_server.mcp_server"] = mcp_server_saved


# ---------------------------------------------------------------------------
# create_app integration: MCP absent → graceful degradation
# ---------------------------------------------------------------------------

class TestCreateAppMcpDegradation:
    def test_create_app_without_mcp_does_not_crash(self, monkeypatch):
        """create_app() continues normally when mcp extra is missing."""
        import ovos_stt_http_server.mcp_server as mcp_mod
        monkeypatch.setattr(mcp_mod, "_MCP_AVAILABLE", False)

        with patch("ovos_stt_http_server.ModelContainer") as mc:
            mc.return_value = _make_model()
            from ovos_stt_http_server import create_app
            app, model = create_app("mock-stt")

        from fastapi import FastAPI
        assert isinstance(app, FastAPI)

    def test_create_app_mcp_import_error_caught(self):
        """create_app() catches ImportError from mount_mcp_on_fastapi gracefully.

        Patches the mcp_server submodule in sys.modules so the ``from … import``
        inside create_app triggers an ImportError through the module's own guard.
        """
        import sys
        import ovos_stt_http_server.mcp_server as mcp_mod

        with patch("ovos_stt_http_server.ModelContainer") as mc, \
             patch.object(mcp_mod, "mount_mcp_on_fastapi", side_effect=ImportError("no mcp")):
            mc.return_value = _make_model()
            # Force create_app to use the patched module by flushing its cache entry.
            saved = sys.modules.get("ovos_stt_http_server.mcp_server")
            sys.modules["ovos_stt_http_server.mcp_server"] = mcp_mod  # already patched
            try:
                from ovos_stt_http_server import create_app
                app, model = create_app("mock-stt")
            finally:
                if saved is not None:
                    sys.modules["ovos_stt_http_server.mcp_server"] = saved

        from fastapi import FastAPI
        assert isinstance(app, FastAPI)
