import { useEffect, useRef, useState } from "react";
import {
  BookOpen,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  XCircle,
  Eye,
  ExternalLink,
  Award,
  Lock,
  Sparkles,
  Clock,
  Target,
  Trophy,
  RotateCcw,
  TrendingUp,
  PlayCircle,
  History,
  Check,
  X,
  AlertTriangle,
  Save,
  Timer,
  Info,
  Image,
} from "lucide-react";

import {
  listBoardPaperYears,
  listBoardPaperSubjects,
  listBoardPapers,
  getBoardPaperQuestions,
  submitBoardPaperAttempt,
  listBoardPaperAttempts,
} from "../api/boardPapers";
import { getUserGrade } from "../utils/syllabusDefaults";
import { isAllAccessTestUser } from "../utils/testAccounts";

const TIMED_TEST_DURATION_MINUTES = 180; // every CBSE sample paper processed so far is "TIME: 3 hours"

const TT_PHASE_INTRO  = "intro";
const TT_PHASE_EXAM   = "exam";
const TT_PHASE_RESULT = "result";

function isMcqQuestion(question) {
  return question.question_type === "mcq" || question.question_type === "assertion_reason";
}

function formatTime(totalSeconds) {
  const s = Math.max(0, totalSeconds);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  const mm = String(m).padStart(2, "0");
  const ss = String(sec).padStart(2, "0");
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}

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

