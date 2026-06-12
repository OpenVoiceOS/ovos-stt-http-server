# Licensed under the Apache License, Version 2.0
"""Live integration test: Speechmatics v5 BatchClient against our /speechmatics router.

Uses ``speechmatics.batch_client.BatchClient`` with a custom ``ConnectionSettings``
URL pointing at our local uvicorn server so no Speechmatics account is required.

The BatchClient automatically appends ``/v2`` to whatever base URL is supplied,
so we pass ``url='http://host/speechmatics'`` → requests land on
``/speechmatics/v2/jobs``.
"""
import io

import pytest

from test.integration.conftest import make_silent_wav, run_live_server


@pytest.fixture(scope="module")
def base_url():
    """Yield base URL for a live uvicorn server with the Speechmatics router."""
    speechmatics_batch_client = pytest.importorskip("speechmatics.batch_client")

    from ovos_stt_http_server.routers.speechmatics import make_speechmatics_router

    def register(app, model):
        app.include_router(make_speechmatics_router(model))

    yield from run_live_server(register)


def test_batch_transcribe_via_sdk(base_url):
    """BatchClient submits audio, polls until done, retrieves transcript."""
    from speechmatics.batch_client import BatchClient, ConnectionSettings
    from speechmatics.models import BatchTranscriptionConfig

    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)

    settings = ConnectionSettings(
        url=f"{base_url}/speechmatics",
        auth_token="dummy",
        generate_temp_token=False,
    )
    with BatchClient(settings) as client:
        job_id = client.submit_job(
            audio=("audio.wav", make_silent_wav()),
            transcription_config=BatchTranscriptionConfig(language="en"),
        )
        assert job_id, "Expected a non-empty job_id"

        result = client.wait_for_completion(job_id, transcription_format="json-v2")
        # Speechmatics json-v2 has top-level 'results' key
        assert "results" in result
        # Our fake engine always returns "hello world"
        words = [
            alt["content"]
            for item in result["results"]
            for alt in item.get("alternatives", [])
        ]
        assert " ".join(words) == "hello world"
