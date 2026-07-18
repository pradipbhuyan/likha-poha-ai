/**
 * Ask Doubt tab — AI-powered doubt solving for CBSE students.
 *
 * Uses POST /api/doubt/answer — same endpoint as the web DoubtPage.
 * Features:
 *  - Grade / Subject / Chapter context selectors
 *  - 4 answer style chips (Explain simply, Give example, Step by step, Create practice)
 *  - Suggested question chips from DKB
 *  - Full answer rendering with math-aware markdown (LaTeX → Unicode)
 *  - Follow-up question panel
 *  - Recent doubt history
 */
import { useEffect, useRef, useState } from "react";
import {
  View, Text, TextInput, ScrollView, StyleSheet,
  TouchableOpacity, ActivityIndicator, KeyboardAvoidingView,
  Platform, Alert,
} from "react-native";
import Markdown from "react-native-markdown-display";
import { authFetch } from "../../lib/authFetch";
import { BRAND_COLOR } from "../../constants";
import { STREAM_SUBJECTS as STREAM_SUBJECTS_DOUBT } from "@likhapoha/shared/utils/subjectAccess";

// ── Shared math utilities (inline — mirrors mobile/app/(tabs)/lessons.tsx) ───
function mathToUnicode(latex: string): string {
  return latex
    .replace(/\\text\{([^}]+)\}/g, "$1")
    .replace(/\\frac\{([^}]+)\}\{([^}]+)\}/g, "($1)/($2)")
    .replace(/\\sqrt\{([^}]+)\}/g, "√($1)")
    .replace(/\\sqrt\s*([a-zA-Z0-9])/g, "√$1")
    .replace(/\^\{2\}/g, "²").replace(/\^2(?![0-9{])/g, "²")
    .replace(/\^\{3\}/g, "³").replace(/\^3(?![0-9{])/g, "³")
    .replace(/\^\{n\}/g, "ⁿ").replace(/\^\{([^}]+)\}/g, "^($1)")
    .replace(/\_\{1\}/g, "₁").replace(/_1(?![0-9])/g, "₁")
    .replace(/\_\{2\}/g, "₂").replace(/_2(?![0-9])/g, "₂")
    .replace(/\_\{0\}/g, "₀").replace(/_0(?![0-9])/g, "₀")
    .replace(/\_\{([^}]+)\}/g, "_($1)")
    .replace(/\\times/g, "×").replace(/\\cdot/g, "·")
    .replace(/\\div/g, "÷").replace(/\\pm/g, "±")
    .replace(/\\leq/g, "≤").replace(/\\geq/g, "≥").replace(/\\neq/g, "≠")
    .replace(/\\approx/g, "≈").replace(/\\infty/g, "∞")
    .replace(/\\rightarrow/g, "→").replace(/\\leftarrow/g, "←")
    .replace(/\\pi/g, "π").replace(/\\alpha/g, "α").replace(/\\beta/g, "β")
    .replace(/\\gamma/g, "γ").replace(/\\delta/g, "δ").replace(/\\theta/g, "θ")
    .replace(/\\lambda/g, "λ").replace(/\\mu/g, "μ").replace(/\\sigma/g, "σ")
    .replace(/\\Sigma/g, "Σ").replace(/\\Delta/g, "Δ").replace(/\\omega/g, "ω")
    .replace(/\\sin/g, "sin").replace(/\\cos/g, "cos").replace(/\\tan/g, "tan")
    .replace(/\\log/g, "log").replace(/\\ln/g, "ln").replace(/\\int/g, "∫")
    .replace(/\\[a-zA-Z]+\{([^}]+)\}/g, "$1")
    .replace(/\\[a-zA-Z]+/g, "")
    .replace(/\{([^}]*)\}/g, "$1")
    .replace(/\s+/g, " ").trim();
}