function QuestionCard({
  question,
  pdfUrl,
  // Timed Test mode passes controlled state down from the parent (it needs
  // every answer to compute the final score) and suppresses reveal/
  // correctness until the parent phase is RESULT. Self-study mode omits
  // all of these props and keeps its original uncontrolled behavior.
  mode = "study",
  selected: controlledSelected,
  onSelectOption,
  revealed: controlledRevealed,
  onReveal,
  showAnswers = true,
  selfMarked,
  onSelfMark,
}) {
  const isTimed = mode === "timed";
  const [internalSelected, setInternalSelected] = useState(null);
  const [internalRevealed, setInternalRevealed] = useState(false);
  const selected = isTimed ? controlledSelected : internalSelected;
  const revealed = isTimed ? controlledRevealed : internalRevealed;
  const isMcq = isMcqQuestion(question);
  const hasAnswer = isMcq ? selected !== null && selected !== undefined : revealed;
  // In timed EXAM phase (showAnswers=false) answers stay hidden even once
  // picked — only the RESULT phase (showAnswers=true) reveals correctness.
  const answered = showAnswers && hasAnswer;

  function selectOption(i) {
    if (isTimed) onSelectOption?.(i); else setInternalSelected(i);
  }
  function reveal() {
    if (isTimed) onReveal?.(); else setInternalRevealed(true);
  }

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
          pdfUrl ? (
            <a
              href={pdfUrl}
              target="_blank"
              rel="noreferrer"
              style={{
                display: "inline-flex", alignItems: "center", gap: 4,
                fontSize: ".7rem", fontWeight: 700, color: "#15803d",
                background: "rgba(22,163,74,0.1)", border: "1px solid rgba(22,163,74,0.25)",
                borderRadius: 999, padding: "2px 8px", textDecoration: "none", cursor: "pointer",
              }}
            >
              <Image size={11} color="#16a34a" />
              Needs PDF
            </a>
          ) : (
            <span style={{
              display: "inline-flex", alignItems: "center", gap: 4,
              fontSize: ".7rem", fontWeight: 700, color: "#15803d",
              background: "rgba(22,163,74,0.1)", border: "1px solid rgba(22,163,74,0.25)",
              borderRadius: 999, padding: "2px 8px",
            }}>
              <Image size={11} color="#16a34a" />
              Needs PDF
            </span>
          )
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
            } else if (!showAnswers && isSelected) {
              // Timed exam phase — answer is hidden, just show it's picked.
              bg = "rgba(124,58,237,0.1)"; border = "1.5px solid var(--accent, #7c3aed)"; color = "var(--accent, #7c3aed)";
            }
            return (
              <button
                key={i}
                type="button"
                disabled={answered}
                onClick={() => selectOption(i)}
                style={{
                  textAlign: "left", padding: "8px 12px", borderRadius: 8, background: bg, border, color,
                  fontSize: ".88rem", cursor: answered ? "default" : "pointer", fontWeight: (answered && (isCorrect || isSelected)) || (!showAnswers && isSelected) ? 700 : 500,
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

      {!isMcq && showAnswers && !revealed && (
        <button
          type="button"
          onClick={reveal}
          style={{
            display: "inline-flex", alignItems: "center", gap: 6, background: "var(--accent, #7c3aed)",
            color: "#fff", border: "none", borderRadius: 8, padding: "8px 14px", fontSize: ".85rem",
            fontWeight: 700, cursor: "pointer", marginTop: 4,
          }}
        >
          <Eye size={14} /> Show official answer
        </button>
      )}

      {!isMcq && !showAnswers && (
        <p style={{ fontSize: ".8rem", color: "var(--muted, #64748b)", fontStyle: "italic", margin: "4px 0 0" }}>
          Attempt this on paper — the official answer unlocks once you submit the test.
        </p>
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

      {/* Timed Test RESULT phase — subjective self-assessment, kept clearly
          separate from the objective MCQ score since this figure is
          student-reported, not verified. */}
      {isTimed && !isMcq && answered && (
        <div style={{ marginTop: 12, display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <span style={{ fontSize: ".8rem", fontWeight: 700, color: "var(--text, #29324a)" }}>Mark yourself:</span>
          <button
            type="button"
            onClick={() => onSelfMark?.(true)}
            style={{
              display: "inline-flex", alignItems: "center", gap: 5, padding: "5px 12px", borderRadius: 999,
              fontSize: ".8rem", fontWeight: 700, cursor: "pointer",
              border: selfMarked === true ? "1.5px solid #16a34a" : "1px solid var(--border, #d6ddeb)",
              background: selfMarked === true ? "rgba(34,197,94,0.15)" : "transparent",
              color: selfMarked === true ? "#15803d" : "var(--text, #29324a)",
            }}
          >
            <Check size={13} /> Correct
          </button>
          <button
            type="button"
            onClick={() => onSelfMark?.(false)}
            style={{
              display: "inline-flex", alignItems: "center", gap: 5, padding: "5px 12px", borderRadius: 999,
              fontSize: ".8rem", fontWeight: 700, cursor: "pointer",
              border: selfMarked === false ? "1.5px solid #ef4444" : "1px solid var(--border, #d6ddeb)",
              background: selfMarked === false ? "rgba(239,68,68,0.12)" : "transparent",
              color: selfMarked === false ? "#b3261e" : "var(--text, #29324a)",
            }}
          >
            <X size={13} /> Incorrect
          </button>
        </div>
      )}
    </div>
  );
}

function PastAttempts({ paper, onBack }) {
  const [attempts, setAttempts] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    listBoardPaperAttempts(paper.id)
      .then((result) => !cancelled && setAttempts(result?.attempts || []))
      .catch((err) => !cancelled && setError(err.message || "Could not load past attempts"));
    return () => { cancelled = true; };
  }, [paper.id]);

  return (
    <div>
      <button
        type="button"
        onClick={onBack}
        style={{ background: "none", border: "none", color: "var(--accent, #7c3aed)", fontSize: ".85rem", fontWeight: 600, cursor: "pointer", padding: 0, marginBottom: 14 }}
      >
        ← Back to paper
      </button>

      <h3 style={{ display: "flex", alignItems: "center", gap: 8, margin: "0 0 14px" }}>
        <History size={18} /> Past Timed Test attempts
      </h3>

      {error && <p style={{ color: "#b3261e" }}>{error}</p>}
      {attempts === null && !error && <p style={{ color: "var(--muted, #64748b)" }}>Loading…</p>}
      {attempts && attempts.length === 0 && (
        <p style={{ color: "var(--muted, #64748b)" }}>No Timed Test attempts yet for this paper.</p>
      )}

      {attempts && attempts.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {attempts.map((a) => {
            const mcqPct = a.mcq_max_score > 0 ? Math.round((a.mcq_score / a.mcq_max_score) * 100) : null;
            const subjPct = a.subjective_max_score > 0 ? Math.round((a.subjective_self_marked_correct / a.subjective_max_score) * 100) : null;
            const when = a.submitted_at ? new Date(a.submitted_at).toLocaleString() : "";
            const mins = a.time_taken_seconds != null ? Math.round(a.time_taken_seconds / 60) : null;
            return (
              <div key={a.id} style={{
                background: "var(--panel, #fff)", border: "1px solid var(--border, #d6ddeb)",
                borderRadius: 10, padding: "12px 16px", display: "flex", alignItems: "center",
                justifyContent: "space-between", flexWrap: "wrap", gap: 10,
              }}>
                <div>
                  <div style={{ fontSize: ".85rem", fontWeight: 700 }}>{when}</div>
                  {mins != null && (
                    <div style={{ fontSize: ".78rem", color: "var(--muted, #64748b)", display: "flex", alignItems: "center", gap: 4, marginTop: 2 }}>
                      <Clock size={12} /> {mins} min
                    </div>
                  )}
                </div>
                <div style={{ display: "flex", gap: 16 }}>
                  {mcqPct != null && (
                    <div style={{ textAlign: "right" }}>
                      <div style={{ fontSize: ".72rem", color: "var(--muted, #64748b)" }}>MCQ (auto-graded)</div>
                      <div style={{ fontSize: ".9rem", fontWeight: 700, color: "var(--accent, #7c3aed)" }}>
                        {a.mcq_score} / {a.mcq_max_score} ({mcqPct}%)
                      </div>
                    </div>
                  )}
                  {subjPct != null && (
                    <div style={{ textAlign: "right" }}>
                      <div style={{ fontSize: ".72rem", color: "var(--muted, #64748b)" }}>Subjective (self-marked)</div>
                      <div style={{ fontSize: ".9rem", fontWeight: 700 }}>
                        {a.subjective_self_marked_correct} / {a.subjective_max_score} ({subjPct}%)
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function TimedTestIntro({ paper, questions, onStart }) {
  const totalMarks = questions.reduce((sum, q) => sum + Number(q.marks || 1), 0);
  const mcqCount = questions.filter(isMcqQuestion).length;
  const subjCount = questions.length - mcqCount;

  return (
    <div style={{
      background: "var(--panel, #fff)", border: "1px solid var(--border, #d6ddeb)",
      borderRadius: 12, padding: "24px 28px", textAlign: "center",
    }}>
      <Clock size={28} color="var(--accent, #7c3aed)" style={{ marginBottom: 8 }} />
      <h3 style={{ margin: "0 0 6px" }}>Timed Test — {paper.subject}{paper.subject_variant ? ` (${paper.subject_variant})` : ""}</h3>
      <p style={{ color: "var(--muted, #64748b)", fontSize: ".88rem", margin: "0 0 18px" }}>
        Attempt the full paper under exam conditions. Answers stay hidden until you submit.
      </p>

      <div style={{ display: "flex", justifyContent: "center", gap: 24, marginBottom: 20, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: "1.3rem", fontWeight: 800 }}>{questions.length}</div>
          <div style={{ fontSize: ".76rem", color: "var(--muted, #64748b)" }}>Questions ({mcqCount} MCQ, {subjCount} subjective)</div>
        </div>
        <div>
          <div style={{ fontSize: "1.3rem", fontWeight: 800 }}>{totalMarks}</div>
          <div style={{ fontSize: ".76rem", color: "var(--muted, #64748b)" }}>Total marks</div>
        </div>
        <div>
          <div style={{ fontSize: "1.3rem", fontWeight: 800 }}>{TIMED_TEST_DURATION_MINUTES} min</div>
          <div style={{ fontSize: ".76rem", color: "var(--muted, #64748b)" }}>Duration (3 hours, same as the real exam)</div>
        </div>
      </div>

      <button
        type="button"
        onClick={onStart}
        style={{
          display: "inline-flex", alignItems: "center", gap: 8, background: "var(--accent, #7c3aed)",
          color: "#fff", border: "none", borderRadius: 8, padding: "10px 22px", fontSize: ".92rem",
          fontWeight: 700, cursor: "pointer",
        }}
      >
        <PlayCircle size={16} /> Start Timed Test
      </button>
    </div>
  );
}

function TimedTestAttempt({ paper, questions, grade, onExit }) {
  const [phase, setPhase] = useState(TT_PHASE_INTRO);
  const [answers, setAnswers] = useState({}); // question_number -> option index
  const [revealedSubjective, setRevealedSubjective] = useState({}); // question_number -> bool
  const [selfMarks, setSelfMarks] = useState({}); // question_number -> bool
  const [secondsLeft, setSecondsLeft] = useState(TIMED_TEST_DURATION_MINUTES * 60);
  const [startedAt, setStartedAt] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState("");
  const autoSubmittedRef = useRef(false);

  // ── Timer — mirrors MockTestPage's countdown pattern ───────────────────
  useEffect(() => {
    if (phase !== TT_PHASE_EXAM || secondsLeft <= 0) return;
    const t = setInterval(() => setSecondsLeft((p) => Math.max(0, p - 1)), 1000);
    return () => clearInterval(t);
  }, [phase, secondsLeft]);

  useEffect(() => {
    if (phase === TT_PHASE_EXAM && secondsLeft === 0 && !autoSubmittedRef.current) {
      autoSubmittedRef.current = true;
      submitExam();
    }
  }, [phase, secondsLeft]);

  function startExam() {
    setStartedAt(new Date());
    setSecondsLeft(TIMED_TEST_DURATION_MINUTES * 60);
    setPhase(TT_PHASE_EXAM);
  }

  function submitExam() {
    setPhase(TT_PHASE_RESULT);
  }

  const mcqQuestions = questions.filter(isMcqQuestion);
  const subjQuestions = questions.filter((q) => !isMcqQuestion(q));
  const mcqMaxScore = mcqQuestions.reduce((sum, q) => sum + Number(q.marks || 1), 0);
  const subjectiveMaxScore = subjQuestions.reduce((sum, q) => sum + Number(q.marks || 1), 0);

  const mcqScore = mcqQuestions.reduce((sum, q) => {
    const sel = answers[q.question_number];
    if (sel == null) return sum;
    return q.options?.[sel] === q.answer_text ? sum + Number(q.marks || 1) : sum;
  }, 0);

  const subjectiveScore = subjQuestions.reduce((sum, q) => {
    return selfMarks[q.question_number] === true ? sum + Number(q.marks || 1) : sum;
  }, 0);

  const selfMarkedCount = subjQuestions.filter((q) => selfMarks[q.question_number] != null).length;
  const timeTakenSeconds = startedAt ? Math.max(0, Math.round((Date.now() - startedAt.getTime()) / 1000)) : null;

  async function handleSaveAttempt() {
    setSaving(true);
    setSaveError("");
    try {
      const answerPayload = {};
      questions.forEach((q) => {
        if (isMcqQuestion(q)) {
          if (answers[q.question_number] != null) {
            answerPayload[q.question_number] = { selected: q.options?.[answers[q.question_number]] };
          }
        } else if (selfMarks[q.question_number] != null) {
          answerPayload[q.question_number] = { self_marked_correct: selfMarks[q.question_number] };
        }
      });
      await submitBoardPaperAttempt(paper.id, {
        grade,
        started_at: (startedAt || new Date()).toISOString(),
        time_taken_seconds: timeTakenSeconds,
        mcq_score: mcqScore,
        mcq_max_score: mcqMaxScore,
        subjective_self_marked_correct: subjectiveScore,
        subjective_max_score: subjectiveMaxScore,
        answers: answerPayload,
      });
      setSaved(true);
    } catch (err) {
      setSaveError(err.message || "Could not save this attempt. Your score above is still accurate.");
    } finally {
      setSaving(false);
    }
  }

  if (phase === TT_PHASE_INTRO) {
    return (
      <div>
        <button
          type="button"
          onClick={onExit}
          style={{ background: "none", border: "none", color: "var(--accent, #7c3aed)", fontSize: ".85rem", fontWeight: 600, cursor: "pointer", padding: 0, marginBottom: 14 }}
        >
          ← Back to paper
        </button>
        <TimedTestIntro paper={paper} questions={questions} onStart={startExam} />
      </div>
    );
  }

  if (phase === TT_PHASE_EXAM) {
    return (
      <div>
        <div style={{
          position: "sticky", top: 0, zIndex: 100, background: "var(--bg, #fff)",
          borderBottom: "1px solid var(--border, #d6ddeb)", padding: "10px 4px",
          display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10,
          marginBottom: 14,
        }}>
          <strong style={{ fontSize: ".9rem" }}>
            {paper.subject}{paper.subject_variant ? ` — ${paper.subject_variant}` : ""} · Timed Test
          </strong>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{
              display: "inline-flex", alignItems: "center", gap: 6, fontWeight: 700, fontSize: "1rem",
              padding: "4px 14px", borderRadius: 8,
              background: secondsLeft < 300 ? "rgba(239,68,68,0.12)" : "rgba(124,58,237,0.1)",
              color: secondsLeft < 300 ? "#dc2626" : "var(--accent, #7c3aed)",
            }}>
              <Clock size={15} /> {formatTime(secondsLeft)}
            </div>
            <button
              type="button"
              onClick={submitExam}
              style={{
                background: "var(--accent, #7c3aed)", color: "#fff", border: "none", borderRadius: 8,
                padding: "7px 18px", fontSize: ".85rem", fontWeight: 700, cursor: "pointer",
              }}
            >
              Submit Test
            </button>
          </div>
        </div>

        {secondsLeft === 0 && (
          <div style={{
            display: "flex", alignItems: "center", gap: 8, background: "rgba(239,68,68,0.1)",
            border: "1px solid #ef4444", borderRadius: 8, padding: "8px 14px", marginBottom: 12, fontSize: ".85rem", color: "#b3261e",
          }}>
            <AlertTriangle size={15} /> Time is over — submitting your test…
          </div>
        )}

        {questions.map((q) => (
          <QuestionCard
            key={q.id}
            question={q}
            pdfUrl={paper.question_paper_url}
            mode="timed"
            showAnswers={false}
            selected={answers[q.question_number] ?? null}
            onSelectOption={(i) => setAnswers((prev) => ({ ...prev, [q.question_number]: i }))}
          />
        ))}

        <button
          type="button"
          onClick={submitExam}
          style={{
            display: "inline-flex", alignItems: "center", gap: 8, background: "var(--accent, #7c3aed)",
            color: "#fff", border: "none", borderRadius: 8, padding: "10px 22px", fontSize: ".9rem",
            fontWeight: 700, cursor: "pointer", marginTop: 8,
          }}
        >
          <CheckCircle2 size={16} /> Submit Test
        </button>
      </div>
    );
  }

  // PHASE: RESULT
  const mcqPct = mcqMaxScore > 0 ? Math.round((mcqScore / mcqMaxScore) * 100) : null;

  return (
    <div>
      <div style={{
        background: "var(--panel, #fff)", border: "1px solid var(--border, #d6ddeb)",
        borderRadius: 12, padding: "20px 24px", marginBottom: 18,
      }}>
        <h3 style={{ display: "flex", alignItems: "center", gap: 8, margin: "0 0 4px" }}>
          <Trophy size={18} color="var(--accent, #7c3aed)" /> Test submitted
        </h3>
        <p style={{ color: "var(--muted, #64748b)", fontSize: ".85rem", margin: "0 0 16px" }}>
          MCQs are auto-graded. Subjective questions need your own honest self-assessment below —
          the two scores are kept separate since only one of them is objectively verified.
        </p>

        <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
          <div style={{ background: "rgba(124,58,237,0.08)", borderRadius: 10, padding: "12px 18px", flex: "1 1 200px" }}>
            <div style={{ fontSize: ".76rem", color: "var(--muted, #64748b)", display: "flex", alignItems: "center", gap: 4 }}>
              <CheckCircle2 size={13} /> MCQ score (auto-graded)
            </div>
            <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "var(--accent, #7c3aed)" }}>
              {mcqScore} / {mcqMaxScore}{mcqPct != null && ` (${mcqPct}%)`}
            </div>
          </div>
          {subjQuestions.length > 0 && (
            <div style={{ background: "rgba(22,163,74,0.08)", borderRadius: 10, padding: "12px 18px", flex: "1 1 200px" }}>
              <div style={{ fontSize: ".76rem", color: "var(--muted, #64748b)", display: "flex", alignItems: "center", gap: 4 }}>
                <TrendingUp size={13} /> Subjective score (self-marked, {selfMarkedCount}/{subjQuestions.length} reviewed)
              </div>
              <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "#16a34a" }}>
                {subjectiveScore} / {subjectiveMaxScore}
              </div>
            </div>
          )}
          {timeTakenSeconds != null && (
            <div style={{ background: "rgba(8,145,178,0.08)", borderRadius: 10, padding: "12px 18px", flex: "1 1 160px" }}>
              <div style={{ fontSize: ".76rem", color: "var(--muted, #64748b)", display: "flex", alignItems: "center", gap: 4 }}>
                <Clock size={13} /> Time taken
              </div>
              <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "#0891b2" }}>
                {Math.floor(timeTakenSeconds / 60)}m {timeTakenSeconds % 60}s
              </div>
            </div>
          )}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 18, flexWrap: "wrap" }}>
          <button
            type="button"
            onClick={handleSaveAttempt}
            disabled={saving || saved}
            style={{
              display: "inline-flex", alignItems: "center", gap: 8,
              background: saved ? "#16a34a" : "var(--accent, #7c3aed)", color: "#fff", border: "none",
              borderRadius: 8, padding: "9px 20px", fontSize: ".88rem", fontWeight: 700,
              cursor: saving || saved ? "default" : "pointer", opacity: saving ? 0.7 : 1,
            }}
          >
            {saved ? <><CheckCircle2 size={15} /> Attempt saved</> : <><Save size={15} /> {saving ? "Saving…" : "Save this attempt"}</>}
          </button>
          <button
            type="button"
            onClick={onExit}
            style={{ background: "none", border: "1px solid var(--border, #d6ddeb)", borderRadius: 8, padding: "9px 18px", fontSize: ".85rem", fontWeight: 600, cursor: "pointer", color: "var(--text, #29324a)" }}
          >
            <RotateCcw size={13} style={{ marginRight: 6, verticalAlign: "-2px" }} /> Back to paper
          </button>
          {saveError && <span style={{ color: "#b3261e", fontSize: ".8rem" }}>{saveError}</span>}
        </div>
      </div>

      <h4 style={{ margin: "0 0 10px" }}>Review</h4>
      {questions.map((q) => (
        <QuestionCard
          key={q.id}
          question={q}
          pdfUrl={paper.question_paper_url}
          mode="timed"
          showAnswers
          selected={answers[q.question_number] ?? null}
          revealed={!!revealedSubjective[q.question_number]}
          onReveal={() => setRevealedSubjective((prev) => ({ ...prev, [q.question_number]: true }))}
          selfMarked={selfMarks[q.question_number] ?? null}
          onSelfMark={(val) => setSelfMarks((prev) => ({ ...prev, [q.question_number]: val }))}
        />
      ))}
    </div>
  );
}

function PaperAttempt({ paper, questions, grade, onBack }) {
  const [subView, setSubView] = useState("study"); // "study" | "timed" | "history"

  if (subView === "timed") {
    return <TimedTestAttempt paper={paper} questions={questions} grade={grade} onExit={() => setSubView("study")} />;
  }
  if (subView === "history") {
    return <PastAttempts paper={paper} onBack={() => setSubView("study")} />;
  }

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

      <div style={{ display: "flex", gap: 10, marginBottom: 18, flexWrap: "wrap" }}>
        <button
          type="button"
          onClick={() => setSubView("timed")}
          style={{
            display: "inline-flex", alignItems: "center", gap: 8, background: "var(--accent, #7c3aed)",
            color: "#fff", border: "none", borderRadius: 8, padding: "9px 18px", fontSize: ".85rem",
            fontWeight: 700, cursor: "pointer",
          }}
        >
          <PlayCircle size={15} /> Start Timed Test
        </button>
        <button
          type="button"
          onClick={() => setSubView("history")}
          style={{
            display: "inline-flex", alignItems: "center", gap: 8, background: "transparent",
            border: "1px solid var(--border, #d6ddeb)", borderRadius: 8, padding: "9px 18px", fontSize: ".85rem",
            fontWeight: 700, cursor: "pointer", color: "var(--text, #29324a)",
          }}
        >
          <History size={15} /> Past Attempts
        </button>
      </div>

      <p style={{ fontSize: ".8rem", color: "var(--muted, #64748b)", margin: "0 0 14px" }}>
        Self-study mode — answer at your own pace below, or switch to a Timed Test for a real
        exam simulation with a {TIMED_TEST_DURATION_MINUTES}-minute countdown.
      </p>

      <div style={{
        display: "flex", alignItems: "flex-start", gap: 8,
        background: "var(--panel-soft, #f8f9fc)", border: "1px solid var(--border, #e5e7eb)",
        borderRadius: 8, padding: "10px 14px", marginBottom: 16,
      }}>
        <Info size={13} color="var(--muted, #64748b)" style={{ marginTop: 2, flexShrink: 0 }} />
        <p style={{ margin: 0, fontSize: ".78rem", color: "var(--muted, #64748b)", lineHeight: 1.6 }}>
          Official CBSE question papers and marking schemes, sourced from cbseacademic.nic.in.
          Answers verified against the marking scheme. Questions with{" "}
          <Image size={12} color="#16a34a" style={{ display: "inline", verticalAlign: "-1px" }} />{" "}
          require the official PDF for complete context — use the PDF link above to verify.
        </p>
      </div>

      {questions.map((q) => (
        <QuestionCard key={q.id} question={q} pdfUrl={paper.question_paper_url} />
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
          grade={grade}
          onBack={() => { setActivePaper(null); setActiveQuestions(null); }}
        />
      </div>
    );
  }

  return (
    <div style={{ padding: "24px 32px" }}>

      {/* ── Feature strip ─────────────────────────────────────────────── */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
        gap: 14,
        marginBottom: 28,
      }}>
        {[
          {
            Icon: BookOpen,
            color: "#7c3aed",
            bg: "rgba(124,58,237,0.10)",
            title: "Decade of Papers",
            desc: "200+ official CBSE papers from 2015–2025, every subject, every year.",
          },
          {
            Icon: Timer,
            color: "#0891b2",
            bg: "rgba(8,145,178,0.10)",
            title: "Simulate Real Exams",
            desc: "Timed mock tests that mirror the actual board exam format, question by question.",
          },
          {
            Icon: CheckCircle2,
            color: "#16a34a",
            bg: "rgba(22,163,74,0.10)",
            title: "Every Mark Explained",
            desc: "Official answers with the full marking scheme for every single question.",
          },
          {
            Icon: Target,
            color: "#dc2626",
            bg: "rgba(220,38,38,0.10)",
            title: "Board-Ready Practice",
            desc: "The only practice that matches exactly what CBSE actually asks in the exam.",
          },
        ].map(({ Icon, color, bg, title, desc }) => (
          <div
            key={title}
            style={{
              background: "var(--panel, #fff)",
              border: "1px solid var(--border, #e5e7eb)",
              borderRadius: 14,
              padding: "18px 16px",
              display: "flex",
              flexDirection: "column",
              gap: 10,
            }}
          >
            <span style={{
              display: "inline-flex", alignItems: "center", justifyContent: "center",
              width: 40, height: 40, borderRadius: 10, background: bg,
            }}>
              <Icon size={20} color={color} strokeWidth={2.2} />
            </span>
            <strong style={{ fontSize: ".95rem", lineHeight: 1.3 }}>{title}</strong>
            <p style={{ margin: 0, fontSize: ".82rem", color: "var(--muted, #64748b)", lineHeight: 1.55 }}>{desc}</p>
          </div>
        ))}
      </div>

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
