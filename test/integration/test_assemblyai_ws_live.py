"""Live test: drive the official AssemblyAI RealtimeTranscriber against our WS endpoint.

The SDK derives the WS URL by `base_url.replace("https", "wss")`. Our local
test server speaks plain ws://, so we monkey-patch the SDK's
`websocket_connect` to swap wss:// → ws:// at connect time. In production
deployments TLS in front of port 443 (per the network-redirect docs) makes
this unnecessary.
"""
import threading
import time

import pytest

from test.integration.conftest import make_silent_wav, run_live_server


@pytest.fixture(scope="module")
def base_url():
    from ovos_stt_http_server.routers.assemblyai import make_assemblyai_router

    def register(app, model):
        app.include_router(make_assemblyai_router(model))

    yield from run_live_server(register)


def test_realtime_via_sdk(base_url, monkeypatch):
    aai = pytest.importorskip("assemblyai")
    # The SDK builds wss://<base>/v2/realtime/ws via .replace("https", "wss").
    # We give it an https-shaped base_url so the replace turns it into wss://,
    # then patch websocket_connect to rewrite wss → ws (local tests don't TLS).
    fake_https = base_url.replace("http://", "https://") + "/assemblyai"
    aai.settings.base_url = fake_https
    aai.settings.api_key = "ignored"

    from assemblyai import transcriber as _aaitrans

    if not hasattr(_aaitrans, "websocket_connect"):
        pytest.skip("assemblyai realtime API changed (v3 streaming); "
                    "websocket_connect was removed from the SDK")
    real_connect = _aaitrans.websocket_connect

    def patched_connect(url, *args, **kwargs):
        if url.startswith("wss://"):
            url = "ws://" + url[len("wss://") :]
        return real_connect(url, *args, **kwargs)

    monkeypatch.setattr(_aaitrans, "websocket_connect", patched_connect)

    final_transcripts = []
    errors = []
    closed = threading.Event()

    def on_data(transcript):
        if isinstance(transcript, aai.RealtimeFinalTranscript):
            final_transcripts.append(transcript)

    def on_error(err):
        errors.append(err)

    def on_close():
        closed.set()

    t = aai.RealtimeTranscriber(
        on_data=on_data,
        on_error=on_error,
        on_close=on_close,
        sample_rate=16000,
    )
    t.connect()

    # Stream the WAV body in two chunks
    wav = make_silent_wav()
    t.stream(wav[: len(wav) // 2])
    t.stream(wav[len(wav) // 2 :])

    t.close()

    # Allow the recv thread to drain the SessionTerminated and call on_close
    closed.wait(timeout=5)

    assert not errors, f"realtime errors: {errors}"
    assert final_transcripts, "no FinalTranscript received"
    assert final_transcripts[0].text == "hello world"
