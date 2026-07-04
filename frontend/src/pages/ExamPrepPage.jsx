/**
 * ExamPrepPage.jsx — JEE / NEET / CUET Exam Prep Center
 *
 * Access: admin role OR akshita.teststudent (pre-launch test access)
 * Data source: Supabase 2 RAG — PYQ papers uploaded via upload_nta_pyq_rag.py
 */

import { useEffect, useState, useCallback } from "react";
import { Loader } from "lucide-react";

const EXAMS = {
  jee: {
    label: "JEE Main", icon: "📐",
    description: "Joint Entrance Examination — Engineering (IITs, NITs, IIITs)",
    color: "#6366f1",
  },
  neet: {
    label: "NEET UG", icon: "🔬",
    description: "National Eligibility cum Entrance Test — Medical (MBBS, BDS)",
    color: "#10b981",
    comingSoon: true,
  },
  cuet: {
    label: "CUET UG", icon: "🏛️",
    description: "Common University Entrance Test — Central Universities",
    color: "#f59e0b",
    comingSoon: true,
  },
};


const TEST_ACCESS_USERS = new Set(["akshita.teststudent"]);

function hasAccess(user) {
  if (!user) return false;
  if (user.role === "admin") return true;
  return TEST_ACCESS_USERS.has(user.username);
}

// ── Sub-components ────────────────────────────────────────────────────────────

function PaperCard({ paper, selected, onClick }) {
  const label = paper.label || paper.chapter.replace("PYQ: ", "");
  // Parse date from label e.g. "B Tech 2nd Apr 2026 Shift 1"
  const dateMatch = label.match(/(\d+\w*\s+\w+\s+\d{4})/);
  const shiftMatch = label.match(/(Shift\s*\d+)/i);
  const date = dateMatch ? dateMatch[1] : label.substring(0, 15);
  const shift = shiftMatch ? shiftMatch[1] : "";

  return (
    <div
      onClick={onClick}
      style={{
        background: selected ? "rgba(99,102,241,.12)" : "var(--panel,#1e293b)",
        border: `1px solid ${selected ? "#6366f1" : "var(--border,#334155)"}`,
        borderRadius: 10, padding: "10px 12px", cursor: "pointer",
        transition: "all .12s",
      }}
    >
      <div style={{ fontSize: ".62rem", color: "var(--muted,#64748b)" }}>{date}</div>
      <div style={{ fontSize: ".78rem", fontWeight: 700, color: "#e2e8f0", margin: "3px 0" }}>
        {shift || label.substring(0, 20)}
      </div>
      {selected && (
        <div style={{ fontSize: ".58rem", background: "rgba(99,102,241,.2)", color: "#a5b4fc", padding: "1px 6px", borderRadius: 6, display: "inline-block" }}>
          Selected ✓
        </div>
      )}
    </div>
  );
}

function ChunkCard({ chunk, selected, onClick }) {
  const text = chunk.chunk_text || "";
  const preview = text.length > 120 ? text.substring(0, 120) + "…" : text;

  return (
    <div
      onClick={onClick}
      style={{
        padding: "11px 15px",
        borderBottom: "1px solid var(--surface,#0f172a)",
        cursor: "pointer",
        background: selected ? "rgba(99,102,241,.09)" : "transparent",
        borderLeft: selected ? "3px solid #6366f1" : "3px solid transparent",
        transition: "background .1s",
      }}
    >
      <div style={{ fontSize: ".62rem", color: "var(--muted,#64748b)", marginBottom: 3 }}>
        Chunk {chunk.chunk_index + 1}
      </div>
      <div style={{ fontSize: ".77rem", color: "#cbd5e1", lineHeight: 1.45 }}>{preview}</div>
    </div>
  );
}

