# QUICK_FACTS — ovos-stt-http-server

| Field | Value |
| :--- | :--- |
| **Package name** | `ovos-stt-http-server` |
| **Version** | `0.1.5a7` (`ovos_stt_http_server/version.py`) |
| **Entry point** | `ovos-stt-server` → `ovos_stt_http_server.__main__:main` |
| **Key classes** | `ModelContainer` — `ovos_stt_http_server/__init__.py:30` |
| | `MultiModelContainer` — `ovos_stt_http_server/__init__.py:57` |
| **Key functions** | `create_app()` — `ovos_stt_http_server/__init__.py:109` |
| | `start_stt_server()` — `ovos_stt_http_server/__init__.py:184` |
| | `multipart_audio_to_audiodata()` — `ovos_stt_http_server/audio_utils.py:10` |
| **Native endpoints** | `GET /status`, `POST /stt`, `POST /lang_detect` |
| **API prefixes** | `/openai`, `/deepgram`, `/google`, `/assemblyai/v2`, `/speechmatics/v1` |
| **Audio format** | PCM 16 kHz mono int16 (native); WAV/MP3/OGG via compat routers |
| **CORS** | Unconditional `allow_origins=["*"]` |
| **Default port** | `8080` |
| **Python** | >=3.9 |
| **License** | Apache-2.0 |
| **Unit tests** | 25 tests — `test/unittests/test_compat_routers.py` |
