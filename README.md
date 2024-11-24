# OpenVoiceOS STT HTTP Server

Turn any OVOS STT plugin into a micro service!

## Install

`pip install ovos-stt-http-server`

## Companion plugin

Use in your voice assistant with OpenVoiceOS [companion plugin](https://github.com/OpenVoiceOS/ovos-stt-server-plugin)

## Configuration

the plugin is configured just like if it was running in the assistant, under mycroft.conf

eg
```
  "stt": {
    "module": "ovos-stt-plugin-deepgram",
    "ovos-stt-plugin-deepgram": {"key": "xtimes40"}
  }
```


## Usage

```bash
ovos-stt-server --help
usage: ovos-stt-server [-h] [--engine ENGINE] [--port PORT] [--host HOST]

options:
  -h, --help            show this help message and exit
  --engine ENGINE       stt plugin to be used
  --lang-engine LANG_ENGINE
                        audio language detection plugin to be used (optional)
  --port PORT           port number
  --host HOST           host
  --lang LANG           default language supported by plugin (default comes from mycroft.conf)
  --multi               Load a plugin instance per language (force lang support, loads multiple plugins into memory)
  --gradio              Enable Gradio Web UI
  --cache               Cache models for Gradio demo
  --title TITLE         Title for webUI
  --description DESCRIPTION
                        Text description to print in UI
  --info INFO           Text to display at end of UI
  --badge BADGE         URL of visitor badge
```
> Note: `ffmpeg` is required for Gradio

eg `ovos-stt-server --engine ovos-stt-plugin-fasterwhisper --lang-engine ovos-audio-transformer-plugin-fasterwhisper`

## Docker

you can create easily create a docker file to serve any plugin

```dockerfile
FROM python:3.7

RUN pip3 install ovos-stt-http-server==0.0.1

RUN pip3 install {PLUGIN_HERE}

ENTRYPOINT ovos-stt-server --engine {PLUGIN_HERE}
```

build it
```bash
docker build . -t my_ovos_stt_plugin
```

run it
```bash
docker run -p 8080:9666 my_ovos_stt_plugin
```

Each plugin can provide its own Dockerfile in its repository using ovos-stt-http-server
