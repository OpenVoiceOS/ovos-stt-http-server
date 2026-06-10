"""Live test: drive the canonical ovos-stt-plugin-chromium against our /speech-api.

The plugin POSTs to a hard-coded `http://www.google.com/speech-api/v2/recognize`.
We monkey-patch `requests.post` (which the plugin uses) to rewrite that URL
to our local server — exactly what an `/etc/hosts` + nginx redirect would do
in production, but in-process for a fast CI run.
"""
import io
import sys
import wave

import pytest

from test.integration.conftest import make_silent_wav, run_live_server


@pytest.fixture(scope="module")
def base_url():
    from ovos_stt_http_server.routers.chromium import make_chromium_router

    def register(app, model):
        app.include_router(make_chromium_router(model))

    yield from run_live_server(register)


def test_chromium_plugin_against_our_server(base_url, monkeypatch):
    pytest.importorskip("ovos_stt_plugin_chromium")
    pytest.importorskip("speech_recognition")  # transitive — provides FLAC encoder

    # The plugin uses requests.post(url, ...) where url is the hard-coded
    # Google host. Rewrite it to our base_url.
    import ovos_stt_plugin_chromium as chromium_mod
    real_post = chromium_mod.requests.post

    def patched_post(url, *args, **kwargs):
        if url.startswith("http://www.google.com/speech-api"):
            url = base_url + "/speech-api" + url.split("/speech-api", 1)[1]
        return real_post(url, *args, **kwargs)

    monkeypatch.setattr(chromium_mod.requests, "post", patched_post)

    from ovos_stt_plugin_chromium import ChromiumSTT
    import speech_recognition as sr

    # Plugin needs an AudioData with .get_flac_data() — that's speech_recognition's
    # type, not OVOS's. Build one from raw PCM.
    wav = make_silent_wav()
    with wave.open(io.BytesIO(wav)) as wf:
        frames = wf.readframes(wf.getnframes())
        rate = wf.getframerate()
    audio = sr.AudioData(frames, rate, 2)

    plugin = ChromiumSTT(config={"lang": "en-us"})
    text = plugin.execute(audio, language="en-us")
    assert text == "hello world"
