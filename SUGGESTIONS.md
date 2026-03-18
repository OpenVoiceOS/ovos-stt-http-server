# Suggestions — ovos-stt-http-server

## S-001: Add unit tests [RESOLVED 2026-03-18]
25 tests added in `test/unittests/test_compat_routers.py` covering all five compat routers.

## S-002: Pin fastapi and uvicorn to broader ranges
`fastapi~=0.95` and `uvicorn~=0.22` are old. Update to `fastapi>=0.95,<1.0` and `uvicorn>=0.22` to allow newer compatible releases.

## S-003: Validate `sample_width` in `/stt`
No validation is performed on `sample_width`. Values other than 1 or 2 will silently produce garbage audio. Add an explicit check and return HTTP 400 on invalid values.

## S-004: Add `python-support.yml` workflow
Add a CI matrix test across Python 3.10, 3.11, 3.12 using `OpenVoiceOS/gh-automations/.github/workflows/build-tests.yml@dev`.

## S-005: Migrate requires-python to >=3.10
The project targets `>=3.9` but the workspace standard is 3.10+. Align after verifying no 3.9-specific usage.

## S-006: Add TTL or size limit to Speechmatics in-memory job store
The `_jobs` dict (`speechmatics.py:13`) grows unboundedly. Add a `maxlen` via `collections.OrderedDict` or an LRU cache, or a TTL-based eviction on the store.

## S-007: Document pydub as an optional dependency in pyproject.toml
`pydub` is imported conditionally in `audio_utils.py:35` but is not listed as a dependency. Add it as an optional extra in `pyproject.toml`: `[project.optional-dependencies] audio = ["pydub"]`.

## S-008: Parse WAV headers in Deepgram router
The Deepgram router blindly treats the body as 16 kHz 16-bit mono. Attempt `wave.open()` first and fall back to the hardcoded parameters only if parsing fails — similar to the pattern in `google_stt.py:90-97`.
