
import gradio as gr

from os.path import join, dirname, basename, splitext, isfile
from ovos_utils.log import LOG
from ovos_stt_http_server import ModelContainer, bytes2audiodata

STT = None


def transcribe(audio_file, language: str):
    try:
        with open(audio_file, 'rb') as f:
            audio = f.read()
        return STT.process_audio(bytes2audiodata(audio), language)
    except TypeError:
        LOG.error(f"Requested file not valid: {audio_file}")
    except FileNotFoundError:
        LOG.error(f"Requested file not found: {audio_file}")

def bind_gradio_service(app, stt_engine: ModelContainer,
                        title, description, info, badge,
                        default_lang="en", cache=True):
    global STT
    STT = stt_engine
    languages = list(stt_engine.engine.available_languages or [default_lang])
    languages.sort()
    LOG.debug(languages)

    if default_lang not in languages:
        LOG.info(f"{default_lang} not in languages, trying ISO 639-1 code")
        default_lang = default_lang.split('-')[0]
    if default_lang not in languages:
        LOG.warning(f"{default_lang} not in languages, choosing first lang")
        default_lang = languages[0]

    examples = [join(dirname(__file__), 'audio', f'{lang.split("-")[0]}.mp3')
                for lang in languages]
    examples = [example for example in examples if isfile(example)]
    iface = gr.Interface(
        fn=transcribe,
        inputs=[
            gr.Audio(source="microphone", type="filepath"),
            gr.Radio(
                label="Language",
                choices=languages,
                value=default_lang
            )
        ],
        outputs=[
            "textbox"
        ],
        examples=[[e, basename(splitext(e)[0])] for e in examples],
        cache_examples=cache,  # Takes some time at init, but speeds up runtime
        live=True,
        title=title,
        description=description,
        article=info,
        analytics_enabled=False)

    LOG.info(f"Mounting app to /gradio")
    gr.mount_gradio_app(app, iface, path="/gradio")
