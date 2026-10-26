import { useEffect, useMemo, useRef, useState } from "react";
import { Pause, Play, RotateCcw, Square, Volume2 } from "lucide-react";

import { getChapterNarration } from "../api/lesson";
import idleNeutral from "../assets/avatar/likha/idle-neutral.png";
import speakingA from "../assets/avatar/likha/speaking-a.png";
import speakingO from "../assets/avatar/likha/speaking-o.png";
import explaining from "../assets/avatar/likha/explaining.png";
import question from "../assets/avatar/likha/question.png";

/**
 * Grades 5–8 English and Hindi avatar-narration experience.
 *
 * Neural audio is requested from the backend. If it is unavailable, the
 * browser Speech Synthesis API provides a language-appropriate fallback.
 */
const NARRATED_GRADES = new Set(["Grade 5", "Grade 6", "Grade 7", "Grade 8"]);
const NARRATED_SUBJECTS = {
  english: {
    displayName: "Neerja",
    language: "en-IN",
    preferredVoice: /\b(neerja|tara)\b/i,
  },
  hindi: {
    displayName: "Swara",
    language: "hi-IN",
    preferredVoice: /\bswara\b/i,
  },
};
const MAX_NARRATION_CHARACTERS = 2500;
const LOADING_MESSAGES = [
  "Likha is preparing your narration…",
  "Turning this lesson into a listening adventure…",
  "Likha is getting your next explanation ready…",
  "A calm moment now — your narration is almost ready.",
];

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

function findWelcomeVoice(narrationConfig) {
  const voices = window.speechSynthesis?.getVoices?.() || [];
  const language = narrationConfig.language.replace("-", "[-_]");
  const preferredLanguage = new RegExp(`^${language}`, "i");

  return (
    voices.find(
      (voice) =>
        preferredLanguage.test(voice.lang) &&
        narrationConfig.preferredVoice.test(voice.name)
    ) ||
    voices.find((voice) => preferredLanguage.test(voice.lang)) ||
    null
  );
}

