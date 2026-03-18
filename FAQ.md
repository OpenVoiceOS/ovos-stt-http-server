# FAQ — ovos-stt-http-server

## General

**Q: What is ovos-stt-http-server?**
A: A FastAPI-based HTTP server that wraps any OVOS STT plugin and exposes it via a REST API. It also provides five vendor-compatible compat routers for drop-in use with OpenAI Whisper, Deepgram, Google Cloud STT, AssemblyAI, and Speechmatics clients.

**Q: What is the default port?**
A: The CLI defaults to `8080`. Override with `--port <number>`.

**Q: How do I start the server?**
A: `ovos-stt-server --engine <plugin-name> --port 8080`. The `--engine` flag is required.

**Q: Do I need API keys or credentials?**
A: No. All vendor-compatible routers accept auth headers and API-key query parameters but silently ignore them. No credentials are validated.

**Q: What Python version is required?**
A: Python 3.9 or later (pyproject.toml `requires-python = ">=3.9"`).

**Q: What audio format does `/stt` expect?**
A: Raw PCM bytes: 16 kHz, mono, 16-bit signed integer (int16). Pass `sample_rate` and `sample_width` query params if your audio differs from the defaults.

**Q: How do I configure CORS?**
A: CORS is unconditionally set to `allow_origins=["*"]`. There is no env-var override. All origins are permitted. See `create_app` — `ovos_stt_http_server/__init__.py:109`.

**Q: How do I enable automatic language detection?**
A: Pass `lang=auto` as a query parameter to `/stt`, or use the `/lang_detect` endpoint directly. A `lang_plugin` must be provided at startup (`--lang-engine`).

**Q: What is `--multi` mode?**
A: `--multi` loads one `MultiModelContainer` (`__init__.py:57`) that instantiates a separate plugin instance per language code on first use. Useful for multilingual deployments with language-specific models.

**Q: How do I specify the STT plugin?**
A: Pass `--engine <plugin-name>` to the CLI. The plugin must be installed and discoverable via `ovos-plugin-manager`.

**Q: What plugins are supported?**
A: Any plugin registered under the `opm.plugin.stt` entry point group. Install the plugin package and reference it by its entry point name.

**Q: What does `/status` return?**
A: `{"status": "ok", "plugin": "<engine-name>", "lang_plugin": "<lang-engine-name-or-null>"}` — `stats` handler in `__init__.py:142`.

**Q: Is Gradio UI supported?**
A: No. Gradio support was removed. The server is a pure REST API only.

---

## OpenAI Whisper Compatible Clients

**Q: Which OpenAI Whisper clients work with this server?**
A: Any client that POSTs to `/v1/audio/transcriptions` or `/v1/audio/translations` with multipart form data works. This includes the official `openai` Python SDK, `whisper-client`, and raw `curl` commands.

**Q: How do I use the OpenAI Python SDK against this server?**
A: Set `base_url="http://localhost:8080/openai"` when constructing the `OpenAI` client. The `api_key` parameter is accepted but ignored.

**Q: What `response_format` values are supported?**
A: `json` (default), `text`, `srt`, `vtt`, and `verbose_json`. See [docs/response-formats.md](docs/response-formats.md).

**Q: Does `verbose_json` return real word-level segments?**
A: No. The `segments` field is always an empty list. `task`, `language`, `duration`, and `text` are populated.

**Q: Does the translations endpoint really translate audio?**
A: No — it calls the same STT engine as transcriptions but forces `language=en`. Translation between languages is not performed; the engine transcribes with English as the target hint.

---

## Deepgram Compatible Clients

**Q: Which Deepgram clients work with this server?**
A: Any client that POSTs raw audio bytes to `/v1/listen`. The official `deepgram-sdk` Python package works when its base URL is overridden.

**Q: How is audio parsed for the Deepgram endpoint?**
A: The raw request body is wrapped in `AudioData(body, 16000, 2)` — no format detection. Send WAV or raw PCM at 16 kHz 16-bit mono for best results.

**Q: Does `punctuate=true` add punctuation?**
A: No. The `punctuate` query parameter is accepted and ignored. Punctuation depends on the underlying STT plugin.

**Q: What does the Deepgram `words` array contain?**
A: An empty list. Word-level timing is not implemented.

---

## Google Speech-to-Text Compatible Clients

**Q: Which Google STT clients work?**
A: Any client that POSTs to `/v1/speech:recognize` with a JSON body containing `config` and `audio.content` (base64-encoded audio).

**Q: Are GCS URIs (`gs://...`) supported?**
A: No. The server returns HTTP 501 if `audio.uri` is set. Use `audio.content` with base64-encoded audio.

**Q: Does the `encoding` field matter?**
A: No — the server attempts to parse uploaded bytes as WAV regardless of the `encoding` field value, then falls back to raw PCM.

---

## AssemblyAI Stub Behavior

**Q: Why does the AssemblyAI GET transcript endpoint always return `status: error`?**
A: This server is synchronous. Transcription completes in the POST response. No job store persists between requests, so GET by ID cannot retrieve prior results.

**Q: Do I need to poll for results like the real AssemblyAI API?**
A: No — the POST response already contains `status: completed` and the `text` field. Read the result directly from the POST response.

**Q: What happens if I send `audio_url` instead of `audio`?**
A: The server returns `status: error` with a message explaining that `audio_url` fetching is not supported. Encode your audio as base64 and put it in the `audio` field.

**Q: Is the `id` in the POST response reusable?**
A: No. The ID is a UUID generated per-request. The GET endpoint ignores it and always returns an error stub.

---

## Speechmatics Behavior

**Q: How does the Speechmatics job model work on this server?**
A: Job creation (POST `/v1/jobs`) transcribes immediately and stores the result in an in-memory dict keyed by job ID. GET retrieves from that dict.

**Q: What happens if I GET a job that doesn't exist?**
A: HTTP 404 is returned: `{"detail": "Job '<id>' not found."}`.

**Q: Are job results preserved across server restarts?**
A: No. The `_jobs` dict (`speechmatics.py:13`) is in-memory only.

**Q: What `format` parameter does GET `/transcript` accept?**
A: The `format` query param is accepted and ignored. The response is always Speechmatics JSON v2.9 format.

---

## Audio Format

**Q: What audio formats are supported?**
A: WAV is supported natively via stdlib. MP3, OGG, FLAC, M4A, and WebM require `pydub` (`pip install pydub`). See [docs/audio-formats.md](docs/audio-formats.md).

**Q: What happens if I upload a non-WAV file without pydub installed?**
A: HTTP 501 is returned with a message indicating that the format requires pydub.

**Q: What sample rate and bit depth should I use?**
A: 16 kHz, mono, 16-bit (int16). The server resamples non-WAV files via pydub to match these parameters.

---

## Language

**Q: How do I specify the transcription language?**
A: Each compat router has its own mechanism: `language` form field (Whisper), `?language=` query param (Deepgram), `config.languageCode` JSON field (Google), `language_code` JSON field (AssemblyAI), `transcription_config.language` in the job config JSON (Speechmatics).

**Q: What happens if no language is specified?**
A: Defaults vary per router: Deepgram defaults to `en`, AssemblyAI defaults to `en`, Speechmatics defaults to `en`, Whisper passes `None` → the engine receives `"auto"`.

**Q: Does language auto-detection work with compat routers?**
A: Not directly. Use the native `/lang_detect` endpoint, or start the server with `--lang-engine` to enable automatic language detection in the underlying engine.
