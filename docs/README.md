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
its docs, examples, and live tests. The **PR** column links to the
in-flight PR; once a row's PR is merged, the per-vendor docs live inline
in [`api-compatibility.md`](api-compatibility.md).

### Foundation

| Branch | Status | PR |
| :--- | :--- | :--- |
| `modernize-base` — gradio drop, CORSMiddleware, audio_utils, shared workflows, unit test scaffolding (≥90% coverage) | shipped | [#52](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/52) |
| `docs/voice-pihole-hub` — this hub itself | shipped | [#70](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/70) |

### Commercial cloud STT

| Vendor | Prefix(es) | Status | PR |
| :--- | :--- | :--- | :--- |
| OpenAI Whisper | `/openai/v1/audio/*` | shipped | [#53](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/53) |
| Deepgram | `/deepgram/v1/listen` (HTTP + WS) | shipped | [#54](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/54) |
| Google Cloud STT | `/google/v1/speech:recognize` | shipped | [#55](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/55) |
| AssemblyAI | `/assemblyai/v2/{upload,transcript,realtime/ws}` | shipped | [#56](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/56) |
| Speechmatics | `/speechmatics/v1/{jobs*, ""}` (REST + WS) | shipped | [#57](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/57) |
| Microsoft Azure Speech | `/azure-stt/cognitiveservices/v1` (REST + WS) | shipped | [#58](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/58) |
| AWS Transcribe | `/aws/transcribe` (batch + streaming WS) | shipped | [#60](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/60) |
| IBM Watson STT | `/watson/speech-to-text/v1/recognize` (REST + WS) | shipped | [#61](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/61) |
| Wit.ai (Meta) | `/wit/speech` | shipped | [#62](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/62) |
| Chromium Web Speech | `/speech-api/v2/recognize` | shipped | [#68](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/68) |

### Self-hosted / open-source server protocols

| Server | Prefix / surface | Status | PR |
| :--- | :--- | :--- | :--- |
| vosk-server (WebSocket) | `/vosk` | shipped | [#63](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/63) |
| vosk-server (gRPC) | `--vosk-grpc-port` opt-in | shipped | [#65](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/65) |
| vosk-server (WebRTC) | `/vosk-webrtc/offer` (opt-in extra) | shipped | [#66](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/66) |
| vosk-server (MQTT) | `--vosk-mqtt-broker` opt-in | shipped | [#67](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/67) |
| kaldi-gstreamer-server | `/client/ws/speech` + `/client/dynamic/recognize` | shipped | [#69](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/69) |
| whisper.cpp HTTP server | `/whisper-cpp/inference` | shipped | [#64](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/64) |
| faster-whisper-server | re-uses `/openai/v1` | docs only | [#72](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/72) |
| Wyoming (HA) | external adapter — see [wyoming-integration.md](wyoming-integration.md) | adapter only | [#59](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/59) |

### OpenAI-shape Whisper hosts (Tier 2 — no router code)

| Host | Status | PR |
| :--- | :--- | :--- |
| Groq, Cloudflare Workers AI, Fireworks AI, Together AI, OpenRouter | docs only | [#71](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/71) |

Apps targeting these hosts already speak the OpenAI `/v1/audio/transcriptions`
contract — point them at our `/openai/v1` prefix.

## Voice-pihole concept

[voice-pihole.md](voice-pihole.md) collects every DNS-rewrite +
nginx-reverse-proxy + CA-trust recipe across all the above vendors. Use
it when you want unmodified consumer apps to transparently hit this
server without any client-side configuration. The per-vendor sections in
`api-compatibility.md` reference back into it.

---

## TODO / WIP

Things explicitly **not** done yet — open issues / PRs welcome.

### Streaming partial transcripts

Every compat router that exposes a streaming surface (Deepgram WS,
AssemblyAI realtime, Speechmatics RT, Azure WS, Watson WS, vosk WS,
AWS streaming, Chromium) currently runs as **buffered batch**: audio is
collected for the lifetime of the stream and a single final transcript is
emitted on close / EOS. This is because OVOS STT plugins themselves are
batch-only — they don't expose a partial / interim hypothesis interface.

To produce true interim transcripts we'd need:

- A VAD-driven chunker upstream of the OVOS plugin call, OR
- New plugin-side support for streaming recognition (an OPM contract change)

Tracking issue: TBD.

### Vendor coverage gaps

- **Web Speech API native protocol** — the binary `Sec-WebSocket-Protocol`
  framing that modern Chrome/Edge use for the in-browser `SpeechRecognition`
  Web API (distinct from the legacy `/speech-api/v2/recognize` REST that
  PR #68 covers). Reverse-engineering needed.
- **Rev.ai** — REST + streaming WS. Lower priority than the Tier-1 vendors
  but apps in the media-transcription space use it.
- **Soniox** — gRPC streaming. Niche but real.
- **AssemblyAI streaming V3** — schema differs from the V2 realtime we
  ship (PR #56). Add when V2 sunsets.
- **Whisper.cpp's verbose-json with segments** — accepted today but
  segment-level timestamps require a VAD pipeline OVOS plugins don't
  expose. Tracked as part of "Streaming partial transcripts" above.
- **AWS Transcribe streaming over real HTTP/2 event-stream** — we expose
  a plain WS surface (PR #60) for ease of integration; the real upstream
  uses AWS event-stream framing over HTTP/2. SDK-level apps that bypass
  the WS path need a separate translator.
- **Vosk gRPC `StatsService`** — `vosk-server`'s second proto service
  (n_streams / n_total_streams / RTF) is not implemented (PR #65 ships
  only `SttService.StreamingRecognize`).

### Documentation TODOs

- One-pager per use-case ("running on a Raspberry Pi", "behind Tailscale",
  "with Caddy instead of nginx") — voice-pihole.md is nginx-centric today.
- A canonical mkcert / step-ca walkthrough for new self-hosters.
- A migration guide from each vendor SDK to drop-in mode (per-vendor
  config diff).

### Process

Once PR #70 (this hub) lands, every open compat PR rebases on `dev` and
in its own diff:
1. Removes its row's PR link from the master index in `api-compatibility.md`.
2. Inlines its full docs section below the index.

That converts each row from "in-flight" to "shipped + officialised". The
TODO list above gets pruned as items land.
