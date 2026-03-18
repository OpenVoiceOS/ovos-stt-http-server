# Licensed under the Apache License, Version 2.0
"""Google Cloud STT-compatible endpoint."""
import base64
import io
import wave
from typing import List, Optional

from fastapi import APIRouter, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

from ovos_plugin_manager.utils.audio import AudioData


class GoogleSTTConfig(BaseModel):
    """Recognition configuration."""
    encoding: Optional[str] = Field(default="LINEAR16", min_length=1)
    sampleRateHertz: Optional[int] = Field(default=16000, gt=0)
    languageCode: str = Field(default="en-US", min_length=1)
    maxAlternatives: Optional[int] = Field(default=1, ge=1, le=30)
    enableAutomaticPunctuation: Optional[bool] = None


class GoogleSTTAudio(BaseModel):
    """Audio input: base64 content or GCS URI."""
    content: Optional[str] = None
    uri: Optional[str] = None


class GoogleSTTRequest(BaseModel):
    """Request body for POST /v1/speech:recognize."""
    config: GoogleSTTConfig
    audio: GoogleSTTAudio


class GoogleSTTAlternative(BaseModel):
    """A single recognition alternative."""
    transcript: str
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)


class GoogleSTTResult(BaseModel):
    """A single recognition result."""
    alternatives: List[GoogleSTTAlternative] = Field(..., min_length=1)


class GoogleSTTResponse(BaseModel):
    """Response for POST /v1/speech:recognize."""
    results: List[GoogleSTTResult]


def make_google_stt_router(model) -> APIRouter:
    """Create Google Cloud STT-compatible router."""
    router = APIRouter(prefix="/google", tags=["google-stt"])

    @router.post("/v1/speech:recognize", response_model=GoogleSTTResponse)
    def recognize(
            request: GoogleSTTRequest,
            key: Optional[str] = Query(default=None),
            authorization: Optional[str] = Header(default=None),
    ) -> GoogleSTTResponse:
        """Transcribe audio (Google Cloud STT-compatible).

        Args:
            request: Google STT recognition request with config and base64 audio.
            key: API key query param (accepted, ignored).
            authorization: Bearer token (accepted, ignored).

        Returns:
            GoogleSTTResponse with recognition results.

        Raises:
            HTTPException: 400 if neither content nor uri is provided.
            HTTPException: 501 if GCS URI is supplied (not supported).
        """
        if request.audio.uri:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="GCS URI audio input is not supported; use 'content' (base64).",
            )
        if not request.audio.content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="audio.content (base64-encoded audio) is required.",
            )

        audio_bytes = base64.b64decode(request.audio.content)
        sr = request.config.sampleRateHertz or 16000

        # Attempt to parse as WAV; fall back to raw PCM
        try:
            with wave.open(io.BytesIO(audio_bytes)) as wf:
                sr = wf.getframerate()
                sw = wf.getsampwidth()
                raw = wf.readframes(wf.getnframes())
            audio = AudioData(raw, sr, sw)
        except Exception:
            audio = AudioData(audio_bytes, sr, 2)

        lang = request.config.languageCode
        transcript = model.process_audio(audio, lang)
        return GoogleSTTResponse(
            results=[
                GoogleSTTResult(
                    alternatives=[GoogleSTTAlternative(transcript=transcript or "", confidence=0.9)]
                )
            ]
        )

    return router
