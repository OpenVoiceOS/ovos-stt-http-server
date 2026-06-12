# Licensed under the Apache License, Version 2.0
"""Speechmatics-compatible STT endpoint (batch REST + realtime WebSocket)."""
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional

from fastapi import (APIRouter, File, Form, Header, HTTPException, UploadFile,
                     WebSocket, WebSocketDisconnect, status)
from pydantic import BaseModel, Field
from starlette.websockets import WebSocketState

from ovos_plugin_manager.utils.audio import AudioData
from ovos_stt_http_server.audio_utils import multipart_audio_to_audiodata


# In-memory job store: job_id → metadata + transcript text. Keeping job
# metadata separate from the transcript so GET /jobs/{id} (status poll)
# doesn't have to fabricate values on every call — the official SDK reads
# `created_at` / `data_name` from this response.
_jobs: Dict[str, Dict] = {}


class SpeechmaticsTranscriptionConfig(BaseModel):
    """Transcription configuration for Speechmatics."""
    language: str = Field(default="en", min_length=1)
    operating_point: Optional[str] = None
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


class SpeechmaticsJobDetails(BaseModel):
    """JobDetails fields used by GET /v1/jobs/{id}."""
    id: str
    status: Literal["running", "done", "rejected", "deleted"] = "done"
    created_at: str
    data_name: str
    duration: Optional[float] = None


class SpeechmaticsJobInfoEnvelope(BaseModel):
    """GET /v1/jobs/{id} response shape: {"job": {...}}."""
    job: SpeechmaticsJobDetails


class SpeechmaticsWord(BaseModel):
    """A word in a Speechmatics transcript."""
    type: Literal["word", "punctuation"] = "word"
    start_time: float = Field(..., ge=0.0)
    end_time: float = Field(..., ge=0.0)
    alternatives: List[Dict] = Field(default_factory=list)


class SpeechmaticsTranscriptResponse(BaseModel):
    """GET /v1/jobs/{job_id}/transcript response.

    Shape matches what the official `speechmatics-batch` SDK expects to parse
    into a `Transcript` dataclass: format + job + metadata + results.
    """
    format: str = "2.9"
    job: SpeechmaticsJobDetails
    metadata: Dict = Field(default_factory=dict)
    results: List[SpeechmaticsWord] = Field(default_factory=list)


