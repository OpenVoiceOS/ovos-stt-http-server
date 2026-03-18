# Licensed under the Apache License, Version 2.0
"""Unit tests for STT server compatibility routers."""
import base64
import io
import json
import os
import struct
import tempfile
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
        """Return fixed transcription regardless of audio."""
        return "hello world"


@pytest.fixture(scope="module")
def model():
    """Shared FakeModel instance."""
    return FakeModel()


def _make_app(model) -> FastAPI:
    """Build minimal FastAPI app with all STT compat routers."""
    from ovos_stt_http_server.routers.openai_whisper import make_openai_whisper_router
    from ovos_stt_http_server.routers.deepgram import make_deepgram_router
    from ovos_stt_http_server.routers.google_stt import make_google_stt_router
    from ovos_stt_http_server.routers.assemblyai import make_assemblyai_router
    from ovos_stt_http_server.routers.speechmatics import make_speechmatics_router

    app = FastAPI()
    app.include_router(make_openai_whisper_router(model))
    app.include_router(make_deepgram_router(model))
    app.include_router(make_google_stt_router(model))
    app.include_router(make_assemblyai_router(model))
    app.include_router(make_speechmatics_router(model))
    return app


@pytest.fixture(scope="module")
def client(model):
    """TestClient wired to the STT compat router app."""
    app = _make_app(model)
    return TestClient(app)


@pytest.fixture(scope="module")
def wav_bytes():
    """Minimal WAV file bytes."""
    return _make_wav_bytes()


@pytest.fixture(scope="module")
def wav_b64(wav_bytes):
    """Base64-encoded WAV bytes."""
    return base64.b64encode(wav_bytes).decode()


# ---------------------------------------------------------------------------
# OpenAI Whisper
# ---------------------------------------------------------------------------

