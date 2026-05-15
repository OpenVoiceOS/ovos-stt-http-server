# API Compatibility

`ovos-stt-http-server` exposes its underlying OVOS STT plugin behind
drop-in compatibility endpoints for popular cloud STT APIs. Each vendor
lives under its own URL prefix so multiple compat layers coexist with no
path collisions.

All routers accept any auth token / API key from the client and silently
ignore it — authentication is the responsibility of your reverse proxy.

Audio format conversion is provided by
`ovos_stt_http_server.audio_utils.multipart_audio_to_audiodata()`. Install
the `[audio]` extra (`pip install ovos-stt-http-server[audio]`) to enable
non-WAV inputs via `pydub`.

The shared network-redirect concept lives in
[`voice-pihole.md`](voice-pihole.md); per-vendor sections cross-reference it.

Status reflects merge state into `dev`:

- ✅ **merged** — full per-vendor docs section below the index.
- 🟡 **open** — PR is up; full docs on the feature branch.

## Commercial cloud STT

| Vendor | Prefix | Status | PR |
| :--- | :--- | :--- | :--- |
| OpenAI Whisper | `/openai` | 🟡 open | [#53](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/53) |
| Deepgram | `/deepgram` | 🟡 open | [#54](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/54) |
| Google Cloud STT | `/google` | 🟡 open | [#55](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/55) |
| AssemblyAI | `/assemblyai/v2` | 🟡 open | [#56](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/56) |
| Speechmatics | `/speechmatics/v1` | 🟡 open | [#57](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/57) |
| Microsoft Azure Speech | `/azure-stt` | 🟡 open | [#58](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/58) |
| AWS Transcribe | `/aws` | 🟡 open | [#60](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/60) |
| IBM Watson STT | `/watson/speech-to-text` | 🟡 open | [#61](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/61) |
| Wit.ai | `/wit` | 🟡 open | [#62](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/62) |
| Chromium Web Speech | `/speech-api/v2` | 🟡 open | [#68](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/68) |

## Self-hosted / OSS server protocols

| Server | Surface | Status | PR |
| :--- | :--- | :--- | :--- |
| vosk-server (WebSocket) | `/vosk` | 🟡 open | [#63](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/63) |
| vosk-server (gRPC) | `--vosk-grpc-port` | 🟡 open | [#65](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/65) |
| vosk-server (WebRTC) | `/vosk-webrtc/offer` | 🟡 open | [#66](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/66) |
| vosk-server (MQTT) | `--vosk-mqtt-broker` | 🟡 open | [#67](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/67) |
| kaldi-gstreamer-server | `/client/ws/speech` + `/client/dynamic/recognize` | 🟡 open | [#69](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/69) |
| whisper.cpp HTTP server | `/whisper-cpp/inference` | 🟡 open | [#64](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/64) |
| faster-whisper-server | re-uses `/openai/v1` | 🟡 open | [#72](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/72) |
| Wyoming (HA) | external adapter | ✅ merged | see [`wyoming-integration.md`](wyoming-integration.md) |

## OpenAI-compatible Whisper hosts

| Hosts | Status | PR |
| :--- | :--- | :--- |
| Groq, Cloudflare Workers AI, Fireworks AI, Together AI, OpenRouter | 🟡 open | [#71](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/71) |

Apps targeting these hosts already speak the OpenAI `/v1/audio/transcriptions`
contract — point them at our `/openai/v1` prefix.
