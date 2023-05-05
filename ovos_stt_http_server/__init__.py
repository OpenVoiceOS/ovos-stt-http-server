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
from tempfile import NamedTemporaryFile

from fastapi import FastAPI
from ovos_plugin_manager.stt import load_stt_plugin
from ovos_utils.log import LOG
from speech_recognition import Recognizer, AudioFile, AudioData
from starlette.requests import Request


class ModelContainer:
    def __init__(self, plugin: str, config: dict=None):
        self.plugin = load_stt_plugin(plugin)
        if not self.plugin:
            raise ValueError(f"Failed to load STT: {plugin}")
        self.engines = {}
        self.data = {}
        self.config = config or {}

    def get_engine(self, session_id):
        if session_id not in self.engines:
            self.load_engine(session_id)
        return self.engines[session_id]

    def load_engine(self, session_id, config=None):
        config = config or self.config
        self.engines[session_id] = self.plugin(config=config)

    def unload_engine(self, session_id):
        if session_id in self.engines:
            self.engines.pop(session_id)
        if session_id in self.data:
            self.data.pop(session_id)

    def process_audio(self, audio: AudioData, lang, session_id=None):
        session_id = session_id or lang  # shared model for non-streaming stt
        engine = self.get_engine(session_id)
        if audio or engine.can_stream:
            return engine.execute(audio, language=lang) or ""
        return ""

    def stream_start(self, session_id):
        engine = self.get_engine(session_id)
        if engine.can_stream:
            engine.stream_start()

    def stream_data(self, audio, session_id):
        engine = self.get_engine(session_id)
        if engine.can_stream:
            # streaming plugin in server + streaming plugin in core
            return engine.stream_data(audio)
        else:
            # non streaming plugin in server + streaming plugin in core
            if session_id not in self.data:
                self.data[session_id] = b""
            self.data[session_id] += audio
        return ""

    def stream_stop(self, session_id):
        engine = self.get_engine(session_id)
        if engine.can_stream:
            transcript = engine.stream_stop()
        else:
            audio = AudioData(self.data[session_id],
                              sample_rate=16000, sample_width=2)
            transcript = engine.execute(audio)
        self.unload_engine(session_id)
        return transcript or ""


def bytes2audiodata(data):
    recognizer = Recognizer()
    with NamedTemporaryFile() as fp:
        fp.write(data)
        with AudioFile(fp.name) as source:
            audio = recognizer.record(source)
    return audio


def create_app(stt_plugin):
    app = FastAPI()
    model = ModelContainer(stt_plugin)

    @app.post("/stt")
    async def get_stt(request: Request):
        LOG.debug(f"Handling STT Request: {request}")
        lang = str(request.query_params.get("lang", "en-us")).lower()
        audio_bytes = await request.body()
        LOG.debug(len(audio_bytes))
        audio = bytes2audiodata(audio_bytes)
        return model.process_audio(audio, lang)

    @app.post("/stream/start")
    def stream_start(request: Request):
        lang = str(request.query_params.get("lang", "en-us")).lower()
        uuid = str(request.query_params.get("uuid") or lang)
        model.load_engine(uuid, {"lang": lang})
        model.stream_start(uuid)
        return {"status": "ok", "uuid": uuid, "lang": lang}

    @app.post("/stream/audio")
    async def stream(request: Request):
        audio = await request.body()
        lang = str(request.query_params.get("lang", "en-us")).lower()
        uuid = str(request.query_params.get("uuid") or lang)
        transcript = model.stream_data(audio, uuid)
        return {"status": "ok", "uuid": uuid,
                "lang": lang, "transcript": transcript}

    @app.post("/stream/end")
    def stream_end(request: Request):
        lang = str(request.query_params.get("lang", "en-us")).lower()
        uuid = str(request.query_params.get("uuid") or lang)
        # model.wait_until_done(uuid)
        transcript = model.stream_stop(uuid)
        LOG.info(transcript)
        return {"status": "ok", "uuid": uuid,
                "lang": lang, "transcript": transcript}

    return app, model


def start_stt_server(engine: str) -> (FastAPI, ModelContainer):
    app, engine = create_app(engine)
    return app, engine
