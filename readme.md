# OpenVoiceOS STT HTTP Server

**THIS IS A WORK IN PROGRESS AND NOT YET FUNCTIONAL**

Turn any OVOS STT plugin into a micro service!

Use with OpenVoiceOS [companion plugin](https://github.com/OpenVoiceOS/ovos-stt-http-server-plugin)

## Install

`pip install ovos-stt-http-server`

## Usage

```bash
ovos-stt-server --help
usage: ovos-stt-server [-h] [--engine ENGINE] [--port PORT] [--host HOST]

options:
  -h, --help       show this help message and exit
  --engine ENGINE  stt plugin to be used
  --port PORT      port number
  --host HOST      host
```

## Companion plugin

coming soon - companion plugin to point to a ovos-stt-http-server instance

## Docker

you can create easily create a docker file to serve any plugin

```dockerfile
FROM python:3.7

RUN pip3 install ovos-utils==0.0.15
RUN pip3 install ovos-plugin-manager==0.0.4
RUN pip3 install ovos-stt-http-server==0.0.1

RUN pip3 install {PLUGIN_HERE}

ENTRYPOINT ovos-stt-http-server --engine {PLUGIN_HERE}
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