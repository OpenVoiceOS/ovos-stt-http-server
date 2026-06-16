"""Live test: drive our /speech-api (Chromium Web Speech) router with a real client.

The Chromium / Chrome Web Speech API is what ``speech_recognition`` speaks in
``Recognizer.recognize_google``: a FLAC body POSTed to
``/speech-api/v2/recognize`` returning newline-delimited JSON. We use
``speech_recognition`` (the canonical client library) to encode FLAC exactly as
that path does, then POST to our local server — exactly what an ``/etc/hosts`` +
reverse-proxy redirect of ``www.google.com`` would achieve in production.
"""
import io
import json
import wave

import pytest
import requests

from test.integration.conftest import make_silent_wav, run_live_server


@pytest.fixture(scope="module")
def base_url():
    from ovos_stt_http_server.routers.chromium import make_chromium_router

    def register(app, model):
        app.include_router(make_chromium_router(model))

    yield from run_live_server(register)


def test_chromium_recognize_endpoint(base_url):
    import speech_recognition as sr

    wav = make_silent_wav()
    with wave.open(io.BytesIO(wav)) as wf:
        frames = wf.readframes(wf.getnframes())
        rate = wf.getframerate()
    # speech_recognition.AudioData is the type recognize_google operates on;
    # get_flac_data() produces the exact FLAC body it would POST.
    audio = sr.AudioData(frames, rate, 2)
    flac = audio.get_flac_data(convert_rate=16000)

    resp = requests.post(
        f"{base_url}/speech-api/v2/recognize?client=chromium&lang=en-us",
        data=flac,
        headers={"Content-Type": "audio/x-flac; rate=16000"},
        timeout=10,
    )
    assert resp.status_code == 200

    # Chromium wire format: newline-delimited JSON; the transcript lives in
    # result[].alternative[].transcript on the non-empty line.
    transcripts = [
        alt["transcript"]
        for line in resp.text.splitlines() if line.strip()
        for result in json.loads(line).get("result", [])
        for alt in result.get("alternative", [])
    ]
    assert "hello world" in transcripts
