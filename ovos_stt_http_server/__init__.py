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
from typing import List, Tuple, Optional, Set, Union
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from ovos_config import Configuration
from ovos_plugin_manager.audio_transformers import load_audio_transformer_plugin, AudioLanguageDetector
from ovos_plugin_manager.stt import load_stt_plugin
from ovos_plugin_manager.utils.audio import AudioFile, AudioData
from ovos_utils.log import LOG
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
        """
        Transcribes the provided audio using the engine for the specified language.
        
        Parameters:
            audio (AudioData): Audio content to transcribe.
            lang (str): Language code identifying which engine to use.
        
        Returns:
            str: Transcribed text for the audio, or an empty string if no transcription is produced.
        """
        engine = self.get_engine(lang)
        return engine.execute(audio, language=lang) or ""


def create_app(stt_plugin: str, lang_plugin: str = None, multi: bool = False):
    """
    Create and configure a FastAPI app that exposes STT and language-detection endpoints.

    Initializes either a single-model or multi-model container using the provided plugins,
    and registers three endpoints:
    - GET /status: returns service and plugin metadata.
    - POST /stt: accepts raw audio bytes (query params: `lang`, `sample_rate`, `sample_width`),
      optionally performs language detection when `lang=auto`, and returns transcribed text.
    - POST /lang_detect: accepts raw audio bytes and returns detected language and confidence
      (supports `valid_langs` query param).

    Parameters:
        stt_plugin: Name or identifier of the STT plugin to load.
        lang_plugin: Name or identifier of an optional language-detection plugin.
        multi: If True, use a MultiModelContainer (one engine per language).

    Returns:
        tuple: (app, model) where `app` is the configured FastAPI application and `model` is
            the initialized ModelContainer or MultiModelContainer instance.
    """
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    if multi:
        model = MultiModelContainer(stt_plugin, lang_plugin)
    else:
        model = ModelContainer(stt_plugin, lang_plugin)

    @app.get("/status")
    def stats(request: Request):
        return {"status": "ok",
                "plugin": stt_plugin,
                "lang_plugin": lang_plugin}

    @app.post("/stt", response_class=PlainTextResponse)
    async def get_stt(request: Request):
        """
        Handle an STT request: read audio from the request body, determine language if requested, and return the transcription.
        
        Parameters:
            request (Request): HTTP request whose body contains raw audio bytes. Query parameters:
                - lang: language code or "auto" (default from Configuration().get("lang", "auto")).
                - sample_rate: sample rate in Hz for the audio (default 16000).
                - sample_width: sample width in bytes (default 2).
        
        Returns:
            str: Transcribed text from the provided audio, or an empty string if no transcription is produced.
        """
        lang = str(request.query_params.get("lang", Configuration().get("lang", "auto"))).lower()
        sr = request.query_params.get("sample_rate", 16000)
        sw = request.query_params.get("sample_width", 2)
        audio_bytes = await request.body()
        audio = AudioData(audio_bytes, sr, sw)
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

    from ovos_stt_http_server.routers.chromium import make_chromium_router
    from ovos_stt_http_server.routers.utcp import make_utcp_router
    from ovos_stt_http_server.routers.deepgram import make_deepgram_router
    app.include_router(make_chromium_router(model))
    app.include_router(make_utcp_router())
    from ovos_stt_http_server.routers.wit_ai import make_wit_ai_router
    app.include_router(make_wit_ai_router(model))
    app.include_router(make_deepgram_router(model))

    # Mount MCP server when the optional dependency is available.
    try:
        from ovos_stt_http_server.mcp_server import mount_mcp_on_fastapi
        mount_mcp_on_fastapi(app, model)
    except ImportError:
        LOG.debug("MCP extra not installed; skipping MCP server. "
                  "Enable with: pip install 'ovos-stt-http-server[mcp]'")

    return app, model


def start_stt_server(engine: str,
                     lang_engine: str = None,
                     multi: bool = False) -> tuple:
    """
    Initialize and return a configured FastAPI STT server and its model container.

    Parameters:
        engine: STT plugin name to load.
        lang_engine: Optional language-detection plugin name.
        multi: If True, load one engine per language via MultiModelContainer.

    Returns:
        tuple: (app, model) — the FastAPI application and the model container.
    """
    app, engine = create_app(engine, lang_engine, multi)
    return app, engine