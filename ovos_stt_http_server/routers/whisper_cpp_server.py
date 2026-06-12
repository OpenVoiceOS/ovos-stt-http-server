# Licensed under the Apache License, Version 2.0
"""whisper.cpp HTTP server-compatible router.

Reference: ggerganov/whisper.cpp/examples/server

Endpoint: POST /inference  (multipart: `file` + optional form fields)
Response: `{"text": "..."}` (or JSON segments for response_format=verbose_json).
"""
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel

from ovos_stt_http_server.audio_utils import multipart_audio_to_audiodata


class WhisperCppResponse(BaseModel):
    text: str


def make_whisper_cpp_server_router(model) -> APIRouter:
    """whisper.cpp HTTP server-compatible router.

    Single endpoint at `/whisper-cpp/inference` (matches upstream
    `/inference`); the prefix lets it coexist with other routers.
    """
    router = APIRouter(prefix="/whisper-cpp", tags=["whisper-cpp-server"])

    @router.post("/inference")
    async def inference(
            file: UploadFile = File(...),
            temperature: Optional[str] = Form(default=None),
            language: Optional[str] = Form(default=None),
            response_format: Optional[str] = Form(default="json"),
            translate: Optional[bool] = Form(default=False),
    ):
        """Transcribe an uploaded audio file.

        Mirrors the wire format documented in `whisper.cpp/examples/server/README.md`.
        `translate=true` is accepted but currently routes to the same OVOS STT
        plugin call; users who need real translation should chain a translate
        plugin (see the /openai-whisper router for the cross-language pattern).
        """
        file_bytes = await file.read()
        audio = multipart_audio_to_audiodata(file_bytes, file.filename or "audio.wav")
        text = model.process_audio(audio, language or "auto") or ""
        if response_format == "text":
            return PlainTextResponse(text)
        return JSONResponse(WhisperCppResponse(text=text).model_dump())

    return router
