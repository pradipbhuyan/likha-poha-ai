import { useEffect, useMemo, useRef, useState } from "react";
import { Pause, Play, RotateCcw, Square, Volume2 } from "lucide-react";

import { getChapterNarration } from "../api/lesson";
import idleNeutral from "../assets/avatar/likha/idle-neutral.png";
import speakingA from "../assets/avatar/likha/speaking-a.png";
import speakingO from "../assets/avatar/likha/speaking-o.png";
import explaining from "../assets/avatar/likha/explaining.png";
import question from "../assets/avatar/likha/question.png";

/**
 * Grade 6 English avatar-narration proof of concept.
 *
 * This intentionally uses the browser Speech Synthesis API instead of a
 * server-side TTS provider. It keeps the POC free, requires no API key, and
 * lets us validate learner engagement before introducing cached paid audio.
 */
const POC_GRADE = "Grade 6";
const POC_SUBJECT = "English";
const MAX_NARRATION_CHARACTERS = 2500;

function stripMarkdown(value) {
  return String(value || "")
    .replace(/```[\s\S]*?```/g, "")
    .replace(/!\[[^\]]*]\([^)]*\)/g, "")
    .replace(/\[([^\]]+)]\([^)]*\)/g, "$1")
    .replace(/[*_`>#~]/g, "")
    .replace(/\$\$?([^$]+)\$\$?/g, "$1")
    .replace(/\s+/g, " ")
    .trim();
}

function narrationTextForMilestone(milestone) {
  if (!milestone) return "";

  const blockText = (milestone.blocks || [])
    .map((block) => {
      switch (block.type) {
        case "hook":
          return block.text;
        case "concept":
        case "watchout":
          return `${block.title || ""}. ${block.body_md || ""}`;
        case "example":
          return `Example. ${block.question || ""}. ${block.body_md || ""}`;
        case "vocab":
          return (block.words || [])
            .map((word) => `${word.term} means ${word.meaning}.`)
            .join(" ");
        case "quickcheck":
          return `Quick check. ${block.question || ""}`;
        case "freetext_qa":
          return `Quick check. ${block.question || ""}`;
        default:
          return "";
      }
    })
    .join(" ");

  return stripMarkdown(`${milestone.title || "Lesson section"}. ${blockText}`)
    .slice(0, MAX_NARRATION_CHARACTERS);
}

function findPreferredVoice() {
  const voices = window.speechSynthesis?.getVoices?.() || [];
  // The Web Speech API does not expose a voice-gender field. Prefer commonly
  // available female voice names, first for Indian English and then for other
  // English voices, while retaining a reliable language-based fallback.
  const femaleVoiceName = /\b(ada|aditi|allison|aria|ava|emma|fiona|heera|jenny|karen|lekha|moira|neerja|samantha|serena|susan|tessa|veena|victoria|zira)\b/i;
  const indianEnglish = (voice) => /^en[-_]IN/i.test(voice.lang);
  const english = (voice) => /^en([-_]|$)/i.test(voice.lang);

  return (
    voices.find((voice) => indianEnglish(voice) && /\btara\b/i.test(voice.name)) ||
    voices.find((voice) => indianEnglish(voice) && femaleVoiceName.test(voice.name)) ||
    voices.find((voice) => english(voice) && femaleVoiceName.test(voice.name)) ||
    voices.find(indianEnglish) ||
    voices.find(english) ||
    null
  );
}

function AvatarNarrator({
  grade,
  mode,
  subject,
  chapter,
  milestone,
  milestoneIndex,
}) {
  const isEnabled = grade === POC_GRADE && subject === POC_SUBJECT;
  const speechSupported =
    typeof window !== "undefined" &&
    "speechSynthesis" in window &&
    "SpeechSynthesisUtterance" in window;

  const [status, setStatus] = useState("idle");
  const [mouthFrame, setMouthFrame] = useState("a");
  const [rate, setRate] = useState(1.05);
  const utteranceRef = useRef(null);
  const audioRef = useRef(null);
  const intervalRef = useRef(null);
  const narrationRequestRef = useRef(0);

  const narrationText = useMemo(
    () => narrationTextForMilestone(milestone),
    [milestone]
  );

  const isSpeaking = status === "speaking";
  const isPaused = status === "paused";
  const isQuestion = /quick check|question|think|why|how/i.test(
    `${milestone?.title || ""} ${narrationText}`
  );

  const avatarSource = isSpeaking
    ? mouthFrame === "a"
      ? speakingA
      : speakingO
    : isQuestion
      ? question
      : status === "complete"
        ? explaining
        : idleNeutral;

  function stopMouthAnimation() {
    window.clearInterval(intervalRef.current);
    intervalRef.current = null;
    setMouthFrame("a");
  }

  function cancelNarration() {
    narrationRequestRef.current += 1;
    if (typeof window !== "undefined" && window.speechSynthesis?.cancel) {
      window.speechSynthesis.cancel();
    }
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = "";
      audioRef.current = null;
    }
    utteranceRef.current = null;
    stopMouthAnimation();
  }

  function beginMouthAnimation() {
    stopMouthAnimation();
    intervalRef.current = window.setInterval(() => {
      setMouthFrame((current) => (current === "a" ? "o" : "a"));
    }, 170);
  }

  function speakWithTara() {
    if (!speechSupported || !narrationText) {
      setStatus("error");
      return;
    }

    const utterance = new window.SpeechSynthesisUtterance(narrationText);
    utterance.lang = "en-IN";
    utterance.rate = rate;
    utterance.pitch = 1.08;

    const preferredVoice = findPreferredVoice();
    if (preferredVoice) utterance.voice = preferredVoice;

    utterance.onstart = () => {
      setStatus("speaking");
      beginMouthAnimation();
    };
    utterance.onend = () => {
      stopMouthAnimation();
      utteranceRef.current = null;
      setStatus("complete");
    };
    utterance.onerror = (event) => {
      if (event.error !== "canceled" && event.error !== "interrupted") {
        setStatus("error");
      } else {
        setStatus("idle");
      }
      stopMouthAnimation();
      utteranceRef.current = null;
    };

    utteranceRef.current = utterance;
    window.speechSynthesis.speak(utterance);
  }

  async function speak() {
    if (!narrationText) return;

    cancelNarration();
    const requestId = narrationRequestRef.current;
    setStatus("loading");

    try {
      const result = await getChapterNarration({
        grade,
        mode,
        subject,
        chapter,
        milestoneIndex,
      });
      if (requestId !== narrationRequestRef.current) return;

      if (!result?.success || !result.audio_url) {
        speakWithTara();
        return;
      }

      const audio = new Audio(result.audio_url);
      audioRef.current = audio;
      audio.onplay = () => {
        if (requestId !== narrationRequestRef.current) return;
        setStatus("speaking");
        beginMouthAnimation();
      };
      audio.onended = () => {
        if (requestId !== narrationRequestRef.current) return;
        stopMouthAnimation();
        audioRef.current = null;
        setStatus("complete");
      };
      audio.onerror = () => {
        if (requestId !== narrationRequestRef.current) return;
        audioRef.current = null;
        stopMouthAnimation();
        speakWithTara();
      };
      await audio.play();
    } catch {
      if (requestId === narrationRequestRef.current) {
        speakWithTara();
      }
    }
  }

  function togglePlayback() {
    if (isPaused) {
      if (audioRef.current) {
        audioRef.current.play().catch(() => speakWithTara());
      } else {
        window.speechSynthesis.resume();
        setStatus("speaking");
        beginMouthAnimation();
      }
      return;
    }
    if (isSpeaking) {
      if (audioRef.current) {
        audioRef.current.pause();
      } else {
        window.speechSynthesis.pause();
      }
      setStatus("paused");
      stopMouthAnimation();
      return;
    }
    speak();
  }

  function handleRateChange(event) {
    const nextRate = Number(event.target.value);
    setRate(nextRate);
    if (isSpeaking || isPaused || status === "loading") {
      cancelNarration();
      setStatus("idle");
    }
  }

  useEffect(() => {
    cancelNarration();
    setStatus("idle");
    // A milestone change must never continue reading the previous section.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [milestoneIndex, narrationText]);

  useEffect(
    () => () => {
      cancelNarration();
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );

  if (!isEnabled) return null;

  return (
    <section
      aria-label="Likha narrated lesson preview"
      className="likha-narrator"
      style={{
        display: "grid",
        gridTemplateColumns: "minmax(120px, 180px) minmax(0, 1fr)",
        gap: 14,
        alignItems: "center",
        marginBottom: 16,
        padding: "12px 16px 12px 8px",
        border: "1.5px solid var(--likha-narrator-border, rgba(59, 130, 246, .3))",
        borderRadius: 16,
        background: "var(--likha-narrator-background, linear-gradient(120deg, rgba(239, 246, 255, .92), rgba(248, 250, 252, .95)))",
        color: "var(--text, #0f172a)",
      }}
    >
      <div style={{ alignSelf: "stretch", minHeight: 150, display: "flex", alignItems: "flex-end", justifyContent: "center" }}>
        <img
          src={avatarSource}
          alt={isSpeaking ? "Likha is narrating this lesson section" : "Likha, your lesson guide"}
          style={{
            width: "100%",
            maxWidth: 170,
            maxHeight: 180,
            objectFit: "contain",
            objectPosition: "bottom center",
            filter: isSpeaking ? "drop-shadow(0 7px 8px rgba(37, 99, 235, .16))" : undefined,
            transition: "filter .2s ease",
          }}
        />
      </div>

      <div style={{ minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 5 }}>
          <Volume2 size={17} color="var(--likha-narrator-accent, #2563eb)" aria-hidden="true" />
          <strong style={{ fontSize: ".98rem" }}>Listen with Likha</strong>
        </div>

        <p style={{ margin: "0 0 10px", fontSize: ".85rem", color: "var(--muted, #64748b)", lineHeight: 1.45 }}>
          {milestone?.title
            ? `Likha can read “${milestone.title}” aloud.`
            : "Choose a lesson section to hear Likha narrate it."}
        </p>

        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <button
              type="button"
              onClick={togglePlayback}
              disabled={!narrationText}
              aria-label={isSpeaking ? "Pause narration" : isPaused ? "Resume narration" : "Play narration"}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                padding: "8px 12px",
                border: "none",
                borderRadius: 9,
                color: "#fff",
                background: "var(--likha-narrator-accent, #2563eb)",
                cursor: narrationText ? "pointer" : "not-allowed",
                font: "inherit",
                fontSize: ".84rem",
                fontWeight: 750,
                opacity: narrationText ? 1 : .55,
              }}
            >
              {isSpeaking ? <Pause size={15} fill="currentColor" /> : <Play size={15} fill="currentColor" />}
              {status === "loading"
                ? "Loading…"
                : isSpeaking
                  ? "Pause"
                  : isPaused
                    ? "Resume"
                    : status === "complete"
                      ? "Play again"
                      : "Listen"}
            </button>
            <button
              type="button"
              onClick={() => {
                cancelNarration();
                setStatus("idle");
              }}
              disabled={!isSpeaking && !isPaused}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 5,
                padding: "8px 10px",
                border: "1px solid var(--border, #cbd5e1)",
                borderRadius: 9,
                color: "var(--text, #334155)",
                background: "var(--panel, #fff)",
                cursor: isSpeaking || isPaused ? "pointer" : "default",
                font: "inherit",
                fontSize: ".82rem",
                opacity: isSpeaking || isPaused ? 1 : .5,
              }}
            >
              <Square size={13} fill="currentColor" />
              Stop
            </button>
            <label style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: ".8rem", color: "var(--muted, #64748b)" }}>
              Speed
              <select value={rate} onChange={handleRateChange} aria-label="Narration speed" style={{ font: "inherit", padding: "5px 4px", borderRadius: 7, border: "1px solid var(--border, #cbd5e1)", background: "var(--panel, #fff)" }}>
                <option value="0.85">0.85×</option>
                <option value="1">1×</option>
                <option value="1.05">1.05×</option>
                <option value="1.15">1.15×</option>
              </select>
            </label>
            {status === "complete" && (
              <button
                type="button"
                onClick={speak}
                style={{ display: "inline-flex", alignItems: "center", gap: 4, border: "none", background: "none", color: "var(--likha-narrator-accent, #2563eb)", cursor: "pointer", font: "inherit", fontSize: ".8rem", fontWeight: 700 }}
              >
                <RotateCcw size={14} /> Replay
              </button>
            )}
          </div>

        {status !== "idle" && (
          <p aria-live="polite" style={{ margin: "9px 0 0", fontSize: ".76rem", color: status === "error" ? "var(--likha-narrator-error, #b91c1c)" : "var(--muted, #64748b)" }}>
            {status === "loading" && "Preparing narration…"}
          {status === "speaking" && "Likha is narrating…"}
            {status === "paused" && "Narration paused."}
            {status === "complete" && "Narration complete."}
            {status === "error" && "Narration could not start. Please try again."}
          </p>
        )}
      </div>
    </section>
  );
}

export default AvatarNarrator;
