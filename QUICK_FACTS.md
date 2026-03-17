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
| **Endpoints** | `GET /status`, `POST /stt`, `POST /lang_detect` |
| **Audio format** | PCM 16 kHz mono int16 |
| **CORS** | Unconditional `allow_origins=["*"]` |
| **Python** | >=3.9 |
| **License** | Apache-2.0 |
