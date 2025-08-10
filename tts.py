from kokoro import KPipeline
from IPython.display import display, Audio
import soundfile as sf
import torch


def say(text, pipeline: KPipeline, no_ext_file_name='say'):
    generator = pipeline(text, voice='af_heart')
    for i, (gs, ps, audio) in enumerate(generator):
        print(i, gs, ps)
        # display(Audio(data=audio, rate=24000, autoplay=i==0))
        sf.write(f"{no_ext_file_name}-{i}.wav", audio, 24000)


pipeline = KPipeline(lang_code='a', repo_id='hexgrad/Kokoro-82M')
say("How can I help you today?", pipeline)
say("Who know?", pipeline, no_ext_file_name="say1")
