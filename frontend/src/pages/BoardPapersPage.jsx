import { useEffect, useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  XCircle,
  Eye,
  ExternalLink,
  Award,
  Lock,
  Sparkles,
} from "lucide-react";

import {
  listBoardPaperYears,
  listBoardPaperSubjects,
  listBoardPapers,
  getBoardPaperQuestions,
} from "../api/boardPapers";
import { getUserGrade } from "../utils/syllabusDefaults";
import { isAllAccessTestUser } from "../utils/testAccounts";

function examGradeFor(rawGrade) {
  // Board Sample Papers only has content for Grade 10 and Grade 12 (CBSE
  // only publishes Class X and XII sample papers) — map every other grade
  // to its nearest upcoming board exam (9 -> 10, 11 -> 12).
  const num = parseInt(String(rawGrade || "").replace(/\D/g, ""), 10);
  return num >= 11 ? "Grade 12" : "Grade 10";
}

function MathText({ text }) {
  // Board paper questions/options carry light math notation (^, fractions
  // written as a/b) — kept as plain text rather than full LaTeX rendering
  // since the source data itself uses plain-text math, not $...$ markup.
  return <span style={{ whiteSpace: "pre-wrap" }}>{String(text || "")}</span>;
}

function QuestionCard({ question }) {
  const [selected, setSelected] = useState(null);
  const [revealed, setRevealed] = useState(false);
  const isMcq = question.question_type === "mcq" || question.question_type === "assertion_reason";
  const answered = isMcq ? selected !== null : revealed;

  return (
    <div style={{
      background: "var(--panel, #fff)", border: "1px solid var(--border, #d6ddeb)",
      borderRadius: 10, padding: "16px 18px", marginBottom: 14,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
        <span style={{
          fontSize: ".7rem", fontWeight: 800, letterSpacing: ".08em", textTransform: "uppercase",
          color: "var(--accent, #7c3aed)", background: "rgba(124,58,237,0.12)",
          borderRadius: 999, padding: "3px 10px",
        }}>
          Section {question.section} · {question.marks} mark{question.marks === 1 ? "" : "s"}
        </span>
        {question.diagram_dependent && (
          <span style={{ fontSize: ".72rem", color: "var(--muted, #64748b)" }}>
            (refers to a figure in the original paper)
          </span>
        )}
      </div>

      <div style={{ fontSize: ".95rem", fontWeight: 600, marginBottom: 10, lineHeight: 1.55 }}>
        Q{question.question_number}. <MathText text={question.question_text} />
      </div>

      {isMcq && (
        <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 10 }}>
          {question.options.map((option, i) => {
            const isCorrect = option === question.answer_text;
            const isSelected = selected === i;
            let bg = "transparent", border = "1px solid var(--border, #d6ddeb)", color = "var(--text, #29324a)";
            if (answered && isCorrect) {
              bg = "rgba(34,197,94,0.12)"; border = "1.5px solid #16a34a"; color = "#15803d";
            } else if (answered && isSelected) {
              bg = "rgba(239,68,68,0.1)"; border = "1.5px solid #ef4444"; color = "#b3261e";
            }
            return (
              <button
                key={i}
                type="button"
                disabled={answered}
                onClick={() => setSelected(i)}
                style={{
                  textAlign: "left", padding: "8px 12px", borderRadius: 8, background: bg, border, color,
                  fontSize: ".88rem", cursor: answered ? "default" : "pointer", fontWeight: answered && (isCorrect || isSelected) ? 700 : 500,
                }}
              >
                <strong>{String.fromCharCode(65 + i)}.</strong> <MathText text={option} />
                {answered && isCorrect && <CheckCircle2 size={14} style={{ marginLeft: 8, verticalAlign: "-2px" }} color="#16a34a" />}
                {answered && isSelected && !isCorrect && <XCircle size={14} style={{ marginLeft: 8, verticalAlign: "-2px" }} color="#ef4444" />}
              </button>
            );
          })}
        </div>
      )}

      {!isMcq && !revealed && (
        <button
          type="button"
          onClick={() => setRevealed(true)}
          style={{
            display: "inline-flex", alignItems: "center", gap: 6, background: "var(--accent, #7c3aed)",
            color: "#fff", border: "none", borderRadius: 8, padding: "8px 14px", fontSize: ".85rem",
            fontWeight: 700, cursor: "pointer", marginTop: 4,
          }}
        >
          <Eye size={14} /> Show official answer
        </button>
      )}

      {answered && question.answer_explanation && (
        <div style={{
          borderTop: "1px dashed var(--border, #d6ddeb)", marginTop: 10, paddingTop: 10,
        }}>
          {!isMcq && (
            <div style={{ fontSize: ".88rem", lineHeight: 1.6, marginBottom: 8, whiteSpace: "pre-wrap" }}>
              <strong style={{ fontSize: ".72rem", textTransform: "uppercase", letterSpacing: ".06em", color: "var(--muted, #64748b)" }}>
                Official answer
              </strong>
              <div style={{ marginTop: 4 }}><MathText text={question.answer_text} /></div>
            </div>
          )}
          <div style={{ fontSize: ".85rem", lineHeight: 1.55, color: "var(--muted, #64748b)" }}>
            <MathText text={question.answer_explanation} />
          </div>
        </div>
      )}
    </div>
  );
}