function findPreferredVoice(narrationConfig) {
  const voices = window.speechSynthesis?.getVoices?.() || [];
  const language = narrationConfig.language.replace("-", "[-_]");
  const preferredLanguage = new RegExp(`^${language}`, "i");
  const english = (voice) => /^en([-_]|$)/i.test(voice.lang);

  return (
    (narrationConfig.language === "en-IN"
      ? voices.find(
          (voice) =>
            preferredLanguage.test(voice.lang) && /\btara\b/i.test(voice.name)
        )
      : null) ||
    voices.find(
      (voice) =>
        preferredLanguage.test(voice.lang) &&
        narrationConfig.preferredVoice.test(voice.name)
    ) ||
    voices.find((voice) => preferredLanguage.test(voice.lang)) ||
    (narrationConfig.language === "en-IN" ? voices.find(english) : null) ||
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
  narrationPaths,
}) {
  const narrationConfig =
    NARRATED_SUBJECTS[String(subject || "").trim().toLowerCase()];
  const isEnabled = NARRATED_GRADES.has(grade) && Boolean(narrationConfig);
  const speechSupported =
    typeof window !== "undefined" &&
    "speechSynthesis" in window &&
    "SpeechSynthesisUtterance" in window;

  const welcomeStorageKey = `likha-narrator-welcomed:${grade}:${subject}:${chapter}`;
  const [selectedPathId, setSelectedPathId] = useState(
    () => narrationPaths?.[0]?.id || `milestone-${milestoneIndex}`
  );
  const [showWelcome, setShowWelcome] = useState(() => {
    try {
      return window.localStorage.getItem(welcomeStorageKey) !== "true";
    } catch {
      return true;
    }
  });
  const [welcomeLoading, setWelcomeLoading] = useState(false);
  const [status, setStatus] = useState("idle");
  const [mouthFrame, setMouthFrame] = useState("a");
  const [loadingMessageIndex, setLoadingMessageIndex] = useState(0);
  const [rate, setRate] = useState(1.05);
  const utteranceRef = useRef(null);
  const audioRef = useRef(null);
  const intervalRef = useRef(null);
  const narrationRequestRef = useRef(0);

  const selectedPath =
    narrationPaths?.find((path) => path.id === selectedPathId) ||
    narrationPaths?.[0] ||
    {
      id: `milestone-${milestoneIndex}`,
      label: milestone?.title || "Lesson section",
      milestone,
      milestoneIndex,
      narrationPath: "milestone",
    };
  const selectedMilestone = selectedPath.milestone || milestone;
  const selectedMilestoneIndex =
    selectedPath.milestoneIndex ?? milestoneIndex;
  const narrationText = useMemo(
    () => selectedPath.text || narrationTextForMilestone(selectedMilestone),
    [selectedPath.text, selectedMilestone]
  );

  const isSpeaking = status === "speaking";
  const isPaused = status === "paused";
  const isQuestion = /quick check|question|think|why|how/i.test(
    `${selectedPath.label || ""} ${narrationText}`
  );

  const avatarSource = isSpeaking
    ? mouthFrame === "a"
      ? speakingA
      : speakingO
    : status === "loading" || status === "complete"
      ? explaining
      : isQuestion
        ? question
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
    utterance.lang = narrationConfig.language;
    utterance.rate = rate;
    utterance.pitch = 1.08;

    const preferredVoice = findPreferredVoice(narrationConfig);
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
        milestoneIndex: selectedMilestoneIndex,
        narrationPath: selectedPath.narrationPath || "milestone",
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
    setSelectedPathId(narrationPaths?.[0]?.id || `milestone-${milestoneIndex}`);
    try {
      setShowWelcome(window.localStorage.getItem(welcomeStorageKey) !== "true");
    } catch {
      setShowWelcome(true);
    }
  }, [welcomeStorageKey, narrationPaths]);

  useEffect(() => {
    if (status !== "loading") return undefined;

    setLoadingMessageIndex(0);
    const loadingMessageTimer = window.setInterval(() => {
      setLoadingMessageIndex(
        (current) => (current + 1) % LOADING_MESSAGES.length
      );
    }, 4200);

    return () => window.clearInterval(loadingMessageTimer);
  }, [status]);

  useEffect(
    () => () => {
      cancelNarration();
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );

  function dismissWelcome() {
    setWelcomeLoading(false);
    setShowWelcome(false);
    try {
      window.localStorage.setItem(welcomeStorageKey, "true");
    } catch {
      // The welcome is still dismissible if browser storage is unavailable.
    }
  }

  async function speakWelcome() {
    if (welcomeLoading) return;
    setWelcomeLoading(true);

    const welcomeText =
      narrationConfig.language === "hi-IN"
        ? "नमस्ते! मैं लिखा हूँ। मैं इस पाठ को एक-एक भाग करके आपको पढ़कर सुना सकती हूँ।"
        : "Hello! I’m Likha. I can read this lesson aloud, one chapter path at a time.";

    try {
      const result = await getChapterNarration({
        grade,
        mode,
        subject,
        chapter,
        milestoneIndex: 0,
        narrationPath: "welcome",
      });

      if (result?.success && result.audio_url) {
        const audio = new Audio(result.audio_url);
        audio.onplay = () => setWelcomeLoading(false);
        audio.onended = dismissWelcome;
        audio.onerror = () => {
          setWelcomeLoading(false);
          if (!speechSupported) {
            dismissWelcome();
            return;
          }
          const utterance = new window.SpeechSynthesisUtterance(welcomeText);
          utterance.lang = narrationConfig.language;
          utterance.rate = 1;
          utterance.pitch = 1.05;
          utterance.voice = findWelcomeVoice(narrationConfig);
          utterance.onend = dismissWelcome;
          utterance.onerror = dismissWelcome;
          window.speechSynthesis.speak(utterance);
        };
        await audio.play();
        return;
      }
    } catch {
      // Fall through to browser speech when neural welcome audio is unavailable.
    }

    if (!speechSupported) {
      dismissWelcome();
      return;
    }

    setWelcomeLoading(false);
    const utterance = new window.SpeechSynthesisUtterance(welcomeText);
    utterance.lang = narrationConfig.language;
    utterance.rate = 1;
    utterance.pitch = 1.05;
    utterance.voice = findWelcomeVoice(narrationConfig);
    utterance.onend = dismissWelcome;
    utterance.onerror = dismissWelcome;
    window.speechSynthesis.speak(utterance);
  }

  function chooseNarrationPath(event) {
    const pathId = event.target.value;
    if (pathId === selectedPathId) return;
    cancelNarration();
    setStatus("idle");
    setSelectedPathId(pathId);
  }

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
      <div
        className={status === "loading" ? "likha-narrator-avatar is-preparing" : "likha-narrator-avatar"}
        style={{ alignSelf: "stretch", minHeight: 150, display: "flex", alignItems: "flex-end", justifyContent: "center" }}
      >
        <img
          src={avatarSource}
          alt={isSpeaking ? "Likha is narrating this lesson section" : status === "loading" ? "Likha is preparing your narration" : "Likha, your lesson guide"}
          style={{
            width: "100%",
            maxWidth: 170,
            maxHeight: 180,
            objectFit: "contain",
            objectPosition: "bottom center",
            filter: isSpeaking || status === "loading" ? "drop-shadow(0 7px 8px rgba(37, 99, 235, .16))" : undefined,
            transition: "filter .2s ease",
          }}
        />
      </div>

      <div style={{ minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 5 }}>
          <Volume2 size={17} color="var(--likha-narrator-accent, #2563eb)" aria-hidden="true" />
          <strong style={{ fontSize: ".98rem" }}>Listen with Likha</strong>
        </div>

        {showWelcome ? (
          <div
            className="likha-narrator-preparing"
            aria-label="Likha has a welcome message"
            style={{ marginTop: 0, marginBottom: 10 }}
          >
            <div>
              <button
                type="button"
                onClick={speakWelcome}
                disabled={welcomeLoading}
                aria-pressed={welcomeLoading}
                style={{ padding: "7px 11px", border: "none", borderRadius: 7, background: "var(--likha-narrator-accent, #2563eb)", color: "#fff", cursor: welcomeLoading ? "wait" : "pointer", font: "inherit", fontSize: ".8rem", fontWeight: 700, opacity: welcomeLoading ? 0.72 : 1 }}
              >
                {welcomeLoading ? "Getting Likha ready…" : "Tap to hear Likha’s welcome"}
              </button>
            </div>
          </div>
        ) : (
          <p style={{ margin: "0 0 10px", fontSize: ".85rem", color: "var(--muted, #64748b)", lineHeight: 1.45 }}>
            Choose one chapter path at a time. Likha will create audio only when you press Listen.
          </p>
        )}

        {narrationPaths?.length > 1 && (
          <label style={{ display: "block", marginBottom: 10, fontSize: ".8rem", color: "var(--muted, #64748b)" }}>
            Narrate this chapter path
            <select
              value={selectedPath.id}
              onChange={chooseNarrationPath}
              aria-label="Chapter path to narrate"
              style={{ display: "block", width: "100%", marginTop: 4, padding: "7px 8px", borderRadius: 8, border: "1px solid var(--border, #cbd5e1)", background: "var(--panel, #fff)", color: "var(--text, #0f172a)", font: "inherit" }}
            >
              {narrationPaths.map((path, index) => (
                <option key={path.id} value={path.id}>
                  {index + 1}. {path.label}
                </option>
              ))}
            </select>
          </label>
        )}

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

        {status === "loading" && (
          <div className="likha-narrator-preparing" role="status" aria-live="polite">
            <span className="likha-narrator-preparing-dots" aria-hidden="true">
              <i />
              <i />
              <i />
            </span>
            <div>
              <strong>Getting Likha ready</strong>
              <p key={loadingMessageIndex}>
                {LOADING_MESSAGES[loadingMessageIndex]}
              </p>
              <small>This can take a few moments for a new lesson section.</small>
            </div>
          </div>
        )}

        {status !== "idle" && status !== "loading" && (
          <p aria-live="polite" style={{ margin: "9px 0 0", fontSize: ".76rem", color: status === "error" ? "var(--likha-narrator-error, #b91c1c)" : "var(--muted, #64748b)" }}>
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
