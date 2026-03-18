# Licensed under the Apache License, Version 2.0
"""Unit tests for STT server compatibility routers.

All compat routers are mounted under a named prefix (e.g. /openai, /deepgram)
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


@pytest.fixture(scope="module")
def model():
    return FakeModel()


def _make_app(model) -> FastAPI:
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
    app = _make_app(model)
    return TestClient(app)


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

    def test_translation_forces_english(self, client, wav_bytes):
        resp = client.post(
            "/openai/v1/audio/translations",
            files={"file": ("audio.wav", wav_bytes, "audio/wav")},
            data={"model": "whisper-1"},
        )
        assert resp.status_code == 200
        assert resp.json()["text"] == "hello world"

    def test_auth_header_ignored(self, client, wav_bytes):
        resp = client.post(
            "/openai/v1/audio/transcriptions",
            files={"file": ("audio.wav", wav_bytes, "audio/wav")},
            data={"model": "whisper-1"},
            headers={"Authorization": "Bearer fake-token"},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Deepgram  (prefix: /deepgram)
# ---------------------------------------------------------------------------

class TestDeepgramRouter:
    def test_listen_basic(self, client, wav_bytes):
        resp = client.post(
            "/deepgram/v1/listen",
            content=wav_bytes,
            headers={"Content-Type": "audio/wav"},
        )
        assert resp.status_code == 200
        body = resp.json()
        alt = body["results"]["channels"][0]["alternatives"][0]
        assert alt["transcript"] == "hello world"
        assert "confidence" in alt

    def test_listen_with_language(self, client, wav_bytes):
        resp = client.post(
            "/deepgram/v1/listen?language=en-US",
            content=wav_bytes,
            headers={"Content-Type": "audio/wav"},
        )
        assert resp.status_code == 200

    def test_auth_header_ignored(self, client, wav_bytes):
        resp = client.post(
            "/deepgram/v1/listen",
            content=wav_bytes,
            headers={"Content-Type": "audio/wav", "Authorization": "Token fake"},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Google STT  (prefix: /google)
# ---------------------------------------------------------------------------

class TestGoogleSTTRouter:
    def test_recognize_base64(self, client, wav_b64):
        resp = client.post(
            "/google/v1/speech:recognize",
            json={
                "config": {"encoding": "LINEAR16", "sampleRateHertz": 16000, "languageCode": "en-US"},
                "audio": {"content": wav_b64},
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["results"][0]["alternatives"][0]["transcript"] == "hello world"

    def test_recognize_uri_not_supported(self, client):
        resp = client.post(
            "/google/v1/speech:recognize",
            json={
                "config": {"encoding": "LINEAR16", "sampleRateHertz": 16000, "languageCode": "en-US"},
                "audio": {"uri": "gs://bucket/file.wav"},
            },
        )
        assert resp.status_code == 501


# ---------------------------------------------------------------------------
# AssemblyAI  (prefix: /assemblyai)
# ---------------------------------------------------------------------------

class TestAssemblyAIRouter:
    def test_submit_b64_transcript(self, client, wav_b64):
        resp = client.post(
            "/assemblyai/v2/transcript",
            json={"audio": wav_b64},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "completed"
        assert body["text"] == "hello world"

    def test_get_transcript_returns_error_stub(self, client, wav_b64):
        """GET by ID is a synchronous stub — always returns error status."""
        create = client.post("/assemblyai/v2/transcript", json={"audio": wav_b64})
        tid = create.json()["id"]
        get_resp = client.get(f"/assemblyai/v2/transcript/{tid}")
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "error"

    def test_submit_audio_url_returns_error(self, client):
        resp = client.post(
            "/assemblyai/v2/transcript",
            json={"audio_url": "https://example.com/audio.wav"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "error"


# ---------------------------------------------------------------------------
# Speechmatics  (prefix: /speechmatics)
# ---------------------------------------------------------------------------

class TestSpeechmaticsRouter:
    def test_submit_job(self, client, wav_bytes):
        resp = client.post(
            "/speechmatics/v1/jobs",
            files={"data_file": ("audio.wav", wav_bytes, "audio/wav")},
            data={"config": json.dumps({"type": "transcription", "transcription_config": {"language": "en"}})},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "id" in body
        assert body["status"] == "done"

    def test_get_transcript(self, client, wav_bytes):
        create = client.post(
            "/speechmatics/v1/jobs",
            files={"data_file": ("audio.wav", wav_bytes, "audio/wav")},
            data={"config": json.dumps({"type": "transcription", "transcription_config": {"language": "en"}})},
        )
        job_id = create.json()["id"]
        resp = client.get(f"/speechmatics/v1/jobs/{job_id}/transcript")
        assert resp.status_code == 200
        assert "results" in resp.json()

    def test_get_missing_job_transcript(self, client):
        resp = client.get("/speechmatics/v1/jobs/nonexistent/transcript")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Additional tests (8 new) covering edge cases
# ---------------------------------------------------------------------------

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

    def test_translations_endpoint_forces_lang_en(self, client, wav_bytes):
        """Translations endpoint must set task=translate and language=en in verbose_json."""
        resp = client.post(
            "/openai/v1/audio/translations",
            files={"file": ("audio.wav", wav_bytes, "audio/wav")},
            data={"model": "whisper-1", "response_format": "verbose_json"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["task"] == "translate"
        assert body["language"] == "en"


class TestDeepgramEdgeCases:
    """Additional Deepgram router edge-case tests."""

    def test_listen_with_punctuate_param_ignored(self, client, wav_bytes):
        """?punctuate=true is accepted and ignored; transcript is still returned."""
        resp = client.post(
            "/deepgram/v1/listen?punctuate=true",
            content=wav_bytes,
            headers={"Content-Type": "audio/wav"},
        )
        assert resp.status_code == 200
        alt = resp.json()["results"]["channels"][0]["alternatives"][0]
        assert alt["transcript"] == "hello world"


class TestGoogleSTTEdgeCases:
    """Additional Google STT router edge-case tests."""

    def test_recognize_with_base64_wav(self, client, wav_b64):
        """Explicit test that base64-encoded WAV bytes are decoded and transcribed."""
        resp = client.post(
            "/google/v1/speech:recognize",
            json={
                "config": {
                    "encoding": "LINEAR16",
                    "sampleRateHertz": 16000,
                    "languageCode": "en-US",
                },
                "audio": {"content": wav_b64},
            },
        )
        assert resp.status_code == 200
        result = resp.json()["results"][0]
        assert result["alternatives"][0]["transcript"] == "hello world"
        assert result["alternatives"][0]["confidence"] == pytest.approx(0.9, abs=0.01)


class TestAssemblyAIEdgeCases:
    """Additional AssemblyAI router edge-case tests."""

    def test_get_transcript_always_has_status_field(self, client, wav_b64):
        """GET by any ID must always return a JSON body with a 'status' key."""
        create = client.post("/assemblyai/v2/transcript", json={"audio": wav_b64})
        tid = create.json()["id"]
        get_resp = client.get(f"/assemblyai/v2/transcript/{tid}")
        assert get_resp.status_code == 200
        body = get_resp.json()
        assert "status" in body


class TestSpeechmaticsEdgeCases:
    """Additional Speechmatics router edge-case tests."""

    def test_get_unknown_job_id_returns_404(self, client):
        """A job ID that was never created must return HTTP 404."""
        resp = client.get("/speechmatics/v1/jobs/totally-unknown-id-xyz/transcript")
        assert resp.status_code == 404

    def test_get_known_job_id_returns_transcript(self, client, wav_bytes):
        """A job ID from a successful POST must return 200 with transcript text."""
        create = client.post(
            "/speechmatics/v1/jobs",
            files={"data_file": ("audio.wav", wav_bytes, "audio/wav")},
            data={
                "config": json.dumps(
                    {"type": "transcription", "transcription_config": {"language": "en"}}
                )
            },
        )
        assert create.status_code == 200
        job_id = create.json()["id"]

        resp = client.get(f"/speechmatics/v1/jobs/{job_id}/transcript")
        assert resp.status_code == 200
        body = resp.json()
        assert "results" in body
        # transcript content should appear in alternatives
        if body["results"]:
            assert body["results"][0]["alternatives"][0]["content"] == "hello world"
