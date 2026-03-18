# Response Formats

## OpenAI Whisper `response_format` Values

The `response_format` form field on `POST /openai/v1/audio/transcriptions` and `POST /openai/v1/audio/translations` controls the shape and content type of the response.

Source: `ovos_stt_http_server/routers/openai_whisper.py:68-86`

| Value | Content-Type | Shape |
| :--- | :--- | :--- |
| `json` (default) | `application/json` | `{"text": "<transcript>"}` |
| `text` | `text/plain` | Raw transcript string, no JSON wrapper |
| `srt` | `text/plain` | SRT subtitle block (index, timecode range, text, blank line) |
| `vtt` | `text/plain` | WebVTT file (`WEBVTT` header + cue block) |
| `verbose_json` | `application/json` | Extended object with `task`, `language`, `duration`, `text`, `segments` |

### json

```json
{"text": "hello world"}
```

### text

```
hello world
```

### srt

```
1
00:00:00,000 --> 00:00:00,000
hello world

```

The end timecode uses `int(duration)` seconds — sub-second durations appear as `00:00:00,000`.

### vtt

```
WEBVTT

00:00:00.000 --> 00:00:00.000
hello world

```

### verbose_json

```json
{
  "task": "transcribe",
  "language": "en",
  "duration": 0.012,
  "text": "hello world",
  "segments": []
}
```

`segments` is always an empty list in this implementation. `task` is `"transcribe"` for the transcriptions endpoint and `"translate"` for the translations endpoint. `duration` is the wall-clock seconds taken by `model.process_audio()`.

## Deepgram Response

Always `application/json`. Shape mirrors the Deepgram v1 API:

```json
{
  "metadata": {"request_id": "<uuid>", "created": "<ISO8601>", "duration": 0.01, "channels": 1, "models": ["ovos"]},
  "results": {
    "channels": [{
      "alternatives": [{"transcript": "hello world", "confidence": 1.0, "words": []}]
    }]
  }
}
```

## Google Cloud STT Response

```json
{
  "results": [{"alternatives": [{"transcript": "hello world", "confidence": 0.9}]}]
}
```

## AssemblyAI Response

POST returns `status: completed` on success, `status: error` when `audio_url` is supplied (not supported) or decoding fails. GET always returns `status: error`.

```json
{"id": "<uuid>", "status": "completed", "text": "hello world", "language_code": "en", "confidence": 0.9, "words": []}
```

## Speechmatics Job Response

POST `/v1/jobs` returns:

```json
{"id": "<uuid>", "status": "done"}
```

GET `/v1/jobs/{id}/transcript` returns:

```json
{
  "format": "2.9",
  "job": {"id": "<uuid>", "status": "done"},
  "results": [{"type": "word", "start_time": 0.0, "end_time": 1.0, "alternatives": [{"content": "hello world", "confidence": 0.9}]}],
  "metadata": {}
}
```
