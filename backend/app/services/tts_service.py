import asyncio
import os
import re
import uuid

import edge_tts


AUDIO_DIR = os.getenv("AUDIO_DIR", "generated_audio")


def clean_text_for_tts(text: str) -> str:
    """Strip markdown/math punctuation so generated speech sounds natural."""
    text = re.sub(r"#+\s*", "", text)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"^\s*[-•]\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"`+", "", text)
    text = re.sub(r"---+", " ", text)

    text = text.replace("\\", "")
    text = text.replace("(", "")
    text = text.replace(")", "")
    text = text.replace("[", "")
    text = text.replace("]", "")
    text = text.replace("{", "")
    text = text.replace("}", "")

    text = text.replace("Rightarrow", " therefore ")
    text = text.replace("^2", " square")
    text = text.replace("^3", " cube")

    text = re.sub(r"\s=\s", " equals ", text)
    text = re.sub(r"\s\+\s", " plus ", text)
    #text = re.sub(r"(\w)-(\w)", r"\1 minus \2", text)
    text = re.sub(r"(?<=\d)-(?=\d)", " minus ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


async def _generate_edge_tts(text, output_file, voice, rate, pitch):
    """Call Edge TTS asynchronously and save the MP3 to disk."""
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        pitch=pitch,
    )
    await communicate.save(output_file)


def generate_speech_file(
    text: str,
    voice: str = "en-IN-NeerjaNeural",
    rate: str = "+0%",
    pitch: str = "+0Hz",
) -> str:
    """
    Generate an MP3 file from lesson text and return its local file path.

    The frontend receives this file through a FastAPI FileResponse.
    """
    os.makedirs(AUDIO_DIR, exist_ok=True)

    file_name = f"{uuid.uuid4()}.mp3"
    output_file = os.path.join(AUDIO_DIR, file_name)

    cleaned_text = clean_text_for_tts(text)

    asyncio.run(
        _generate_edge_tts(
            cleaned_text,
            output_file,
            voice,
            rate,
            pitch,
        )
    )

    return output_file
