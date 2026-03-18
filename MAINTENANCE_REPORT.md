# Maintenance Report — ovos-stt-http-server

## 2026-03-18

**AI Model**: claude-sonnet-4-6
**Oversight**: Human-directed, agent-executed

### Actions Taken

- **Created `docs/api-compatibility.md`**: Full table of all 5 compat routers with vendor prefix, endpoints, auth method, input formats, response formats, and curl examples per endpoint.
- **Created `docs/audio-formats.md`**: Documents `multipart_audio_to_audiodata()` WAV/pydub paths, 501 fallback, Deepgram raw-body handling, Google/AssemblyAI base64 handling, and supported MIME types.
- **Created `docs/response-formats.md`**: Documents all Whisper `response_format` values (`json`, `text`, `srt`, `vtt`, `verbose_json`) with example outputs, plus Deepgram/Google/AssemblyAI/Speechmatics response shapes.
- **Updated `docs/index.md`**: Added table of contents linking to all three new docs files, added compat router section to architecture, updated audio format note.
- **Rewrote `FAQ.md`**: Expanded from 8 to 30+ Q&A entries covering OpenAI Whisper, Deepgram, Google STT, AssemblyAI, Speechmatics, audio formats, language parameters, port/startup, and all general questions.
- **Updated `QUICK_FACTS.md`**: Added `multipart_audio_to_audiodata()`, all 5 API prefixes, default port, and test count.
- **Updated `AUDIT.md`**: Marked `[MAJOR]` test issue as resolved (25 tests added). Added new issues for compat router edge cases.
- **Updated `SUGGESTIONS.md`**: Marked S-001 resolved. Added S-006 (Speechmatics in-memory store), S-007 (pydub optional dep documentation).
- **Extended `test/unittests/test_compat_routers.py`**: Added 8 new tests — `response_format=text` plain text, `verbose_json` with `segments` field, translations endpoint forces `lang=en`, Deepgram with `?punctuate=true`, Google STT with base64 WAV, AssemblyAI GET transcript `status` field, Speechmatics GET unknown job_id returns 404, Speechmatics GET known job_id returns transcript.

## 2026-03-17

**AI Model**: claude-sonnet-4-6
**Oversight**: Human-directed, agent-executed

### Actions Taken

- **Removed Gradio**: Deleted `ovos_stt_http_server/gradio_app.py`. Removed `has_gradio` parameter from `create_app()` and `start_stt_server()`. Removed `"gradio"` key from `/status` response. Removed `--gradio`, `--cache`, `--title`, `--description`, `--info`, `--badge` CLI args from `__main__.py`.
- **Fixed CORSMiddleware**: Removed `CORS_ORIGINS` env-var logic; `allow_origins` is now unconditionally `["*"]` — `ovos_stt_http_server/__init__.py:130`.
- **Cleaned imports**: Removed unused `import os` from `__init__.py`.
- **Updated `pyproject.toml`**: Removed `gradio~=3.28` and `flask` from dependencies.
- **Added workflows**: `lint.yml`, `build_tests.yml`, `pip_audit.yml` using `OpenVoiceOS/gh-automations@dev`.
- **Updated `unit_tests.yml`**: Replaced obsolete `neongeckocom/.github` reference with `OpenVoiceOS/gh-automations/.github/workflows/build-tests.yml@dev`.
- **Created documentation**: `docs/index.md`, `QUICK_FACTS.md`, `FAQ.md`, `AUDIT.md` (updated), `SUGGESTIONS.md`, `MAINTENANCE_REPORT.md`.
