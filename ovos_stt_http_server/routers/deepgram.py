# Licensed under the Apache License, Version 2.0
"""Deepgram-compatible STT endpoint."""
import time
import uuid
from typing import List, Optional

from fastapi import APIRouter, Header, Query, Request
from pydantic import BaseModel, Field

from ovos_plugin_manager.utils.audio import AudioData


class DeepgramWord(BaseModel):
    """A single word with timing in a Deepgram transcript."""
    word: str
    start: float = Field(..., ge=0.0)
    end: float = Field(..., ge=0.0)
    confidence: float = Field(..., ge=0.0, le=1.0)


class DeepgramAlternative(BaseModel):
    """A single transcription alternative."""
    transcript: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    words: List[DeepgramWord] = Field(default_factory=list)


class DeepgramChannel(BaseModel):
    """A single audio channel's transcription results."""
    alternatives: List[DeepgramAlternative]


class DeepgramResults(BaseModel):
    """Top-level results container."""
    channels: List[DeepgramChannel]


class DeepgramMetadata(BaseModel):
    """Request metadata in Deepgram response."""
    request_id: str
    created: str
    duration: float = Field(..., ge=0.0)
    channels: int = Field(default=1, ge=1)
    models: List[str] = Field(default_factory=lambda: ["general"])


class DeepgramResponse(BaseModel):
    """Full Deepgram transcription response."""
    metadata: DeepgramMetadata
    results: DeepgramResults


def make_deepgram_router(model) -> APIRouter:
    """Create Deepgram-compatible router."""
    router = APIRouter(prefix="/deepgram", tags=["deepgram"])

    @router.post("/v1/listen", response_model=DeepgramResponse)
    async def listen(
            request: Request,
            language: str = Query(default="en"),
            model_name: Optional[str] = Query(default=None, alias="model"),
            punctuate: Optional[bool] = Query(default=None),
            diarize: Optional[bool] = Query(default=None),
            authorization: Optional[str] = Header(default=None),
    ) -> DeepgramResponse:
        """Transcribe audio (Deepgram-compatible).

        Args:
            request: Raw request whose body contains audio bytes.
            language: BCP-47 language code.
            model_name: Model name (accepted, ignored).
            punctuate: Punctuation flag (accepted, ignored).
            diarize: Diarization flag (accepted, ignored).
            authorization: Token auth header (accepted, ignored).

        Returns:
            DeepgramResponse with transcription results.
        """
        audio_bytes = await request.body()
        # Default 16kHz 16-bit mono
        audio = AudioData(audio_bytes, 16000, 2)
        start = time.time()
        transcript = model.process_audio(audio, language)
        duration = time.time() - start

        return DeepgramResponse(
            metadata=DeepgramMetadata(
                request_id=str(uuid.uuid4()),
                created=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                duration=duration,
                channels=1,
                models=["ovos"],
            ),
            results=DeepgramResults(
                channels=[
                    DeepgramChannel(
                        alternatives=[
                            DeepgramAlternative(
                                transcript=transcript or "",
                                confidence=1.0,
                                words=[],
                            )
                        ]
                    )
                ]
            ),
        )

    return router
