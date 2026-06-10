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
```

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

## MCP (Model Context Protocol)

Install the optional extra to expose the server as an MCP tool provider:

```bash
pip install "ovos-stt-http-server[mcp]"
```

When `mcp` is installed, the server automatically mounts an MCP endpoint at `/mcp`
using the streamable-HTTP transport (compatible with both the legacy SSE path `/mcp/sse`
and the newer `POST /mcp` format).

### Connecting an MCP client

#### Claude Desktop / claude-code (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "ovos-stt": {
      "transport": "http",
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

#### ovos-tool-adapters persona JSON

```json
{
  "toolboxes": ["ovos-mcp-toolbox"],
  "ovos-mcp-toolbox": {
    "transport": "http",
    "url": "http://localhost:8080/mcp",
    "timeout": 30
  }
}
```

### Available MCP tool

| Tool | Description |
|---|---|
| `transcribe` | Transcribe PCM audio to text. Accepts `audio_b64` (base64 PCM) or `audio_path` (server-side file path), plus `lang`, `sample_rate`, `sample_width`. |

Example call (Python MCP client):

```python
import asyncio, base64
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession

async def main():
    async with streamablehttp_client("http://localhost:8080/mcp") as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            audio_b64 = base64.b64encode(open("speech.pcm", "rb").read()).decode()
            result = await session.call_tool("transcribe", {
                "audio_b64": audio_b64,
                "lang": "en-us",
            })
            print(result.content[0].text)

asyncio.run(main())
```

---

## UTCP (Universal Tool Calling Protocol)

No extra dependencies are required. Every running server exposes a UTCP manual at:

```
GET /utcp
```

The response is a UTCP-1.0 JSON document describing all endpoints so that any
UTCP client can discover and invoke them without separate documentation.

### Registering as a UTCP provider

Point a UTCP client's provider config at `/utcp`:

```json
{
  "toolboxes": ["ovos-utcp-toolbox"],
  "ovos-utcp-toolbox": {
    "utcp_config": {
      "tool_providers": [
        {
          "name": "ovos-stt",
          "provider_type": "http",
          "url": "http://localhost:8080/utcp"
        }
      ]
    }
  }
}
```

### Manual format (excerpt)

```json
{
  "utcp_version": "1.0.0",
  "manual_version": "1.0.0",
  "tools": [
    {
      "name": "stt",
      "description": "Transcribe raw PCM audio to text …",
      "inputs": {
        "type": "object",
        "properties": {
          "body":         { "type": "string", "format": "binary" },
          "lang":         { "type": "string", "default": "auto" },
          "sample_rate":  { "type": "integer", "default": 16000 },
          "sample_width": { "type": "integer", "default": 2 }
        },
        "required": ["body"]
      },
      "tool_call_template": {
        "protocol": "http",
        "method": "POST",
        "url": "http://localhost:8080/stt",
        "query_params": { "lang": "{{lang}}", "sample_rate": "{{sample_rate}}", "sample_width": "{{sample_width}}" },
        "headers": { "Content-Type": "application/octet-stream" },
        "body": "{{body}}",
        "auth": { "type": "none" }
      }
    }
  ]
}
```

Three tools are listed: `stt`, `lang_detect`, and `status`.
The `url` fields use the server's actual base URL so the manual is correct
when deployed behind a proxy.
