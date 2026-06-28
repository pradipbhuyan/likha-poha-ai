/**
 * FormulaSheetPage.jsx
 * Full syllabus-aligned Formula Sheet page with freemium access control.
 * - FREE_TIER: chapter structure visible, first 3 formulas per chapter unlocked
 *   (name + expression + variables); solved examples, memory tips locked.
 * - PAID: full access — examples, solution steps, memory tips.
 * Data from GET /api/student/formula-sheets?grade=&subject=
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { authFetch } from "../api/authClient";

const SUBJECTS_DEFAULT = ["Mathematics", "Science"];

// ── Shared helpers ────────────────────────────────────────────────────────────
function Badge({ children, color = "#6366f118", textColor = "#6366f1" }) {
  return (
    <span style={{ fontSize: ".65rem", fontWeight: 700, padding: "1px 7px", borderRadius: 10, background: color, color: textColor, display: "inline-block", marginRight: 3 }}>
      {children}
    </span>
  );
}

function CopyBtn({ text }) {
  const [copied, setCopied] = useState(false);
  function handleCopy() {
    navigator.clipboard.writeText(text).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }
  return (
    <button onClick={handleCopy} title="Copy formula"
      style={{ background: "none", border: "1px solid var(--border,#e5e7eb)", borderRadius: 6, padding: "2px 8px", cursor: "pointer", fontSize: ".68rem", color: copied ? "#22c55e" : "#6366f1", fontFamily: "inherit", fontWeight: 600 }}>
      {copied ? "✓ Copied" : "Copy"}
    </button>
  );
}

function LockPrompt({ message = "Upgrade to see this content." }) {
  return (
    <div style={{ background: "var(--surface2,#f8fafc)", border: "1px dashed var(--border,#e5e7eb)", borderRadius: 8, padding: "8px 12px", display: "flex", alignItems: "center", gap: 8, marginTop: 6 }}>
      <span style={{ fontSize: ".9rem" }}>🔒</span>
      <span style={{ fontSize: ".75rem", color: "var(--text-muted,#64748b)", fontStyle: "italic" }}>{message}</span>
    </div>
  );
}

function FormulaCard({ formula, hasAskDoubt, onAskAI, onPractice }) {
  const [open, setOpen] = useState(false);

  return (
    <div data-testid="formula-card"
      style={{ background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 10, padding: "12px 14px", borderLeft: formula.locked ? "3px solid #94a3b8" : "3px solid #6366f1", opacity: formula.locked ? 0.75 : 1 }}>

      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: ".82rem", marginBottom: 2 }}>
            {formula.locked ? <span style={{ color: "#94a3b8" }}>🔒 </span> : null}
            {formula.name}
          </div>
          {formula.difficulty && (
            <Badge color={formula.difficulty === "easy" ? "#dcfce7" : formula.difficulty === "hard" ? "#fee2e2" : "#ede9fe"}
                   textColor={formula.difficulty === "easy" ? "#16a34a" : formula.difficulty === "hard" ? "#dc2626" : "#7c3aed"}>
              {formula.difficulty}
            </Badge>
          )}
          {(formula.tags || []).map(t => <Badge key={t}>{t}</Badge>)}
        </div>
        {!formula.locked && <CopyBtn text={formula.expression} />}
      </div>

      {/* Expression */}
      {formula.preview_allowed ? (
        <div style={{ fontFamily: "monospace", fontSize: ".95rem", fontWeight: 600, background: "var(--surface2,#f8fafc)", padding: "6px 10px", borderRadius: 6, marginBottom: 6, userSelect: "all" }}>
          {formula.expression}
        </div>
      ) : (
        <div style={{ fontFamily: "monospace", fontSize: ".88rem", background: "#f1f5f9", padding: "5px 10px", borderRadius: 6, marginBottom: 6, filter: "blur(3px)", userSelect: "none" }}>
          {formula.expression.substring(0, 8)}...
        </div>
      )}

      {/* Description + Variables */}
      {formula.preview_allowed && formula.description && (
        <div style={{ fontSize: ".78rem", color: "var(--text-muted,#64748b)", marginBottom: 4 }}>{formula.description}</div>
      )}
      {formula.preview_allowed && formula.variables && (
        <div style={{ fontSize: ".74rem", color: "var(--text-muted,#94a3b8)", fontStyle: "italic", marginBottom: 4 }}>Where: {formula.variables}</div>
      )}

      {/* Premium sections — show for paid, lock prompts for free */}
      {formula.preview_allowed && (
        <button onClick={() => setOpen(o => !o)}
          style={{ background: "none", border: "none", color: "#6366f1", fontSize: ".73rem", fontWeight: 600, cursor: "pointer", fontFamily: "inherit", marginBottom: 4 }}>
          {open ? "▲ Hide details" : "▼ Show details"}
        </button>
      )}

      {open && formula.preview_allowed && (
        <div style={{ marginTop: 4 }}>
          {/* Example */}
          {formula.example ? (
            <div style={{ marginBottom: 6 }}>
              <div style={{ fontSize: ".72rem", fontWeight: 700, color: "#059669", marginBottom: 2 }}>✏️ Example</div>
              <div style={{ fontSize: ".78rem" }}>{formula.example}</div>
            </div>
          ) : (
            <LockPrompt message="Upgrade to see a solved CBSE example." />
          )}

          {/* Solution steps */}
          {formula.solution_steps ? (
            <div style={{ marginBottom: 6 }}>
              <div style={{ fontSize: ".72rem", fontWeight: 700, color: "#0ea5e9", marginBottom: 2 }}>📋 Solution Steps</div>
              <div style={{ fontSize: ".78rem", whiteSpace: "pre-line" }}>{formula.solution_steps}</div>
            </div>
          ) : (
            <LockPrompt message="Upgrade to see step-by-step solution." />
          )}

          {/* Memory tip */}
          {formula.memory_tip ? (
            <div style={{ marginBottom: 6, background: "#fefce8", borderRadius: 6, padding: "5px 8px" }}>
              <div style={{ fontSize: ".72rem", fontWeight: 700, color: "#d97706", marginBottom: 2 }}>💡 Memory Tip</div>
              <div style={{ fontSize: ".78rem" }}>{formula.memory_tip}</div>
            </div>
          ) : (
            <LockPrompt message="Upgrade to unlock memory tricks." />
          )}

          {/* Action buttons */}
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 6 }}>
            {hasAskDoubt && onAskAI && (
              <button onClick={() => onAskAI(formula)}
                style={{ padding: "4px 10px", borderRadius: 7, border: "1px solid #6366f1", background: "transparent", color: "#6366f1", fontSize: ".72rem", fontWeight: 600, cursor: "pointer", fontFamily: "inherit" }}>
                Ask AI 🤖
              </button>
            )}
            {onPractice && (
              <button onClick={() => onPractice(formula)}
                style={{ padding: "4px 10px", borderRadius: 7, border: "none", background: "#6366f1", color: "#fff", fontSize: ".72rem", fontWeight: 600, cursor: "pointer", fontFamily: "inherit" }}>
                Practice ›
              </button>
            )}
          </div>
        </div>
      )}

      {/* Fully locked formula */}
      {formula.locked && (
        <LockPrompt message="Upgrade to unlock this formula with examples and memory tips." />
      )}
    </div>
  );
}

