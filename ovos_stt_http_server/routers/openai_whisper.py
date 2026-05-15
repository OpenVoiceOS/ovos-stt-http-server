# Licensed under the Apache License, Version 2.0
"""OpenAI Whisper-compatible transcription endpoints."""
import time
from typing import Annotated, Any, Dict, List, Literal, Optional

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile
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


def make_openai_whisper_router(model, translator=None) -> APIRouter:
    """Create OpenAI Whisper-compatible router.

    Args:
        model: ModelContainer or MultiModelContainer instance.
        translator: OVOS LanguageTranslator instance for /audio/translations.
            Pass None to disable the endpoint (it will return 503).

    Returns:
        Configured APIRouter with OpenAI-compatible transcription endpoints.
    """
    router = APIRouter(prefix="/openai", tags=["openai-whisper"])

    async def _transcribe(
            file: UploadFile,
            language: Optional[str],
            response_format: _ResponseFormat,
            task: Literal["transcribe", "translate"] = "transcribe",
            translate_to_en: bool = False,
    ):
        """Internal transcription helper.

        Args:
            file: Uploaded audio file.
            language: Optional language hint passed to the STT plugin.
            response_format: One of json, text, srt, vtt, verbose_json.
            task: Task type for verbose response metadata.
            translate_to_en: If True, after STT run the text through the
                OVOS translator to produce English output. The STT plugin
                runs in the audio's actual language (auto-detect if no
                language hint), matching what OpenAI's /audio/translations
                does upstream.

        Returns:
            Transcription response in the requested format.
        """
        file_bytes = await file.read()
        audio = multipart_audio_to_audiodata(file_bytes, file.filename or "audio.wav")
        source_lang = language or "auto"
        start = time.time()
        text = model.process_audio(audio, source_lang)

        output_lang = source_lang
        if translate_to_en and text:
            if translator is None:
                raise HTTPException(
                    status_code=503,
                    detail="No OVOS translation plugin loaded. "
                           "Start the server with --translate-plugin <name>.",
                )
            try:
                text = translator.translate(text, target="en",
                                            source=None if source_lang == "auto"
                                            else source_lang)
            except Exception as exc:
                raise HTTPException(
                    status_code=502,
                    detail=f"Translation failed: {exc}",
                )
            output_lang = "en"

        lang = output_lang
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
        return await _transcribe(file, None, response_format, task="translate", translate_to_en=True)

    return router