def make_speechmatics_router(model) -> APIRouter:
    """Create Speechmatics-compatible router (synchronous stub)."""
    router = APIRouter(prefix="/speechmatics/v1", tags=["speechmatics"])

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
        filename = data_file.filename or "audio.wav"
        audio = multipart_audio_to_audiodata(file_bytes, filename)
        transcript_text = model.process_audio(audio, lang)
        _jobs[job_id] = {
            "text": transcript_text or "",
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "data_name": filename,
            "language": lang,
        }
        return SpeechmaticsJobResponse(id=job_id, status="done")

    @router.get("/jobs/{job_id}", response_model=SpeechmaticsJobInfoEnvelope)
    def get_job_info(
            job_id: str,
            authorization: Optional[str] = Header(default=None),
    ) -> SpeechmaticsJobInfoEnvelope:
        """Return job status — used by the official SDK's polling loop."""
        if job_id not in _jobs:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Job {job_id!r} not found.")
        j = _jobs[job_id]
        return SpeechmaticsJobInfoEnvelope(job=SpeechmaticsJobDetails(
            id=job_id, status="done",
            created_at=j["created_at"], data_name=j["data_name"],
        ))

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
        j = _jobs[job_id]
        text = j["text"]
        return SpeechmaticsTranscriptResponse(
            job=SpeechmaticsJobDetails(
                id=job_id, status="done",
                created_at=j["created_at"], data_name=j["data_name"],
            ),
            metadata={
                "created_at": j["created_at"],
                "type": "transcription",
                "transcription_config": {"language": j["language"]},
            },
            results=[
                SpeechmaticsWord(
                    type="word",
                    start_time=0.0,
                    end_time=1.0,
                    alternatives=[{"content": text, "confidence": 0.9}],
                )
            ] if text else [],
        )

    @router.websocket("")
    @router.websocket("/")
    async def realtime_ws(ws: WebSocket) -> None:
        """Realtime WS endpoint matching Speechmatics' RT API wire format.

        The official `speechmatics-rt` SDK connects to `wss://.../v2` (the
        prefix root) and exchanges:

        Inbound (text JSON):
          - `{"message":"StartRecognition","audio_format":{...},
              "transcription_config":{...}}`
          - `{"message":"EndOfStream","last_seq_no": N}`
          - `{"message":"ForceEndOfUtterance"}`
          - `{"message":"SetRecognitionConfig", ...}` (acked, ignored)

        Inbound (binary): raw audio bytes — one frame per AddAudio.

        Outbound (text JSON):
          - `{"message":"RecognitionStarted","id":"...","language_pack_info":{...}}`
          - `{"message":"AudioAdded","seq_no": N}` (one per binary frame)
          - `{"message":"AddTranscript","format":"2.9","metadata":{...},
              "results":[{"type":"word","alternatives":[{"content":"..."}]}]}`
          - `{"message":"EndOfTranscript"}`

        OVOS plugins are batch-only, so this buffers every AddAudio frame
        until EndOfStream / ForceEndOfUtterance / disconnect, then emits
        a single AddTranscript followed by EndOfTranscript and closes.
        """
        await ws.accept()
        session_id = str(uuid.uuid4())
        seq_no = 0
        buffer = bytearray()
        sample_rate = 16000
        language = "en"
        sample_width = 2
        start = time.time()
        started = False
        try:
            while True:
                msg = await ws.receive()
                if msg["type"] == "websocket.disconnect":
                    break
                if (data := msg.get("bytes")) is not None:
                    if not started:
                        # Audio without StartRecognition — drop silently
                        continue
                    buffer.extend(data)
                    seq_no += 1
                    await ws.send_text(json.dumps({
                        "message": "AudioAdded", "seq_no": seq_no,
                    }))
                    continue
                if (text := msg.get("text")) is not None:
                    try:
                        payload = json.loads(text)
                    except json.JSONDecodeError:
                        continue
                    mtype = payload.get("message")
                    if mtype == "StartRecognition":
                        audio_format = payload.get("audio_format") or {}
                        sample_rate = int(audio_format.get("sample_rate") or 16000)
                        encoding = audio_format.get("encoding") or "pcm_s16le"
                        sample_width = 1 if encoding.endswith("8") else 2
                        cfg = payload.get("transcription_config") or {}
                        language = cfg.get("language") or "en"
                        started = True
                        await ws.send_text(json.dumps({
                            "message": "RecognitionStarted",
                            "id": session_id,
                            "language_pack_info": {
                                "language_description": language,
                                "word_delimiter": " ",
                                "writing_direction": "left-to-right",
                            },
                        }))
                        continue
                    if mtype == "SetRecognitionConfig":
                        # Accept (e.g. language change), update language if given.
                        cfg = payload.get("transcription_config") or {}
                        if "language" in cfg:
                            language = cfg["language"]
                        continue
                    if mtype in ("EndOfStream", "ForceEndOfUtterance"):
                        break
        except WebSocketDisconnect:
            pass

        if buffer and ws.client_state == WebSocketState.CONNECTED:
            audio = AudioData(bytes(buffer), sample_rate, sample_width)
            transcript_text = model.process_audio(audio, language) or ""
            elapsed = time.time() - start
            await ws.send_text(json.dumps({
                "message": "AddTranscript",
                "format": "2.9",
                "metadata": {
                    "start_time": 0.0,
                    "end_time": elapsed,
                    "transcript": transcript_text,
                },
                "results": [{
                    "type": "word",
                    "start_time": 0.0,
                    "end_time": elapsed,
                    "alternatives": [{
                        "content": transcript_text,
                        "confidence": 1.0,
                        "language": language,
                    }],
                }] if transcript_text else [],
            }))
        if ws.client_state == WebSocketState.CONNECTED:
            await ws.send_text(json.dumps({"message": "EndOfTranscript"}))
            await ws.close()

    return router