const ANSWER_MARKDOWN_STYLES = {
  body: { color: "#1f2937", fontSize: 15, lineHeight: 24 },
  heading1: { color: "#111827", fontWeight: "800" as const, fontSize: 18, marginTop: 12, marginBottom: 6 },
  heading2: { color: "#111827", fontWeight: "700" as const, fontSize: 16, marginTop: 10, marginBottom: 4 },
  heading3: { color: "#111827", fontWeight: "700" as const, fontSize: 15, marginTop: 8, marginBottom: 4 },
  strong: { fontWeight: "700" as const, color: "#111827" },
  em: { fontStyle: "italic" as const, color: "#374151" },
  bullet_list: { marginVertical: 6 },
  ordered_list: { marginVertical: 6 },
  list_item: { marginBottom: 4 },
  bullet_list_icon: { color: BRAND_COLOR, fontWeight: "700" as const },
  code_inline: { backgroundColor: "#f3f4f6", color: "#1e40af", borderRadius: 4, fontSize: 13 },
  fence: { backgroundColor: "#f8fafc", borderRadius: 8, padding: 12, fontSize: 13, fontFamily: "monospace" },
  blockquote: { backgroundColor: "rgba(99,102,241,.07)", borderLeftWidth: 3, borderLeftColor: BRAND_COLOR, paddingLeft: 12, marginVertical: 6, borderRadius: 4 },
  paragraph: { marginBottom: 8, lineHeight: 24 },
};

// ── Structured visual renderer (flow / steps / cycle) ────────────────────────
function StructuredVisual({ visual }: { visual: { type: string; title?: string; items: string[]; note?: string } }) {
  const isFlow = visual.type === "flow" || visual.type === "steps";
  return (
    <View style={{ backgroundColor: "rgba(99,102,241,.06)", borderRadius: 12, padding: 14, marginVertical: 8, borderWidth: 1, borderColor: "rgba(99,102,241,.2)" }}>
      {visual.title ? (
        <Text style={{ fontSize: 13, fontWeight: "800", color: BRAND_COLOR, textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 10 }}>
          {isFlow ? "📊" : visual.type === "cycle" ? "🔄" : "📋"} {visual.title}
        </Text>
      ) : null}
      {visual.items.map((item, idx) => (
        <View key={idx}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 6 }}>
            <View style={{ width: 26, height: 26, borderRadius: 6, backgroundColor: BRAND_COLOR, alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
              <Text style={{ color: "#fff", fontSize: 12, fontWeight: "800" }}>{idx + 1}</Text>
            </View>
            <Text style={{ flex: 1, fontSize: 14, fontWeight: "600", color: "#111827", lineHeight: 20 }}>{item}</Text>
          </View>
          {isFlow && idx < visual.items.length - 1 && (
            <Text style={{ textAlign: "center", color: BRAND_COLOR, fontSize: 18, marginBottom: 4 }}>↓</Text>
          )}
        </View>
      ))}
      {visual.note ? (
        <View style={{ marginTop: 8, backgroundColor: "rgba(99,102,241,.08)", borderRadius: 8, padding: 8 }}>
          <Text style={{ fontSize: 12, color: "#374151", fontStyle: "italic", lineHeight: 17 }}>💡 {visual.note}</Text>
        </View>
      ) : null}
    </View>
  );
}

// Try to parse a structured visual JSON block from a string
function tryParseVisual(text: string): { type: string; title?: string; items: string[]; note?: string } | null {
  try {
    const v = JSON.parse(text.trim());
    if (v && typeof v === "object" && ["flow","steps","cycle","compare"].includes(v.type) && Array.isArray(v.items) && v.items.length >= 2) {
      return v;
    }
  } catch { /* not JSON */ }
  return null;
}

