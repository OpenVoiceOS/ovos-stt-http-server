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
