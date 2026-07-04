import { useEffect, useState } from "react";
import { BookOpen, FlaskConical, Calculator, Leaf, Globe } from "lucide-react";

const EXAMS = {
  jee: {
    label: "JEE Main", icon: "📐",
    description: "Joint Entrance Examination — Engineering admissions (IITs, NITs, IIITs)",
    grades: ["Grade 11", "Grade 12"], streams: ["PCM"],
    subjects: { PCM: ["Physics", "Chemistry", "Mathematics"] },
    examMode: "jee", color: "#6366f1",
  },
  neet: {
    label: "NEET UG", icon: "🔬",
    description: "National Eligibility cum Entrance Test — Medical admissions (MBBS, BDS)",
    grades: ["Grade 11", "Grade 12"], streams: ["PCB"],
    subjects: { PCB: ["Physics", "Chemistry", "Biology"] },
    examMode: "neet", color: "#10b981",
  },
  cuet: {
    label: "CUET UG", icon: "🏛️",
    description: "Common University Entrance Test — Central University admissions",
    grades: ["Grade 12"], streams: ["Science", "Commerce", "Arts"],
    subjects: {
      Science:  ["Physics", "Chemistry", "Mathematics", "Biology"],
      Commerce: ["Economics", "Business Studies", "Accountancy", "Mathematics"],
      Arts:     ["History", "Geography", "Political Science", "Sociology", "Economics"],
    },
    examMode: "cuet", color: "#f59e0b",
  },
};

const CHAPTER_COUNTS = {
  "Grade 11": {
    Physics: { jee: 15, neet: 15 }, Chemistry: { jee: 14, neet: 14 },
    Mathematics: { jee: 16 }, Biology: { neet: 22 },
  },
  "Grade 12": {
    Physics: { jee: 15, neet: 15, cuet: 15 }, Chemistry: { jee: 16, neet: 16, cuet: 16 },
    Mathematics: { jee: 13, cuet: 13 }, Biology: { neet: 18, cuet: 18 },
    Economics: { cuet: 10 }, "Business Studies": { cuet: 12 }, Accountancy: { cuet: 9 },
    History: { cuet: 15 }, Geography: { cuet: 8 }, "Political Science": { cuet: 10 }, Sociology: { cuet: 9 },
  },
};

const SUBJECT_ICONS = {
  Physics: FlaskConical, Chemistry: FlaskConical, Mathematics: Calculator,
  Biology: Leaf, Economics: Globe, "Business Studies": Globe,
  Accountancy: Calculator, History: BookOpen, Geography: Globe,
  "Political Science": BookOpen, Sociology: BookOpen,
};

const TEST_ACCESS_USERS = new Set(["akshita.teststudent"]);

function hasExamPrepAccess(user) {
  if (!user) return false;
  if (user.role === "admin") return true;
  return TEST_ACCESS_USERS.has(user.username);
}

