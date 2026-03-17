# FAQ — ovos-stt-http-server

**Q: What audio format does `/stt` expect?**
Raw PCM bytes: 16 kHz, mono, 16-bit signed integer (int16). Pass `sample_rate` and `sample_width` query params if your audio differs from the defaults.

**Q: How do I configure CORS?**
CORS is unconditionally set to `allow_origins=["*"]`. There is no env-var override. All origins are permitted. See `create_app` — `ovos_stt_http_server/__init__.py:109`.

**Q: How do I enable automatic language detection?**
Pass `lang=auto` as a query parameter to `/stt`, or use the `/lang_detect` endpoint directly. A `lang_plugin` must be provided at startup (`--lang-engine`).

**Q: What is `--multi` mode?**
`--multi` loads one `MultiModelContainer` (`__init__.py:57`) that instantiates a separate plugin instance per language code on first use. Useful for multilingual deployments with language-specific models.

**Q: How do I specify the STT plugin?**
Pass `--engine <plugin-name>` to the CLI. The plugin must be installed and discoverable via `ovos-plugin-manager`.

**Q: What plugins are supported?**
Any plugin registered under the `opm.plugin.stt` entry point group. Install the plugin package and reference it by its entry point name.

**Q: What does `/status` return?**
`{"status": "ok", "plugin": "<engine-name>", "lang_plugin": "<lang-engine-name-or-null>"}` — `stats` handler in `__init__.py:142`.

**Q: Is Gradio UI supported?**
No. Gradio support was removed. The server is a pure REST API only.
