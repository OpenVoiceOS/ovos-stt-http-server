# Licensed under the Apache License, Version 2.0
"""AssemblyAI-compatible STT endpoint (synchronous stub)."""
import base64
import io
import uuid
import wave
from typing import Dict, List, Literal, Optional

from fastapi import APIRouter, Header
from pydantic import BaseModel, Field

from ovos_plugin_manager.utils.audio import AudioData


class AssemblyAIRequest(BaseModel):
    """Request body for POST /v2/transcript."""
    audio_url: Optional[str] = None
    audio: Optional[str] = Field(default=None, description="Base64-encoded audio bytes")
    language_code: Optional[str] = Field(default=None, min_length=1)
    punctuate: Optional[bool] = None
    format_text: Optional[bool] = None
    disfluencies: Optional[bool] = None
    speaker_labels: Optional[bool] = None


class AssemblyAIWord(BaseModel):
    """Word-level timing information."""
    text: str
    start: int = Field(..., ge=0)
    end: int = Field(..., ge=0)
    confidence: float = Field(..., ge=0.0, le=1.0)


class AssemblyAITranscript(BaseModel):
    """AssemblyAI transcript response."""
    id: str
    status: Literal["queued", "processing", "completed", "error"] = "completed"
    audio_url: Optional[str] = None
    text: Optional[str] = None
    words: List[AssemblyAIWord] = Field(default_factory=list)
    language_code: Optional[str] = None
    audio_duration: Optional[float] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    error: Optional[str] = None


def make_assemblyai_router(model) -> APIRouter:
    """Create AssemblyAI-compatible router (synchronous stub)."""
    router = APIRouter(prefix="/v2", tags=["assemblyai"])

    @router.post("/transcript", response_model=AssemblyAITranscript)
    def create_transcript(
            request: AssemblyAIRequest,
            authorization: Optional[str] = Header(default=None),
    ) -> AssemblyAITranscript:
        """Transcribe audio (AssemblyAI-compatible, synchronous stub).

        Accepts base64 audio in the `audio` field. The `audio_url` field is
        acknowledged but audio fetching is not supported — supply `audio` instead.

        Args:
            request: AssemblyAI transcript request.
            authorization: API key header (accepted, ignored).

        Returns:
            AssemblyAITranscript with status 'completed' and transcript text.
        """
        job_id = str(uuid.uuid4())
        lang = request.language_code or "en"

        if request.audio:
            try:
                audio_bytes = base64.b64decode(request.audio)
                try:
                    with wave.open(io.BytesIO(audio_bytes)) as wf:
                        sr = wf.getframerate()
                        sw = wf.getsampwidth()
                        raw = wf.readframes(wf.getnframes())
                    audio = AudioData(raw, sr, sw)
                except Exception:
                    audio = AudioData(audio_bytes, 16000, 2)
                transcript_text = model.process_audio(audio, lang)
            except Exception as exc:
                return AssemblyAITranscript(
                    id=job_id,
                    status="error",
                    audio_url=request.audio_url,
                    error=str(exc),
                )
        else:
            # audio_url provided but fetching not supported — return error
            return AssemblyAITranscript(
                id=job_id,
                status="error",
                audio_url=request.audio_url,
                error="audio_url fetching is not supported; supply base64 'audio' field instead.",
            )

        return AssemblyAITranscript(
            id=job_id,
            status="completed",
            audio_url=request.audio_url,
            text=transcript_text or "",
            language_code=lang,
            confidence=0.9,
        )

    @router.get("/transcript/{transcript_id}", response_model=AssemblyAITranscript)
    def get_transcript(
            transcript_id: str,
            authorization: Optional[str] = Header(default=None),
    ) -> AssemblyAITranscript:
        """Get transcript by ID (AssemblyAI-compatible stub).

        Since this server is synchronous, all transcripts are immediately
        completed. This endpoint returns a not-found stub.

        Args:
            transcript_id: ID of the transcript to retrieve.
            authorization: API key header (accepted, ignored).

        Returns:
            AssemblyAITranscript stub with error status.
        """
        return AssemblyAITranscript(
            id=transcript_id,
            status="error",
            error="Transcript retrieval by ID is not supported in synchronous mode.",
        )

    return router