function PaperAttempt({ paper, questions, onBack }) {
  return (
    <div>
      <button
        type="button"
        onClick={onBack}
        style={{ background: "none", border: "none", color: "var(--accent, #7c3aed)", fontSize: ".85rem", fontWeight: 600, cursor: "pointer", padding: 0, marginBottom: 14 }}
      >
        ← Back to papers
      </button>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10, marginBottom: 16 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: "1.2rem" }}>
            {paper.subject}{paper.subject_variant ? ` — ${paper.subject_variant}` : ""}
          </h2>
          <div style={{ fontSize: ".82rem", color: "var(--muted, #64748b)" }}>
            {paper.board} · {paper.grade} · {paper.academic_year}
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {paper.question_paper_url && (
            <a href={paper.question_paper_url} target="_blank" rel="noreferrer" style={{ fontSize: ".8rem", display: "inline-flex", alignItems: "center", gap: 4, color: "var(--accent, #7c3aed)" }}>
              <ExternalLink size={13} /> Original PDF
            </a>
          )}
          {paper.marking_scheme_url && (
            <a href={paper.marking_scheme_url} target="_blank" rel="noreferrer" style={{ fontSize: ".8rem", display: "inline-flex", alignItems: "center", gap: 4, color: "var(--accent, #7c3aed)" }}>
              <Award size={13} /> Marking scheme PDF
            </a>
          )}
        </div>
      </div>

      {questions.map((q) => (
        <QuestionCard key={q.id} question={q} />
      ))}

      <p style={{ fontSize: ".78rem", color: "var(--muted, #64748b)", textAlign: "center", marginTop: 20 }}>
        Question paper and marking scheme are official {paper.board} publications, sourced from{" "}
        cbseacademic.nic.in, reproduced here for student practice.
      </p>
    </div>
  );
}

