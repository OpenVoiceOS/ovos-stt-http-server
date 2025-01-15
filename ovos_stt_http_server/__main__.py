# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import argparse

import uvicorn
from ovos_config import Configuration
from ovos_utils.log import LOG

from ovos_stt_http_server import start_stt_server
from ovos_stt_http_server.gradio_app import bind_gradio_service


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", help="stt plugin to be used", required=True)
    parser.add_argument("--lang-engine", help="audio language detection plugin to be used")
    parser.add_argument("--port", help="port number", default=8080)
    parser.add_argument("--host", help="host", default="0.0.0.0")
    parser.add_argument("--lang", help="default language supported by plugin",
                        default=Configuration().get("lang", "en-us"))
    parser.add_argument("--multi", help="Load a plugin instance per language (force lang support)",
                        action="store_true")
    parser.add_argument("--gradio", help="Enable Gradio Web UI",
                        action="store_true")
    parser.add_argument("--cache", help="Cache models for Gradio demo",
                        action="store_true")
    parser.add_argument("--title", help="Title for webUI",
                        default="STT")
    parser.add_argument("--description", help="Text description to print in UI",
                        default="Get Speech-To-Text")
    parser.add_argument("--info", help="Text to display at end of UI",
                        default=None)
    parser.add_argument("--badge", help="URL of visitor badge", default=None)
    args = parser.parse_args()

    server, engine = start_stt_server(args.engine, lang_engine=args.lang_engine,
                                      multi=bool(args.multi),
                                      has_gradio=bool(args.gradio))
    LOG.info("Server Started")
    if args.gradio:
        bind_gradio_service(server, engine, args.title, args.description,
                            args.info, args.badge, args.lang, args.cache)
        LOG.info("Gradio Started")
    uvicorn.run(server, host=args.host, port=int(args.port))


if __name__ == '__main__':
    main()