// ── Main page ────────────────────────────────────────────────────────────────
export default function FormulaSheetPage({ user, setActivePage }) {
  const grade = user?.grade || "Grade 9";
  const [subject, setSubject] = useState("Mathematics");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);
  const [search, setSearch] = useState("");
  const [activeChapter, setActiveChapter] = useState(null);
  const searchRef = useRef(null);

  const hasPremium = data?.has_premium || false;
  const hasAskDoubt = !!(user?.accessCbse);

  const load = useCallback(async function () {
    setLoading(true);
    setErr(null);
    setActiveChapter(null);
    try {
      const params = new URLSearchParams({ grade, subject });
      const res = await authFetch(`/api/student/formula-sheets?${params}`);
      setData(res);
      if (res?.chapters?.length > 0) setActiveChapter(res.chapters[0].chapter_id);
    } catch (e) {
      setErr("Could not load formula sheets. Please try again.");
    } finally {
      setLoading(false);
    }
  }, [grade, subject]);

  useEffect(() => { load(); }, [load]);

  function handleAskAI(_formula) {
    if (setActivePage) setActivePage("askDoubt");
  }
  function handlePractice(_formula) {
    if (setActivePage) setActivePage("mockTest");
  }

  // Filter formulas by search
  function getFilteredChapters() {
    if (!data?.chapters) return [];
    const q = search.toLowerCase().trim();
    if (!q) return data.chapters;
    return data.chapters.map(ch => ({
      ...ch,
      topics: ch.topics.map(t => ({
        ...t,
        formulas: t.formulas.filter(f =>
          f.name.toLowerCase().includes(q) ||
          f.expression.toLowerCase().includes(q) ||
          (f.description || "").toLowerCase().includes(q) ||
          (f.variables || "").toLowerCase().includes(q) ||
          ch.chapter_name.toLowerCase().includes(q)
        ),
      })).filter(t => t.formulas.length > 0),
    })).filter(ch => ch.topics.length > 0);
  }

  const filteredChapters = getFilteredChapters();
  const displayedChapters = search
    ? filteredChapters
    : filteredChapters.filter(ch => ch.chapter_id === activeChapter);

  return (
    <div data-testid="formula-sheet-page" style={{ maxWidth: 1100, margin: "0 auto", padding: "0 0 60px" }}>

      {/* Header */}
      <div style={{ marginBottom: 16 }}>
        <h2 style={{ fontWeight: 800, fontSize: "1.2rem", margin: "0 0 3px" }}>📐 Formula Sheet</h2>
        <div style={{ fontSize: ".85rem", color: "var(--text-muted,#64748b)" }}>
          {grade} · CBSE Reference Formulas
          {data && (
            <span style={{ marginLeft: 12, fontWeight: 600, color: hasPremium ? "#22c55e" : "#f59e0b", fontSize: ".78rem" }}>
              {hasPremium ? `✓ ${data.total_count} formulas unlocked` : `🔒 ${data.unlocked_count} of ${data.total_count} unlocked`}
            </span>
          )}
        </div>
      </div>

      {/* Subject selector */}
      <div style={{ display: "flex", gap: 8, marginBottom: 14, flexWrap: "wrap" }}>
        {(data?.subjects || SUBJECTS_DEFAULT).map(s => (
          <button key={s}
            data-testid={`fs-subject-${s.toLowerCase().replace(/ /g, "-")}`}
            onClick={() => setSubject(s)}
            style={{ padding: "6px 16px", borderRadius: 20, border: "none", background: subject === s ? "#6366f1" : "var(--surface2,#f1f5f9)", color: subject === s ? "#fff" : "var(--text,#374151)", fontWeight: 600, fontSize: ".82rem", cursor: "pointer", fontFamily: "inherit" }}>
            {s}
          </button>
        ))}
      </div>

      {/* Search */}
      <div style={{ marginBottom: 14 }}>
        <input
          ref={searchRef}
          data-testid="formula-search"
          placeholder="Search formulas, chapters, variables…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ width: "100%", padding: "8px 14px", borderRadius: 8, border: "1px solid var(--border,#e5e7eb)", fontFamily: "inherit", fontSize: ".85rem", boxSizing: "border-box" }}
        />
      </div>

      {/* Upgrade banner for free users */}
      {!loading && data?.available && !hasPremium && (
        <div data-testid="upgrade-banner"
          style={{ background: "linear-gradient(135deg,#6366f1 0%,#818cf8 100%)", color: "#fff", borderRadius: 10, padding: "10px 16px", marginBottom: 14, display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: ".88rem" }}>🔒 Unlock the full Formula Library</div>
            <div style={{ fontSize: ".75rem", opacity: .9 }}>You have access to {data.unlocked_count} preview formulas. Upgrade to unlock all {data.total_count} formulas with solved examples and memory tips.</div>
          </div>
          {setActivePage && (
            <button onClick={() => setActivePage("subscription")}
              data-testid="upgrade-cta"
              style={{ background: "#fff", color: "#6366f1", border: "none", borderRadius: 8, padding: "7px 16px", fontWeight: 700, fontSize: ".8rem", cursor: "pointer", fontFamily: "inherit", whiteSpace: "nowrap" }}>
              Upgrade →
            </button>
          )}
        </div>
      )}

      {/* Chapter sidebar + formula cards layout */}
      {loading && (
        <div style={{textAlign:"center",padding:40,color:"var(--text-muted,#94a3b8)"}}>Loading formula sheets…</div>
      )}

      {!loading && err && (
        <div style={{padding:20,color:"#dc2626"}}>{err} <button onClick={load} style={{color:"#6366f1",background:"none",border:"none",cursor:"pointer",fontFamily:"inherit",fontWeight:600}}>Retry</button></div>
      )}

      {!loading && !err && data && !data.available && (
        <div data-testid="formula-sheet-unavailable"
          style={{background:"var(--panel,#fff)",border:"1px solid var(--border,#e5e7eb)",borderRadius:12,padding:32,textAlign:"center"}}>
          <div style={{fontSize:"2rem",marginBottom:8}}>📋</div>
          <div style={{fontWeight:700,fontSize:".95rem",marginBottom:6}}>{data.message || `Formula sheet is not available for ${grade} yet.`}</div>
          <div style={{fontSize:".82rem",color:"var(--text-muted,#64748b)"}}>Formula content is added regularly. Check back soon.</div>
        </div>
      )}

      {!loading && !err && data && data.available && (
        <div data-testid="formula-sheet-content" style={{display:"flex",gap:16,alignItems:"flex-start",flexWrap:"wrap"}}>

          {/* Chapter sidebar */}
          {!search && (
            <div data-testid="chapter-sidebar" style={{width:200,flexShrink:0,minWidth:150}}>
              <div style={{fontWeight:700,fontSize:".75rem",color:"var(--text-muted,#64748b)",textTransform:"uppercase",letterSpacing:".06em",marginBottom:8}}>Chapters</div>
              {data.chapters.map(ch=>(
                <button key={ch.chapter_id} onClick={()=>setActiveChapter(ch.chapter_id)}
                  data-testid={"chapter-btn-"+ch.chapter_id}
                  style={{display:"block",width:"100%",textAlign:"left",padding:"6px 10px",borderRadius:7,border:"none",marginBottom:3,cursor:"pointer",fontFamily:"inherit",fontWeight:activeChapter===ch.chapter_id?700:400,fontSize:".78rem",background:activeChapter===ch.chapter_id?"#6366f1":"var(--surface2,#f1f5f9)",color:activeChapter===ch.chapter_id?"#fff":"var(--text,#374151)"}}>
                  {ch.chapter_name}
                  {ch.locked&&<span style={{marginLeft:4,fontSize:".65rem",opacity:.7}}>🔒</span>}
                  <span style={{float:"right",fontSize:".65rem",opacity:.6}}>{ch.unlocked_count}/{ch.total_formulas}</span>
                </button>
              ))}
            </div>
          )}

          {/* Formula cards */}
          <div style={{flex:1,minWidth:0}}>
            {displayedChapters.length===0?(
              <div style={{color:"var(--text-muted,#94a3b8)",padding:20}}>
                {search?"No formulas match your search.":"Select a chapter to view formulas."}
              </div>
            ):(
              displayedChapters.map(ch=>(
                <div key={ch.chapter_id} style={{marginBottom:24}}>
                  <div style={{fontWeight:700,fontSize:".88rem",color:"#6366f1",borderBottom:"2px solid #e0e7ff",paddingBottom:6,marginBottom:12}}>
                    {ch.chapter_name}
                    {ch.locked&&!hasPremium&&<span style={{marginLeft:8,fontSize:".72rem",color:"#f59e0b"}}>({ch.unlocked_count} of {ch.total_formulas} shown)</span>}
                  </div>
                  {ch.topics.map(t=>(
                    <div key={t.topic_name} style={{marginBottom:16}}>
                      {t.topic_name!=="General"&&<div style={{fontSize:".72rem",fontWeight:600,color:"var(--text-muted,#94a3b8)",textTransform:"uppercase",letterSpacing:".04em",marginBottom:8}}>{t.topic_name}</div>}
                      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(280px,1fr))",gap:10}}>
                        {t.formulas.map(f=>(
                          <FormulaCard key={f.id||f.name} formula={f} hasAskDoubt={hasAskDoubt} onAskAI={handleAskAI} onPractice={handlePractice}/>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
