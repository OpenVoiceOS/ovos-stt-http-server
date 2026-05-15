# API Compatibility Reference

`ovos-stt-http-server` exposes its underlying OVOS STT plugin behind drop-in
compatibility endpoints for popular cloud STT APIs. Each vendor lives
under its own URL prefix so multiple compat layers coexist with no path
collisions.

All routers accept any auth token / API key from the client and silently
ignore it — authentication is the responsibility of your reverse proxy.

Audio format conversion is provided by `ovos_stt_http_server.audio_utils.multipart_audio_to_audiodata()`.
Install the `[audio]` extra (`pip install ovos-stt-http-server[audio]`) to enable
non-WAV inputs via `pydub`.

Vendor sections are added by their respective compat-router PRs.
