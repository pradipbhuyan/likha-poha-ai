import { useEffect, useState } from "react";
import {
  Settings, Headphones, Loader2, Ban, BarChart3, Lightbulb, Volume2, History,
} from "lucide-react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const GRADES = ["Grade 5","Grade 6","Grade 7","Grade 8","Grade 9","Grade 10","Grade 11","Grade 12"];

export default function TeacherLectureAudioPage({ user }) {
  const [syllabus, setSyllabus] = useState({});
  const [syllabusLoading, setSyllabusLoading] = useState(true);

  const [grade, setGrade] = useState("Grade 9");
  const [subject, setSubject] = useState("");
  const [chapter, setChapter] = useState("");

  const [loading, setLoading] = useState(false);
  const [audio, setAudio] = useState(null); // { url, cached, grade, subject, chapter }
  const [error, setError] = useState("");

  const [history, setHistory] = useState([]);
  const [historyOpen, setHistoryOpen] = useState(false);

  useEffect(() => {
    async function loadSyllabus() {
      setSyllabusLoading(true);
      try {
        const res = await fetch(`${API_BASE}/api/syllabus`);
        const data = await res.json();
        setSyllabus(data.syllabus || {});
      } catch { /* ignore */ }
      setSyllabusLoading(false);
    }
    loadSyllabus();
  }, []);

  const subjects = Object.keys(syllabus?.[grade]?.CBSE || {});
  const chapters = (syllabus?.[grade]?.CBSE?.[subject] || []).filter(c => c !== "Uploaded Book Content");

  useEffect(() => { setSubject(subjects[0] || ""); setChapter(""); }, [grade]);
  useEffect(() => { setChapter(chapters[0] || ""); }, [subject, grade]);

  // ── Free-tier daily limit (mirrors Create Lesson Plans) ─────────────────────
  const freeTeacher = user?.role === "teacher" &&
    (!user?.subscriptionPlan || user.subscriptionPlan === "free") &&
    !user?.accessCbse;
  const todayCount = freeTeacher
    ? (() => { try { return parseInt(localStorage.getItem(`teacher_lectureaudio_${user?.username}_${new Date().toISOString().slice(0,10)}`)||"0",10); } catch(e) { return 0; } })()
    : 0;
  const limitReached = freeTeacher && todayCount >= 2;
  function incrementCount() {
    try { const k=`teacher_lectureaudio_${user?.username}_${new Date().toISOString().slice(0,10)}`; localStorage.setItem(k,String(parseInt(localStorage.getItem(k)||"0",10)+1)); } catch(e) { /* non-critical */ }
  }

  async function handleListen() {
    if (limitReached) return;
    if (!grade || !subject || !chapter) {
      setError("Please select Grade, Subject and Chapter.");
      return;
    }
    setError("");
    setLoading(true);
    setAudio(null);
    try {
      const res = await fetch(`${API_BASE}/api/teacher/lesson-plan/lecture-audio`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${user?.accessToken}`,
        },
        body: JSON.stringify({ grade, subject, chapter }),
      });
      const data = await res.json();
      if (!res.ok || !data.success) throw new Error(data.detail || data.message || "Could not generate lecture audio.");
      const result = { url: data.audio_url, cached: data.cached, grade, subject, chapter, ts: new Date().toLocaleTimeString() };
      setAudio(result);
      setHistory(prev => [result, ...prev.filter(h => !(h.grade === grade && h.subject === subject && h.chapter === chapter)).slice(0, 9)]);
      if (freeTeacher) incrementCount();
    } catch (err) {
      setError(err.message || "Failed to generate lecture audio. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="premium-page">
      {/* Settings card */}
      <div className="premium-card" style={{ marginBottom: 24 }}>
        <h3 style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
          <Settings size={17} strokeWidth={2.2} /> Lecture Settings
        </h3>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 14, marginBottom: 14 }}>
          <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <span style={{ fontSize: ".82rem", fontWeight: 600, color: "var(--muted)" }}>Grade</span>
            <select value={grade} onChange={e => setGrade(e.target.value)}>
              {GRADES.map(g => <option key={g}>{g}</option>)}
            </select>
          </label>
          <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <span style={{ fontSize: ".82rem", fontWeight: 600, color: "var(--muted)" }}>Subject</span>
            <select value={subject} onChange={e => setSubject(e.target.value)}>
              {syllabusLoading ? <option>Loading…</option> : subjects.map(s => <option key={s}>{s}</option>)}
            </select>
          </label>
          <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <span style={{ fontSize: ".82rem", fontWeight: 600, color: "var(--muted)" }}>Chapter / Topic</span>
            <select value={chapter} onChange={e => setChapter(e.target.value)}>
              {chapters.length === 0 ? <option>Select subject first</option> : chapters.map(c => <option key={c}>{c}</option>)}
            </select>
          </label>
        </div>

        {error && <div className="error-box" style={{ marginBottom: 12 }}>{error}</div>}

        {freeTeacher && (
          <div style={{ marginBottom: 10, padding: "8px 12px", borderRadius: 8, fontSize: ".82rem", fontWeight: 600,
            display: "flex", alignItems: "center", gap: 7,
            background: limitReached ? "rgba(239,68,68,.08)" : "rgba(99,102,241,.07)",
            border: `1px solid ${limitReached ? "rgba(239,68,68,.3)" : "rgba(167,139,250,.25)"}`,
            color: limitReached ? "#f87171" : "#a78bfa" }}>
            {limitReached
              ? <><Ban size={15} /> Daily limit reached (2/2 lectures today). Upgrade for unlimited or come back tomorrow.</>
              : <><BarChart3 size={15} /> {todayCount}/2 free lectures used today</>}
          </div>
        )}

        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          <button className="primary-btn" onClick={handleListen} disabled={loading || syllabusLoading || limitReached} style={{ maxWidth: 260, marginTop: 0, display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
            {limitReached
              ? <><Ban size={16} /> Daily Limit Reached</>
              : loading
                ? <><Loader2 size={16} className="spin" /> Generating Lecture Audio…</>
                : <><Headphones size={16} /> Listen to Lecture</>}
          </button>
          {history.length > 0 && (
            <button onClick={() => setHistoryOpen(h => !h)}
              style={{ padding: "11px 18px", borderRadius: 10, border: "1.5px solid var(--border)", background: "transparent", color: "var(--muted)", fontFamily: "inherit", fontSize: ".85rem", cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 7 }}>
              <History size={15} /> History ({history.length})
            </button>
          )}
        </div>
      </div>

      {/* History panel */}
      {historyOpen && history.length > 0 && (
        <div className="premium-card" style={{ marginBottom: 20 }}>
          <h4 style={{ marginBottom: 12, display: "flex", alignItems: "center", gap: 7 }}>
            <History size={16} /> Recently Played Lectures
          </h4>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {history.map((h, i) => (
              <button key={i} onClick={() => { setAudio(h); setHistoryOpen(false); }}
                style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 12px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--card-bg)", cursor: "pointer", fontFamily: "inherit", textAlign: "left" }}>
                <div>
                  <span style={{ fontWeight: 600, fontSize: ".85rem" }}>{h.grade} — {h.subject}</span>
                  <span style={{ fontSize: ".75rem", color: "var(--muted)", marginLeft: 8 }}>{h.chapter.length > 40 ? h.chapter.slice(0, 38) + "…" : h.chapter}</span>
                </div>
                <span style={{ fontSize: ".72rem", color: "var(--muted)" }}>{h.ts}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Generating state */}
      {loading && (
        <div className="premium-card" style={{ padding: "36px 28px", textAlign: "center" }}>
          <img
            src="/likhapohaai.gif"
            alt="Likha Poha AI is preparing your lecture…"
            style={{ width: 150, height: "auto", margin: "0 auto 10px", display: "block" }}
          />
          <div style={{ fontWeight: 700, fontSize: "1rem" }}>Preparing your lecture audio…</div>
          <div style={{ fontSize: ".8rem", color: "var(--muted)", marginTop: 6 }}>
            First listen for a chapter takes a little longer — after that it's instant.
          </div>
        </div>
      )}

      {/* Player */}
      {audio && !loading && (
        <div className="premium-card" style={{ padding: "28px 32px" }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
            {[
              { label: audio.grade, color: "#2563eb" },
              { label: audio.subject, color: "#7c3aed" },
              { label: audio.chapter.length > 42 ? audio.chapter.slice(0, 40) + "…" : audio.chapter, color: "#059669" },
            ].map(b => (
              <span key={b.label} style={{ fontSize: ".78rem", fontWeight: 700, padding: "4px 10px", borderRadius: 20, background: `${b.color}22`, color: b.color, border: `1px solid ${b.color}44` }}>
                {b.label}
              </span>
            ))}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
            <Volume2 size={20} style={{ color: "var(--primary)", flexShrink: 0 }} />
            <span style={{ fontWeight: 700 }}>Lecture read-through</span>
            {audio.cached && (
              <span style={{ fontSize: ".72rem", fontWeight: 600, color: "var(--muted)" }}>(from cache)</span>
            )}
          </div>
          <audio controls src={audio.url} style={{ width: "100%" }} />
        </div>
      )}

      {/* Empty state tip */}
      {!audio && !loading && (
        <div style={{ padding: "20px 22px", borderRadius: 12, background: "rgba(99,102,241,.06)", border: "1px solid rgba(99,102,241,.2)", display: "flex", gap: 14, alignItems: "flex-start" }}>
          <Lightbulb size={26} strokeWidth={2} style={{ flexShrink: 0, color: "#7c6fe0" }} />
          <div>
            <div style={{ fontWeight: 700, fontSize: ".88rem", marginBottom: 6 }}>What "Listen to Lecture" does</div>
            <div style={{ fontSize: ".8rem", color: "var(--muted)", lineHeight: 1.7 }}>
              Reads out a model spoken run-through of the chapter's lesson plan —
              the hook, the explanation, guided practice, the student activity,
              closing questions, and homework — in a teacher's voice, so you can
              rehearse the delivery before class. Requires a lesson plan to
              already exist for the chapter (create one first if needed).
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
