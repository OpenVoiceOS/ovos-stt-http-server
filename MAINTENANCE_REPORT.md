# Maintenance Report — ovos-stt-http-server

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
