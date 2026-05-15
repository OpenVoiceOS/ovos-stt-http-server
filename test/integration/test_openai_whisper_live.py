"""Live test: hit our /openai router with the real OpenAI Python SDK."""
import io

import pytest

from test.integration.conftest import make_silent_wav, run_live_server


class FakeTranslator:
    """Stand-in OVOS translator that prefixes the source-lang tag.

    Lets the live test assert /translations actually ran STT output through
    a translator (rather than just labelling the response as English) without
    requiring the public OVOS translate server in CI.
    """

    def translate(self, text, target=None, source=None):
        return f"[{source or 'auto'}->{target}] {text}"


@pytest.fixture(scope="module")
def base_url():
    from ovos_stt_http_server.routers.openai_whisper import make_openai_whisper_router

    def register(app, model):
        app.include_router(make_openai_whisper_router(model, translator=FakeTranslator()))

    yield from run_live_server(register)


def test_transcriptions_json(base_url):
    openai = pytest.importorskip("openai")
    client = openai.OpenAI(base_url=f"{base_url}/openai/v1", api_key="ignored")
    wav = make_silent_wav()
    r = client.audio.transcriptions.create(
        model="whisper-1",
        file=("clip.wav", io.BytesIO(wav), "audio/wav"),
    )
    assert r.text == "hello world"


def test_transcriptions_text_format(base_url):
    openai = pytest.importorskip("openai")
    client = openai.OpenAI(base_url=f"{base_url}/openai/v1", api_key="ignored")
    wav = make_silent_wav()
    r = client.audio.transcriptions.create(
        model="whisper-1",
        file=("clip.wav", io.BytesIO(wav), "audio/wav"),
        response_format="text",
    )
    # SDK returns plain str for text response_format
    assert "hello world" in str(r)


def test_translations_runs_through_translator(base_url):
    """The /translations endpoint must invoke the OVOS translator, not just
    label STT output as English."""
    openai = pytest.importorskip("openai")
    client = openai.OpenAI(base_url=f"{base_url}/openai/v1", api_key="ignored")
    wav = make_silent_wav()
    r = client.audio.translations.create(
        model="whisper-1",
        file=("clip.wav", io.BytesIO(wav), "audio/wav"),
    )
    # FakeTranslator prefixed the STT text — proves the translator ran.
    assert r.text == "[auto->en] hello world"