function ExplanationPanel({ chunk, paper, user, apiBase }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [followUp, setFollowUp] = useState("");
  const [followUpResult, setFollowUpResult] = useState(null);
  const [followUpLoading, setFollowUpLoading] = useState(false);

  // Auto-explain when chunk changes
  useEffect(() => {
    if (!chunk || !user?.accessToken) return;
    setResult(null);
    setFollowUpResult(null);
    setFollowUp("");

    async function explain() {
      setLoading(true);
      try {
        const r = await fetch(`${apiBase}/api/exam-prep/explain`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${user.accessToken}`,
          },
          body: JSON.stringify({
            question_text: chunk.chunk_text,
            subject: paper?.subject || "Physics",
            exam: "JEE Main",
          }),
        });
        const data = await r.json();
        if (data.success) setResult(data);
      } catch { /* ignore */ }
      finally { setLoading(false); }
    }
    explain();
  }, [chunk?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleAskAI(e) {
    e.preventDefault();
    if (!followUp.trim() || !user?.accessToken) return;
    setFollowUpLoading(true);
    try {
      const r = await fetch(`${apiBase}/api/exam-prep/explain`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${user.accessToken}`,
        },
        body: JSON.stringify({
          question_text: chunk.chunk_text,
          subject: paper?.subject || "Physics",
          exam: "JEE Main",
          follow_up: followUp,
        }),
      });
      const data = await r.json();
      if (data.success) setFollowUpResult(data.raw || data.solution);
    } catch { /* ignore */ }
    finally { setFollowUpLoading(false); }
  }

  if (!chunk) {
    return (
      <div style={{ padding: 20, color: "var(--muted,#64748b)", fontSize: ".78rem", textAlign: "center" }}>
        <div style={{ fontSize: "2rem", marginBottom: 10 }}>🤖</div>
        Select a question chunk from the left panel to get an AI explanation.
      </div>
    );
  }

  return (
    <div style={{ padding: 15, fontSize: ".75rem", lineHeight: 1.6, color: "#cbd5e1", overflowY: "auto" }}>
      {/* Question display */}
      <div style={{ background: "var(--surface,#0f172a)", border: "1px solid var(--border,#334155)", borderRadius: 7, padding: 10, marginBottom: 12, fontStyle: "italic", color: "var(--muted,#94a3b8)", fontSize: ".72rem", lineHeight: 1.5 }}>
        {chunk.chunk_text.length > 300 ? chunk.chunk_text.substring(0, 300) + "…" : chunk.chunk_text}
      </div>

      {loading && (
        <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--muted,#64748b)" }}>
          <Loader size={14} style={{ animation: "spin 1s linear infinite" }} />
          Generating explanation…
          <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
        </div>
      )}

      {result && !loading && (
        <>
          {result.correct_answer && (
            <div style={{ background: "rgba(34,197,94,.08)", border: "1px solid rgba(34,197,94,.2)", borderRadius: 7, padding: "8px 10px", marginBottom: 10, fontSize: ".73rem" }}>
              <strong style={{ color: "#4ade80" }}>✓ Answer: </strong>
              <span style={{ color: "#cbd5e1" }}>{result.correct_answer}</span>
            </div>
          )}

          {result.solution && (
            <>
              <div style={{ fontSize: ".7rem", fontWeight: 700, color: "#a5b4fc", marginBottom: 6 }}>Step-by-step solution:</div>
              <div style={{ background: "rgba(99,102,241,.05)", border: "1px solid rgba(99,102,241,.15)", borderRadius: 7, padding: 10, fontSize: ".72rem", lineHeight: 1.65, whiteSpace: "pre-wrap" }}>
                {result.solution}
              </div>
            </>
          )}

          {result.tip && (
            <div style={{ background: "rgba(245,158,11,.06)", border: "1px solid rgba(245,158,11,.2)", borderRadius: 7, padding: "7px 10px", marginTop: 10, fontSize: ".7rem" }}>
              <strong style={{ color: "#fbbf24" }}>💡 JEE Tip: </strong>
              <span style={{ color: "#cbd5e1" }}>{result.tip}</span>
            </div>
          )}
        </>
      )}

      {/* Follow-up */}
      {result && !loading && (
        <>
          <form onSubmit={handleAskAI} style={{ display: "flex", gap: 6, marginTop: 12 }}>
            <input
              value={followUp}
              onChange={e => setFollowUp(e.target.value)}
              placeholder="Ask AI: Why does this formula apply here?"
              style={{ flex: 1, background: "var(--surface,#0f172a)", border: "1px solid var(--border,#334155)", borderRadius: 6, padding: "6px 9px", color: "#f1f5f9", fontSize: ".72rem", fontFamily: "inherit" }}
            />
            <button
              type="submit"
              disabled={followUpLoading || !followUp.trim()}
              style={{ padding: "6px 11px", background: "#6366f1", border: "none", borderRadius: 6, color: "#fff", fontWeight: 700, fontSize: ".72rem", cursor: "pointer", opacity: followUpLoading ? .6 : 1 }}
            >
              {followUpLoading ? "…" : "Ask ✦"}
            </button>
          </form>

          {followUpResult && (
            <div style={{ background: "rgba(99,102,241,.06)", border: "1px solid rgba(99,102,241,.18)", borderRadius: 7, padding: 10, marginTop: 8, fontSize: ".72rem", lineHeight: 1.6, whiteSpace: "pre-wrap" }}>
              {followUpResult}
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ExamPrepPage({ user }) {
  const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
  const [selectedExam, setSelectedExam] = useState("jee");
  const [papers, setPapers] = useState([]);
  const [loadingPapers, setLoadingPapers] = useState(false);
  const [selectedPaper, setSelectedPaper] = useState(null);
  const [chunks, setChunks] = useState([]);
  const [loadingChunks, setLoadingChunks] = useState(false);
  const [selectedChunk, setSelectedChunk] = useState(null);

  const isTestUser = TEST_ACCESS_USERS.has(user?.username);

  const loadPapers = useCallback(async (exam) => {
    if (!user?.accessToken) return;
    setLoadingPapers(true);
    setPapers([]);
    setSelectedPaper(null);
    setChunks([]);
    setSelectedChunk(null);
    try {
      const r = await fetch(`${API_BASE}/api/exam-prep/papers?exam=${exam}`, {
        headers: { Authorization: `Bearer ${user.accessToken}` },
      });
      const data = await r.json();
      if (data.success) setPapers(data.papers || []);
    } catch { /* ignore */ }
    finally { setLoadingPapers(false); }
  }, [user, API_BASE]);

  useEffect(() => { loadPapers(selectedExam); }, [selectedExam]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!hasAccess(user)) {
    return (
      <div className="premium-page">
        <section className="premium-section">
          <div className="error-box">You do not have access to this page.</div>
        </section>
      </div>
    );
  }

  async function selectPaper(paper) {
    setSelectedPaper(paper);
    setSelectedChunk(null);
    setChunks([]);
    setLoadingChunks(true);
    try {
      const r = await fetch(`${API_BASE}/api/exam-prep/paper/${paper.id}/chunks?limit=50`, {
        headers: { Authorization: `Bearer ${user.accessToken}` },
      });
      const data = await r.json();
      if (data.success) setChunks(data.chunks || []);
    } catch { /* ignore */ }
    finally { setLoadingChunks(false); }
  }

  return (
    <div className="premium-page">
      <section className="premium-section">
        <div className="premium-header">
          <p className="eyebrow">Grade 11 & 12 — Competitive Exam Preparation</p>
          <h2>🎯 Exam Prep Center</h2>
          <p>Practice with real previous year papers and get AI step-by-step explanations.</p>
        </div>

        {/* Test user banner */}
        <div style={{
          background: isTestUser ? "rgba(99,102,241,.07)" : "rgba(245,158,11,.07)",
          border: `1px solid ${isTestUser ? "rgba(99,102,241,.3)" : "rgba(245,158,11,.3)"}`,
          borderRadius: 10, padding: "10px 14px", fontSize: ".82rem", marginBottom: 20,
          display: "flex", alignItems: "center", gap: 9,
        }}>
          <span style={{ fontSize: "1.1rem" }}>{isTestUser ? "🧪" : "🔒"}</span>
          <div>
            {isTestUser
              ? <><strong>Test Access.</strong> Early access to Grade 11 & 12 content — not yet live for all students
.</>
              : <><strong>Phase 1 — Admin Preview.</strong> Grade 11 & 12 not yet visible to students.</>
            }
          </div>
        </div>

        {/* Exam tabs */}
        <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
          {Object.entries(EXAMS).map(([key, e]) => (
            <button key={key} onClick={() => !e.comingSoon && setSelectedExam(key)}
              style={{ padding: "8px 16px", borderRadius: 9, border: `2px solid ${selectedExam === key ? e.color : "var(--border,#334155)"}`, background: selectedExam === key ? `${e.color}14` : "var(--panel,#1e293b)", color: selectedExam === key ? e.color : "var(--muted,#94a3b8)", fontWeight: 700, fontSize: ".8rem", cursor: e.comingSoon ? "default" : "pointer", fontFamily: "inherit", opacity: e.comingSoon ? .55 : 1 }}>
              {e.icon} {e.label}{e.comingSoon && <span style={{ fontSize: ".58rem", background: "rgba(245,158,11,.2)", color: "#fbbf24", padding: "1px 5px", borderRadius: 6, marginLeft: 5 }}>Soon</span>}
            </button>
          ))}
        </div>

        {/* Stats */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 10, marginBottom: 20 }}>
          <div style={{ background: "var(--panel,#1e293b)", border: "1px solid var(--border,#334155)", borderRadius: 9, padding: "11px 14px" }}>
            <div style={{ fontSize: "1.4rem", fontWeight: 800 }}>{papers.length}</div>
            <div style={{ fontSize: ".65rem", color: "var(--muted,#64748b)" }}>Papers Available</div>
          </div>
          <div style={{ background: "var(--panel,#1e293b)", border: "1px solid var(--border,#334155)", borderRadius: 9, padding: "11px 14px" }}>
            <div style={{ fontSize: "1.4rem", fontWeight: 800 }}>Apr 2026</div>
            <div style={{ fontSize: ".65rem", color: "var(--muted,#64748b)" }}>Latest Session</div>
          </div>
          <div style={{ background: "var(--panel,#1e293b)", border: "1px solid var(--border,#334155)", borderRadius: 9, padding: "11px 14px" }}>
            <div style={{ fontSize: "1.4rem", fontWeight: 800 }}>PCM</div>
            <div style={{ fontSize: ".65rem", color: "var(--muted,#64748b)" }}>Physics · Chem · Maths</div>
          </div>
        </div>
      </section>

      {/* Paper selector */}
      <section className="premium-section" style={{ paddingTop: 0 }}>
        <div style={{ fontSize: ".7rem", fontWeight: 700, color: "var(--muted,#64748b)", textTransform: "uppercase", letterSpacing: ".05em", marginBottom: 10 }}>
          Select Paper
        </div>
        {loadingPapers ? (
          <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--muted,#64748b)", fontSize: ".8rem" }}>
            <Loader size={14} style={{ animation: "spin 1s linear infinite" }} />
            Loading papers…
            <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
          </div>
        ) : papers.length === 0 ? (
          <div style={{ color: "var(--muted,#64748b)", fontSize: ".8rem", padding: "12px 0" }}>
            No papers available for this exam yet.
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(160px,1fr))", gap: 8, marginBottom: 20 }}>
            {papers.map(p => (
              <PaperCard key={p.id} paper={p} selected={selectedPaper?.id === p.id} onClick={() => selectPaper(p)} />
            ))}
          </div>
        )}
      </section>

      {/* Content: chunks list + AI panel */}
      {selectedPaper && (
        <section className="premium-section" style={{ paddingTop: 0 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 360px", gap: 14 }}>

            {/* Chunks list */}
            <div style={{ background: "var(--panel,#1e293b)", border: "1px solid var(--border,#334155)", borderRadius: 11, overflow: "hidden" }}>
              <div style={{ padding: "10px 14px", borderBottom: "1px solid var(--border,#334155)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div>
                  <div style={{ fontSize: ".82rem", fontWeight: 700 }}>{selectedPaper.label}</div>
                  <div style={{ fontSize: ".65rem", color: "var(--muted,#64748b)", marginTop: 2 }}>{selectedPaper.subject} · {chunks.length} chunks</div>
                </div>
              </div>
              <div style={{ maxHeight: 420, overflowY: "auto" }}>
                {loadingChunks ? (
                  <div style={{ padding: 16, display: "flex", alignItems: "center", gap: 8, color: "var(--muted,#64748b)", fontSize: ".78rem" }}>
                    <Loader size={14} style={{ animation: "spin 1s linear infinite" }} />
                    Loading questions…
                  </div>
                ) : chunks.length === 0 ? (
                  <div style={{ padding: 16, color: "var(--muted,#64748b)", fontSize: ".78rem" }}>No content found for this paper.</div>
                ) : (
                  chunks.map(ch => (
                    <ChunkCard key={ch.id} chunk={ch} selected={selectedChunk?.id === ch.id} onClick={() => setSelectedChunk(ch)} />
                  ))
                )}
              </div>
            </div>

            {/* AI explanation panel */}
            <div style={{ background: "var(--panel,#1e293b)", border: "1px solid var(--border,#334155)", borderRadius: 11, overflow: "hidden", display: "flex", flexDirection: "column" }}>
              <div style={{ padding: "10px 14px", borderBottom: "1px solid var(--border,#334155)", background: "rgba(99,102,241,.06)", display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{ width: 24, height: 24, borderRadius: "50%", background: "linear-gradient(135deg,#6366f1,#10b981)", display: "grid", placeItems: "center", fontSize: ".75rem", flexShrink: 0 }}>🤖</div>
                <div style={{ fontSize: ".8rem", fontWeight: 700, color: "#a5b4fc" }}>
                  {selectedChunk ? `AI Explanation — Chunk ${selectedChunk.chunk_index + 1}` : "AI Explanation"}
                </div>
              </div>
              <ExplanationPanel chunk={selectedChunk} paper={selectedPaper} user={user} apiBase={API_BASE} />
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
