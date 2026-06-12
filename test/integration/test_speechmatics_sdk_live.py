"""Live test: drive the official speechmatics-batch SDK against our /speechmatics router."""
import asyncio

import pytest

from test.integration.conftest import make_silent_wav, run_live_server


@pytest.fixture(scope="module")
def base_url():
    from ovos_stt_http_server.routers.speechmatics import make_speechmatics_router

    def register(app, model):
        app.include_router(make_speechmatics_router(model))

    yield from run_live_server(register)


def test_transcribe_via_sdk(base_url, tmp_path):
    batch = pytest.importorskip("speechmatics.batch")

    wav = tmp_path / "clip.wav"
    wav.write_bytes(make_silent_wav())

    async def _run():
        client = batch.AsyncClient(
            api_key="ignored",
            url=f"{base_url}/speechmatics/v1",
        )
        try:
            transcript = await client.transcribe(
                str(wav),
                transcription_config=batch.TranscriptionConfig(language="en"),
                polling_interval=0.1,
            )
        finally:
            await client.close()
        return transcript

    transcript = asyncio.run(_run())
    # transcribe() returns a Transcript dataclass; .transcript_text walks results
    text = transcript.transcript_text.strip()
    assert text == "hello world"