class TestOpenAIWhisperRouter:
    def test_transcription_json(self, client, wav_bytes):
        resp = client.post(
            "/v1/audio/transcriptions",
            files={"file": ("audio.wav", wav_bytes, "audio/wav")},
            data={"model": "whisper-1"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "text" in body
        assert body["text"] == "hello world"

    def test_transcription_text_format(self, client, wav_bytes):
        resp = client.post(
            "/v1/audio/transcriptions",
            files={"file": ("audio.wav", wav_bytes, "audio/wav")},
            data={"model": "whisper-1", "response_format": "text"},
        )
        assert resp.status_code == 200
        assert "hello world" in resp.text

    def test_transcription_verbose_json(self, client, wav_bytes):
        resp = client.post(
            "/v1/audio/transcriptions",
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
            "/v1/audio/transcriptions",
            files={"file": ("audio.wav", wav_bytes, "audio/wav")},
            data={"model": "whisper-1", "response_format": "srt"},
        )
        assert resp.status_code == 200
        assert "hello world" in resp.text

    def test_translation_forces_english(self, client, wav_bytes):
        resp = client.post(
            "/v1/audio/translations",
            files={"file": ("audio.wav", wav_bytes, "audio/wav")},
            data={"model": "whisper-1"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "text" in body

    def test_transcription_with_language_hint(self, client, wav_bytes):
        resp = client.post(
            "/v1/audio/transcriptions",
            files={"file": ("audio.wav", wav_bytes, "audio/wav")},
            data={"model": "whisper-1", "language": "de"},
        )
        assert resp.status_code == 200

    def test_auth_header_ignored(self, client, wav_bytes):
        resp = client.post(
            "/v1/audio/transcriptions",
            files={"file": ("audio.wav", wav_bytes, "audio/wav")},
            data={"model": "whisper-1"},
            headers={"Authorization": "Bearer fake-token"},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Deepgram
# ---------------------------------------------------------------------------

class TestDeepgramRouter:
    def test_listen_basic(self, client, wav_bytes):
        resp = client.post(
            "/v1/listen",
            content=wav_bytes,
            headers={"Content-Type": "audio/wav"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "results" in body
        channels = body["results"]["channels"]
        assert len(channels) >= 1
        alt = channels[0]["alternatives"][0]
        assert alt["transcript"] == "hello world"
        assert "confidence" in alt

    def test_listen_with_language(self, client, wav_bytes):
        resp = client.post(
            "/v1/listen?language=en-US",
            content=wav_bytes,
            headers={"Content-Type": "audio/wav"},
        )
        assert resp.status_code == 200

    def test_listen_auth_ignored(self, client, wav_bytes):
        resp = client.post(
            "/v1/listen",
            content=wav_bytes,
            headers={"Content-Type": "audio/wav", "Authorization": "Token fake"},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Google STT
# ---------------------------------------------------------------------------

class TestGoogleSTTRouter:
    def test_recognize_base64(self, client, wav_b64):
        resp = client.post(
            "/v1/speech:recognize",
            json={
                "config": {"encoding": "LINEAR16", "sampleRateHertz": 16000, "languageCode": "en-US"},
                "audio": {"content": wav_b64},
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "results" in body
        assert body["results"][0]["alternatives"][0]["transcript"] == "hello world"

    def test_recognize_uri_not_supported(self, client):
        resp = client.post(
            "/v1/speech:recognize",
            json={
                "config": {"encoding": "LINEAR16", "sampleRateHertz": 16000, "languageCode": "en-US"},
                "audio": {"uri": "gs://bucket/file.wav"},
            },
        )
        assert resp.status_code == 501

    def test_recognize_missing_audio_rejected(self, client):
        resp = client.post(
            "/v1/speech:recognize",
            json={
                "config": {"encoding": "LINEAR16", "sampleRateHertz": 16000, "languageCode": "en-US"},
                "audio": {},
            },
        )
        assert resp.status_code in (400, 422, 501)


# ---------------------------------------------------------------------------
# AssemblyAI
# ---------------------------------------------------------------------------

class TestAssemblyAIRouter:
    def test_submit_b64_transcript(self, client, wav_b64):
        resp = client.post(
            "/v2/transcript",
            json={"audio": wav_b64},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "completed"
        assert body["text"] == "hello world"

    def test_get_transcript_by_id_returns_error_stub(self, client, wav_b64):
        """GET by ID is a synchronous stub — always returns error status."""
        create = client.post("/v2/transcript", json={"audio": wav_b64})
        assert create.status_code == 200
        tid = create.json()["id"]
        get_resp = client.get(f"/v2/transcript/{tid}")
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "error"

    def test_get_any_transcript_returns_error_stub(self, client):
        """GET is a synchronous stub regardless of ID."""
        resp = client.get("/v2/transcript/nonexistent-id")
        assert resp.status_code == 200
        assert resp.json()["status"] == "error"

    def test_submit_audio_url_returns_error(self, client):
        """audio_url is a remote URL stub returns error status."""
        resp = client.post(
            "/v2/transcript",
            json={"audio_url": "https://example.com/audio.wav"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "error"


# ---------------------------------------------------------------------------
# Speechmatics
# ---------------------------------------------------------------------------

class TestSpeechmaticsRouter:
    def test_submit_job(self, client, wav_bytes):
        resp = client.post(
            "/v1/jobs",
            files={"data_file": ("audio.wav", wav_bytes, "audio/wav")},
            data={"config": json.dumps({"type": "transcription", "transcription_config": {"language": "en"}})},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "id" in body
        assert body["status"] == "done"

    def test_get_transcript(self, client, wav_bytes):
        create = client.post(
            "/v1/jobs",
            files={"data_file": ("audio.wav", wav_bytes, "audio/wav")},
            data={"config": json.dumps({"type": "transcription", "transcription_config": {"language": "en"}})},
        )
        job_id = create.json()["id"]
        resp = client.get(f"/v1/jobs/{job_id}/transcript")
        assert resp.status_code == 200
        body = resp.json()
        assert "results" in body

    def test_get_missing_job_transcript(self, client):
        resp = client.get("/v1/jobs/nonexistent/transcript")
        assert resp.status_code == 404
