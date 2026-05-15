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
| Chromium Web Speech | `/speech-api/v2` | ✅ merged |

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

### Zero-setup redirect: intercept `www.google.com/speech-api`

Chrome and Chromium itself hard-code `http://www.google.com/speech-api/v2/recognize`
(plain HTTP, not HTTPS — the original implementation predates the mass
HTTPS push). To intercept:

**1. DNS interception.**

```text
# /etc/hosts on the client
192.168.1.50    www.google.com
```

> :warning: Mapping `www.google.com` to your box affects **every other
> request to google.com from that client**. Almost always you want to
> scope this with a reverse proxy that 404s or forwards everything but
> `/speech-api/...` to the real Google.

LAN-wide (Pi-hole / Unbound):
```text
local-data: "www.google.com. A 192.168.1.50"
```

**2. SDK paths to rewrite.**

| Upstream URL | Our path |
| :--- | :--- |
| `POST http://www.google.com/speech-api/v2/recognize` | `POST /speech-api/v2/recognize` |

The path is identical — no rewrite needed inside nginx, just `proxy_pass`.

**3. nginx reverse proxy** — terminate plain HTTP on port 80, forward
everything else through:

```nginx
server {
    listen 80;
    server_name www.google.com;

    location /speech-api/ {
        proxy_pass         http://127.0.0.1:8080/speech-api/;
        proxy_set_header   Host $host;
        proxy_set_header   X-Forwarded-For $remote_addr;
        proxy_buffering    off;
    }

    # Everything else proxies to the real Google so other features keep
    # working. Resolve through a public DNS that doesn't hit our hosts file.
    resolver 8.8.8.8 ipv6=off;
    location / {
        proxy_pass         http://www.google.com$request_uri;
        proxy_set_header   Host www.google.com;
    }
}
```

For HTTPS clients (modern Chrome ships with HTTPS-only): add a `listen 443
ssl;` block with a cert signed by a CA the client already trusts. Most
deployments need this because modern Chromium upgrades the request to
HTTPS unless you specifically run Chrome's `--unsafely-treat-insecure-origin-as-secure`.

**4. Trust the CA on each client.** Standard `requests` / `urllib` behaviour;
`REQUESTS_CA_BUNDLE` or system trust store.

**Caveats:**
- The wire-format key (`AIzaSy...`) is scraped from a 2014 Chromium commit
  and has no quota with us — but real Chrome may rotate it; we accept
  any key.
- FLAC decoding requires `pydub` + `ffmpeg` (install via the `[audio]`
  extra). Raw PCM (`audio/x-raw;rate=16000;bits=16`) bypasses pydub.
- The Web Speech API in browsers (`SpeechRecognition` Web API) uses a
  different binary streaming protocol over a bidi HTTP/2 channel; it is
  **not** the same as this REST endpoint. Chrome falls back to this
  endpoint for headless contexts and for older Chromium builds.
