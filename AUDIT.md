# ovos-stt-http-server — Audit Report

## Documentation Status
- [x] QUICK_FACTS.md
- [x] FAQ.md
- [x] MAINTENANCE_REPORT.md
- [x] AUDIT.md
- [x] SUGGESTIONS.md
- [x] docs/index.md

## Technical Debt & Issues

- `[MAJOR]` **tests**: No unit tests — `test/` directory does not exist (`__init__.py` has no corresponding test coverage).
- `[MINOR]` **pyproject.toml**: `requires-python = ">=3.9"` — workspace standard is 3.10+; align after verifying compatibility — `pyproject.toml:12`.
- `[MINOR]` **deps**: `fastapi~=0.95` and `uvicorn~=0.22` are old pinned versions; should be broadened — `pyproject.toml:21-22`.
- `[MINOR]` **validation**: `/stt` does not validate `sample_width` values — `__init__.py:165`.
- `[INFO]` **ci**: `publish_stable.yml` and `release_workflow.yml` already use `@dev` refs — no action needed.

## Resolved Issues (2026-03-17)
- Gradio dependency and `gradio_app.py` removed.
- `CORS_ORIGINS` env-var removed; `allow_origins=["*"]` unconditional.
- `unit_tests.yml` updated from obsolete `neongeckocom` reference to `OpenVoiceOS/gh-automations@dev`.
- `lint.yml`, `build_tests.yml`, `pip_audit.yml` workflows added.
