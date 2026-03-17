# Suggestions — ovos-stt-http-server

## S-001: Add unit tests
No tests exist. Add `test/unittests/` with at least:
- `create_app()` smoke test using a mock STT plugin.
- `/status` endpoint response shape assertion.
- `/stt` endpoint with synthetic PCM bytes.

## S-002: Pin fastapi and uvicorn to broader ranges
`fastapi~=0.95` and `uvicorn~=0.22` are old. Update to `fastapi>=0.95,<1.0` and `uvicorn>=0.22` to allow newer compatible releases.

## S-003: Validate `sample_width` in `/stt`
No validation is performed on `sample_width`. Values other than 1 or 2 will silently produce garbage audio. Add an explicit check and return HTTP 400 on invalid values.

## S-004: Add `python-support.yml` workflow
Add a CI matrix test across Python 3.10, 3.11, 3.12 using `OpenVoiceOS/gh-automations/.github/workflows/build-tests.yml@dev`.

## S-005: Migrate requires-python to >=3.10
The project targets `>=3.9` but the workspace standard is 3.10+. Align after verifying no 3.9-specific usage.