export default function BoardPapersPage({ user }) {
  const canSwitchGrade = user?.role === "admin" || isAllAccessTestUser(user);
  const [grade, setGrade] = useState(() => examGradeFor(getUserGrade(user, "Grade 10")));
  const [years, setYears] = useState([]); // [{year, locked}]
  const [fullAccess, setFullAccess] = useState(true);
  const [expandedYear, setExpandedYear] = useState(null);
  const [subjectsByYear, setSubjectsByYear] = useState({}); // year -> [{subject, locked}]
  const [papersByYear, setPapersByYear] = useState({}); // year -> [paper] (unlocked papers only)
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activePaper, setActivePaper] = useState(null);
  const [activeQuestions, setActiveQuestions] = useState(null);
  const [loadingPaper, setLoadingPaper] = useState(false);

  useEffect(() => {
    let cancelled = false;
    // Year/subject labels (e.g. "2025-26") can repeat across grades, so the
    // per-year caches below must be cleared on every grade switch — otherwise
    // switching from Grade 10 to Grade 12 could show Grade 10's cached
    // subjects under a same-named Grade 12 year.
    setYears([]);
    setSubjectsByYear({});
    setPapersByYear({});
    setExpandedYear(null);
    setError("");
    setLoading(true);
    listBoardPaperYears(grade)
      .then((result) => {
        if (cancelled) return;
        const yrs = result?.years || [];
        setYears(yrs);
        setFullAccess(result?.full_access !== false);
        if (yrs.length) setExpandedYear(yrs[0].year);
      })
      .catch((err) => !cancelled && setError(err.message || "Could not load years"))
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, [grade]);

  useEffect(() => {
    if (!expandedYear || subjectsByYear[expandedYear]) return;
    listBoardPaperSubjects(grade, expandedYear)
      .then((result) => {
        setSubjectsByYear((prev) => ({ ...prev, [expandedYear]: result?.subjects || [] }));
      })
      .catch((err) => setError(err.message || "Could not load subjects"));
    listBoardPapers({ grade, academicYear: expandedYear })
      .then((result) => {
        setPapersByYear((prev) => ({ ...prev, [expandedYear]: result?.papers || [] }));
      })
      .catch((err) => setError(err.message || "Could not load papers"));
  }, [expandedYear, grade, subjectsByYear]);

  function openPaper(paper) {
    setLoadingPaper(true);
    setError("");
    getBoardPaperQuestions(paper.id, grade)
      .then((result) => {
        setActivePaper(result?.paper || paper);
        setActiveQuestions(result?.questions || []);
      })
      .catch((err) => setError(err.message || "Could not load this paper"))
      .finally(() => setLoadingPaper(false));
  }

  if (activePaper && activeQuestions) {
    return (
      <div style={{ padding: "24px 32px" }}>
        <PaperAttempt
          paper={activePaper}
          questions={activeQuestions}
          onBack={() => { setActivePaper(null); setActiveQuestions(null); }}
        />
      </div>
    );
  }

  return (
    <div style={{ padding: "24px 32px" }}>
      {canSwitchGrade && (
        <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
          {["Grade 10", "Grade 12"].map((g) => (
            <button
              key={g}
              type="button"
              onClick={() => setGrade(g)}
              style={{
                padding: "6px 14px", borderRadius: 999, fontSize: ".82rem", fontWeight: 700, cursor: "pointer",
                border: g === grade ? "1px solid var(--accent, #7c3aed)" : "1px solid var(--border, #d6ddeb)",
                background: g === grade ? "rgba(124,58,237,0.12)" : "var(--panel, #fff)",
                color: g === grade ? "var(--accent, #7c3aed)" : "var(--text, #29324a)",
              }}
            >
              {g}
            </button>
          ))}
        </div>
      )}

      {loadingPaper && <p>Loading paper…</p>}
      {error && <p style={{ color: "#b3261e" }}>{error}</p>}
      {loading && <p>Loading…</p>}

      {!loading && years.length === 0 && (
        <p style={{ color: "var(--muted, #64748b)" }}>No sample papers available for {grade} yet.</p>
      )}

      {!fullAccess && (
        <div style={{
          display: "flex", alignItems: "center", gap: 10, background: "rgba(124,58,237,0.12)",
          border: "1px solid var(--accent, #7c3aed)", borderRadius: 10, padding: "10px 14px", marginBottom: 16,
        }}>
          <Sparkles size={16} color="var(--accent, #7c3aed)" />
          <span style={{ fontSize: ".85rem", color: "var(--text, #29324a)" }}>
            Free plan: the latest year, one subject. Upgrade to unlock every year and subject.
          </span>
        </div>
      )}

      {years.map(({ year, locked: yearLocked }) => {
        const isOpen = expandedYear === year;
        const subjects = subjectsByYear[year] || [];
        const papers = papersByYear[year] || [];
        const paperBySubject = Object.fromEntries(papers.map((p) => [p.subject, p]));
        return (
          <div key={year} style={{ border: "1px solid var(--border, #d6ddeb)", borderRadius: 10, marginBottom: 10, overflow: "hidden", opacity: yearLocked ? 0.6 : 1 }}>
            <button
              type="button"
              onClick={() => setExpandedYear(isOpen ? null : year)}
              style={{
                width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
                background: "var(--panel, #fff)", border: "none", padding: "12px 16px", cursor: "pointer",
                fontSize: ".95rem", fontWeight: 700, color: "var(--text, #29324a)",
              }}
            >
              <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                {year}
                {yearLocked && <Lock size={13} color="var(--muted, #64748b)" />}
              </span>
              {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            </button>
            {isOpen && (
              <div style={{ padding: "0 16px 14px" }}>
                {subjects.length === 0 && <p style={{ fontSize: ".85rem", color: "var(--muted, #64748b)" }}>Loading subjects…</p>}
                {subjects.map(({ subject, locked: subjectLocked }) => {
                  const paper = paperBySubject[subject];
                  const label = paper?.subject_variant ? `${subject} — ${paper.subject_variant}` : subject;
                  if (subjectLocked || !paper) {
                    return (
                      <div
                        key={subject}
                        style={{
                          display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%",
                          background: "var(--panel-soft, #f8f9fc)", border: "1px dashed var(--border, #e5e7eb)",
                          borderRadius: 8, padding: "10px 12px", marginTop: 8, fontSize: ".88rem",
                          fontWeight: 600, color: "var(--muted, #64748b)",
                        }}
                      >
                        <span>{label}</span>
                        <span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: ".76rem" }}>
                          <Lock size={12} /> Upgrade to unlock
                        </span>
                      </div>
                    );
                  }
                  return (
                    <button
                      key={subject}
                      type="button"
                      onClick={() => openPaper(paper)}
                      style={{
                        display: "block", width: "100%", textAlign: "left", background: "var(--panel-soft, #f8f9fc)",
                        border: "1px solid var(--border, #e5e7eb)", borderRadius: 8, padding: "10px 12px",
                        marginTop: 8, cursor: "pointer", fontSize: ".88rem", fontWeight: 600,
                        color: "var(--text, #29324a)",
                      }}
                    >
                      {label}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
