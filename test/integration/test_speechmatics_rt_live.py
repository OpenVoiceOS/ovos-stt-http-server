# Licensed under the Apache License, Version 2.0
"""Live integration test: Speechmatics v5 WebsocketClient against our /speechmatics router.

Uses ``speechmatics.client.WebsocketClient`` with a custom ``ConnectionSettings``
URL pointing at our local uvicorn server.  The SDK appends ``/{language}`` to
whatever path is given, so we pass ``url='ws://host/speechmatics/v2/rt'`` and
the SDK connects to ``/speechmatics/v2/rt/en``.
"""
import io

import pytest

from test.integration.conftest import make_silent_wav, run_live_server


@pytest.fixture(scope="module")
def base_url():
    """Yield base URL for a live uvicorn server with the Speechmatics router."""
    pytest.importorskip("speechmatics.client")

    from ovos_stt_http_server.routers.speechmatics import make_speechmatics_router

    def register(app, model):
        app.include_router(make_speechmatics_router(model))

    yield from run_live_server(register)


def test_realtime_transcribe_via_sdk(base_url):
    """WebsocketClient streams audio and collects AddTranscript messages."""
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)

    from speechmatics.client import WebsocketClient, ConnectionSettings
    from speechmatics.models import AudioSettings, TranscriptionConfig

    transcripts = []

    ws_url = base_url.replace("http://", "ws://") + "/speechmatics/v2/rt"

    settings = ConnectionSettings(
        url=ws_url,
        auth_token="dummy",
        generate_temp_token=False,
    )
    # The default ssl_context is an SSLContext; websockets raises ValueError
    # when ssl is passed for a plain ws:// URI.  Override to None so the SDK
    # omits the ssl kwarg when connecting to our unencrypted local server.
    settings.ssl_context = None

    client = WebsocketClient(settings)

    def on_transcript(msg):
        text = msg.get("metadata", {}).get("transcript", "")
        if text:
            transcripts.append(text)

    client.add_event_handler("AddTranscript", on_transcript)

    audio_data = make_silent_wav()
    audio_stream = io.BytesIO(audio_data)

    audio_settings = AudioSettings(
        encoding="pcm_s16le",
        sample_rate=16000,
        chunk_size=1024,
    )
    transcription_config = TranscriptionConfig(language="en")

    client.run_synchronously(
        stream=audio_stream,
        transcription_config=transcription_config,
        audio_settings=audio_settings,
        timeout=30,
    )

    # Our fake engine always returns "hello world"
    assert transcripts, "Expected at least one transcript message"
    assert "hello world" in " ".join(transcripts)
