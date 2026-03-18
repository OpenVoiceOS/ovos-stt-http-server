# API Compatibility Routers

All five compat routers are mounted in `create_app` (`__init__.py:180-190`) and share the same underlying `ModelContainer` or `MultiModelContainer`. Authentication headers and API-key query parameters are accepted and silently ignored — no credentials are required or validated.

## Router Summary

| Vendor | Prefix | Endpoints | Auth Method | Input Format | Response Format |
| :--- | :--- | :--- | :--- | :--- | :--- |
| OpenAI Whisper | `/openai` | `POST /v1/audio/transcriptions`, `POST /v1/audio/translations` | `Authorization: Bearer <token>` (ignored) | multipart/form-data (WAV, MP3, etc.) | json, text, srt, vtt, verbose_json |
| Deepgram | `/deepgram` | `POST /v1/listen` | `Authorization: Token <token>` (ignored) | Raw audio bytes (body), `Content-Type` header | Deepgram JSON |
| Google Cloud STT | `/google` | `POST /v1/speech:recognize` | `?key=<api_key>` or `Authorization` (ignored) | JSON with base64 `audio.content` | Google STT JSON |
| AssemblyAI | `/assemblyai` | `POST /v2/transcript`, `GET /v2/transcript/{id}` | `Authorization: <token>` (ignored) | JSON with base64 `audio` field | AssemblyAI JSON |
| Speechmatics | `/speechmatics` | `POST /v1/jobs`, `GET /v1/jobs/{id}/transcript` | `Authorization: Bearer <token>` (ignored) | multipart/form-data (`data_file` + `config` JSON string) | Speechmatics JSON |

---

## OpenAI Whisper (`/openai`)

Source: `ovos_stt_http_server/routers/openai_whisper.py`

### POST /openai/v1/audio/transcriptions

Transcribe audio. Mirrors the OpenAI Whisper API.

**Form fields:**

| Field | Required | Description |
| :--- | :--- | :--- |
| `file` | yes | Audio file (WAV, MP3, etc.) |
| `model` | no | Model name — accepted, ignored |
| `language` | no | BCP-47 language code hint |
| `response_format` | no | `json` (default), `text`, `srt`, `vtt`, `verbose_json` |
| `temperature` | no | 0–1 — accepted, ignored |

```bash
curl -X POST http://localhost:8080/openai/v1/audio/transcriptions \
  -H "Authorization: Bearer sk-fake" \
  -F "file=@audio.wav" \
  -F "model=whisper-1" \
  -F "response_format=json"
```

### POST /openai/v1/audio/translations

Identical to transcriptions but forces `language=en`. Always returns English output.

```bash
curl -X POST http://localhost:8080/openai/v1/audio/translations \
  -F "file=@audio.wav" \
  -F "model=whisper-1"
```

---

## Deepgram (`/deepgram`)

Source: `ovos_stt_http_server/routers/deepgram.py`

### POST /deepgram/v1/listen

Audio bytes sent directly in the request body. Language and options are query parameters.

**Query parameters:**

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `language` | `en` | BCP-47 language code |
| `model` | — | Model name — accepted, ignored |
| `punctuate` | — | Boolean — accepted, ignored |
| `diarize` | — | Boolean — accepted, ignored |

Audio is treated as raw 16 kHz 16-bit mono PCM regardless of `Content-Type`.

```bash
curl -X POST "http://localhost:8080/deepgram/v1/listen?language=en-US&punctuate=true" \
  -H "Authorization: Token fake-token" \
  -H "Content-Type: audio/wav" \
  --data-binary @audio.wav
```

---

## Google Cloud STT (`/google`)

Source: `ovos_stt_http_server/routers/google_stt.py`

### POST /google/v1/speech:recognize

JSON body with `config` and `audio` objects. Only base64 `content` is supported; GCS URIs return 501.

```bash
AUDIO_B64=$(base64 -w0 audio.wav)
curl -X POST http://localhost:8080/google/v1/speech:recognize \
  -H "Content-Type: application/json" \
  -d "{
    \"config\": {\"encoding\": \"LINEAR16\", \"sampleRateHertz\": 16000, \"languageCode\": \"en-US\"},
    \"audio\": {\"content\": \"$AUDIO_B64\"}
  }"
```

---

## AssemblyAI (`/assemblyai`)

Source: `ovos_stt_http_server/routers/assemblyai.py`

This is a **synchronous stub**. Unlike the real AssemblyAI API there is no async job queue — transcription completes immediately in the POST response. The GET endpoint always returns `status: error` because no job store is maintained across requests.

### POST /assemblyai/v2/transcript

```bash
AUDIO_B64=$(base64 -w0 audio.wav)
curl -X POST http://localhost:8080/assemblyai/v2/transcript \
  -H "Authorization: fake-api-key" \
  -H "Content-Type: application/json" \
  -d "{\"audio\": \"$AUDIO_B64\", \"language_code\": \"en\"}"
```

### GET /assemblyai/v2/transcript/{id}

Always returns `{"status": "error", ...}`. Use the POST response directly.

```bash
curl http://localhost:8080/assemblyai/v2/transcript/some-id
```

---

## Speechmatics (`/speechmatics`)

Source: `ovos_stt_http_server/routers/speechmatics.py`

This is a **synchronous stub**. Transcription happens immediately on POST. Results are stored in an in-memory dict (`_jobs`) and retrievable via GET until the server restarts.

### POST /speechmatics/v1/jobs

```bash
curl -X POST http://localhost:8080/speechmatics/v1/jobs \
  -H "Authorization: Bearer fake-token" \
  -F "data_file=@audio.wav" \
  -F 'config={"type":"transcription","transcription_config":{"language":"en"}}'
```

### GET /speechmatics/v1/jobs/{job_id}/transcript

Returns 404 if the job ID is unknown (e.g. after server restart). Returns 200 with `results` array when found.

```bash
curl http://localhost:8080/speechmatics/v1/jobs/<job_id>/transcript
```
