import { Mic, MicOff, Send } from "lucide-react";

function LikhaVoiceTutorComposer({
  question,
  onQuestionChange,
  onSubmit,
  asking,
  suggestions,
  onSuggestionSelect,
  language,
  onLanguageChange,
  recognitionState,
  recognitionMessage,
  onVoiceInput,
}) {
  const voiceAvailable = recognitionState !== "unsupported";
  const recording = recognitionState === "recording";

  return (
    <section className="premium-section" aria-labelledby="likha-question-heading">
      <div className="composer-header">
        <div>
          <p className="eyebrow">Ask Likha</p>
          <h3 id="likha-question-heading">What would you like Likha to explain?</h3>
          <p>Type your academic question, or speak it to send it directly to Likha when listening stops.</p>
        </div>
      </div>

      <textarea
        aria-label="Your question for Likha"
        rows="4"
        value={question}
        onChange={(event) => onQuestionChange(event.target.value)}
        onKeyDown={(event) => {
          if ((event.metaKey || event.ctrlKey) && event.key === "Enter") onSubmit();
        }}
        placeholder="Example: Why is a shadow dark?"
        disabled={asking}
      />

      <div className="likha-voice-composer-actions" style={{ display: "flex", alignItems: "stretch", gap: 12, marginTop: 12, minHeight: 56, flexWrap: "nowrap", overflowX: "auto", overflowY: "hidden", paddingBottom: 2 }}>
        <button
          type="button"
          className="primary-btn"
          onClick={onSubmit}
          disabled={asking || !question.trim()}
          style={{ flex: "0 0 auto", alignSelf: "stretch", height: 56, minHeight: 56, margin: 0, boxSizing: "border-box", display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8, padding: "0 20px", lineHeight: 1, verticalAlign: "middle", whiteSpace: "nowrap" }}
        >
          <Send size={16} /> {asking ? "Likha is checking…" : "Ask Likha"}
        </button>

        <div style={{ flex: "0 0 auto", alignSelf: "stretch", height: 56, minHeight: 56, boxSizing: "border-box", display: "inline-flex", alignItems: "center", gap: 8, padding: "0 2px 0 10px", borderLeft: "1px solid var(--border,#d1d5db)" }}>
          <label htmlFor="likha-voice-language" style={{ fontSize: ".8rem", fontWeight: 700, color: "var(--text-muted,#64748b)", whiteSpace: "nowrap" }}>
            Voice language
          </label>
          <select
            id="likha-voice-language"
            aria-label="Voice input language"
            value={language}
            onChange={(event) => onLanguageChange(event.target.value)}
            disabled={asking || recording}
            style={{ height: 56, minWidth: 142, boxSizing: "border-box", padding: "0 32px 0 11px", borderRadius: 10, border: "1px solid var(--border,#cbd5e1)", background: "var(--panel,#fff)", color: "var(--text,#334155)", font: "inherit", fontWeight: 600 }}
          >
            <option value="en-IN">English</option>
            <option value="hi-IN">Hindi</option>
          </select>
        </div>

        <button
          type="button"
          onClick={onVoiceInput}
          disabled={asking || !voiceAvailable}
          aria-pressed={recording}
          title={voiceAvailable ? "Speak your question" : "Voice input is not available in this browser"}
          style={{
            alignSelf: "stretch", height: 56, minHeight: 56, margin: 0, boxSizing: "border-box", display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8, padding: "0 18px", lineHeight: 1, verticalAlign: "middle",
            borderRadius: 8, border: `1px solid ${recording ? "#dc2626" : "rgba(99,102,241,.35)"}`,
            background: recording ? "rgba(220,38,38,.1)" : "rgba(99,102,241,.08)",
            color: recording ? "#b91c1c" : "#4f46e5", fontWeight: 700, cursor: voiceAvailable ? "pointer" : "not-allowed",
            flex: "0 0 auto", opacity: voiceAvailable ? 1 : .55, whiteSpace: "nowrap",
          }}
        >
          {recording ? <MicOff size={16} /> : <Mic size={16} />}
          {recording ? "Stop listening" : "Speak your question"}
        </button>
      </div>

      <p role="status" aria-live="polite" style={{ minHeight: 20, margin: "10px 0 0", fontSize: ".79rem", color: recognitionState === "error" ? "#b91c1c" : "var(--text-muted,#64748b)" }}>
        {recognitionMessage}
      </p>

      {suggestions.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <p style={{ margin: "0 0 7px", fontSize: ".8rem", fontWeight: 700, color: "var(--text-muted,#64748b)" }}>
            Suggested questions
          </p>
          <div className="prompt-chip-row">
            {suggestions.map((suggestion) => (
              <button
                key={suggestion.id}
                type="button"
                className="followup-chip"
                disabled={asking}
                onClick={() => onSuggestionSelect(suggestion)}
              >
                {suggestion.question}
              </button>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

export default LikhaVoiceTutorComposer;
