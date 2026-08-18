/**
 * FeedbackPromptContext.jsx — contextual "share feedback" prompt.
 *
 * Deliberately NOT a persistent floating button. Pages call
 * `triggerFeedbackPrompt(eventName, context)` right after a user completes
 * a meaningful action (lesson, mock test, doubt answered, formula sheet
 * used, exam prep session, a Learn More resource). The backend decides
 * whether this user is a "serious user" due for a prompt (activity
 * threshold + a cooldown since they were last shown one) — the frontend
 * only asks once per session and remembers the answer so repeated
 * completions in one sitting don't hammer the eligibility endpoint or
 * show the card more than once.
 *
 * Usage anywhere in the tree:
 *   import { useFeedbackPrompt } from "./useFeedbackPrompt";
 *   const { triggerFeedbackPrompt } = useFeedbackPrompt();
 *   triggerFeedbackPrompt("lesson_completed", { grade, subject, chapter });
 */
import { useCallback, useRef, useState } from "react";
import { getFeedbackEligibility, markFeedbackPromptShown } from "../api/feedback";
import FeedbackModal from "../components/FeedbackModal";
import { FeedbackPromptContext } from "./feedbackPromptContextObject";

export function FeedbackPromptProvider({ children, user }) {
  const [prompt, setPrompt] = useState(null); // { triggerEvent, context } | null
  const [modalOpen, setModalOpen] = useState(false);
  const [modalContext, setModalContext] = useState({});
  const session = useRef({ checked: false, eligible: false, shownThisSession: false });

  const triggerFeedbackPrompt = useCallback(async (triggerEvent, context = {}) => {
    if (!user?.id) return;
    const s = session.current;
    if (s.shownThisSession) return;
    if (s.checked && !s.eligible) return;

    if (!s.checked) {
      try {
        const res = await getFeedbackEligibility();
        s.checked = true;
        s.eligible = !!res?.eligible;
      } catch {
        s.checked = true;
        s.eligible = false;
        return;
      }
    }
    if (!s.eligible) return;

    s.shownThisSession = true;
    setPrompt({ triggerEvent, context });
    markFeedbackPromptShown().catch(() => { /* cooldown restarts server-side next time regardless */ });
  }, [user?.id]);

  function openModal() {
    setModalContext({ ...prompt?.context, triggerEvent: prompt?.triggerEvent });
    setModalOpen(true);
    setPrompt(null);
  }
  function dismissPrompt() {
    setPrompt(null);
  }
  function closeModal() {
    setModalOpen(false);
  }

  return (
    <FeedbackPromptContext.Provider value={{ triggerFeedbackPrompt }}>
      {children}

      {prompt && (
        <div
          data-testid="feedback-prompt-card"
          role="dialog"
          aria-label="Share feedback"
          style={{
            position: "fixed", bottom: 24, right: 24, zIndex: 1500,
            background: "var(--panel,#fff)", border: "1px solid var(--border,#dde2f0)",
            borderRadius: 14, padding: "16px 18px", maxWidth: 300,
            boxShadow: "0 12px 32px rgba(79,70,229,.12),0 2px 8px rgba(15,23,42,.08)",
            fontFamily: "inherit",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
            <p style={{ margin: 0, fontSize: ".85rem", fontWeight: 600, color: "var(--text,#0f172a)" }}>
              🙂 Got 30 seconds for quick feedback?
            </p>
            <button onClick={dismissPrompt} aria-label="Dismiss"
              data-testid="feedback-prompt-dismiss"
              style={{ background: "none", border: "none", cursor: "pointer", fontSize: "1rem", color: "#94a3b8", lineHeight: 1, flexShrink: 0 }}>
              ✕
            </button>
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
            <button onClick={openModal} data-testid="feedback-prompt-share"
              style={{ background: "#4f46e5", color: "#fff", border: "none", borderRadius: 8,
                padding: "7px 14px", fontWeight: 700, fontSize: ".78rem", cursor: "pointer", fontFamily: "inherit" }}>
              Share feedback
            </button>
            <button onClick={dismissPrompt} data-testid="feedback-prompt-not-now"
              style={{ background: "none", border: "none", color: "#94a3b8", fontSize: ".78rem",
                fontWeight: 600, cursor: "pointer", fontFamily: "inherit" }}>
              Not now
            </button>
          </div>
        </div>
      )}

      <FeedbackModal open={modalOpen} onClose={closeModal} context={modalContext} user={user} />
    </FeedbackPromptContext.Provider>
  );
}