function MathAnswer({ content }: { content: string }) {
  // Split on $$...$$ display math AND code fences that might contain visual JSON
  const DISPLAY_MATH_RE = /(\$\$[\s\S]+?\$\$)/g;
  const CODE_FENCE_RE = /(```[\s\S]*?```)/g;

  // First strip any JSON visual blocks from the content and collect them
  const parts = content.split(/(\$\$[\s\S]+?\$\$|```[\s\S]*?```)/g);
  return (
    <View>
      {parts.map((part, i) => {
        if (part.startsWith("$$") && part.endsWith("$$")) {
          const rendered = mathToUnicode(part.slice(2, -2).trim());
          return (
            <View key={i} style={{ flexDirection: "row", alignItems: "flex-start", gap: 8, borderLeftWidth: 3, borderLeftColor: BRAND_COLOR, backgroundColor: "rgba(99,102,241,.06)", borderRadius: 8, padding: 12, marginVertical: 6 }}>
              <Text style={{ fontSize: 16 }}>📐</Text>
              <Text style={{ flex: 1, fontSize: 15, fontFamily: "monospace", fontWeight: "600", color: "#111827", lineHeight: 22 }}>{rendered}</Text>
            </View>
          );
        }
        // Code fence — check if it contains a visual JSON block
        if (part.startsWith("```")) {
          const inner = part.replace(/^```[^\n]*\n?/, "").replace(/```$/, "").trim();
          const visual = tryParseVisual(inner);
          if (visual) return <StructuredVisual key={i} visual={visual} />;
          // Regular code block
          return <Markdown key={i} style={ANSWER_MARKDOWN_STYLES}>{part}</Markdown>;
        }
        // Inline JSON visual (no code fence, just raw JSON in text)
        const inlineVisual = tryParseVisual(part.trim());
        if (inlineVisual) return <StructuredVisual key={i} visual={inlineVisual} />;
        const processed = part.replace(/\$([^$\n]+)\$/g, (_m, l) => mathToUnicode(l));
        if (!processed.trim()) return null;
        return <Markdown key={i} style={ANSWER_MARKDOWN_STYLES}>{processed}</Markdown>;
      })}
    </View>
  );
}

// ── Answer style options ───────────────────────────────────────────────────────
const ANSWER_STYLES = [
  { key: "simple",   label: "Explain simply",        instruction: "Explain this in simple language first." },
  { key: "example",  label: "Give example",           instruction: "Include one clear example." },
  { key: "steps",    label: "Step by step",           instruction: "Show the answer step by step." },
  { key: "practice", label: "Create practice Q",      instruction: "End with one similar practice question." },
];

const GRADES = ["Grade 5","Grade 6","Grade 7","Grade 8","Grade 9","Grade 10","Grade 11","Grade 12"];
const SUBJECTS = ["Mathematics","Science","Social Science","English","Hindi","Physics","Chemistry","Biology"];

