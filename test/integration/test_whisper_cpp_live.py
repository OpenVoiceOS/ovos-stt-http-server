"""Live test: hit /whisper-cpp/inference with the canonical multipart form.

whisper.cpp's HTTP server has no client SDK — apps use plain `requests` or
`curl`. We mirror that.
"""
import io

import pytest
import requests

from test.integration.conftest import make_silent_wav, run_live_server


@pytest.fixture(scope="module")
def base_url():
    from ovos_stt_http_server.routers.whisper_cpp_server import (
        make_whisper_cpp_server_router,
    )

    def register(app, model):
        app.include_router(make_whisper_cpp_server_router(model))

    yield from run_live_server(register)


def test_inference_multipart(base_url):
    r = requests.post(
        f"{base_url}/whisper-cpp/inference",
        files={"file": ("clip.wav", io.BytesIO(make_silent_wav()), "audio/wav")},
    )
    r.raise_for_status()
    assert r.json() == {"text": "hello world"}


def test_inference_text_response_format(base_url):
    r = requests.post(
        f"{base_url}/whisper-cpp/inference",
        files={"file": ("clip.wav", io.BytesIO(make_silent_wav()), "audio/wav")},
        data={"response_format": "text"},
    )
    r.raise_for_status()
    assert r.text == "hello world"
