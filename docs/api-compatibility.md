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
| OpenAI Whisper | `/openai` | ✅ merged |
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

Groq, Cloudflare Workers AI, Fireworks AI, Together AI, and OpenRouter
all speak the OpenAI `/v1/audio/transcriptions` contract — point them at
our `/openai/v1` prefix. Per-host nginx blocks live in
[`voice-pihole.md`](voice-pihole.md) under the OpenAI section.

---

## OpenAI Whisper (`/openai/v1`)

**Upstream sources**:
- Python SDK: [openai/openai-python — `resources/audio/transcriptions.py`](https://github.com/openai/openai-python/blob/main/src/openai/resources/audio/transcriptions.py)
- API reference: [OpenAI Audio Transcriptions](https://platform.openai.com/docs/api-reference/audio/createTranscription)
- Node SDK: [openai/openai-node](https://github.com/openai/openai-node)

### Endpoints

| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/openai/v1/audio/transcriptions` | STT in source language |
| `POST` | `/openai/v1/audio/translations` | STT in source language → translated to English |

`/audio/translations` pipes STT output through an OVOS translation plugin
selected at launch via `--translate-plugin`. Defaults to
[`ovos-translate-plugin-server`](https://github.com/OpenVoiceOS/ovos-translate-server-plugin)
(public OVOS translate server). Returns `503` if no plugin is loaded, `502` if
the translator raises.

```bash
# default — public OVOS server
ovos-stt-server --engine ovos-stt-plugin-whisper

# Google Translate
ovos-stt-server --engine ovos-stt-plugin-whisper \
                --translate-plugin ovos-translate-plugin-google

# disable /translations entirely
ovos-stt-server --engine ovos-stt-plugin-whisper --translate-plugin ""
```

### Pointing apps at this server

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8080/openai/v1", api_key="ignored")

with open("clip.wav", "rb") as fp:
    r = client.audio.transcriptions.create(model="whisper-1", file=fp)
print(r.text)

with open("clip-fr.wav", "rb") as fp:
    r = client.audio.translations.create(model="whisper-1", file=fp)
print(r.text)
```

### Zero-setup redirect: intercept `api.openai.com`

Goal: any unmodified app pointing at the real OpenAI host transparently
hits this server. Two layers — first DNS, then a TLS reverse proxy that
rewrites `/v1/audio/*` to `/openai/v1/audio/*`.

**1. DNS interception.**

Single host:
```text
# /etc/hosts on the client
192.168.1.50    api.openai.com
```

Whole LAN — Pi-hole / Unbound / dnsmasq:
```text
local-data: "api.openai.com. A 192.168.1.50"
```

**2. SDK paths to rewrite.**

The OpenAI Python/Node/Go SDKs build URLs against `https://api.openai.com/v1`:

| Upstream URL | Our path |
| :--- | :--- |
| `https://api.openai.com/v1/audio/transcriptions` | `/openai/v1/audio/transcriptions` |
| `https://api.openai.com/v1/audio/translations`   | `/openai/v1/audio/translations` |

**3. nginx reverse proxy** on the ovos-stt-http-server machine (port 443):

```nginx
server {
    listen 443 ssl;
    server_name api.openai.com;

    # TLS cert must be signed by a CA the clients trust. The OpenAI SDKs
    # honour the system trust store and `REQUESTS_CA_BUNDLE` / `SSL_CERT_FILE`.
    ssl_certificate     /etc/ssl/private/api.openai.com.crt;
    ssl_certificate_key /etc/ssl/private/api.openai.com.key;

    # Rewrite /v1/audio/* → /openai/v1/audio/* and pass through.
    location /v1/audio/ {
        proxy_pass         http://127.0.0.1:8080/openai/v1/audio/;
        proxy_set_header   Host $host;
        proxy_set_header   X-Forwarded-For $remote_addr;
        proxy_buffering    off;
    }

    # Optional: return a benign stub for billing / model-list calls SDKs make
    # at startup so they don't blow up.
    location /v1/models { return 200 '{"data":[]}'; add_header Content-Type application/json; }

    location / { return 404; }
}
```

**4. Trust the CA on each client.** The SDK uses `httpx`/`requests`, which
read the system trust store. Either sign the cert with a CA already trusted
by the client (corporate PKI, mkcert root, etc.) or set
`SSL_CERT_FILE=/path/to/ca.crt` / `REQUESTS_CA_BUNDLE=...` in the client's
environment.

**Caveats:**
- `api.openai.com` is shared with chat/completions/embeddings. The 404
  fallback above means non-audio SDK calls fail loudly; deploy a separate
  upstream for those if your apps mix workloads.
- OpenAI may add certificate pinning in future SDK releases; check the
  current SDK source before relying on this in production.
