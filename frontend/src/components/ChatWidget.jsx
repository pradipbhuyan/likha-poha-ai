import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { Bot, X } from "lucide-react";
import logoImg from "../assets/AITutorLogo1.png";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const INITIAL_MESSAGE = {
  role: "bot",
  text: "Hi! 👋 I'm Likha Poha AI's assistant. Ask me anything about our CBSE tutoring platform — grades, subjects, pricing, or how to get started!",
};

// All FAQ topics from the landing page — preloaded as clickable chips
const QUICK_CHIPS = [
  "Which classes are supported?",
  "How much does it cost?",
  "How do lessons work?",
  "Is there a free trial?",
  "Is the AI safe for children?",
  "What subjects are available?",
  "How many practice questions are available?",
  "What does the Parent Dashboard show?",
  "How do I add a child?",
  "Is there a mobile app?",
  "Does the AI use real NCERT textbooks?",
  "How do I reset my password?",
  "How do I contact support?",
  "Tell me about Likha Poha AI",
];

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([INITIAL_MESSAGE]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState(QUICK_CHIPS);
  const [unread, setUnread] = useState(0);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  // Scroll to bottom when messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, open]);

  // Focus input when opened
  useEffect(() => {
    if (open) {
      inputRef.current?.focus();
      setUnread(0);
    }
  }, [open]);

  async function sendMessage(text) {
    const q = (text || input).trim();
    if (!q || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: q }]);
    setLoading(true);
    setSuggestions([]);

    try {
      const res = await fetch(`${API_BASE}/api/chatbot`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      const data = await res.json();
      const answer = data.answer || "I'm not sure about that. Please email us at likhapohaai@gmail.com";
      setMessages((prev) => [...prev, { role: "bot", text: answer }]);
      setSuggestions(data.suggestions || []);
      if (!open) setUnread((n) => n + 1);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "bot", text: "Sorry, something went wrong. Please try again or email **likhapohaai@gmail.com**." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  return (
    <>
      {/* ── Chat window ── */}
      {open && (
        <div style={{
          position: "fixed", bottom: 88, right: 20, zIndex: 9999,
          width: 360, maxWidth: "calc(100vw - 40px)",
          height: 520, maxHeight: "calc(100vh - 120px)",
          background: "#0f172a", border: "1px solid #334155",
          borderRadius: 16, display: "flex", flexDirection: "column",
          boxShadow: "0 20px 60px rgba(0,0,0,0.5)",
          fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
          overflow: "hidden",
        }}>
          {/* Header */}
          <div style={{
            display: "flex", alignItems: "center", gap: 10,
            padding: "14px 16px", borderBottom: "1px solid #1e293b",
            background: "linear-gradient(135deg, #1e3a5f, #2563eb)",
          }}>
            <img
              src={logoImg}
              alt="Likha Poha AI"
              style={{
                width: 36, height: 36, borderRadius: "50%",
                objectFit: "cover", background: "#fff", flexShrink: 0,
              }}
            />
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 700, fontSize: 14, color: "#fff" }}>Likha Poha AI Assistant</div>
              <div style={{ fontSize: 11, color: "rgba(255,255,255,0.65)" }}>Ask anything about the platform</div>
            </div>
            <button
              onClick={() => setOpen(false)}
              style={{
                background: "rgba(255,255,255,0.12)", border: "none",
                color: "#fff", borderRadius: 8, width: 28, height: 28,
                cursor: "pointer", fontSize: 16, display: "flex",
                alignItems: "center", justifyContent: "center",
              }}>×</button>
          </div>

          {/* Messages */}
          <div style={{
            flex: 1, overflowY: "auto", padding: "14px 14px 8px",
            display: "flex", flexDirection: "column", gap: 10,
          }}>
            {messages.map((msg, i) => (
              <div key={i} style={{
                display: "flex",
                justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
              }}>
                <div style={{
                  maxWidth: "85%",
                  background: msg.role === "user"
                    ? "linear-gradient(135deg, #2563eb, #7c3aed)"
                    : "#1e293b",
                  color: "#f8fafc",
                  borderRadius: msg.role === "user"
                    ? "16px 16px 4px 16px"
                    : "16px 16px 16px 4px",
                  padding: "10px 13px",
                  fontSize: 13, lineHeight: 1.55,
                }}>
                  <ReactMarkdown
                    components={{
                      p: ({ children }) => <p style={{ margin: "0 0 6px" }}>{children}</p>,
                      strong: ({ children }) => <strong style={{ color: "#93c5fd" }}>{children}</strong>,
                      ul: ({ children }) => <ul style={{ margin: "4px 0", paddingLeft: 18 }}>{children}</ul>,
                      li: ({ children }) => <li style={{ marginBottom: 2 }}>{children}</li>,
                      table: ({ children }) => (
                        <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 12, marginTop: 6 }}>
                          {children}
                        </table>
                      ),
                      th: ({ children }) => (
                        <th style={{ background: "#0f172a", padding: "4px 8px", textAlign: "left", borderBottom: "1px solid #334155" }}>
                          {children}
                        </th>
                      ),
                      td: ({ children }) => (
                        <td style={{ padding: "3px 8px", borderBottom: "1px solid #1e293b" }}>{children}</td>
                      ),
                    }}
                  >{msg.text}</ReactMarkdown>
                </div>
              </div>
            ))}
            {loading && (
              <div style={{ display: "flex", justifyContent: "flex-start" }}>
                <div style={{
                  background: "#1e293b", borderRadius: "16px 16px 16px 4px",
                  padding: "10px 14px", display: "flex", gap: 5, alignItems: "center",
                }}>
                  {[0, 1, 2].map((i) => (
                    <div key={i} style={{
                      width: 7, height: 7, borderRadius: "50%",
                      background: "#6366f1",
                      animation: `bounce 1.2s ease-in-out ${i * 0.2}s infinite`,
                    }} />
                  ))}
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Suggestions */}
          {suggestions.length > 0 && !loading && (
            <div style={{
              padding: "6px 14px 2px",
              display: "flex", flexWrap: "wrap", gap: 6,
            }}>
              {suggestions.slice(0, 3).map((s) => (
                <button
                  key={s}
                  onClick={() => sendMessage(s)}
                  style={{
                    background: "rgba(99,102,241,0.12)",
                    border: "1px solid rgba(99,102,241,0.3)",
                    color: "#a5b4fc", borderRadius: 20,
                    padding: "4px 10px", fontSize: 11.5,
                    cursor: "pointer", fontFamily: "inherit",
                    whiteSpace: "nowrap",
                  }}
                >{s}</button>
              ))}
            </div>
          )}

          {/* Input */}
          <div style={{
            padding: "10px 12px", borderTop: "1px solid #1e293b",
            display: "flex", gap: 8, alignItems: "flex-end",
          }}>
            <textarea
              ref={inputRef}
              rows={1}
              value={input}
              placeholder="Ask about Likha Poha AI..."
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              style={{
                flex: 1, background: "#111827", border: "1px solid #334155",
                borderRadius: 10, padding: "9px 12px", color: "#f8fafc",
                fontFamily: "inherit", fontSize: 13, resize: "none",
                outline: "none", lineHeight: 1.4, maxHeight: 80,
                overflowY: "auto",
              }}
            />
            <button
              onClick={() => sendMessage()}
              disabled={!input.trim() || loading}
              style={{
                background: input.trim() && !loading
                  ? "linear-gradient(135deg, #2563eb, #7c3aed)"
                  : "#1e293b",
                border: "none", borderRadius: 10, width: 38, height: 38,
                cursor: input.trim() && !loading ? "pointer" : "not-allowed",
                color: "#fff", fontSize: 16, display: "flex",
                alignItems: "center", justifyContent: "center",
                flexShrink: 0, transition: "background 0.2s",
              }}
            >→</button>
          </div>
        </div>
      )}

      {/* ── Floating button ── */}
      <button
        onClick={() => setOpen((v) => !v)}
        style={{
          position: "fixed", bottom: 20, right: 20, zIndex: 9999,
          width: 58, height: 58, borderRadius: "50%", border: "none",
          background: open
            ? "#334155"
            : "linear-gradient(135deg, #7c3aed, #2563eb)",
          color: "#fff", cursor: "pointer",
          boxShadow: "0 4px 20px rgba(124,58,237,0.45)",
          display: "flex", alignItems: "center", justifyContent: "center",
          transition: "all 0.2s",
        }}
        title="Ask us anything"
      >
        {open ? <X size={22} strokeWidth={2.5} /> : <Bot size={26} strokeWidth={1.8} />}
        {/* Unread badge */}
        {!open && unread > 0 && (
          <span style={{
            position: "absolute", top: 0, right: 0,
            background: "#ef4444", color: "#fff",
            borderRadius: "50%", width: 18, height: 18,
            fontSize: 10, fontWeight: 700,
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>{unread}</span>
        )}
      </button>

      {/* Bounce animation */}
      <style>{`
        @keyframes bounce {
          0%, 60%, 100% { transform: translateY(0); }
          30% { transform: translateY(-6px); }
        }
      `}</style>
    </>
  );
}
