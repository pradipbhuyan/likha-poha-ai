import { useEffect, useRef, useState } from "react";
import { Pause, Play, RotateCcw, Square, Volume2 } from "lucide-react";

import { speakDoubtAnswer } from "../../api/likhaVoiceTutor";
import idleNeutral from "../../assets/avatar/likha/idle-neutral.png";
import speakingA from "../../assets/avatar/likha/speaking-a.png";
import speakingO from "../../assets/avatar/likha/speaking-o.png";
import explaining from "../../assets/avatar/likha/explaining.png";

const FOLLOW_UP_PROMPT = "Do you have a follow-up question? Tap Speak follow-up to continue with Likha.";

function preferredBrowserVoice(language) {
  const voices = window.speechSynthesis?.getVoices?.() || [];
  const languagePattern = new RegExp(`^${language.replace("-", "[-_]")}`, "i");
  const preferredName = language === "hi-IN" ? /\bswara\b/i : /\b(neerja|tara)\b/i;

  return (
    voices.find((voice) => languagePattern.test(voice.lang) && preferredName.test(voice.name)) ||
    voices.find((voice) => languagePattern.test(voice.lang)) ||
    voices.find((voice) => /^en([-_]|$)/i.test(voice.lang)) ||
    null
  );
}

function LikhaVoicePlayer({
  historyId,
  answer,
  language,
  autoPlay = false,
  includeFirstAnswerGreeting = false,
  firstAnswerGreeting = "",
  onStatusChange,
  onFollowUpReady,
}) {
  const [status, setStatus] = useState("idle");
  const [rate, setRate] = useState(1);
  const [mouthFrame, setMouthFrame] = useState("a");
  const audioRef = useRef(null);
  const utteranceRef = useRef(null);
  const intervalRef = useRef(null);
  const animationFrameRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const requestIdRef = useRef(0);
  const firstGreetingPlayedRef = useRef(false);
  const nextSegmentRef = useRef(null);

  const speechSupported =
    typeof window !== "undefined" &&
    "speechSynthesis" in window &&
    "SpeechSynthesisUtterance" in window;
  const isSpeaking = status === "speaking";
  const isPaused = status === "paused";

  const avatar = status === "loading"
    ? explaining
    : isSpeaking
      ? (mouthFrame === "a" ? speakingA : speakingO)
      : idleNeutral;

  function updateStatus(nextStatus) {
    setStatus(nextStatus);
    onStatusChange?.(nextStatus);
  }

  function stopMouthAnimation() {
    window.clearInterval(intervalRef.current);
    intervalRef.current = null;
    window.cancelAnimationFrame(animationFrameRef.current);
    animationFrameRef.current = null;
    analyserRef.current = null;

    if (audioContextRef.current) {
      audioContextRef.current.close?.().catch?.(() => {});
      audioContextRef.current = null;
    }

    setMouthFrame("a");
  }

  function beginTimerMouthAnimation() {
    stopMouthAnimation();
    intervalRef.current = window.setInterval(() => {
      setMouthFrame((frame) => (frame === "a" ? "o" : "a"));
    }, 240);
  }

  function beginAudioReactiveMouthAnimation() {
    // Do not create a MediaElementSource/AudioContext graph for narration
    // playback. Chrome permits only one such source per HTMLAudioElement; a
    // pause → resume cycle previously tore down and recreated that graph,
    // which could leave the UI "speaking" while its audio output was silent.
    // The lightweight timer keeps the avatar expressive without altering the
    // browser's native audio routing or resumability.
    beginTimerMouthAnimation();
  }

  function stop() {
    requestIdRef.current += 1;
    window.speechSynthesis?.cancel?.();
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = "";
      audioRef.current = null;
    }
    nextSegmentRef.current = null;
    utteranceRef.current = null;
    stopMouthAnimation();
    updateStatus("idle");
  }

  function speakWithBrowser(text) {
    if (!speechSupported || !text) {
      updateStatus("error");
      return;
    }

    const utterance = new window.SpeechSynthesisUtterance(text);
    utterance.lang = language;
    utterance.rate = rate;
    utterance.pitch = 1.05;
    utterance.voice = preferredBrowserVoice(language);
    utterance.onstart = () => {
      updateStatus("speaking");
      beginTimerMouthAnimation();
    };
    utterance.onend = () => {
      utteranceRef.current = null;
      stopMouthAnimation();
      updateStatus("complete");
      onFollowUpReady?.();
    };
    utterance.onerror = (event) => {
      utteranceRef.current = null;
      stopMouthAnimation();
      updateStatus(["canceled", "interrupted"].includes(event.error) ? "idle" : "error");
    };

    utteranceRef.current = utterance;
    window.speechSynthesis.speak(utterance);
  }

  async function requestSegment(segmentIndex, includeGreeting) {
    return speakDoubtAnswer({
      historyId,
      language,
      replyStyle: "full_follow_up",
      includeFirstAnswerGreeting: includeGreeting,
      progressive: true,
      segmentIndex,
    });
  }

  function finishNarration(requestId) {
    if (requestId !== requestIdRef.current) return;
    audioRef.current = null;
    nextSegmentRef.current = null;
    stopMouthAnimation();
    updateStatus("complete");
    onFollowUpReady?.();
  }

  async function playSegment(
    result,
    requestId,
    browserFallbackText,
    includeGreetingForStream
  ) {
    if (requestId !== requestIdRef.current) return;

    if (!result?.success || !result.audio_url) {
      speakWithBrowser(browserFallbackText);
      return;
    }

    const audio = new Audio(result.audio_url);
    audio.playbackRate = rate;
    audioRef.current = audio;

    if (result.has_more) {
      nextSegmentRef.current = requestSegment(
        result.next_segment_index,
        includeGreetingForStream
      ).catch(() => null);
    }

    audio.onplay = () => {
      if (requestId !== requestIdRef.current) return;
      updateStatus("speaking");
      beginAudioReactiveMouthAnimation(audio);
    };
    audio.onended = async () => {
      if (requestId !== requestIdRef.current) return;

      // Only await a prefetched segment when this segment explicitly has a
      // successor. The final segment deliberately has no queued request;
      // reusing the previous resolved promise would replay it indefinitely.
      if (!result.has_more) {
        finishNarration(requestId);
        return;
      }

      const nextRequest = nextSegmentRef.current;
      nextSegmentRef.current = null;
      const nextResult = await nextRequest;
      if (requestId !== requestIdRef.current) return;

      if (nextResult) {
        await playSegment(
          nextResult,
          requestId,
          browserFallbackText,
          includeGreetingForStream
        );
      } else {
        // Keep the completed portion intact if a later segment cannot load.
        finishNarration(requestId);
      }
    };
    audio.onerror = () => {
      if (requestId !== requestIdRef.current) return;
      audioRef.current = null;
      stopMouthAnimation();
      speakWithBrowser(browserFallbackText);
    };
    await audio.play();
  }

  async function listen() {
    if (!answer || !historyId) return;

    stop();
    const requestId = requestIdRef.current;
    const useFirstAnswerGreeting =
      includeFirstAnswerGreeting && !firstGreetingPlayedRef.current;
    const browserFallbackText = `${useFirstAnswerGreeting ? `${firstAnswerGreeting} ` : ""}${answer} ${FOLLOW_UP_PROMPT}`;
    if (useFirstAnswerGreeting) firstGreetingPlayedRef.current = true;
    updateStatus("loading");

    try {
      const firstSegment = await requestSegment(0, useFirstAnswerGreeting);
      await playSegment(
        firstSegment,
        requestId,
        browserFallbackText,
        useFirstAnswerGreeting
      );
    } catch {
      if (requestId === requestIdRef.current) {
        speakWithBrowser(browserFallbackText);
      }
    }
  }

  function togglePlayback() {
    if (isSpeaking) {
      if (audioRef.current) audioRef.current.pause();
      else window.speechSynthesis.pause();
      stopMouthAnimation();
      updateStatus("paused");
      return;
    }

    if (isPaused) {
      if (audioRef.current) {
        audioRef.current.play().catch(() => speakWithBrowser(answer));
      } else {
        window.speechSynthesis.resume();
        beginTimerMouthAnimation();
        updateStatus("speaking");
      }
      return;
    }

    listen();
  }

  function changeRate(event) {
    const nextRate = Number(event.target.value);
    setRate(nextRate);
    if (audioRef.current) audioRef.current.playbackRate = nextRate;
    if (utteranceRef.current) stop();
  }

  useEffect(() => stop, []);
  useEffect(() => stop, [historyId]);

  useEffect(() => {
    if (!autoPlay || !historyId || !answer) return undefined;

    // The student initiated this answer by pressing Ask Likha, so begin the
    // requested spoken explanation as soon as its written answer is ready.
    const timer = window.setTimeout(() => {
      listen();
    }, 0);

    return () => window.clearTimeout(timer);
    // `historyId` uniquely identifies each approved answer. Deliberately do
    // not depend on `listen`, which is recreated during player state updates.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [historyId, autoPlay]);

  return (
    <section className="likha-voice-player" aria-label="Listen to Likha" style={{
      display: "grid", gridTemplateColumns: "189px minmax(0, 1fr)", gap: 20,
      alignItems: "center", marginTop: 18, padding: "18px 20px", borderRadius: 14,
      background: "rgba(99,102,241,.08)", border: "1px solid rgba(99,102,241,.24)",
    }}>
      <div className="likha-voice-player-avatar" style={{ alignSelf: "stretch", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <img
          src={avatar}
          alt={isSpeaking ? "Likha is speaking" : status === "loading" ? "Likha is preparing audio" : "Likha, your voice tutor"}
          style={{ width: "100%", maxWidth: 166, maxHeight: 211, objectFit: "contain", objectPosition: "bottom center" }}
        />
      </div>
      <div className="likha-voice-player-content" style={{ minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 5 }}>
          <Volume2 size={17} color="#6366f1" />
          <strong>Listen to Likha</strong>
        </div>
        <p style={{ margin: "0 0 14px", color: "var(--text-muted,#64748b)", fontSize: ".83rem", lineHeight: 1.45 }}>
          Likha starts explaining as soon as your answer is ready. Your written answer stays visible while she speaks.
        </p>
        <div className="likha-voice-player-controls" style={{ display: "flex", alignItems: "stretch", gap: 10, flexWrap: "wrap", minHeight: 56 }}>
          <button type="button" onClick={togglePlayback} disabled={!historyId || status === "loading"} className="primary-btn" style={{ alignSelf: "stretch", height: 56, minHeight: 56, margin: 0, boxSizing: "border-box", display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8, padding: "0 20px", lineHeight: 1, verticalAlign: "middle", whiteSpace: "nowrap" }}>
            {isSpeaking ? <Pause size={18} fill="currentColor" style={{ flexShrink: 0 }} /> : <Play size={18} fill="currentColor" style={{ flexShrink: 0 }} />}
            {status === "loading" ? "Preparing…" : isSpeaking ? "Pause" : isPaused ? "Resume" : status === "complete" ? "Listen again" : "Listen to Likha"}
          </button>
          <button type="button" onClick={stop} disabled={!isSpeaking && !isPaused && status !== "loading"} style={{ alignSelf: "stretch", height: 56, minHeight: 56, margin: 0, boxSizing: "border-box", display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8, padding: "0 18px", lineHeight: 1, verticalAlign: "middle", borderRadius: 10, border: "1px solid var(--border,#cbd5e1)", background: "var(--panel,#fff)", color: "var(--text,#334155)", cursor: "pointer", whiteSpace: "nowrap" }}>
            <Square size={18} fill="currentColor" style={{ flexShrink: 0 }} /> Stop
          </button>
          <label style={{ alignSelf: "stretch", height: 56, minHeight: 56, margin: 0, boxSizing: "border-box", display: "inline-flex", alignItems: "center", gap: 9, padding: "0 0 0 2px", fontSize: ".82rem", fontWeight: 700, color: "var(--text-muted,#64748b)", whiteSpace: "nowrap" }}>
            Speed
            <select value={rate} onChange={changeRate} aria-label="Likha speaking speed" style={{ height: 56, minWidth: 150, boxSizing: "border-box", padding: "0 34px 0 14px", borderRadius: 10, border: "1px solid var(--border,#cbd5e1)", background: "var(--panel,#fff)", color: "var(--text,#334155)", font: "inherit", fontWeight: 600, lineHeight: 1 }}>
              <option value="0.85">0.85×</option>
              <option value="1">1×</option>
              <option value="1.15">1.15×</option>
            </select>
          </label>
          {status === "complete" && (
            <button type="button" onClick={listen} style={{ height: 56, minHeight: 56, display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 7, padding: "0 6px", lineHeight: 1, border: "none", background: "none", color: "#4f46e5", cursor: "pointer", fontWeight: 700, whiteSpace: "nowrap" }}>
              <RotateCcw size={18} style={{ flexShrink: 0 }} /> Replay
            </button>
          )}
        </div>
        <p aria-live="polite" style={{ margin: "12px 0 0", minHeight: 18, fontSize: ".78rem", color: status === "error" ? "#b91c1c" : "var(--text-muted,#64748b)" }}>
          {status === "loading" && "Likha is preparing your explanation…"}
          {status === "speaking" && "Likha is explaining…"}
          {status === "paused" && "Likha is paused."}
          {status === "complete" && "Likha has finished explaining."}
          {status === "error" && "Audio could not start. Please try again."}
          {!historyId && "This answer cannot be read aloud yet. Please ask again."}
        </p>
      </div>
    </section>
  );
}

export default LikhaVoicePlayer;
