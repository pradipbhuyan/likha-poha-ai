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

    # ── 5. Expand abbreviations and common short forms for natural speech
    # Order matters: longer/specific forms before shorter ones
    abbrev_map = [
        # Latin abbreviations
        (r"\be\.g\.", "for example"),
        (r"\bi\.e\.", "that is"),
        (r"\betc\.", "et cetera"),
        (r"\bvs\.", "versus"),
        (r"\bviz\.", "namely"),
        (r"\bcf\.", "compare"),
        (r"\bNB\b", "note that"),
        # Academic/exam
        (r"\bHOTS\b", "higher order thinking skills"),
        (r"\bCBSE\b", "C B S E"),
        (r"\bSOF\b", "S O F"),
        (r"\bNCERT\b", "N C E R T"),
        (r"\bLHS\b", "left hand side"),
        (r"\bRHS\b", "right hand side"),
        (r"\bAM\b", "A M"),
        (r"\bPM\b", "P M"),
        # Science
        (r"\bDNA\b", "D N A"),
        (r"\bRNA\b", "R N A"),
        (r"\bATP\b", "A T P"),
        (r"\bpH\b", "P H"),
        (r"\bSI\b", "S I"),
        (r"\bm/s\b", "metres per second"),
        (r"\bkm/h\b", "kilometres per hour"),
        (r"\bkm/hr\b", "kilometres per hour"),
        # Maths
        (r"\bLCM\b", "L C M"),
        (r"\bHCF\b", "H C F"),
        (r"\bGCD\b", "G C D"),
        (r"\bAP\b(?=\s)", "arithmetic progression"),
        (r"\bGP\b(?=\s)", "geometric progression"),
        # Units
        (r"\bcm\b", "centimetres"),
        (r"\bmm\b", "millimetres"),
        (r"\bkm\b", "kilometres"),
        (r"\bkg\b", "kilograms"),
        (r"\bmg\b", "milligrams"),
        (r"\bml\b", "millilitres"),
        (r"\bkl\b", "kilolitres"),
        (r"\bkJ\b", "kilojoules"),
        (r"\bkW\b", "kilowatts"),
    ]
    for pattern, replacement in abbrev_map:
        text = re.sub(pattern, replacement, text)

    # ── 5b. Unicode math symbols → spoken English
    # Handles formatted text like "2¹ × 3¹" → "2 to the power 1 times 3 to the power 1"
    # Unicode superscripts (common in NCERT/CBSE textbooks)
    unicode_superscripts = {
        "⁰": " to the power 0",
        "¹": " to the power 1",
        "²": " squared",
        "³": " cubed",
        "⁴": " to the power 4",
        "⁵": " to the power 5",
        "⁶": " to the power 6",
        "⁷": " to the power 7",
        "⁸": " to the power 8",
        "⁹": " to the power 9",
    }
    for char, spoken in unicode_superscripts.items():
        text = text.replace(char, spoken)

    # Unicode subscripts (common in chemistry: H₂O, CO₂)
    unicode_subscripts = {
        "₀": " sub 0", "₁": " sub 1", "₂": " sub 2",
        "₃": " sub 3", "₄": " sub 4", "₅": " sub 5",
        "₆": " sub 6", "₇": " sub 7", "₈": " sub 8", "₉": " sub 9",
    }
    for char, spoken in unicode_subscripts.items():
        text = text.replace(char, spoken)

    # Unicode math operators
    text = text.replace("×", " times ")
    text = text.replace("÷", " divided by ")
    text = text.replace("≠", " is not equal to ")
    text = text.replace("≤", " is less than or equal to ")
    text = text.replace("≥", " is greater than or equal to ")
    text = text.replace("≈", " is approximately ")
    text = text.replace("∞", " infinity ")
    text = text.replace("√", " square root of ")
    text = text.replace("∑", " sum of ")
    text = text.replace("∏", " product of ")
    text = text.replace("∈", " is in ")
    text = text.replace("∉", " is not in ")
    text = text.replace("∪", " union ")
    text = text.replace("∩", " intersection ")
    text = text.replace("∠", " angle ")
    text = text.replace("°", " degrees ")
    text = text.replace("π", " pi ")
    text = text.replace("α", " alpha ")
    text = text.replace("β", " beta ")
    text = text.replace("γ", " gamma ")
    text = text.replace("δ", " delta ")
    text = text.replace("θ", " theta ")
    text = text.replace("λ", " lambda ")
    text = text.replace("μ", " mu ")
    text = text.replace("σ", " sigma ")
    text = text.replace("ω", " omega ")
    text = text.replace("→", " gives ")
    text = text.replace("⇒", " implies ")
    text = text.replace("⟹", " implies ")
    text = text.replace("↔", " if and only if ")
    text = text.replace("∴", " therefore ")
    text = text.replace("∵", " because ")
    # Fraction slash in unicode math
    text = re.sub(r"(\d)\s*/\s*(\d)", r"\1 over \2", text)

    # ── 6. LaTeX and math: convert to spoken English (Option 3)
    # Note: Devanagari/Hindi script (\u0900-\u097F) is preserved — do NOT strip it.
    # Process inside-out: innermost expressions first, then wrappers.

    def _latex_to_speech(expr: str) -> str:
        """
        Recursively convert a LaTeX expression string to natural spoken English.
        Called on the content inside $...$ and $$...$$
        """
        s = expr.strip()

        # ── Remove outer braces wrapping (common in LaTeX) ─────────────────
        def strip_outer_braces(x):
            x = x.strip()
            if x.startswith("{") and x.endswith("}"):
                return x[1:-1].strip()
            return x

        # ── \frac{numerator}{denominator} → "numerator over denominator" ───
        # Handle nested: process innermost first via repeated substitution
        for _ in range(5):  # max 5 levels of nesting
            s = re.sub(
                r"\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}",
                lambda m: f"{_latex_to_speech(m.group(1))} over {_latex_to_speech(m.group(2))}",
                s,
            )

        # ── \sqrt{x} → "square root of x" ───────────────────────────────────
        s = re.sub(
            r"\\sqrt\s*\{([^{}]*)\}",
            lambda m: f"square root of {_latex_to_speech(m.group(1))}",
            s,
        )
        # \sqrt[n]{x} → "nth root of x"
        s = re.sub(
            r"\\sqrt\s*\[([^\]]*)\]\s*\{([^{}]*)\}",
            lambda m: f"{_latex_to_speech(m.group(1))} root of {_latex_to_speech(m.group(2))}",
            s,
        )

        # ── Superscripts: x^{n} and x^n ─────────────────────────────────────
        # Named powers first
        s = re.sub(r"\^2\b", " squared", s)
        s = re.sub(r"\^3\b", " cubed", s)
        s = re.sub(r"\^\{2\}", " squared", s)
        s = re.sub(r"\^\{3\}", " cubed", s)
        # General: a^{n} → "a to the power n"
        s = re.sub(r"\^\{([^{}]+)\}", lambda m: f" to the power {m.group(1).strip()}", s)
        # a^n (single char) → "a to the power n"
        s = re.sub(r"\^([a-zA-Z0-9])", lambda m: f" to the power {m.group(1)}", s)

        # ── Subscripts: x_{n} → "x sub n" (used in sequences) ──────────────
        s = re.sub(r"_\{([^{}]+)\}", lambda m: f" sub {m.group(1).strip()}", s)
        s = re.sub(r"_([a-zA-Z0-9])", lambda m: f" sub {m.group(1)}", s)

        # ── Greek letters → spoken names ────────────────────────────────────
        greek = {
            r"\\alpha": "alpha", r"\\beta": "beta", r"\\gamma": "gamma",
            r"\\delta": "delta", r"\\theta": "theta", r"\\pi\b": "pi",
            r"\\sigma": "sigma", r"\\omega": "omega", r"\\lambda": "lambda",
            r"\\mu\b": "mu", r"\\epsilon": "epsilon", r"\\phi": "phi",
        }
        for pattern, name in greek.items():
            s = re.sub(pattern, f" {name} ", s)

        # ── Operators and symbols ────────────────────────────────────────────
        s = s.replace("\\times", " times ")
        s = s.replace("\\cdot", " times ")
        s = s.replace("\\div", " divided by ")
        s = s.replace("\\pm", " plus or minus ")
        s = s.replace("\\mp", " minus or plus ")
        s = s.replace("\\leq", " is less than or equal to ")
        s = s.replace("\\geq", " is greater than or equal to ")
        s = s.replace("\\neq", " is not equal to ")
        s = s.replace("\\approx", " is approximately equal to ")
        s = s.replace("\\equiv", " is equivalent to ")
        s = s.replace("\\Rightarrow", " implies ")
        s = s.replace("\\rightarrow", " gives ")
        s = s.replace("\\Leftrightarrow", " if and only if ")
        s = s.replace("\\therefore", " therefore ")
        s = s.replace("\\because", " because ")
        s = s.replace("\\infty", " infinity ")
        s = s.replace("\\in", " is in ")
        s = s.replace("\\notin", " is not in ")
        s = s.replace("\\subset", " is a subset of ")
        s = s.replace("\\cup", " union ")
        s = s.replace("\\cap", " intersection ")
        s = s.replace("\\ldots", " and so on ")
        s = s.replace("\\cdots", " and so on ")

        # ── Inline operators ─────────────────────────────────────────────────
        s = re.sub(r"\s*=\s*", " equals ", s)
        s = re.sub(r"\s*\+\s*", " plus ", s)
        s = re.sub(r"(?<=\d)\s*-\s*(?=\d)", " minus ", s)
        s = re.sub(r"(?<=[a-zA-Z])\s*-\s*(?=[a-zA-Z0-9])", " minus ", s)

        # ── Strip remaining LaTeX commands ───────────────────────────────────
        s = re.sub(r"\\[a-zA-Z]+", " ", s)

        # ── Remove braces ─────────────────────────────────────────────────────
        s = re.sub(r"[{}]", " ", s)

        # ── Parentheses in math context → spoken ────────────────────────────
        # Keep them for structure but don't say "open bracket"
        s = re.sub(r"\(", " ", s)
        s = re.sub(r"\)", " ", s)

        return re.sub(r"\s+", " ", s).strip()

    def _convert_latex_block(match: re.Match) -> str:
        """Convert one $...$ or $$...$$ block to spoken English."""
        content = match.group(1)
        spoken = _latex_to_speech(content)
        return f" {spoken} " if spoken.strip() else " "

    # Convert display math $$...$$ first
    text = re.sub(r"\$\$([^\$]+)\$\$", _convert_latex_block, text, flags=re.DOTALL)
    # Convert inline math $...$
    text = re.sub(r"\$([^\$]+)\$", _convert_latex_block, text)

    # Handle any remaining raw LaTeX outside $...$ (from broken formatting)
    text = text.replace("\\", " ")
    # Only remove ASCII brackets/braces — NOT Devanagari punctuation
    text = re.sub(r"[{}\[\]]", " ", text)
    text = text.replace("Rightarrow", " therefore ")
    # Handle standalone ^2 ^3 outside LaTeX
    text = re.sub(r"\^2\b", " squared ", text)
    text = re.sub(r"\^3\b", " cubed ", text)
    text = re.sub(r"(?<=\d)-(?=\d)", " minus ", text)

    # ── 7. Blank lines (paragraph breaks) → strong sentence pause
    # Two+ newlines become ". " so Edge TTS pauses between paragraphs
    text = re.sub(r"\n{2,}", ". \n", text)

    # ── 8. Single newlines → brief comma pause (keeps narration flowing naturally)
    # Only between non-empty lines to avoid spurious pauses
    text = re.sub(r"(?<=[^\n])\n(?=[^\n])", ", ", text)

    # ── 9. Clean up any remaining newlines and collapse whitespace
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    # ── 10. Clean up empty bullets (LaTeX-only items that became empty strings)
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
