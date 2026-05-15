# `ovos-stt-http-server` Documentation Hub

`ovos-stt-http-server` exposes any OVOS STT plugin as a network service. On
its own it speaks one native protocol — but with compat routers enabled it
also pretends to be every major cloud STT API and every popular
self-hosted server, so **unmodified consumer apps transparently land on
this box** instead of a third-party cloud.

This directory is the documentation hub. Start with the use-case guide
that matches your goal:

| Goal | Read |
| :--- | :--- |
| Make unmodified consumer apps stop calling cloud STT services | [voice-pihole.md](voice-pihole.md) |
| Drive this server with the official Python/Node SDK of a specific vendor | [api-compatibility.md](api-compatibility.md) |
| Replace an existing self-hosted STT server on the wire | [api-compatibility.md](api-compatibility.md) (per-server section) |
| Bridge Home Assistant Voice / Voice PE | [wyoming-integration.md](wyoming-integration.md) |
| Understand the audio format negotiation | [audio-formats.md](audio-formats.md) |

The remaining files (`index.md`, etc.) cover the native `/stt` and
`/lang_detect` endpoints — what every other consumer of this server uses
when it doesn't need to pretend to be someone else.

## Compat coverage matrix

Each row is one compat surface — one router (or process-side bridge) plus
its docs, examples, and live tests.

### Commercial cloud STT

| Vendor | Prefix(es) | Status |
| :--- | :--- | :--- |
| OpenAI Whisper | `/openai/v1/audio/*` | shipped |
| OpenAI Whisper translation | `/openai/v1/audio/translations` | shipped (via OVOS translate plugin) |
| Deepgram | `/deepgram/v1/listen` (HTTP + WS) | shipped |
| Google Cloud STT | `/google/v1/speech:recognize` | shipped |
| AssemblyAI | `/assemblyai/v2/{upload,transcript,realtime/ws}` | shipped |
| Speechmatics | `/speechmatics/v1/{jobs*, ""}` (REST + WS) | shipped |
| Microsoft Azure Speech | `/azure-stt/cognitiveservices/v1` (REST + WS) | shipped |
| AWS Transcribe | `/aws/transcribe` (batch + streaming WS) | shipped |
| IBM Watson STT | `/watson/speech-to-text/v1/recognize` (REST + WS) | shipped |
| Wit.ai (Meta) | `/wit/speech` | shipped |
| Chromium Web Speech | `/speech-api/v2/recognize` | shipped |

### Self-hosted / open-source server protocols

| Server | Prefix / surface | Status |
| :--- | :--- | :--- |
| vosk-server (WebSocket) | `/vosk` | shipped |
| vosk-server (gRPC) | `--vosk-grpc-port` opt-in | shipped |
| vosk-server (WebRTC) | `/vosk-webrtc/offer` (opt-in extra) | shipped |
| vosk-server (MQTT) | `--vosk-mqtt-broker` opt-in | shipped |
| kaldi-gstreamer-server | `/client/ws/speech` + `/client/dynamic/recognize` | shipped |
| whisper.cpp HTTP server | `/whisper-cpp/inference` | shipped |
| faster-whisper-server | (re-uses `/openai/v1`) | docs-only |
| Wyoming (HA) | external adapter — see [wyoming-integration.md](wyoming-integration.md) | adapter only |

### OpenAI-shape Whisper hosts (no new code needed)

Apps that target Groq/Cloudflare/Fireworks/Together/OpenRouter all use the
OpenAI `/v1/audio/transcriptions` contract. Point them at our `/openai/v1`
prefix and they work — see [api-compatibility.md](api-compatibility.md) for
per-host nginx blocks.

## Voice-pihole concept

A single document — [voice-pihole.md](voice-pihole.md) — collects every
DNS-rewrite + nginx-reverse-proxy + CA-trust recipe across all the above
vendors. Use it when you want unmodified consumer apps to transparently
hit this server without any client-side configuration. The per-vendor
sections in `api-compatibility.md` reference back into it.
