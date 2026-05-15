# Audio Formats

The native `/stt` endpoint accepts raw PCM bytes (16 kHz, mono, 16-bit signed).

Compat routers accept uploaded audio files in a variety of formats via the
shared helper `ovos_stt_http_server.audio_utils.multipart_audio_to_audiodata`:

- **WAV** is decoded with the stdlib `wave` module.
- Any other format (mp3, flac, ogg, m4a, webm, …) is decoded via `pydub`,
  which requires `ffmpeg` to be available on the host.

`pydub` is an optional dependency — install via the `[audio]` extra:

```bash
pip install ovos-stt-http-server[audio]
```

If a non-WAV upload arrives and `pydub` is not installed, the server replies
with `501 Not Implemented`.
