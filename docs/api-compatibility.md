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

---

## Available now

These routers are mounted by `create_app()` and live on `dev`. A runnable
client script for each is in [`../examples/`](../examples/).

### Commercial cloud STT

| Vendor | Method | Path | Client / example |
| :--- | :--- | :--- | :--- |
| OpenAI Whisper | POST | `/openai/v1/audio/transcriptions`, `/openai/v1/audio/translations` | official `openai` — [`openai_whisper_example.py`](../examples/openai_whisper_example.py) |
| Deepgram | POST / WS | `/deepgram/v1/listen` | official `deepgram-sdk` — [`deepgram_example.py`](../examples/deepgram_example.py) |
| Google Cloud STT | POST | `/google/v1/speech:recognize` | HTTP — [`../examples/`](../examples/) |
| AssemblyAI | POST / GET / WS | `/assemblyai/v2/upload`, `/assemblyai/v2/transcript`, realtime WS | official `assemblyai` — [`assemblyai_example.py`](../examples/assemblyai_example.py) |
| Speechmatics | POST / GET / WS | `/speechmatics/...` batch jobs + realtime WS | official `speechmatics-batch` — [`speechmatics_example.py`](../examples/speechmatics_example.py) |
| Microsoft Azure Speech | POST / WS | `/azure-stt/cognitiveservices/v1` | HTTP — [`azure_stt_example.py`](../examples/azure_stt_example.py) |
| AWS Transcribe | POST / WS | `/aws/transcribe` (batch) + streaming WS | official `boto3` — [`aws_transcribe_example.py`](../examples/aws_transcribe_example.py) |
| IBM Watson STT | POST / WS | `/watson/speech-to-text/v1/recognize` | official `ibm-watson` — [`ibm_watson_example.py`](../examples/ibm_watson_example.py) |
| Wit.ai | POST | `/wit/speech` | official `wit` — [`wit_ai_example.py`](../examples/wit_ai_example.py) |
| Chromium Web Speech | POST | `/speech-api/v2/recognize` | `ovos-stt-plugin-chromium` — [`chromium_example.py`](../examples/chromium_example.py) — [details below](#chromium--chrome-web-speech-api-speech-apiv2) |

### Self-hosted / OSS server protocols

| Server | Method | Path | Client / example |
| :--- | :--- | :--- | :--- |
| whisper.cpp HTTP server | POST | `/whisper-cpp/inference` (and OpenAI alias `/whisper-cpp/v1/audio/transcriptions`) | HTTP — [`whisper_cpp_example.py`](../examples/whisper_cpp_example.py) |
| vosk-server (WebRTC) | POST | `/vosk-webrtc/offer` | requires the optional `aiortc` dependency |
| OpenAI-compatible Whisper hosts | POST | `/openai/v1/audio/transcriptions` | Groq, Cloudflare Workers AI, Fireworks AI, Together AI, OpenRouter, faster-whisper-server — all speak the OpenAI contract, so point them at the `/openai/v1` prefix |
| Wyoming (Home Assistant) | — | external adapter | see [`wyoming-integration.md`](wyoming-integration.md) |

## Planned / not mounted by default

These routers exist in the package but are **not** mounted by `create_app()` in
the default application (they need extra dependencies, a separate process, or a
dedicated CLI flag) and are tracked for a future release:

| Server | Surface | Notes |
| :--- | :--- | :--- |
| vosk-server (WebSocket) | `/vosk` | router present, not mounted in the default app |
| vosk-server (gRPC) | `--vosk-grpc-port` | separate gRPC service |
| vosk-server (MQTT) | `--vosk-mqtt-broker` | separate MQTT bridge |
| kaldi-gstreamer-server | `/client/ws/speech`, `/client/ws/status` | router present, not mounted in the default app |

For streaming-partial-transcript limitations and additional vendor gaps, see
the project `TODO.md`.

---

## Chromium / Chrome Web Speech API (`/speech-api/v2`)

**Upstream sources**:
- Wire format reverse-engineered in
  [OpenVoiceOS/ovos-stt-plugin-chromium](https://github.com/OpenVoiceOS/ovos-stt-plugin-chromium)
- Original protocol description: [Chromium speech API key history](http://web.archive.org/web/20160309230031/http://www.chromium.org/developers/how-tos/api-keys)

### Endpoint

| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/speech-api/v2/recognize` | FLAC body → newline-delimited JSON results |

Query parameters (all accepted, all silently ignored — the OVOS plugin
chooses what to recognise):

| Param | Notes |
| :--- | :--- |
| `client` | Defaults to `chromium`; some upstream clients use `chrome`. |
| `lang` | BCP-47 language tag; forwarded to the OVOS plugin. |
| `key` | Chromium API key. Accepted, never validated. |
| `pFilter` | Profanity filter flag — accepted, ignored. |

### Response

Two newline-delimited JSON lines, matching the upstream wire format
verbatim. Some clients only parse the second; others stream both. We send
both even for empty results so streaming consumers see at least one frame:

```json
{"result":[]}
{"result":[{"alternative":[{"transcript":"hello world","confidence":0.99}],"final":true}],"result_index":0}
```

Empty-transcript case emits only the first line.

### Pointing apps at this server

The canonical "SDK" for this API is the `ovos-stt-plugin-chromium`
package — it speaks the exact wire format. Drive it against this server
with a `requests` monkey-patch (in production replace this with the
nginx redirect below):

```python
import ovos_stt_plugin_chromium as chromium_mod
real_post = chromium_mod.requests.post

def patched_post(url, *args, **kwargs):
    if url.startswith("http://www.google.com/speech-api"):
        url = "http://localhost:8080/speech-api" + url.split("/speech-api", 1)[1]
    return real_post(url, *args, **kwargs)

chromium_mod.requests.post = patched_post

from ovos_stt_plugin_chromium import ChromiumSTT
plugin = ChromiumSTT(config={"lang": "en-us"})
# plugin.execute(audio) routes through patched_post → our server
```

A runnable version (with full `speech_recognition` audio fixture) lives in
[`examples/chromium_example.py`](../examples/chromium_example.py).

### Network-level redirect

For DNS interception + reverse-proxy recipes (replace the vendor host on a LAN without touching client code), see the per-vendor section in [`voice-pihole.md`](voice-pihole.md).
