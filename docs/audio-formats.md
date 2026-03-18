# Audio Formats

## Native `/stt` Endpoint

The native endpoint (`POST /stt`) accepts raw PCM bytes in the request body with no container. Parameters are passed as query strings:

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `sample_rate` | `16000` | Sample rate in Hz |
| `sample_width` | `2` | Sample width in bytes (2 = int16) |

## Compat Router Audio Handling

Compat routers that accept file uploads (OpenAI Whisper, Speechmatics) use `multipart_audio_to_audiodata` (`audio_utils.py:10`) to convert uploaded bytes into `AudioData`.

### WAV (stdlib)

When the uploaded filename ends in `.wav`, the file is parsed with Python's stdlib `wave` module. Sample rate and sample width are read from the WAV header. No external dependencies required.

```
multipart_audio_to_audiodata(wav_bytes, "audio.wav")
→ wave.open() → AudioData(raw_pcm, sample_rate, sample_width)
```

### Other Formats (pydub)

All non-WAV extensions (`.mp3`, `.ogg`, `.flac`, `.m4a`, etc.) are processed via `pydub.AudioSegment`. The audio is resampled to 16 kHz mono int16 before passing to the STT engine.

```
multipart_audio_to_audiodata(mp3_bytes, "audio.mp3")
→ AudioSegment.from_file() → resample → wave.open() → AudioData(raw_pcm, 16000, 2)
```

If `pydub` is not installed and a non-WAV file is uploaded, the server returns:

```
HTTP 501 Not Implemented
{"detail": "Format 'mp3' requires pydub. Install with: pip install pydub"}
```

### Deepgram Raw Body

The Deepgram router (`deepgram.py:80-81`) reads the raw request body and wraps it in `AudioData(audio_bytes, 16000, 2)` — no format detection is performed. Send WAV or raw PCM at 16 kHz 16-bit mono.

### Google STT and AssemblyAI Base64

Both routers accept base64-encoded audio in a JSON field (`audio.content` for Google, `audio` for AssemblyAI). After decoding, they attempt to parse as WAV first; if that fails they treat the bytes as raw PCM at the configured sample rate.

## Supported MIME Types (compat routers)

| MIME Type | Extension | Handler |
| :--- | :--- | :--- |
| `audio/wav` / `audio/x-wav` | `.wav` | stdlib `wave` |
| `audio/mpeg` | `.mp3` | pydub |
| `audio/ogg` | `.ogg` | pydub |
| `audio/flac` | `.flac` | pydub |
| `audio/mp4` / `audio/x-m4a` | `.m4a` | pydub |
| `audio/webm` | `.webm` | pydub |

Any extension not matching `.wav` falls through to pydub. If pydub cannot handle the format, it will raise its own error before the 501 is returned.
