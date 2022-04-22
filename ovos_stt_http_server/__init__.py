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
from flask import Flask, request
from speech_recognition import Recognizer, AudioFile
from tempfile import NamedTemporaryFile
from ovos_plugin_manager.stt import load_stt_plugin


ENGINE = None


def create_app():
    app = Flask(__name__)
    recognizer = Recognizer()

    @app.route("/stt", methods=['POST'])
    def get_stt():
        audio = request.data
        lang = str(request.args.get("lang", "en-us")).lower()
        transcript = None

        with NamedTemporaryFile() as fp:
            fp.write(audio)
            with AudioFile(fp.name) as source:
                audio = recognizer.record(source)

        try:
            transcript = ENGINE.execute(audio, language=lang)
        except Exception as e:
            print(e)
        return transcript or ""

    return app


def start_stt_server(engine, port=9666, host="0.0.0.0"):
    global ENGINE

    engine = load_stt_plugin(engine)
    if not engine:
        raise ValueError(f"Failed to load STT: {engine}")

    ENGINE = engine()

    app = create_app()
    app.run(port=port, use_reloader=False, host=host)
    return app



