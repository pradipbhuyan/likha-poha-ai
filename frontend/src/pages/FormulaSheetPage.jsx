/**
 * FormulaSheetPage.jsx
 * Syllabus-aligned CBSE Formula Sheet with:
 * - KaTeX math rendering (falls back to monospace)
 * - Collapsed/expanded card UX
 * - Freemium: preview only for Free Tier; paid users can expand for examples/tips
 * - Subject + chapter filter + search
 * Data: GET /api/student/formula-sheets?grade=&subject=
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { authFetch } from "../api/authClient";

// ── KaTeX renderer (lazy) ─────────────────────────────────────────────────────
let katex = null;
async function loadKatex() {
  if (!katex) {
    try {
      const mod = await import("katex");
      katex = mod.default || mod;
      // Load KaTeX CSS once
      if (!document.getElementById("katex-css")) {
        const link = document.createElement("link");
        link.id = "katex-css";
        link.rel = "stylesheet";
        link.href = "https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css";
        document.head.appendChild(link);
      }
    } catch { katex = null; }
  }
  return katex;
}

function MathExpr({ tex, display = false }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!tex || !ref.current) return;
    loadKatex().then(k => {
      if (!k || !ref.current) return;
      try {
        k.render(tex, ref.current, { throwOnError: false, displayMode: display, output: "html" });
      } catch { if (ref.current) ref.current.textContent = tex; }
    });
  }, [tex, display]);
  // Show expression text while KaTeX loads
  return (
    <span ref={ref} style={{ fontFamily: "monospace", fontSize: display ? "1rem" : ".95rem" }}>
      {tex}
    </span>
  );
}

// ── Shared UI helpers ─────────────────────────────────────────────────────────
function Badge({ children, bg = "rgba(139,92,246,0.2)", color = "#a78bfa" }) {
  return <span style={{ fontSize: ".65rem", fontWeight: 700, padding: "1px 7px", borderRadius: 10, background: bg, color, display: "inline-block", marginRight: 3 }}>{children}</span>;
}

function CopyBtn({ text }) {
  const [copied, setCopied] = useState(false);
  return (
    <button onClick={() => { navigator.clipboard.writeText(text).catch(() => {}); setCopied(true); setTimeout(() => setCopied(false), 1500); }}
      title="Copy formula"
      style={{ background: "none", border: "1px solid var(--border,#e5e7eb)", borderRadius: 6, padding: "2px 8px", cursor: "pointer", fontSize: ".68rem", color: copied ? "#22c55e" : "#6366f1", fontFamily: "inherit", fontWeight: 600 }}>
      {copied ? "✓" : "Copy"}
    </button>
  );
}

function UpgradePrompt({ msg = "Unlock this content with Premium." }) {
  return (
    <div data-testid="upgrade-lock-prompt" style={{ background: "var(--surface2,#f8fafc)", border: "1px dashed #cbd5e1", borderRadius: 7, padding: "7px 11px", display: "flex", gap: 7, alignItems: "center", marginTop: 6 }}>
      <span>🔒</span>
      <span style={{ fontSize: ".74rem", color: "var(--text-muted,#64748b)", fontStyle: "italic" }}>{msg}</span>
    </div>
  );
}


// ── MCQ Practice component ─────────────────────────────────────────────────
// Generates 4 original MCQs from formula data (rule-based, no LLM call)
// Shows inline with detailed answer explanations — like Exemplar section

function buildMCQs(formula) {
  // Rule-based MCQ generation from formula content
  // Returns up to 4 questions with options and explanations
  var nm = formula.name || "this formula";
  var ex = formula.expression || "";
  var chapter = formula.chapter || "";
  var desc = formula.description || "";
  var examp = formula.example || "";
  // Generic template MCQs for any formula
  return [
    {
      q: "What does the formula " + nm + " calculate?",
      options: [
        desc || ("The value given by " + ex),
        "The perimeter of a shape",
        "The total surface area only",
        "The number of sides",
      ],
      correct: 0,
      explain: (desc || ("This formula computes " + nm)) + ". The expression is: " + ex,
    },
    {
      q: "Which chapter/topic does " + nm + " belong to?",
      options: [
        chapter || "Geometry",
        "Number Systems",
        "Statistics",
        "Linear Equations",
      ],
      correct: 0,
      explain: nm + " is a key formula in the " + (chapter || "Mathematics") + " chapter of CBSE Grade 9.",
    },
    {
      q: examp ? ("Given the example: " + examp + " — which formula was applied?") : ("The expression '" + ex.substring(0,30) + "' represents?"),
      options: [
        nm,
        "Pythagoras Theorem",
        "Mean Formula",
        "Ohm's Law",
      ],
      correct: 0,
      explain: "The expression " + ex + " is the " + nm + (examp ? ". In the example: " + examp : "") + ".",
    },
    {
      q: "When should you use " + nm + "?",
      options: [
        desc ? ("When you need to find: " + desc.substring(0,60)) : ("To apply " + nm + " in a " + chapter + " problem"),
        "Only in electrical circuits",
        "For calculating speed",
        "To find probability of events",
      ],
      correct: 0,
      explain: (desc || ("Use " + nm + " when solving " + chapter + " problems requiring " + ex)) + ".",
    },
  ];
}

function MCQPractice({ formula }) {
  const [open, setOpen] = useState(false);
  const [answers, setAnswers] = useState({});
  const [submitted, setSubmitted] = useState(false);

  var mcqs = buildMCQs(formula);

  function handleSelect(qi, oi) {
    if (submitted) return;
    setAnswers(prev => ({ ...prev, [qi]: oi }));
  }

  function handleSubmit() {
    if (Object.keys(answers).length < mcqs.length) return;
    setSubmitted(true);
  }

  function handleReset() {
    setAnswers({});
    setSubmitted(false);
  }

  return (
    <div style={{ marginTop: 8 }}>
      <button
        data-testid="practice-btn"
        onClick={() => setOpen(o => !o)}
        style={{ padding: "6px 14px", borderRadius: 7, border: "none",
          background: "#6366f1", color: "#fff", fontSize: ".76rem",
          fontWeight: 700, cursor: "pointer", fontFamily: "inherit" }}>
        {open ? "▲ Close Practice" : "📝 Practice ›"}
      </button>

      {open && (
        <div data-testid="mcq-practice-panel"
          style={{ marginTop: 12, background: "var(--surface2,#f8fafc)",
            border: "1px solid var(--border,#e5e7eb)", borderRadius: 10, padding: 14 }}>
          <div style={{ fontWeight: 700, fontSize: ".82rem", marginBottom: 10, color: "#6366f1" }}>
            📝 Practice Questions — {formula.name}
          </div>

          {mcqs.map((q, qi) => (
            <div key={qi} data-testid={"mcq-"+qi}
              style={{ marginBottom: 14, padding: "10px 12px",
                background: "var(--panel,#fff)", borderRadius: 8,
                border: "1px solid var(--border,#e5e7eb)" }}>
              <div style={{ fontWeight: 600, fontSize: ".8rem", marginBottom: 8 }}>
                Q{qi+1}. {q.q}
              </div>
              {q.options.map((opt, oi) => {
                var sel = answers[qi] === oi;
                var correct = oi === q.correct;
                var bg = !submitted ? (sel ? "#ede9fe" : "transparent")
                  : correct ? "#dcfce7" : (sel ? "#fee2e2" : "transparent");
                var border = !submitted ? (sel ? "1.5px solid #6366f1" : "1px solid var(--border,#e5e7eb)")
                  : correct ? "1.5px solid #22c55e" : (sel ? "1.5px solid #ef4444" : "1px solid var(--border,#e5e7eb)");
                return (
                  <div key={oi} onClick={() => handleSelect(qi, oi)}
                    style={{ display: "flex", alignItems: "center", gap: 8,
                      padding: "6px 10px", marginBottom: 5, borderRadius: 7,
                      background: bg, border: border,
                      cursor: submitted ? "default" : "pointer",
                      fontSize: ".77rem" }}>
                    <span style={{ fontWeight: 700, color: sel ? "#6366f1" : "var(--text-muted,#94a3b8)", minWidth: 16 }}>
                      {["A","B","C","D"][oi]}
                    </span>
                    <span>{opt}</span>
                    {submitted && correct && <span style={{ marginLeft: "auto", color: "#22c55e", fontSize: ".75rem" }}>✓ Correct</span>}
                    {submitted && sel && !correct && <span style={{ marginLeft: "auto", color: "#ef4444", fontSize: ".75rem" }}>✗ Wrong</span>}
                  </div>
                );
              })}

              {/* Explanation shown after submit */}
              {submitted && (
                <div data-testid={"mcq-explanation-"+qi}
                  style={{ marginTop: 8, padding: "8px 10px", background: "#f0fdf4",
                    borderRadius: 7, border: "1px solid #bbf7d0", fontSize: ".75rem",
                    lineHeight: 1.5 }}>
                  <span style={{ fontWeight: 700, color: "#16a34a" }}>💡 Explanation: </span>
                  {q.explain}
                </div>
              )}
            </div>
          ))}

          {!submitted ? (
            <button onClick={handleSubmit}
              disabled={Object.keys(answers).length < mcqs.length}
              style={{ padding: "7px 16px", borderRadius: 7, border: "none",
                background: Object.keys(answers).length < mcqs.length ? "#94a3b8" : "#6366f1",
                color: "#fff", fontWeight: 700, fontSize: ".78rem", cursor: Object.keys(answers).length < mcqs.length ? "not-allowed" : "pointer",
                fontFamily: "inherit" }}>
              Submit Answers
            </button>
          ) : (
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{ fontWeight: 700, color: "#22c55e", fontSize: ".82rem" }}>
                Score: {mcqs.filter((_,qi) => answers[qi] === 0).length}/{mcqs.length}
              </div>
              <button onClick={handleReset}
                style={{ padding: "5px 12px", borderRadius: 7, border: "1px solid #6366f1",
                  background: "transparent", color: "#6366f1", fontWeight: 600, fontSize: ".75rem",
                  cursor: "pointer", fontFamily: "inherit" }}>
                Try Again
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Formula Card ─────────────────────────────────────────────────────────────
function FormulaCard({ formula, hasPremium, onUpgrade }) {
  const [expanded, setExpanded] = useState(false);

  const canExpand = hasPremium && formula.preview_allowed && !formula.locked;

  function handleExpand() {
    if (!canExpand) {
      if (onUpgrade) onUpgrade();
      return;
    }
    setExpanded(e => !e);
  }

  const diffColor = formula.difficulty === "easy" ? "#4ade80" : formula.difficulty === "hard" ? "#f87171" : "#a78bfa";
  const diffBg   = "rgba(0,0,0,0.15)";

  return (
    <div data-testid="formula-card"
      style={{ background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 10, padding: "12px 14px", borderLeft: `3px solid ${formula.locked ? "#94a3b8" : "#6366f1"}`, opacity: formula.locked ? 0.8 : 1 }}>

      {/* Card header — always visible */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: ".82rem", marginBottom: 3 }}>
            {formula.locked && <span style={{ color: "#94a3b8" }}>🔒 </span>}
            {formula.name}
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 3, marginBottom: 4 }}>
            {formula.difficulty && <Badge bg={diffBg} color={diffColor}>{formula.difficulty}</Badge>}
            {formula.chapter && <Badge bg="rgba(74,222,128,0.15)" color="#4ade80">{formula.chapter}</Badge>}
            {(formula.tags || []).map(t => <Badge key={t}>{t}</Badge>)}
          </div>
        </div>
        {formula.preview_allowed && !formula.locked && <CopyBtn text={formula.expression} />}
      </div>

      {/* Expression — visible for preview formulas, blurred for fully locked */}
      {formula.preview_allowed ? (
        <div data-testid="formula-expression"
          style={{ fontFamily: "monospace", fontSize: ".93rem", fontWeight: 600, background: "var(--surface2,#f8fafc)", padding: "6px 10px", borderRadius: 6, marginBottom: 6, userSelect: "all" }}>
          <MathExpr tex={formula.expression_latex || formula.expression} />
        </div>
      ) : (
        <div style={{ fontFamily: "monospace", fontSize: ".88rem", background: "#f1f5f9", padding: "5px 10px", borderRadius: 6, marginBottom: 6, filter: "blur(4px)", userSelect: "none", pointerEvents: "none" }}>
          {formula.expression?.substring(0, 10)}•••
        </div>
      )}

      {/* Short description — preview */}
      {formula.preview_allowed && formula.description && (
        <div style={{ fontSize: ".77rem", color: "var(--text-muted,#64748b)", marginBottom: 4, lineHeight: 1.4 }}>{formula.description}</div>
      )}

      {/* Expand / collapse button */}
      {formula.preview_allowed && (
        <button
          data-testid={canExpand ? "expand-btn" : "expand-locked-btn"}
          onClick={handleExpand}
          style={{ background: "none", border: "none", color: canExpand ? "#6366f1" : "#94a3b8", fontSize: ".72rem", fontWeight: 600, cursor: "pointer", fontFamily: "inherit", padding: 0, marginBottom: 2 }}>
          {expanded ? "▲ Collapse" : (canExpand ? "▼ Show details" : "🔒 Upgrade to expand")}
        </button>
      )}

      {/* Expanded content — paid only */}
      {expanded && canExpand && (
        <div data-testid="expanded-content" style={{ marginTop: 8, borderTop: "1px solid var(--border,#f1f5f9)", paddingTop: 8 }}>
          {/* Variables */}
          {formula.variables && (
            <div style={{ marginBottom: 8 }}>
              <div style={{ fontSize: ".7rem", fontWeight: 700, color: "#6366f1", marginBottom: 3 }}>📌 Variables</div>
              <div style={{ fontSize: ".76rem" }}>{formula.variables}</div>
            </div>
          )}

          {/* Use when */}
          {formula.description && (
            <div style={{ marginBottom: 8 }}>
              <div style={{ fontSize: ".7rem", fontWeight: 700, color: "#6366f1", marginBottom: 3 }}>🎯 When to use</div>
              <div style={{ fontSize: ".76rem" }}>{formula.description}</div>
            </div>
          )}

          {/* Solved example */}
          {formula.example ? (
            <div style={{ marginBottom: 8 }}>
              <div style={{ fontSize: ".7rem", fontWeight: 700, color: "#059669", marginBottom: 3 }}>✏️ Example</div>
              <div style={{ fontSize: ".76rem" }}>{formula.example}</div>
            </div>
          ) : (
            <UpgradePrompt msg="Solved example coming soon." />
          )}

          {/* Memory tip */}
          {formula.memory_tip ? (
            <div style={{ marginBottom: 8, background: "#fefce8", borderRadius: 6, padding: "5px 8px" }}>
              <div style={{ fontSize: ".7rem", fontWeight: 700, color: "#d97706", marginBottom: 2 }}>💡 Memory Tip</div>
              <div style={{ fontSize: ".76rem" }}>{formula.memory_tip}</div>
            </div>
          ) : null}

          {/* MCQ Practice expander (inline, like Exemplar) */}
          <MCQPractice formula={formula} />
        </div>
      )}

      {/* Locked upgrade inline prompt */}
      {formula.locked && <UpgradePrompt msg="Upgrade to unlock this formula with examples and memory tips." />}
      {!formula.locked && formula.preview_allowed && !canExpand && !expanded && (
        <div style={{ fontSize: ".72rem", color: "var(--text-muted,#94a3b8)", marginTop: 4 }}>
          Formula preview ·{" "}
          <button onClick={() => onUpgrade && onUpgrade()}
            style={{ background: "none", border: "none", color: "#818cf8", fontWeight: 700,
              cursor: "pointer", fontFamily: "inherit", fontSize: ".72rem", padding: 0,
              textDecoration: "underline" }}>
            Upgrade to expand →
          </button>
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function FormulaSheetPage({ user, setActivePage }) {
  const grade = user?.grade || "Grade 9";
  const [subject, setSubject]         = useState("Mathematics");
  const [data, setData]               = useState(null);
  const [loading, setLoading]         = useState(false);
  const [err, setErr]                 = useState(null);
  const [search, setSearch]           = useState("");
  const [activeChapter, setActiveChapter] = useState(null);

  const hasPremium = !!(data?.has_premium);

  const load = useCallback(async () => {
    setLoading(true); setErr(null); setActiveChapter(null);
    try {
      const params = new URLSearchParams({ grade, subject });
      const res = await authFetch(`/api/student/formula-sheets?${params}`);
      setData(res);
      if (res?.chapters?.length > 0) setActiveChapter(res.chapters[0].chapter_id);
    } catch { setErr("Could not load formula sheets. Please try again."); }
    finally { setLoading(false); }
  }, [grade, subject]);

  useEffect(() => { load(); }, [load]);

  function nav(page) { if (setActivePage) setActivePage(page); }
  function handleUpgrade() { nav("subscription"); }

  // Filter formulas by search
  function getFiltered() {
    if (!data?.chapters) return [];
    const q = search.toLowerCase().trim();
    if (!q) return data.chapters;
    return data.chapters.map(ch => ({
      ...ch,
      topics: ch.topics.map(t => ({
        ...t,
        formulas: t.formulas.filter(f =>
          f.name.toLowerCase().includes(q) ||
          f.expression?.toLowerCase().includes(q) ||
          (f.description || "").toLowerCase().includes(q) ||
          ch.chapter_name.toLowerCase().includes(q)
        ),
      })).filter(t => t.formulas.length > 0),
    })).filter(ch => ch.topics.length > 0);
  }

  const filteredChapters = getFiltered();
  const displayed = search ? filteredChapters : filteredChapters.filter(ch => ch.chapter_id === activeChapter);

  return (
    <div data-testid="formula-sheet-page" style={{ maxWidth: 1100, margin: "0 auto", padding: "0 0 60px" }}>

      {/* Header */}
      <div style={{ marginBottom: 14 }}>
        <h2 style={{ fontWeight: 800, fontSize: "1.15rem", margin: "0 0 3px" }}>📐 Formula Sheet</h2>
        <div style={{ fontSize: ".85rem", color: "var(--text-muted,#64748b)" }}>
          {grade} · CBSE Reference
          {data && (
            <span style={{ marginLeft: 10, fontWeight: 600, color: hasPremium ? "#22c55e" : "#f59e0b", fontSize: ".77rem" }}>
              {hasPremium ? `✓ ${data.total_count} formulas unlocked` : `🔒 ${data.unlocked_count} of ${data.total_count} preview`}
            </span>
          )}
        </div>
      </div>

      {/* Subject selector */}
      <div style={{ display: "flex", gap: 7, marginBottom: 12, flexWrap: "wrap" }}>
        {(data?.subjects || ["Mathematics","Science","Physics","Chemistry"]).map(s => (
          <button key={s} data-testid={"fs-subject-"+s.toLowerCase().replace(/ /g,"-")}
            onClick={() => setSubject(s)}
            style={{ padding: "6px 16px", borderRadius: 20, border: "none",
              background: subject===s ? "#6366f1" : "var(--surface2,#f1f5f9)",
              color: subject===s ? "#fff" : "var(--text,#374151)",
              fontWeight: 600, fontSize: ".82rem", cursor: "pointer", fontFamily: "inherit" }}>
            {s}
          </button>
        ))}
      </div>

      {/* Search */}
      <input data-testid="formula-search" placeholder="Search formulas, chapters..." value={search}
        onChange={e => setSearch(e.target.value)}
        style={{ width: "100%", padding: "8px 14px", borderRadius: 8, border: "1px solid var(--border,#e5e7eb)",
          fontFamily: "inherit", fontSize: ".85rem", boxSizing: "border-box", marginBottom: 12 }}/>

      {/* Upgrade banner for free users */}
      {!loading && data && data.available && !hasPremium && (
        <div data-testid="upgrade-banner"
          style={{ background: "linear-gradient(135deg,#6366f1 0%,#818cf8 100%)", color: "#fff",
            borderRadius: 10, padding: "10px 16px", marginBottom: 12,
            display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: ".88rem" }}>Unlock Full Formula Library</div>
            <div style={{ fontSize: ".75rem", opacity: .9 }}>
              You have {data.unlocked_count} preview formulas. Upgrade to unlock all {data.total_count} with examples and memory tips.
            </div>
          </div>
          <button data-testid="upgrade-cta" onClick={handleUpgrade}
            style={{ background: "#fff", color: "#6366f1", border: "none", borderRadius: 8,
              padding: "7px 16px", fontWeight: 700, fontSize: ".8rem", cursor: "pointer",
              fontFamily: "inherit", whiteSpace: "nowrap" }}>
            Upgrade
          </button>
        </div>
      )}

      {/* Loading */}
      {loading && <div style={{ textAlign: "center", padding: 40, color: "var(--text-muted,#94a3b8)" }}>Loading...</div>}

      {/* Error */}
      {!loading && err && (
        <div style={{ padding: 20, color: "#dc2626" }}>{err}
          <button onClick={load} style={{ color: "#6366f1", background: "none", border: "none", cursor: "pointer", fontFamily: "inherit", fontWeight: 600, marginLeft: 8 }}>Retry</button>
        </div>
      )}

      {/* Unavailable */}
      {!loading && !err && data && !data.available && (
        <div data-testid="formula-sheet-unavailable"
          style={{ background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 12, padding: 32, textAlign: "center" }}>
          <div style={{ fontSize: "2rem", marginBottom: 8 }}>📋</div>
          <div style={{ fontWeight: 700, fontSize: ".95rem", marginBottom: 6 }}>{data.message}</div>
          <div style={{ fontSize: ".82rem", color: "var(--text-muted,#64748b)" }}>Formula content is being added. Check back soon.</div>
        </div>
      )}

      {/* Main layout */}
      {!loading && !err && data && data.available && (
        <div data-testid="formula-sheet-content" style={{ display: "flex", gap: 16, alignItems: "flex-start", flexWrap: "wrap" }}>

          {/* Chapter sidebar */}
          {!search && (
            <div data-testid="chapter-sidebar" style={{ width: 190, flexShrink: 0, minWidth: 140 }}>
              <div style={{ fontWeight: 700, fontSize: ".7rem", color: "var(--text-muted,#94a3b8)", textTransform: "uppercase", letterSpacing: ".05em", marginBottom: 8 }}>Chapters</div>
              {data.chapters.map(ch => (
                <button key={ch.chapter_id} data-testid={"chapter-btn-"+ch.chapter_id}
                  onClick={() => setActiveChapter(ch.chapter_id)}
                  style={{ display: "block", width: "100%", textAlign: "left", padding: "6px 10px",
                    borderRadius: 7, border: "none", marginBottom: 3, cursor: "pointer",
                    fontFamily: "inherit",
                    fontWeight: activeChapter===ch.chapter_id ? 700 : 400,
                    fontSize: ".77rem",
                    background: activeChapter===ch.chapter_id ? "#6366f1" : "var(--surface2,#f1f5f9)",
                    color: activeChapter===ch.chapter_id ? "#fff" : "var(--text,#374151)" }}>
                  {ch.chapter_name}
                  {ch.locked && <span style={{ marginLeft: 4, fontSize: ".62rem", opacity: .7 }}>🔒</span>}
                  <span style={{ float: "right", fontSize: ".62rem", opacity: .55 }}>{ch.unlocked_count}/{ch.total_formulas}</span>
                </button>
              ))}
            </div>
          )}

          {/* Formula cards */}
          <div style={{ flex: 1, minWidth: 0 }}>
            {displayed.length === 0 ? (
              <div style={{ color: "var(--text-muted,#94a3b8)", padding: 20 }}>
                {search ? "No formulas match your search." : "Select a chapter to view formulas."}
              </div>
            ) : displayed.map(ch => (
              <div key={ch.chapter_id} style={{ marginBottom: 24 }}>
                <div style={{ fontWeight: 700, fontSize: ".88rem", color: "#6366f1",
                  borderBottom: "2px solid #e0e7ff", paddingBottom: 6, marginBottom: 12 }}>
                  {ch.chapter_name}
                  {!hasPremium && ch.total_formulas > ch.unlocked_count && (
                    <span style={{ marginLeft: 8, fontSize: ".7rem", color: "#f59e0b" }}>
                      ({ch.unlocked_count} of {ch.total_formulas} shown)
                    </span>
                  )}
                </div>
                {ch.topics.map(t => (
                  <div key={t.topic_name} style={{ marginBottom: 14 }}>
                    {t.topic_name !== "General" && (
                      <div style={{ fontSize: ".7rem", fontWeight: 600, color: "var(--text-muted,#94a3b8)",
                        textTransform: "uppercase", letterSpacing: ".04em", marginBottom: 8 }}>{t.topic_name}</div>
                    )}
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(270px,1fr))", gap: 10 }}>
                      {t.formulas.map(f => (
                        <FormulaCard key={f.id || f.name} formula={f} hasPremium={hasPremium}
                          onUpgrade={handleUpgrade} />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
