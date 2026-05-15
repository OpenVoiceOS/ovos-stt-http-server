# `ovos-stt-http-server` Documentation Hub

`ovos-stt-http-server` exposes any OVOS STT plugin as a network service. On
its own it speaks one native protocol — but with compat routers enabled it
also pretends to be every major cloud STT API and every popular
self-hosted server, so **unmodified consumer apps transparently land on
this box** instead of a third-party cloud.

| Goal | Read |
| :--- | :--- |
| Make unmodified consumer apps stop calling cloud STT services | [voice-pihole.md](voice-pihole.md) |
| Drive this server with the official Python/Node SDK of a specific vendor | [api-compatibility.md](api-compatibility.md) |
| Replace an existing self-hosted STT server on the wire | [api-compatibility.md](api-compatibility.md) |
| Bridge Home Assistant Voice / Voice PE | [wyoming-integration.md](wyoming-integration.md) |
| Audio format negotiation | [audio-formats.md](audio-formats.md) |

## Compat coverage matrix

- ✅ **merged** — landed on `dev`; per-vendor docs inlined in [`api-compatibility.md`](api-compatibility.md).
- 🟡 **open** — PR up; per-vendor docs on the feature branch.
- ⚪ **planned** — see [TODO / WIP](#todo--wip).

### Commercial cloud STT

| Vendor | Prefix | Status | PR |
| :--- | :--- | :--- | :--- |
| OpenAI Whisper | `/openai/v1/audio/*` | 🟡 open | [#53](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/53) |
| Deepgram | `/deepgram/v1/listen` (HTTP + WS) | 🟡 open | [#54](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/54) |
| Google Cloud STT | `/google/v1/speech:recognize` | 🟡 open | [#55](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/55) |
| AssemblyAI | `/assemblyai/v2/{upload,transcript,realtime/ws}` | 🟡 open | [#56](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/56) |
| Speechmatics | `/speechmatics/v1` (REST + WS) | 🟡 open | [#57](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/57) |
| Microsoft Azure Speech | `/azure-stt/cognitiveservices/v1` (REST + WS) | 🟡 open | [#58](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/58) |
| AWS Transcribe | `/aws/transcribe` (batch + streaming WS) | 🟡 open | [#60](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/60) |
| IBM Watson STT | `/watson/speech-to-text/v1/recognize` (REST + WS) | 🟡 open | [#61](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/61) |
| Wit.ai (Meta) | `/wit/speech` | 🟡 open | [#62](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/62) |
| Chromium Web Speech | `/speech-api/v2/recognize` | 🟡 open | [#68](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/68) |

### Self-hosted / open-source server protocols

| Server | Surface | Status | PR |
| :--- | :--- | :--- | :--- |
| vosk-server (WebSocket) | `/vosk` | 🟡 open | [#63](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/63) |
| vosk-server (gRPC) | `--vosk-grpc-port` | 🟡 open | [#65](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/65) |
| vosk-server (WebRTC) | `/vosk-webrtc/offer` | 🟡 open | [#66](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/66) |
| vosk-server (MQTT) | `--vosk-mqtt-broker` | 🟡 open | [#67](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/67) |
| kaldi-gstreamer-server | `/client/ws/speech` + `/client/dynamic/recognize` | 🟡 open | [#69](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/69) |
| whisper.cpp HTTP server | `/whisper-cpp/inference` | 🟡 open | [#64](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/64) |
| faster-whisper-server | re-uses `/openai/v1` | 🟡 open | [#72](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/72) |
| Wyoming (HA) | external adapter — see [wyoming-integration.md](wyoming-integration.md) | ✅ merged | [#59](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/59) |

### OpenAI-compatible Whisper hosts

| Hosts | Status | PR |
| :--- | :--- | :--- |
| Groq, Cloudflare Workers AI, Fireworks AI, Together AI, OpenRouter | 🟡 open | [#71](https://github.com/OpenVoiceOS/ovos-stt-http-server/pull/71) |

Apps targeting these hosts already speak the OpenAI `/v1/audio/transcriptions`
contract — point them at our `/openai/v1` prefix.

## Voice-pihole

[voice-pihole.md](voice-pihole.md) collects every DNS-rewrite + reverse-proxy
+ CA-trust recipe across all the above vendors.

---

## TODO / WIP

### Streaming partial transcripts

Every compat router with a streaming surface (Deepgram WS, AssemblyAI
realtime, Speechmatics RT, Azure WS, Watson WS, vosk WS, AWS streaming,
Chromium) runs as buffered batch — audio is collected for the lifetime
of the stream and a single final transcript is emitted on close. OVOS
STT plugins don't expose a partial / interim hypothesis interface.

Needed:
- A VAD-driven chunker upstream of the OVOS plugin call, OR
- New plugin-side streaming support (OPM contract change).

### Vendor coverage gaps

- **Web Speech API native binary protocol** — the `Sec-WebSocket-Protocol`
  framing modern Chrome/Edge use for the in-browser `SpeechRecognition`
  Web API. Distinct from the legacy `/speech-api/v2/recognize` REST (#68).
- **Rev.ai** — REST + streaming WS.
- **Soniox** — gRPC streaming.
- **AssemblyAI streaming V3** — schema differs from the V2 realtime in #56.
- **whisper.cpp `verbose_json` with segment timestamps** — needs VAD pipeline.
- **AWS Transcribe streaming over real HTTP/2 event-stream** — #60 ships
  a plain WS surface; SDK-level apps that bypass WS need a translator.
- **vosk gRPC `StatsService`** — second proto service in #65's vendored
  `.proto` not implemented.
