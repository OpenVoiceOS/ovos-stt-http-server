# Licensed under the Apache License, Version 2.0
"""OpenAI Whisper-compatible transcription endpoints."""
import time
from typing import Annotated, Any, Dict, List, Literal, Optional

from fastapi import APIRouter, File, Form, Header, UploadFile
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel, Field

from ovos_stt_http_server.audio_utils import multipart_audio_to_audiodata

_ResponseFormat = Literal["json", "text", "srt", "vtt", "verbose_json"]


class WhisperTranscriptionResponse(BaseModel):
    """JSON response for OpenAI transcription API."""

    text: str


class WhisperVerboseResponse(BaseModel):
    """Verbose JSON response for OpenAI transcription API."""

    task: Literal["transcribe", "translate"]
    language: str = Field(..., min_length=1)
    duration: float = Field(..., ge=0.0)
    text: str
    segments: List[Dict[str, Any]] = Field(default_factory=list)


def make_openai_whisper_router(model) -> APIRouter:
    """Create OpenAI Whisper-compatible router.

    Args:
        model: ModelContainer or MultiModelContainer instance.

    Returns:
        Configured APIRouter with OpenAI-compatible transcription endpoints.
    """
    router = APIRouter(prefix="/openai", tags=["openai-whisper"])

    async def _transcribe(
            file: UploadFile,
            language: Optional[str],
            response_format: _ResponseFormat,
            task: Literal["transcribe", "translate"] = "transcribe",
            force_lang: Optional[str] = None,
    ):
        """Internal transcription helper.

        Args:
            file: Uploaded audio file.
            language: Optional language hint.
            response_format: One of json, text, srt, vtt, verbose_json.
            task: Task type for verbose response metadata.
            force_lang: If set, overrides language (used for translation endpoint).

        Returns:
            Transcription response in the requested format.
        """
        file_bytes = await file.read()
        audio = multipart_audio_to_audiodata(file_bytes, file.filename or "audio.wav")
        lang = force_lang or language or "auto"
        start = time.time()
        text = model.process_audio(audio, lang)
        duration = time.time() - start

        if response_format == "text":
            return PlainTextResponse(text)
        elif response_format == "srt":
            srt = f"1\n00:00:00,000 --> 00:00:{int(duration):02d},000\n{text}\n"
            return PlainTextResponse(srt)
        elif response_format == "vtt":
            vtt = f"WEBVTT\n\n00:00:00.000 --> 00:00:{int(duration):02d}.000\n{text}\n"
            return PlainTextResponse(vtt)
        elif response_format == "verbose_json":
            resp = WhisperVerboseResponse(
                task=task,
                language=lang,
                duration=duration,
                text=text,
                segments=[],
            )
            return JSONResponse(resp.model_dump())
        else:
            return JSONResponse(WhisperTranscriptionResponse(text=text).model_dump())

    @router.post("/v1/audio/transcriptions")
    async def transcriptions(
            file: UploadFile = File(...),
            model_name: Optional[str] = Form(default=None, alias="model"),
            language: Optional[str] = Form(default=None),
            response_format: _ResponseFormat = Form(default="json"),
            temperature: Annotated[Optional[float], Field(ge=0.0, le=1.0)] = Form(default=None),
            authorization: Optional[str] = Header(default=None),
    ):
        """Transcribe audio (OpenAI Whisper-compatible).

        Args:
            file: Audio file to transcribe.
            model_name: Model identifier (accepted, ignored).
            language: Optional language hint (BCP-47 code).
            response_format: Output format: json, text, srt, vtt, verbose_json.
            temperature: Sampling temperature 0–1 (accepted, ignored).
            authorization: Bearer token (accepted, ignored).

        Returns:
            Transcription in the requested format.
        """
        return await _transcribe(file, language, response_format)

    @router.post("/v1/audio/translations")
    async def translations(
            file: UploadFile = File(...),
            model_name: Optional[str] = Form(default=None, alias="model"),
            response_format: _ResponseFormat = Form(default="json"),
            temperature: Annotated[Optional[float], Field(ge=0.0, le=1.0)] = Form(default=None),
            authorization: Optional[str] = Header(default=None),
    ):
        """Translate audio to English (OpenAI Whisper-compatible).

        Forces language to 'en' regardless of audio language.

        Args:
            file: Audio file to translate.
            model_name: Model identifier (accepted, ignored).
            response_format: Output format: json, text, srt, vtt, verbose_json.
            temperature: Sampling temperature 0–1 (accepted, ignored).
            authorization: Bearer token (accepted, ignored).

        Returns:
            Transcription in the requested format with forced English output.
        """
        return await _transcribe(file, None, response_format, task="translate", force_lang="en")

    return router
