import gradio as gr

from os.path import join, dirname, basename, splitext, isfile
from ovos_utils.log import LOG
from ovos_stt_http_server import ModelContainer
from ovos_plugin_manager.utils.audio import AudioData

STT = None


def transcribe(audio_file, language: str, sample_rate: int = 16000, sample_width: int = 2):
    """
    Transcribe an audio file into text using the configured STT engine.
    
    Parameters:
        audio_file (str): Path to the audio file to transcribe.
        language (str): Language code to use for transcription.
        sample_rate (int): Sample rate in Hz for the provided audio (default 16000).
        sample_width (int): Sample width in bytes for the provided audio (default 2).
    
    Returns:
        transcription (str): The transcribed text, or `None` if the file is missing or invalid.
    """
    try:
        with open(audio_file, 'rb') as f:
            audio = f.read()
        return STT.process_audio(AudioData(audio, sample_rate, sample_width), language)
    except TypeError:
        LOG.error(f"Requested file not valid: {audio_file}")
    except FileNotFoundError:
        LOG.error(f"Requested file not found: {audio_file}")

def bind_gradio_service(app, stt_engine: ModelContainer,
                        title, description, info, badge,
                        default_lang="en", cache=True):
    """
    Create and mount a Gradio-based transcription UI at /gradio using the provided STT engine.
    
    Initializes the module STT with the given ModelContainer, prepares available language choices and example audio files, constructs a Gradio Interface configured to call the transcribe function, and mounts that interface to the supplied app at path "/gradio". This function logs a deprecation warning for the Gradio interface.
    
    Parameters:
        app: The web application or framework instance to which the Gradio interface will be mounted.
        stt_engine (ModelContainer): Speech-to-text engine container used to perform transcriptions and to obtain available languages.
        title (str): Title to display in the Gradio UI.
        description (str): Short description shown in the Gradio UI.
        info (str): Additional informational HTML or text displayed in the Gradio UI article section.
        badge: UI badge metadata (present for API compatibility; not used by this function).
        default_lang (str): Preferred default language code; if not available it will be adjusted or replaced with the first available language.
        cache (bool): Whether to cache example executions to speed up runtime after initial initialization.
    """
    global STT
    LOG.warning("gradio interface is deprecated and will be removed in a follow up release")
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
