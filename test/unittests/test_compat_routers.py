# Licensed under the Apache License, Version 2.0
"""Unit tests for STT server compatibility routers.

All compat routers are mounted under a named prefix (e.g. /openai, /speech-api)
to avoid path conflicts when all routers are registered in the same FastAPI app.
"""
import base64
import io
import json
import wave
from typing import Optional

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_wav_bytes() -> bytes:
    """Return minimal valid PCM WAV bytes."""
    buf = io.BytesIO()
    with wave.open(buf, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00\x00" * 160)
    return buf.getvalue()


class FakeModel:
    """Mock ModelContainer for testing routers."""

    def process_audio(self, audio, lang: str = "auto") -> str:
        return "hello world"


class FakeEmptyModel:
    def process_audio(self, audio, lang: str = "auto") -> str:
        return ""


@pytest.fixture(scope="module")
def model():
    return FakeModel()


class FakeTranslator:
    """Mock OVOS translator — uppercases the input so we can tell the
    /translations path actually invoked the translator."""

    def translate(self, text, target=None, source=None):
        return text.upper()


@pytest.fixture(scope="module")
def translator():
    return FakeTranslator()


def _make_openai_app(model, translator=None) -> FastAPI:
    from ovos_stt_http_server.routers.openai_whisper import make_openai_whisper_router
    app = FastAPI()
    app.include_router(make_openai_whisper_router(model, translator=translator))
    return app


def _make_chromium_app(model) -> FastAPI:
    from ovos_stt_http_server.routers.chromium import make_chromium_router
    app = FastAPI()
    app.include_router(make_chromium_router(model))
    return app


@pytest.fixture(scope="module")
def client(model, translator):
    app = _make_openai_app(model, translator=translator)
    return TestClient(app)


@pytest.fixture(scope="module")
def chromium_client(model):
    return TestClient(_make_chromium_app(model))


@pytest.fixture(scope="module")
def wav_bytes():
    return _make_wav_bytes()


@pytest.fixture(scope="module")
def wav_b64(wav_bytes):
    return base64.b64encode(wav_bytes).decode()


# ---------------------------------------------------------------------------
# OpenAI Whisper  (prefix: /openai)
# ---------------------------------------------------------------------------

class TestOpenAIWhisperRouter:
    def test_transcription_json(self, client, wav_bytes):
        resp = client.post(
            "/openai/v1/audio/transcriptions",
            files={"file": ("audio.wav", wav_bytes, "audio/wav")},
            data={"model": "whisper-1"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["text"] == "hello world"

    def test_transcription_text_format(self, client, wav_bytes):
        resp = client.post(
            "/openai/v1/audio/transcriptions",
            files={"file": ("audio.wav", wav_bytes, "audio/wav")},
            data={"model": "whisper-1", "response_format": "text"},
        )
        assert resp.status_code == 200
        assert "hello world" in resp.text

    def test_transcription_verbose_json(self, client, wav_bytes):
        resp = client.post(
            "/openai/v1/audio/transcriptions",
            files={"file": ("audio.wav", wav_bytes, "audio/wav")},
            data={"model": "whisper-1", "response_format": "verbose_json"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["text"] == "hello world"
        assert body["task"] == "transcribe"
        assert "duration" in body

    def test_transcription_srt_format(self, client, wav_bytes):
        resp = client.post(
            "/openai/v1/audio/transcriptions",
            files={"file": ("audio.wav", wav_bytes, "audio/wav")},
            data={"model": "whisper-1", "response_format": "srt"},
        )
        assert resp.status_code == 200
        assert "hello world" in resp.text

    def test_translations_runs_through_translator(self, client, wav_bytes):
        """/audio/translations must run STT output through an OVOS translator.

        FakeTranslator uppercases its input, so the result should be uppercased
        — proving the translator was actually invoked (not just the STT text
        returned with lang='en').
        """
        resp = client.post(
            "/openai/v1/audio/translations",
            files={"file": ("audio.wav", wav_bytes, "audio/wav")},
            data={"model": "whisper-1"},
        )
        assert resp.status_code == 200
        assert resp.json()["text"] == "HELLO WORLD"

    def test_auth_header_ignored(self, client, wav_bytes):
        resp = client.post(
            "/openai/v1/audio/transcriptions",
            files={"file": ("audio.wav", wav_bytes, "audio/wav")},
            data={"model": "whisper-1"},
            headers={"Authorization": "Bearer fake-token"},
        )
        assert resp.status_code == 200


class TestWhisperResponseFormats:
    """Additional Whisper response_format edge-case tests."""

    def test_response_format_text_is_plain_text(self, client, wav_bytes):
        """response_format=text must return Content-Type text/plain, not JSON."""
        resp = client.post(
            "/openai/v1/audio/transcriptions",
            files={"file": ("audio.wav", wav_bytes, "audio/wav")},
            data={"model": "whisper-1", "response_format": "text"},
        )
        assert resp.status_code == 200
        # Must NOT be a JSON object
        assert resp.text.strip() == "hello world"
        assert "text/plain" in resp.headers["content-type"]

    def test_response_format_verbose_json_has_segments_field(self, client, wav_bytes):
        """verbose_json response must contain a 'segments' key (may be empty list)."""
        resp = client.post(
            "/openai/v1/audio/transcriptions",
            files={"file": ("audio.wav", wav_bytes, "audio/wav")},
            data={"model": "whisper-1", "response_format": "verbose_json"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "segments" in body
        assert isinstance(body["segments"], list)

    def test_translations_verbose_response(self, client, wav_bytes):
        """verbose_json on /translations: task=translate, language=en, text translated."""
        resp = client.post(
            "/openai/v1/audio/translations",
            files={"file": ("audio.wav", wav_bytes, "audio/wav")},
            data={"model": "whisper-1", "response_format": "verbose_json"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["task"] == "translate"
        assert body["language"] == "en"
        assert body["text"] == "HELLO WORLD"

    def test_translations_503_when_no_translator(self, wav_bytes, model):
        """If no translator was loaded at startup, /translations returns 503."""
        app = _make_openai_app(model, translator=None)
        c = TestClient(app)
        resp = c.post(
            "/openai/v1/audio/translations",
            files={"file": ("audio.wav", wav_bytes, "audio/wav")},
            data={"model": "whisper-1"},
        )
        assert resp.status_code == 503
        assert "translate-plugin" in resp.json()["detail"]

    def test_translations_502_when_translator_raises(self, wav_bytes, model):
        """If the translator raises, /translations returns 502."""

        class BrokenTranslator:
            def translate(self, text, target=None, source=None):
                raise RuntimeError("backend down")

        app = _make_openai_app(model, translator=BrokenTranslator())
        c = TestClient(app)
        resp = c.post(
            "/openai/v1/audio/translations",
            files={"file": ("audio.wav", wav_bytes, "audio/wav")},
            data={"model": "whisper-1"},
        )
        assert resp.status_code == 502
        assert "backend down" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Chromium / Chrome Web Speech API  (prefix: /speech-api)
# ---------------------------------------------------------------------------

class TestChromiumRouter:
    def test_recognize_wav(self, chromium_client, wav_bytes):
        r = chromium_client.post(
            "/speech-api/v2/recognize?client=chromium&lang=en-US&key=fake&pFilter=0",
            content=wav_bytes,
            headers={"Content-Type": "audio/wav"},
        )
        assert r.status_code == 200
        # Two newline-delimited JSON objects, per the Chrome wire format
        lines = [l for l in r.text.split("\n") if l]
        assert len(lines) == 2
        assert json.loads(lines[0]) == {"result": []}
        second = json.loads(lines[1])
        assert second["result_index"] == 0
        alt = second["result"][0]["alternative"][0]
        assert alt["transcript"] == "hello world"
        assert second["result"][0]["final"] is True

    def test_recognize_raw_pcm(self, chromium_client):
        raw = b"\x00\x00" * 1600
        r = chromium_client.post(
            "/speech-api/v2/recognize?lang=en-US",
            content=raw,
            headers={"Content-Type": "audio/x-raw; rate=16000; bits=16"},
        )
        assert r.status_code == 200
        lines = [l for l in r.text.split("\n") if l]
        assert json.loads(lines[1])["result"][0]["alternative"][0]["transcript"] == \
            "hello world"

    def test_empty_transcript_returns_empty_first_line_only(self, wav_bytes):
        """Empty transcription returns just `{"result":[]}` — no second line."""
        app = FastAPI()
        from ovos_stt_http_server.routers.chromium import make_chromium_router
        app.include_router(make_chromium_router(FakeEmptyModel()))
        c = TestClient(app)
        r = c.post(
            "/speech-api/v2/recognize",
            content=wav_bytes,
            headers={"Content-Type": "audio/wav"},
        )
        lines = [l for l in r.text.split("\n") if l]
        assert len(lines) == 1
        assert json.loads(lines[0]) == {"result": []}

    def test_default_key_accepted(self, chromium_client, wav_bytes):
        """No key query param — still works (key is accepted-and-ignored)."""
        r = chromium_client.post(
            "/speech-api/v2/recognize?lang=en-US",
            content=wav_bytes,
            headers={"Content-Type": "audio/wav"},
        )
        assert r.status_code == 200
