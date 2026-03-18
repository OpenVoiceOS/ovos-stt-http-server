# ovos-stt-http-server — Audit Report

## Documentation Status
- [x] QUICK_FACTS.md
- [x] FAQ.md
- [x] MAINTENANCE_REPORT.md
- [x] AUDIT.md
- [x] SUGGESTIONS.md
- [x] docs/index.md
- [x] docs/api-compatibility.md
- [x] docs/audio-formats.md
- [x] docs/response-formats.md

## Technical Debt & Issues

- `[MINOR]` **pyproject.toml**: `requires-python = ">=3.9"` — workspace standard is 3.10+; align after verifying compatibility — `pyproject.toml:12`.
- `[MINOR]` **deps**: `fastapi~=0.95` and `uvicorn~=0.22` are old pinned versions; should be broadened — `pyproject.toml:21-22`.
- `[MINOR]` **validation**: `/stt` does not validate `sample_width` values — `__init__.py:165`.
- `[MINOR]` **Speechmatics in-memory store**: `_jobs` dict in `speechmatics.py:13` is module-level and not thread-safe under concurrent requests; grows unboundedly — `routers/speechmatics.py:13`.
- `[MINOR]` **Deepgram audio assumption**: Deepgram router assumes 16 kHz 16-bit mono regardless of `Content-Type` — `routers/deepgram.py:81`. WAV files with different parameters will produce incorrect results.
- `[INFO]` **ci**: `publish_stable.yml` and `release_workflow.yml` already use `@dev` refs — no action needed.

## Resolved Issues

- `[RESOLVED 2026-03-18]` **tests**: 25 unit tests added in `test/unittests/test_compat_routers.py`.
- `[RESOLVED 2026-03-17]` Gradio dependency and `gradio_app.py` removed.
- `[RESOLVED 2026-03-17]` `CORS_ORIGINS` env-var removed; `allow_origins=["*"]` unconditional.
- `[RESOLVED 2026-03-17]` `unit_tests.yml` updated from obsolete `neongeckocom` reference to `OpenVoiceOS/gh-automations@dev`.
- `[RESOLVED 2026-03-17]` `lint.yml`, `build_tests.yml`, `pip_audit.yml` workflows added.
