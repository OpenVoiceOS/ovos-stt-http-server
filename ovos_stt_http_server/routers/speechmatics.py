# Licensed under the Apache License, Version 2.0
"""Speechmatics-compatible STT endpoint (synchronous stub)."""
import json
import uuid
from typing import Dict, List, Literal, Optional

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from ovos_stt_http_server.audio_utils import multipart_audio_to_audiodata

# In-memory store: job_id → transcript text
_jobs: Dict[str, str] = {}


class SpeechmaticsTranscriptionConfig(BaseModel):
    """Transcription configuration for Speechmatics."""
    language: str = Field(default="en", min_length=1)
    operating_point: Optional[Literal["standard", "enhanced"]] = None
    diarization: Optional[str] = None


class SpeechmaticsJobConfig(BaseModel):
    """Top-level job configuration."""
    type: Literal["transcription"] = "transcription"
    transcription_config: SpeechmaticsTranscriptionConfig = Field(
        default_factory=SpeechmaticsTranscriptionConfig
    )


class SpeechmaticsJobResponse(BaseModel):
    """Response from POST /v1/jobs."""
    id: str
    status: Literal["running", "done", "rejected", "deleted"] = "done"


class SpeechmaticsWord(BaseModel):
    """A word in a Speechmatics transcript."""
    type: Literal["word", "punctuation"] = "word"
    start_time: float = Field(..., ge=0.0)
    end_time: float = Field(..., ge=0.0)
    alternatives: List[Dict] = Field(default_factory=list)


class SpeechmaticsTranscriptResponse(BaseModel):
    """GET /v1/jobs/{job_id}/transcript response."""
    format: str = "2.9"
    job: SpeechmaticsJobResponse
    results: List[SpeechmaticsWord] = Field(default_factory=list)
    metadata: Dict = Field(default_factory=dict)


def make_speechmatics_router(model) -> APIRouter:
    """Create Speechmatics-compatible router (synchronous stub)."""
    router = APIRouter(prefix="/v1", tags=["speechmatics"])

    @router.post("/jobs", response_model=SpeechmaticsJobResponse)
    async def create_job(
            data_file: UploadFile = File(...),
            config: str = Form(...),
            authorization: Optional[str] = Header(default=None),
    ) -> SpeechmaticsJobResponse:
        """Create transcription job (Speechmatics-compatible, synchronous stub).

        Transcribes immediately and stores result for GET retrieval.

        Args:
            data_file: Audio file upload.
            config: JSON string with SpeechmaticsJobConfig.
            authorization: Auth header (accepted, ignored).

        Returns:
            SpeechmaticsJobResponse with job ID and 'done' status.
        """
        job_id = str(uuid.uuid4())
        try:
            cfg = SpeechmaticsJobConfig(**json.loads(config))
            lang = cfg.transcription_config.language
        except Exception:
            lang = "en"

        file_bytes = await data_file.read()
        audio = multipart_audio_to_audiodata(file_bytes, data_file.filename or "audio.wav")
        transcript_text = model.process_audio(audio, lang)
        _jobs[job_id] = transcript_text or ""

        return SpeechmaticsJobResponse(id=job_id, status="done")

    @router.get("/jobs/{job_id}/transcript", response_model=SpeechmaticsTranscriptResponse)
    def get_transcript(
            job_id: str,
            format: str = "json-v2",
            authorization: Optional[str] = Header(default=None),
    ) -> SpeechmaticsTranscriptResponse:
        """Retrieve transcript for a completed job (Speechmatics-compatible).

        Args:
            job_id: Job identifier from POST /v1/jobs response.
            format: Response format (accepted, json-v2 returned regardless).
            authorization: Auth header (accepted, ignored).

        Returns:
            SpeechmaticsTranscriptResponse with results.

        Raises:
            HTTPException: 404 if job_id not found.
        """
        if job_id not in _jobs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id!r} not found.",
            )
        text = _jobs[job_id]
        return SpeechmaticsTranscriptResponse(
            job=SpeechmaticsJobResponse(id=job_id, status="done"),
            results=[
                SpeechmaticsWord(
                    type="word",
                    start_time=0.0,
                    end_time=1.0,
                    alternatives=[{"content": text, "confidence": 0.9}],
                )
            ] if text else [],
        )

    return router
