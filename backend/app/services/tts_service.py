import asyncio
import os
import re
import uuid

import edge_tts


AUDIO_DIR = os.getenv("AUDIO_DIR", "generated_audio")


def clean_text_for_tts(text: str) -> str:
    """
    Strip markdown/math punctuation and introduce natural speech pauses.

    Pause strategy (Edge TTS honours sentence-ending punctuation):
    - Section headings (## / ###) → read heading text then pause (period + newline)
    - Blank lines between paragraphs → sentence pause (period)
    - Bullet/list items → each item ends with a comma pause, last item with period
    - Single newlines within a paragraph → brief comma pause
    This ensures the narrator pauses between steps rather than running on.
    """
    # ── 1. Section headings: strip # markers, keep text, append a period for pause
    # "## Worked Example" → "Worked Example."
    text = re.sub(r"^#{1,6}\s*(.+)$", r"\1.", text, flags=re.MULTILINE)

    # ── 2. Strip bold/italic markers but keep the text
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)

    # ── 3. Bullet/list items: each bullet becomes a sentence ending with comma pause
    # "- Item one" → "Item one,"  (last line cleanup done after)
    text = re.sub(r"^\s*[-•*]\s+(.+)$", r"\1,", text, flags=re.MULTILINE)

    # ── 4. Remove code backticks and horizontal rules
    text = re.sub(r"`+[^`]*`+", "", text)   # inline code
    text = re.sub(r"```[\s\S]*?```", "", text)  # fenced code blocks
    text = re.sub(r"---+", ". ", text)

    # ── 5. LaTeX and math: convert to spoken equivalents
    text = text.replace("\\", " ")
    text = re.sub(r"\$\$[\s\S]*?\$\$", " ", text)  # strip display math
    text = re.sub(r"\$[^$]+\$", " ", text)           # strip inline math
    text = text.replace("(", " ")
    text = text.replace(")", " ")
    text = text.replace("[", " ")
    text = text.replace("]", " ")
    text = text.replace("{", " ")
    text = text.replace("}", " ")
    text = text.replace("Rightarrow", " therefore ")
    text = text.replace("^2", " squared ")
    text = text.replace("^3", " cubed ")
    text = re.sub(r"\s=\s", " equals ", text)
    text = re.sub(r"\s\+\s", " plus ", text)
    text = re.sub(r"(?<=\d)-(?=\d)", " minus ", text)

    # ── 6. Blank lines (paragraph breaks) → strong sentence pause
    # Two+ newlines become ". " so Edge TTS pauses between paragraphs
    text = re.sub(r"\n{2,}", ". \n", text)

    # ── 7. Single newlines → brief comma pause (keeps narration flowing naturally)
    # Only between non-empty lines to avoid spurious pauses
    text = re.sub(r"(?<=[^\n])\n(?=[^\n])", ", ", text)

    # ── 8. Clean up any remaining newlines and collapse whitespace
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    # ── 9. Clean up empty bullets (LaTeX-only items that became empty strings)
    text = re.sub(r"(,\s*){2,}", ", ", text)     # consecutive commas → single comma
    text = re.sub(r"\.\s*\.", ".", text)           # double periods
    text = re.sub(r"(\.\s*){3,}", ". ", text)     # triple+ periods → single
    text = re.sub(r",\s*\.", ".", text)            # comma then period → period
    text = re.sub(r"\.\s*,", ".", text)            # period then comma → period
    text = re.sub(r":\s*[,\.]+", ".", text)        # "are:,," → "are." (empty list)
    text = re.sub(r"\s{2,}", " ", text)            # collapse any remaining extra spaces

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