function SubjectCard({ subject, grade, examKey, cachedCount, totalChapters }) {
  const Icon = SUBJECT_ICONS[subject] || BookOpen;
  const pct = totalChapters > 0 ? Math.min(100, Math.round((cachedCount / (totalChapters * 5)) * 100)) : 0;
  const done = pct === 100;
  return (
    <div style={{ background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 12, padding: "16px 18px", display: "flex", flexDirection: "column", gap: 10 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <span style={{ display: "grid", placeItems: "center", width: 36, height: 36, borderRadius: 10, flexShrink: 0, background: done ? "rgba(34,197,94,.12)" : "rgba(99,102,241,.08)", color: done ? "#16a34a" : "#6366f1" }}>
          <Icon size={18} strokeWidth={2.2} />
        </span>
        <div>
          <div style={{ fontWeight: 700, fontSize: ".9rem" }}>{subject}</div>
          <div style={{ fontSize: ".72rem", color: "var(--muted,#64748b)" }}>{grade} · {totalChapters} chapters × 5 steps</div>
        </div>
      </div>
      <div style={{ background: "#e5e7eb", borderRadius: 6, height: 6, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", transition: "width 0.4s", background: done ? "#22c55e" : "#6366f1" }} />
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: ".75rem", color: "var(--muted,#64748b)" }}>
        <span>{cachedCount} / {totalChapters * 5} lesson steps cached</span>
        <span style={{ fontWeight: 700, color: done ? "#16a34a" : "var(--muted)" }}>{pct}%</span>
      </div>
    </div>
  );
}

export default function ExamPrepPage({ user }) {
  const [selectedExam, setSelectedExam] = useState("jee");
  const [selectedStream, setSelectedStream] = useState("PCM");
  const [lessonStats, setLessonStats] = useState({});
  const exam = EXAMS[selectedExam];
  const isTestUser = TEST_ACCESS_USERS.has(user?.username);

  if (!hasExamPrepAccess(user)) {
    return (
      <div className="premium-page">
        <section className="premium-section">
          <div className="error-box">You do not have access to this page.</div>
        </section>
      </div>
    );
  }

  // eslint-disable-next-line react-hooks/rules-of-hooks
  useEffect(() => { setSelectedStream(exam.streams[0]); }, [selectedExam]);

  // eslint-disable-next-line react-hooks/rules-of-hooks
  useEffect(() => {
    async function load() {
      if (!user?.accessToken) return;
      try {
        const API = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
        const r = await fetch(`${API}/api/cache-management/status`, { headers: { Authorization: `Bearer ${user.accessToken}` } });
        const data = await r.json();
        const stats = {};
        (data.grades || []).forEach(gd => {
          (exam.subjects[selectedStream] || []).forEach(s => { stats[`${gd.grade}|${s}`] = { cached: 0 }; });
        });
        setLessonStats(stats);
      } catch { /* best effort */ }
    }
    load();
  }, [selectedExam, selectedStream, user?.accessToken]);

  const subjects = exam.subjects[selectedStream] || [];

  return (
    <div className="premium-page">
      <section className="premium-section">
        <div className="premium-header">
          <p className="eyebrow">Grade 11 & 12 — Competitive Exam Preparation</p>
          <h2>🎯 Exam Prep Center</h2>
          <p>Structured content for JEE, NEET, and CUET aligned to NTA syllabus. Prewarm lessons here before enabling student access.</p>
        </div>

        <div style={{ background: isTestUser ? "rgba(99,102,241,.07)" : "rgba(245,158,11,.08)", border: `1px solid ${isTestUser ? "rgba(99,102,241,.3)" : "rgba(245,158,11,.35)"}`, borderRadius: 10, padding: "12px 16px", fontSize: ".85rem", marginBottom: 24, display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: "1.2rem" }}>{isTestUser ? "🧪" : "🔒"}</span>
          <div>
            {isTestUser ? (
              <><strong>Test Access Mode.</strong> You have early access to Grade 11 & 12 content for review and testing. Not yet live for regular students.</>
            ) : (
              <><strong>Phase 1 — Admin Preview.</strong> Grade 11 & 12 lessons are not visible to students yet.</>
            )}
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 12, marginBottom: 8 }}>
          {Object.entries(EXAMS).map(([key, e]) => (
            <button key={key} onClick={() => setSelectedExam(key)} style={{ padding: 16, borderRadius: 12, textAlign: "left", fontFamily: "inherit", cursor: "pointer", transition: "all .15s", border: `2px solid ${selectedExam === key ? e.color : "var(--border,#e5e7eb)"}`, background: selectedExam === key ? `${e.color}12` : "var(--panel,#fff)" }}>
              <div style={{ fontSize: "1.5rem", marginBottom: 6 }}>{e.icon}</div>
              <div style={{ fontWeight: 800, fontSize: ".95rem", color: selectedExam === key ? e.color : "var(--text,#1e293b)" }}>{e.label}</div>
              <div style={{ fontSize: ".73rem", color: "var(--muted,#64748b)", marginTop: 4, lineHeight: 1.4 }}>{e.description}</div>
            </button>
          ))}
        </div>
      </section>

      {exam.streams.length > 1 && (
        <section className="premium-section" style={{ paddingTop: 0 }}>
          <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
            {exam.streams.map(stream => (
              <button key={stream} onClick={() => setSelectedStream(stream)} style={{ padding: "8px 18px", borderRadius: 20, fontWeight: 700, fontSize: ".85rem", cursor: "pointer", fontFamily: "inherit", border: `2px solid ${selectedStream === stream ? exam.color : "var(--border,#e5e7eb)"}`, background: selectedStream === stream ? `${exam.color}18` : "var(--panel,#fff)", color: selectedStream === stream ? exam.color : "var(--text,#374151)" }}>
                {stream}
              </button>
            ))}
          </div>
        </section>
      )}

      {exam.grades.map(grade => (
        <section key={grade} className="premium-section" style={{ paddingTop: 0 }}>
          <h3 style={{ margin: "0 0 14px", fontSize: "1rem", fontWeight: 700 }}>
            {grade}
            <span style={{ marginLeft: 10, fontSize: ".75rem", fontWeight: 600, background: "rgba(99,102,241,.1)", color: "#6366f1", padding: "2px 10px", borderRadius: 20 }}>{exam.label} syllabus</span>
          </h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(260px,1fr))", gap: 12 }}>
            {subjects.map(subject => {
              const info = CHAPTER_COUNTS[grade]?.[subject] || {};
              const total = info[selectedExam] ?? info.cuet ?? 10;
              const stats = lessonStats[`${grade}|${subject}`] || { cached: 0 };
              return <SubjectCard key={subject} subject={subject} grade={grade} examKey={selectedExam} cachedCount={stats.cached} totalChapters={total} />;
            })}
          </div>
        </section>
      ))}

      <section className="premium-section">
        <div className="premium-grid premium-grid-3">
          <div className="premium-card">
            <h4 style={{ margin: "0 0 8px", fontSize: ".9rem" }}>📋 Syllabus Source</h4>
            <p style={{ fontSize: ".78rem", color: "var(--muted,#64748b)", margin: 0, lineHeight: 1.6 }}>
              Aligned to NTA official 2024-25 syllabus. Physics, Chemistry, Maths, Biology chapters match NCERT Class 11 & 12.
            </p>
          </div>
          <div className="premium-card">
            <h4 style={{ margin: "0 0 8px", fontSize: ".9rem" }}>⚡ How to Prewarm</h4>
            <p style={{ fontSize: ".78rem", color: "var(--muted,#64748b)", margin: 0, lineHeight: 1.6 }}>
              Go to <strong>Cache & Question Bank</strong>, select Grade 11 or Grade 12, click <strong>Generate Lessons</strong>. All subjects prewarm automatically.
            </p>
          </div>
          <div className="premium-card">
            <h4 style={{ margin: "0 0 8px", fontSize: ".9rem" }}>🚀 Phase 2 Roadmap</h4>
            <p style={{ fontSize: ".78rem", color: "var(--muted,#64748b)", margin: 0, lineHeight: 1.6 }}>
              Previous Year Questions (PYQ) bank upload, exam-mode mock tests (180 min, +4/-1), difficulty tagging per topic.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
