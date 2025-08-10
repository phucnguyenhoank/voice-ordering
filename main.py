import sys
import os
import logging

logging.basicConfig(level=logging.INFO)
# sys.path.append(os.path.abspath("../my_tts_module"))

from tts import TextToSpeech

tts = TextToSpeech()
messages = [
    "Can I help you?",
    "What would you like to eat?",
    "This is a third test message."
]

for msg in messages:
    try:
        tts.text_to_speech(msg)
    except Exception as e:
        logging.error(f"Error for '{msg}': {e}")