# ovos-stt-http-server

A lightweight FastAPI server that exposes any OVOS STT plugin as an HTTP service.

## Architecture

- **Framework**: FastAPI with Uvicorn ASGI server.
- **Plugin loading**: `ovos-plugin-manager` discovers and loads STT plugins by name — `ModelContainer` (`__init__.py:30`) for single-language mode, `MultiModelContainer` (`__init__.py:57`) for per-language model loading.
- **CORS**: Unconditional `allow_origins=["*"]` — `create_app` (`__init__.py:109`).

## Endpoints

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/status` | Returns `{"status": "ok", "plugin": ..., "lang_plugin": ...}` |
| `POST` | `/stt` | Raw audio bytes in body → transcribed text (plain text response) |
| `POST` | `/lang_detect` | Raw audio bytes in body → `{"lang": ..., "conf": ...}` |

### `/stt` query parameters

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `lang` | system lang or `auto` | Language code or `auto` to trigger language detection |
| `sample_rate` | `16000` | Audio sample rate in Hz |
| `sample_width` | `2` | Sample width in bytes (2 = int16) |

## Usage

```bash
ovos-stt-server --engine ovos-stt-plugin-whisper --port 8080
ovos-stt-server --engine ovos-stt-plugin-whisper --lang-engine ovos-audio-transformer-plugin-fasterwhisper --multi
```

## Audio Format

Input audio must be raw PCM: 16 kHz, mono, 16-bit signed integer (int16). Send bytes directly as the POST body.
