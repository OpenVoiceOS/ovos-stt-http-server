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

from typing import List, Tuple, Optional, Set, Union
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from ovos_config import Configuration
from ovos_plugin_manager.audio_transformers import load_audio_transformer_plugin, AudioLanguageDetector
from ovos_plugin_manager.stt import load_stt_plugin
from ovos_utils.log import LOG
from speech_recognition import AudioData, Recognizer, AudioFile
from starlette.requests import Request

LOG.set_level("ERROR")  # avoid server side logs


class ModelContainer:
    def __init__(self, plugin: str, lang_plugin: str = None, config: dict = None):
        plugin = load_stt_plugin(plugin)
        self.lang_plugin = None
        if not plugin:
            raise ValueError(f"Failed to load STT: {plugin}")
        if lang_plugin:
            lang_plugin = load_audio_transformer_plugin(lang_plugin)
            if not lang_plugin:
                raise ValueError(f"Failed to load lang detection plugin: {lang_plugin}")
            assert issubclass(lang_plugin, AudioLanguageDetector)
            LOG.info(f"Loading Audio Language detector plugin: {lang_plugin}")
            self.lang_plugin = lang_plugin()
        LOG.info(f"Loading STT plugin: {plugin}")
        self.engine = plugin(config)
        if self.lang_plugin:
            self.engine.bind(self.lang_plugin)

    def detect_language(self, audio, valid_langs: Optional[Union[Set[str], List[str]]] = None) -> Tuple[str, float]:
        if self.lang_plugin is None:
            return self.engine.detect_language(audio, valid_langs)
        return self.lang_plugin.detect(audio, valid_langs)

    def process_audio(self, audio: AudioData, lang: str = "auto"):
        return self.engine.execute(audio, language=lang) or ""


class MultiModelContainer:
    """ loads 1 model per language """

    def __init__(self, plugin: str, lang_plugin: str = None, config: dict = None):
        self.plugin_class = load_stt_plugin(plugin)
        self.lang_plugin = None
        if not self.plugin_class:
            raise ValueError(f"Failed to load STT: {plugin}")
        if lang_plugin:
            lang_plugin = load_audio_transformer_plugin(lang_plugin)
            if not lang_plugin:
                raise ValueError(f"Failed to load lang detection plugin: {lang_plugin}")
            assert issubclass(lang_plugin, AudioLanguageDetector)
            self.lang_plugin = lang_plugin()
        self.engines = {}
        self.config = config or {}

    def detect_language(self, audio, valid_langs: Optional[Union[Set[str], List[str]]] = None) -> Tuple[str, float]:
        return self.lang_plugin.detect(audio, valid_langs)

    def get_engine(self, lang: str):
        if lang not in self.engines:
            self.load_engine(lang)
        return self.engines[lang]

    def load_engine(self, lang: str, config=None):
        # might need to load multiple models per language
        config = config or self.config
        config["lang"] = lang
        self.engines[lang] = self.plugin_class(config=config)
        if self.lang_plugin:
            self.engines[lang].bind(self.lang_plugin)

    def unload_engine(self, lang: str):
        if lang in self.engines:
            self.engines.pop(lang)

    def process_audio(self, audio: AudioData, lang: str):
        engine = self.get_engine(lang)
        return engine.execute(audio, language=lang) or ""


def bytes2audiodata(data: bytes) -> AudioData:
    recognizer = Recognizer()
    with NamedTemporaryFile() as fp:
        fp.write(data)
        with AudioFile(fp.name) as source:
            audio = recognizer.record(source)
    return audio


def create_app(stt_plugin, lang_plugin=None, multi=False, has_gradio=False):
    app = FastAPI()
    if multi:
        model = MultiModelContainer(stt_plugin, lang_plugin)
    else:
        model = ModelContainer(stt_plugin, lang_plugin)

    @app.get("/status")
    def stats(request: Request):
        return {"status": "ok",
                "plugin": stt_plugin,
                "lang_plugin": lang_plugin,
                "gradio": has_gradio}

    @app.post("/stt", response_class=PlainTextResponse)
    async def get_stt(request: Request):
        lang = str(request.query_params.get("lang", Configuration().get("lang", "auto"))).lower()
        audio_bytes = await request.body()
        audio = bytes2audiodata(audio_bytes)
        if lang == "auto":
            lang, prob = model.detect_language(audio_bytes)
        return model.process_audio(audio, lang)

    @app.post("/lang_detect")
    async def get_lang(request: Request):
        valid = request.query_params.get("valid_langs").split(",")
        if len(valid) == 1:
            return {"lang": valid[0], "conf": 1.0}
        audio_bytes = await request.body()
        lang, prob = model.detect_language(audio_bytes, valid_langs=valid)
        return {"lang": lang, "conf": prob}

    return app, model


def start_stt_server(engine: str,
                     lang_engine: str = None,
                     multi: bool = False,
                     has_gradio: bool = False) -> (FastAPI, ModelContainer):
    app, engine = create_app(engine, lang_engine, multi, has_gradio)
    return app, engine
