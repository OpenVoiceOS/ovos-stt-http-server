# Licensed under the Apache License, Version 2.0
"""vosk-server WebRTC variant.

Mirrors `alphacep/vosk-server/webrtc/asr_server_webrtc.py`:
  - POST /vosk-webrtc/offer  with body {"sdp": ..., "type": "offer"}
  - Server creates RTCPeerConnection, accepts the audio track + datachannel
  - Server returns {"sdp": ..., "type": "answer"}
  - Client streams audio over the peer connection
  - When the audio track ends (or peer closes), server runs the OVOS plugin
    on the buffered audio and sends `{"text": "..."}` on the datachannel
"""
import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from ovos_plugin_manager.utils.audio import AudioData


_LOG = logging.getLogger(__name__)

# Hold open peer connections so they don't get garbage-collected mid-stream.
_active_pcs: set = set()


class SDPOffer(BaseModel):
    sdp: str
    type: str = "offer"


class SDPAnswer(BaseModel):
    sdp: str
    type: str = "answer"


def make_vosk_webrtc_router(model) -> APIRouter:
    """vosk-server WebRTC-compatible router.

    Args:
        model: ModelContainer / MultiModelContainer.
    """
    try:
        from aiortc import RTCPeerConnection, RTCSessionDescription
        from av.audio.resampler import AudioResampler
    except ImportError as exc:
        raise ImportError(
            "vosk-webrtc compat requires the [webrtc] extra: pip install "
            "ovos-stt-http-server[webrtc]"
        ) from exc

    router = APIRouter(prefix="/vosk-webrtc", tags=["vosk-webrtc"])

    @router.post("/offer", response_model=SDPAnswer)
    async def offer(payload: SDPOffer) -> SDPAnswer:
        offer_desc = RTCSessionDescription(sdp=payload.sdp, type=payload.type)
        pc = RTCPeerConnection()
        _active_pcs.add(pc)

        # Per-connection state
        buffer = bytearray()
        resampler = AudioResampler(format="s16", layout="mono", rate=16000)
        datachannel: Optional[object] = None
        audio_finished = asyncio.Event()

        async def _send_result_and_close() -> None:
            """Run plugin on buffered audio, send via datachannel, close."""
            if buffer and datachannel is not None:
                audio = AudioData(bytes(buffer), 16000, 2)
                transcript = model.process_audio(audio, "auto") or ""
                try:
                    datachannel.send(json.dumps({"text": transcript}))
                except Exception:
                    _LOG.exception("failed to send transcript via datachannel")
            await pc.close()
            _active_pcs.discard(pc)

        @pc.on("datachannel")
        def _on_datachannel(channel):
            nonlocal datachannel
            datachannel = channel
            # Upstream sends an empty JSON to signal "listening"
            channel.send("{}")

        @pc.on("iceconnectionstatechange")
        async def _on_ice_change():
            if pc.iceConnectionState in ("failed", "closed"):
                audio_finished.set()
                await pc.close()
                _active_pcs.discard(pc)

        @pc.on("track")
        async def _on_track(track):
            if track.kind != "audio":
                return

            async def _pump():
                try:
                    while True:
                        frame = await track.recv()
                        for resampled in resampler.resample(frame):
                            buffer.extend(
                                bytes(resampled.planes[0])[: resampled.samples * 2]
                            )
                except Exception:
                    pass
                finally:
                    audio_finished.set()
                    await _send_result_and_close()

            asyncio.create_task(_pump())

            @track.on("ended")
            async def _on_ended():
                audio_finished.set()

        await pc.setRemoteDescription(offer_desc)
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        return SDPAnswer(
            sdp=pc.localDescription.sdp,
            type=pc.localDescription.type,
        )

    return router