// ── Main Screen ───────────────────────────────────────────────────────────────
export default function DoubtScreen() {
  const [grade, setGrade]         = useState("Grade 9");
  const [subject, setSubject]     = useState("");
  const [studentGrade, setStudentGrade] = useState<string | null>(null);
  const [cbseSubjects, setCbseSubjects] = useState<string[]>([]);
  const [studentStream, setStudentStream] = useState<string>("");
  const [hasFullAccess, setHasFullAccess] = useState(false);
  const [question, setQuestion]   = useState("");
  const [answerStyle, setStyle]   = useState("simple");
  const [answer, setAnswer]       = useState("");
  const [asking, setAsking]       = useState(false);
  const [error, setError]         = useState("");
  const [suggestions, setSuggs]   = useState<{ id: string; question: string }[]>([]);
  const [history, setHistory]     = useState<{ id: string; question: string; answer: string; grade: string; subject?: string; created_at: string }[]>([]);
  const [followUp, setFollowUp]   = useState("");
  const [fuAsking, setFuAsking]   = useState(false);
  const [fuAnswer, setFuAnswer]   = useState("");
  const [showHistory, setShowHist] = useState(false);
  const scrollRef = useRef<ScrollView>(null);

  // Load student grade + subjects on mount
  useEffect(() => {
    authFetch("/api/auth/me").then((me: any) => {
      const sg = me?.grade ?? null;
      setStudentGrade(sg);
      if (sg) setGrade(sg);
      const subs = me?.cbse_subjects ?? [];
      setCbseSubjects(subs);
      setStudentStream(me?.stream ?? "");
    }).catch(() => {});
    authFetch("/api/subscription/features").then((d: any) => {
      setHasFullAccess(d?.has_full_access ?? false);
    }).catch(() => {});
  }, []); // eslint-disable-line

  // Grade lock for free users
  const isGradeLocked = studentGrade !== null && !hasFullAccess;
  // Subject list: use cbse_subjects if available, fall back to stream-derived
  const isGrade1112 = grade === "Grade 11" || grade === "Grade 12";
  const effectiveSubjectsDoubt = cbseSubjects.length > 0 ? cbseSubjects
    : (studentStream && STREAM_SUBJECTS_DOUBT[studentStream] ? STREAM_SUBJECTS_DOUBT[studentStream] : []);
  const availableSubjects = isGrade1112 && effectiveSubjectsDoubt.length > 0 ? effectiveSubjectsDoubt : SUBJECTS;

  // Load suggestions when grade/subject changes
  useEffect(() => {
    const params = new URLSearchParams({ grade, mode: "CBSE", limit: "5" });
    if (subject) params.set("subject", subject);
    authFetch(`/api/doubt/suggestions?${params.toString()}`)
      .then((r: any) => setSuggs(Array.isArray(r?.doubt_suggestions) ? r.doubt_suggestions : []))
      .catch(() => setSuggs([]));
  }, [grade, subject]);

  // Load recent history on mount
  useEffect(() => {
    authFetch("/api/doubt/history?limit=10")
      .then((r: any) => setHistory(r.history || []))
      .catch(() => setHistory([]));
  }, []);

  function buildPayload(q: string, save = true) {
    const style = ANSWER_STYLES.find(s => s.key === answerStyle);
    const enriched = style ? `${q.trim()}\n\nPreferred answer style: ${style.instruction}` : q.trim();
    return {
      grade, mode: "CBSE", board: "CBSE",
      subject: subject || "",
      chapter: "",
      question: enriched,
      display_question: q.trim(),
      save_to_history: save,
    };
  }

  function buildPayloadFromSuggestion(s: { id: string; question: string }, save = true) {
    const style = ANSWER_STYLES.find(st => st.key === answerStyle);
    const enriched = style ? `${s.question.trim()}\n\nPreferred answer style: ${style.instruction}` : s.question.trim();
    return {
      grade, mode: "CBSE", board: "CBSE",
      subject: subject || "",
      chapter: "",
      question: enriched,
      display_question: s.question.trim(),
      dkb_id: s.id,  // Direct DKB lookup — bypasses text matching entirely
      save_to_history: save,
    };
  }

  async function handleAsk(overrideQ?: string) {
    const q = overrideQ ?? question;
    if (!q.trim()) { setError("Please type your question."); return; }
    setAsking(true); setError(""); setAnswer(""); setFuAnswer(""); setFollowUp("");
    try {
      const res: any = await authFetch("/api/doubt/answer", {
        method: "POST",
        body: JSON.stringify(buildPayload(q)),
      });
      if (!res.success) { setError(res.message || "Could not answer."); return; }
      setAnswer(res.answer || "");
      // Refresh history
      authFetch("/api/doubt/history?limit=10")
        .then((r: any) => setHistory(r.history || []))
        .catch(() => {});
      setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 300);
    } catch (e: any) {
      setError(e.message || "Could not answer. Please try again.");
    } finally {
      setAsking(false);
    }
  }

  async function handleFollowUp() {
    if (!followUp.trim() || !question.trim()) return;
    setFuAsking(true); setFuAnswer("");
    try {
      const fuQ = `Deeper follow-up: ${followUp.trim()}\n\nOriginal doubt: ${question.trim()}`;
      const res: any = await authFetch("/api/doubt/answer", {
        method: "POST",
        body: JSON.stringify(buildPayload(fuQ, false)),
      });
      if (res.success) setFuAnswer(res.answer || "");
      else setError(res.message || "Could not answer follow-up.");
    } catch (e: any) {
      setError(e.message || "Follow-up failed.");
    } finally {
      setFuAsking(false);
    }
  }

  function formatDate(v: string) {
    if (!v) return "";
    return new Date(v).toLocaleDateString([], { month: "short", day: "numeric" });
  }

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView ref={scrollRef} style={styles.container} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">

        {/* ── Page title ── */}
        <Text style={styles.pageTitle}>💬 Ask AI Tutor</Text>
        <Text style={styles.pageSubtitle}>Ask any CBSE doubt — concepts, problems, textbook questions</Text>

        {/* ── Grade selector ── */}
        <View style={{ flexDirection:"row", justifyContent:"space-between", alignItems:"center", marginBottom:4 }}>
          <Text style={styles.label}>Grade</Text>
          {isGradeLocked && studentGrade && <Text style={{ fontSize:11, color:BRAND_COLOR, fontWeight:"600" }}>🔒 {studentGrade}</Text>}
        </View>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipRow}>
          {GRADES.map(g => {
            const locked = isGradeLocked && g !== studentGrade;
            const active = grade === g;
            return (
              <TouchableOpacity key={g}
                style={[styles.chip, active && styles.chipActive, locked && { borderColor:"#e5e7eb", backgroundColor:"#f9fafb", opacity:0.55 }]}
                onPress={() => !locked && setGrade(g)} disabled={locked}>
                <Text style={[styles.chipText, active && styles.chipTextActive, locked && { color:"#9ca3af" }]}>{g.replace("Grade ", "")}</Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>

        {/* ── Subject selector (optional) ── */}
        <Text style={styles.label}>Subject <Text style={styles.optional}>(optional)</Text></Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipRow}>
          <TouchableOpacity style={[styles.chip, subject === "" && styles.chipActive]} onPress={() => setSubject("")}>
            <Text style={[styles.chipText, subject === "" && styles.chipTextActive]}>Any</Text>
          </TouchableOpacity>
          {availableSubjects.map(s => (
            <TouchableOpacity key={s} style={[styles.chip, subject === s && styles.chipActive]} onPress={() => setSubject(s)}>
              <Text style={[styles.chipText, subject === s && styles.chipTextActive]}>{s}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        {/* ── Answer style ── */}
        <Text style={styles.label}>How should I explain?</Text>
        <View style={styles.styleRow}>
          {ANSWER_STYLES.map(opt => (
            <TouchableOpacity key={opt.key} style={[styles.styleBtn, answerStyle === opt.key && styles.styleBtnActive]} onPress={() => setStyle(opt.key)}>
              <Text style={[styles.styleBtnText, answerStyle === opt.key && styles.styleBtnTextActive]}>{opt.label}</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* ── Suggested question chips ── */}
        {suggestions.length > 0 && (
          <View style={styles.suggestBox}>
            <Text style={styles.suggestLabel}>💡 Common questions:</Text>
            <View style={styles.suggestChips}>
              {suggestions.map(s => (
                <TouchableOpacity key={s.id} style={styles.suggestChip}
                  onPress={() => {
                    setQuestion(s.question);
                    // Use dkb_id for direct lookup — no text matching needed
                    setAsking(true); setError(""); setAnswer(""); setFuAnswer(""); setFollowUp("");
                    authFetch("/api/doubt/answer", {
                      method: "POST",
                      body: JSON.stringify(buildPayloadFromSuggestion(s)),
                    }).then((res: any) => {
                      if (res?.success) setAnswer(res.answer || "");
                      else setError(res?.message || "Could not answer.");
                      setTimeout(() => {}, 300);
                    }).catch((e: any) => setError(e?.message || "Could not answer."))
                     .finally(() => setAsking(false));
                  }}>
                  <Text style={styles.suggestChipText} numberOfLines={2}>{s.question}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        )}

        {/* ── Question input ── */}
        <TextInput
          style={styles.questionInput}
          multiline
          numberOfLines={5}
          placeholder="Type your doubt here… e.g. Explain Newton's 3rd law with examples."
          placeholderTextColor="#9ca3af"
          value={question}
          onChangeText={setQuestion}
          textAlignVertical="top"
        />

        <TouchableOpacity style={[styles.askBtn, asking && styles.askBtnDisabled]} onPress={() => handleAsk()} disabled={asking}>
          {asking ? <ActivityIndicator color="#fff" /> : <Text style={styles.askBtnText}>✨ Ask AI Tutor</Text>}
        </TouchableOpacity>

        {error ? <View style={styles.errorBox}><Text style={styles.errorText}>❌ {error}</Text></View> : null}

        {/* ── Generating state ── */}
        {asking && (
          <View style={styles.thinkingBox}>
            <ActivityIndicator color={BRAND_COLOR} style={{ marginRight: 10 }} />
            <Text style={styles.thinkingText}>Your AI tutor is thinking…</Text>
          </View>
        )}

        {/* ── Answer card ── */}
        {!asking && answer ? (
          <View style={styles.answerCard}>
            <View style={styles.answerHeader}>
              <View style={styles.answerBadge}>
                <Text style={styles.answerBadgeText}>🤖 AI Tutor</Text>
              </View>
              {subject ? <Text style={styles.answerContext}>{grade} · {subject}</Text> : <Text style={styles.answerContext}>{grade}</Text>}
            </View>

            <MathAnswer content={answer} />

            {/* Follow-up */}
            <View style={styles.followUpSection}>
              <Text style={styles.followUpLabel}>💬 Ask a follow-up</Text>
              <TextInput
                style={styles.followUpInput}
                placeholder="Go deeper on any part of this answer…"
                placeholderTextColor="#9ca3af"
                value={followUp}
                onChangeText={setFollowUp}
                multiline
                numberOfLines={2}
                textAlignVertical="top"
              />
              <TouchableOpacity style={[styles.fuBtn, (fuAsking || !followUp.trim()) && styles.fuBtnDisabled]}
                onPress={handleFollowUp} disabled={fuAsking || !followUp.trim()}>
                {fuAsking ? <ActivityIndicator color="#fff" size="small" /> : <Text style={styles.fuBtnText}>Ask Follow-up</Text>}
              </TouchableOpacity>

              {!fuAsking && fuAnswer ? (
                <View style={styles.fuAnswerBox}>
                  <Text style={styles.fuAnswerLabel}>Follow-up answer:</Text>
                  <MathAnswer content={fuAnswer} />
                </View>
              ) : null}
            </View>
          </View>
        ) : null}

        {/* ── Recent history ── */}
        {history.length > 0 && (
          <View style={styles.historySection}>
            <TouchableOpacity style={styles.historyToggle} onPress={() => setShowHist(v => !v)}>
              <Text style={styles.historyToggleText}>
                {showHistory ? "▼" : "▶"} Recent Doubts ({history.length})
              </Text>
            </TouchableOpacity>
            {showHistory && history.map(h => (
              <TouchableOpacity key={h.id} style={styles.historyItem}
                onPress={() => { setQuestion(h.question); setAnswer(h.answer || ""); setFuAnswer(""); setFollowUp(""); setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 200); }}>
                <Text style={styles.historyQ} numberOfLines={2}>{h.question}</Text>
                <Text style={styles.historyMeta}>{h.grade}{h.subject ? ` · ${h.subject}` : ""} · {formatDate(h.created_at)}</Text>
              </TouchableOpacity>
            ))}
          </View>
        )}

      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f8fafc" },
  content: { padding: 16, paddingBottom: 80 },
  pageTitle: { fontSize: 22, fontWeight: "800", color: "#111827", marginBottom: 4 },
  pageSubtitle: { fontSize: 13, color: "#6b7280", marginBottom: 18, lineHeight: 19 },
  label: { fontSize: 11, fontWeight: "700", color: "#6b7280", textTransform: "uppercase", letterSpacing: 0.6, marginBottom: 8, marginTop: 14 },
  optional: { fontWeight: "400", textTransform: "none", letterSpacing: 0, color: "#9ca3af", fontSize: 11 },
  chipRow: { flexDirection: "row", marginBottom: 4 },
  chip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 99, borderWidth: 1.5, borderColor: "#d1d5db", backgroundColor: "#fff", marginRight: 8 },
  chipActive: { borderColor: BRAND_COLOR, backgroundColor: BRAND_COLOR },
  chipText: { fontSize: 13, fontWeight: "600", color: "#374151" },
  chipTextActive: { color: "#fff" },
  // Answer style
  styleRow: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 4 },
  styleBtn: { paddingHorizontal: 12, paddingVertical: 7, borderRadius: 8, borderWidth: 1.5, borderColor: "#d1d5db", backgroundColor: "#fff" },
  styleBtnActive: { borderColor: BRAND_COLOR, backgroundColor: "rgba(99,102,241,.08)" },
  styleBtnText: { fontSize: 12, fontWeight: "600", color: "#374151" },
  styleBtnTextActive: { color: BRAND_COLOR },
  // Suggest chips
  suggestBox: { backgroundColor: "#fff", borderRadius: 12, padding: 12, marginBottom: 14, borderWidth: 1, borderColor: "#e5e7eb" },
  suggestLabel: { fontSize: 11, fontWeight: "700", color: "#6b7280", marginBottom: 8, textTransform: "uppercase", letterSpacing: 0.5 },
  suggestChips: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  suggestChip: { paddingHorizontal: 10, paddingVertical: 6, borderRadius: 8, backgroundColor: "rgba(99,102,241,.07)", borderWidth: 1, borderColor: "rgba(99,102,241,.2)", maxWidth: "100%" },
  suggestChipText: { fontSize: 12, color: BRAND_COLOR, fontWeight: "600", lineHeight: 17 },
  // Question input
  questionInput: { backgroundColor: "#fff", borderWidth: 1.5, borderColor: "#d1d5db", borderRadius: 12, padding: 14, fontSize: 15, color: "#111827", minHeight: 100, marginBottom: 12 },
  askBtn: { backgroundColor: BRAND_COLOR, borderRadius: 12, padding: 15, alignItems: "center", marginBottom: 12 },
  askBtnDisabled: { opacity: 0.6 },
  askBtnText: { color: "#fff", fontWeight: "700", fontSize: 16 },
  errorBox: { backgroundColor: "#fef2f2", borderRadius: 10, padding: 12, marginBottom: 12 },
  errorText: { color: "#dc2626", fontSize: 14 },
  // Thinking
  thinkingBox: { flexDirection: "row", alignItems: "center", padding: 16, backgroundColor: "#fff", borderRadius: 12, borderWidth: 1, borderColor: "#e5e7eb", marginBottom: 12 },
  thinkingText: { color: "#374151", fontSize: 14, fontStyle: "italic" },
  // Answer card
  answerCard: { backgroundColor: "#fff", borderRadius: 16, borderWidth: 1, borderColor: "#e5e7eb", padding: 16, marginBottom: 16, shadowColor: "#6366f1", shadowOpacity: 0.06, shadowRadius: 12, shadowOffset: { width: 0, height: 3 }, elevation: 3 },
  answerHeader: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: 14 },
  answerBadge: { backgroundColor: "rgba(99,102,241,.1)", borderRadius: 99, paddingHorizontal: 10, paddingVertical: 4 },
  answerBadgeText: { fontSize: 12, fontWeight: "700", color: BRAND_COLOR },
  answerContext: { fontSize: 11, color: "#9ca3af", fontWeight: "600" },
  // Follow-up
  followUpSection: { marginTop: 18, borderTopWidth: 1, borderTopColor: "#f3f4f6", paddingTop: 14 },
  followUpLabel: { fontSize: 13, fontWeight: "700", color: "#374151", marginBottom: 8 },
  followUpInput: { backgroundColor: "#f8fafc", borderWidth: 1, borderColor: "#d1d5db", borderRadius: 10, padding: 10, fontSize: 14, color: "#111827", minHeight: 60, marginBottom: 8 },
  fuBtn: { backgroundColor: BRAND_COLOR, borderRadius: 8, padding: 10, alignItems: "center" },
  fuBtnDisabled: { opacity: 0.5 },
  fuBtnText: { color: "#fff", fontWeight: "700", fontSize: 13 },
  fuAnswerBox: { marginTop: 12, backgroundColor: "#f0f4ff", borderRadius: 10, padding: 12, borderWidth: 1, borderColor: "rgba(99,102,241,.2)" },
  fuAnswerLabel: { fontSize: 11, fontWeight: "700", color: BRAND_COLOR, marginBottom: 8, textTransform: "uppercase", letterSpacing: 0.5 },
  // History
  historySection: { marginTop: 8 },
  historyToggle: { paddingVertical: 12, paddingHorizontal: 4 },
  historyToggleText: { fontSize: 13, fontWeight: "700", color: "#374151" },
  historyItem: { backgroundColor: "#fff", borderRadius: 10, padding: 12, marginBottom: 8, borderWidth: 1, borderColor: "#e5e7eb" },
  historyQ: { fontSize: 13, fontWeight: "600", color: "#111827", lineHeight: 19, marginBottom: 4 },
  historyMeta: { fontSize: 11, color: "#9ca3af", fontWeight: "600" },
});
