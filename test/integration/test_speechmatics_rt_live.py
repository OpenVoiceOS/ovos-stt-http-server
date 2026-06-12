"""Live test: drive the official speechmatics-rt SDK against /speechmatics/v1 WS."""
import asyncio
import io
import wave

import pytest

from test.integration.conftest import run_live_server


@pytest.fixture(scope="module")
def base_url():
    from ovos_stt_http_server.routers.speechmatics import make_speechmatics_router

    def register(app, model):
        app.include_router(make_speechmatics_router(model))

    yield from run_live_server(register)


def _raw_pcm(seconds: float = 0.1, sample_rate: int = 16000) -> bytes:
    """Return raw 16-bit mono PCM bytes (no WAV header) — what SDK expects."""
    return b"\x00\x00" * int(seconds * sample_rate)


def test_realtime_via_sdk(base_url):
    rt = pytest.importorskip("speechmatics.rt")

    ws_url = base_url.replace("http://", "ws://") + "/speechmatics/v1"
    transcripts: list = []

    async def _run():
        client = rt.AsyncClient(api_key="ignored", url=ws_url)

        @client.on(rt.ServerMessageType.ADD_TRANSCRIPT)
        def _on_add(msg):
            transcripts.append(msg)

        async with client:
            audio = io.BytesIO(_raw_pcm(0.5))
            # `transcribe()` is a one-shot helper that streams the file
            # then closes the session.
            await client.transcribe(
                audio,
                audio_format=rt.AudioFormat(
                    encoding=rt.AudioEncoding.PCM_S16LE,
                    sample_rate=16000,
                ),
                transcription_config=rt.TranscriptionConfig(language="en"),
            )

    asyncio.run(_run())

    assert transcripts, "no AddTranscript received"
    msg = transcripts[0]
    results = msg.get("results") if isinstance(msg, dict) else msg.results
    assert results, "AddTranscript had no results"
    first = results[0] if isinstance(results, list) else results[0]
    alts = first.get("alternatives") if isinstance(first, dict) else first.alternatives
    text = alts[0].get("content") if isinstance(alts[0], dict) else alts[0].content
    assert text == "hello world"
