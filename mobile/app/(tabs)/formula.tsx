/**
 * Formula Sheet tab — CBSE syllabus-aligned formula reference.
 * Uses GET /api/student/formula-sheets?grade=&subject=
 *
 * Features:
 *  - Grade 5–12 + subject selector
 *  - Chapter navigation (horizontal chips)
 *  - Formula cards: name, expression (LaTeX→Unicode), description
 *  - Premium expansion: variables, worked example, step-by-step, memory tip
 *  - Search across all chapters/formulas
 *  - Lock indicator for free users
 *
 * Field mapping (backend → mobile):
 *  description   → shown below expression (brief)
 *  variables     → plain string e.g. "A = area, b = base"
 *  example       → worked example text (premium)
 *  solution_steps → step-by-step array or newline string (premium)
 *  memory_tip    → memory tip (premium)
 */
import { useEffect, useState } from "react";
import {
  View, Text, ScrollView, TextInput, StyleSheet,
  TouchableOpacity, ActivityIndicator,
} from "react-native";
import { authFetch } from "../../lib/authFetch";
import { BRAND_COLOR } from "../../constants";

// ── LaTeX → Unicode ───────────────────────────────────────────────────────────
function mathToUnicode(latex: string): string {
  if (!latex) return "";
  return latex
    .replace(/\\text\{([^}]+)\}/g, "$1")
    .replace(/\\frac\{([^}]+)\}\{([^}]+)\}/g, "($1)/($2)")
    .replace(/\\sqrt\{([^}]+)\}/g, "√($1)")
    .replace(/\\sqrt\s*([a-zA-Z0-9])/g, "√$1")
    // Escaped space/percent — common in Chemistry expression_latex (e.g.
    // "mass\ of\ element", "Element\%"); without this they show as stray "\".
    .replace(/\\ /g, " ").replace(/\\%/g, "%").replace(/\\quad/g, " ")
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
    .replace(/\\approx/g, "≈").replace(/\\infty/g, "∞").replace(/\\equiv/g, "≡")
    .replace(/\\rightarrow/g, "→").replace(/\\leftarrow/g, "←").replace(/\\to/g, "→")
    .replace(/\\Rightarrow/g, "⇒").replace(/\\rightleftharpoons/g, "⇌")
    .replace(/\\uparrow/g, "↑").replace(/\\downarrow/g, "↓")
    .replace(/\\prime/g, "′").replace(/\\bullet/g, "•").replace(/\\circ/g, "°")
    .replace(/\\sum/g, "∑").replace(/\\ldots/g, "…").replace(/\\cdots/g, "…")
    .replace(/\\pi/g, "π").replace(/\\alpha/g, "α").replace(/\\beta/g, "β")
    .replace(/\\gamma/g, "γ").replace(/\\delta/g, "δ").replace(/\\theta/g, "θ")
    .replace(/\\lambda/g, "λ").replace(/\\mu/g, "μ").replace(/\\nu/g, "ν").replace(/\\sigma/g, "σ")
    .replace(/\\Sigma/g, "Σ").replace(/\\Delta/g, "Δ").replace(/\\omega/g, "ω")
    .replace(/\\sin/g, "sin").replace(/\\cos/g, "cos").replace(/\\tan/g, "tan")
    .replace(/\\log/g, "log").replace(/\\ln/g, "ln").replace(/\\int/g, "∫")
    .replace(/\\[a-zA-Z]+\{([^}]+)\}/g, "$1")
    .replace(/\\[a-zA-Z]+/g, "")
    .replace(/\{([^}]*)\}/g, "$1")
    .replace(/\s+/g, " ").trim();
}

// ── Types — matches backend _build_chapters() output fields ──────────────────
interface Formula {
  id?: string;
  name: string;
  expression?: string;
  expression_latex?: string;
  description?: string;         // brief description shown below expression
  variables?: string;           // plain string e.g. "A = area, b = base, h = height"
  difficulty?: string;
  chapter?: string;
  topic?: string;
  tags?: string[];
  locked: boolean;
  preview_allowed: boolean;
  // Premium fields — only returned by backend when has_premium=true
  example?: string;                        // worked example text
  solution_steps?: string | string[];      // step-by-step (array or newline string)
  memory_tip?: string;                     // memory tip
}

interface Topic { topic_name: string; formulas: Formula[]; }
interface Chapter {
  chapter_id: string;
  chapter_name: string;
  unlocked_count: number;
  total_formulas: number;
  locked: boolean;
  topics: Topic[];
}
interface SheetData {
  available: boolean;
  has_premium: boolean;
  chapters: Chapter[];
  subjects: string[];
  total_count: number;
  unlocked_count: number;
  message?: string;
}

const GRADES = ["Grade 5","Grade 6","Grade 7","Grade 8","Grade 9","Grade 10","Grade 11","Grade 12"];

// Biology entries are all definitions/key concepts, never symbolic formulas;
// Maths entries are all symbolic formulas; Physics/Chemistry are a genuine mix.
function formulaLabelFor(subj: string): string {
  const s = (subj || "").toLowerCase();
  if (s === "biology") return "concepts";
  if (s === "mathematics") return "formulas";
  return "formulas & concepts";
}

// ── Grade label row (shared) ──────────────────────────────────────────────────
function GradeLabelRow({ isGradeLocked, studentGrade }: { isGradeLocked: boolean; studentGrade: string | null }) {
  return (
    <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: 14, marginBottom: 8 }}>
      <Text style={{ fontSize: 11, fontWeight: "700", color: "#6b7280", textTransform: "uppercase", letterSpacing: 0.6 }}>Grade</Text>
      {isGradeLocked && studentGrade && (
        <Text style={{ fontSize: 10, fontWeight: "600", color: "#6366f1" }}>🔒 Locked to {studentGrade}</Text>
      )}
    </View>
  );
}

// ── Detect whether expression is a math formula or plain-text concept ────────
function isMathFormula(expr: string): boolean {
  if (!expr) return false;
  // LaTeX commands are an unambiguous signal — always math.
  if (/\\[a-zA-Z]/.test(expr)) return true;
  // A run of several lowercase words reads as a sentence even if it contains
  // a bare "=" or "-" (e.g. "Rate = rate constant and concentration powers").
  // Rows without curated expression_latex fall back to this plain-English
  // expression, so without this check they'd get squished by monospace math.
  const words = expr.trim().split(/\s+/);
  const wordish = words.filter(w => /^[a-z]{3,}$/.test(w)).length;
  if (words.length >= 4 && wordish >= 3) return false;
  if (/[=+\-*/^÷×∝→←≈≠≤≥∞∑∫√π²³¹₀₁₂₃αβγδθλμωΩ]/.test(expr)) return true;
  if (expr.length < 30 && /[A-Z]/.test(expr)) return true;
  return false;
}

// ── Formula Card ──────────────────────────────────────────────────────────────
function FormulaCard({ formula, hasPremium, subject }: { formula: Formula; hasPremium: boolean; subject: string }) {
  const [expanded, setExpanded] = useState(false);
  // Biology is always Key Concepts — never render as math formula
  const isBiology = (subject || "").toLowerCase() === "biology";
  // Chemistry gets its own accent so it reads as distinct from Maths/Physics
  const isChemistry = (subject || "").toLowerCase() === "chemistry";
  const accentColor = isChemistry ? "#0d9488" : BRAND_COLOR;
  const rawExpr = formula.expression_latex || formula.expression || "";
  const expr = mathToUnicode(rawExpr);
  const isFormula = !isBiology && isMathFormula(rawExpr);

  const diffColor = formula.difficulty === "easy" ? "#16a34a"
    : formula.difficulty === "hard" ? "#dc2626" : "#7c3aed";

  // Normalise solution_steps to array
  const steps: string[] = formula.solution_steps
    ? (Array.isArray(formula.solution_steps)
        ? (formula.solution_steps as string[])
        : String(formula.solution_steps).split(/\n+/).filter(Boolean))
    : [];

  const hasPremiumContent = !!(formula.variables || formula.example || steps.length > 0 || formula.memory_tip);

  return (
    <View style={[fc.card, { borderLeftColor: accentColor }, formula.locked && { opacity: 0.75 }]}>
      {/* Header */}
      <View style={fc.header}>
        <View style={{ flex: 1 }}>
          <Text style={fc.name}>
            {formula.locked ? "🔒 " : ""}
            {formula.name}
          </Text>
          <View style={fc.tagRow}>
            {formula.difficulty ? (
              <View style={[fc.badge, { backgroundColor: diffColor + "20" }]}>
                <Text style={[fc.badgeText, { color: diffColor }]}>{formula.difficulty}</Text>
              </View>
            ) : null}
            {formula.chapter ? (
              <View style={[fc.badge, { backgroundColor: "rgba(34,197,94,.12)" }]}>
                <Text style={[fc.badgeText, { color: "#15803d" }]} numberOfLines={1}>{formula.chapter}</Text>
              </View>
            ) : null}
          </View>
        </View>
      </View>

      {/* Expression — math formula or plain-text concept */}
      {formula.preview_allowed && expr ? (
        <View style={[fc.exprBox,
          isFormula && isChemistry && { backgroundColor: "rgba(13,148,136,0.07)", borderColor: "rgba(13,148,136,0.18)" },
          !isFormula && { backgroundColor: "rgba(99,102,241,0.06)", borderWidth: 1, borderColor: "rgba(99,102,241,0.15)" }]}>
          {!isFormula && (
            <Text style={{ fontSize: 9, fontWeight: "800", color: BRAND_COLOR, textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 3 }}>📖 Key Concept</Text>
          )}
          <Text style={[fc.expr, !isFormula && { fontFamily: undefined, fontStyle: "normal", fontSize: 13, fontWeight: "500", color: "#374151" }]} selectable>{expr}</Text>
        </View>
      ) : !formula.preview_allowed ? (
        <View style={fc.exprBoxLocked}>
          <Text style={fc.exprLocked}>••••••••</Text>
        </View>
      ) : null}

      {/* Description */}
      {formula.preview_allowed && formula.description ? (
        <Text style={fc.desc}>{formula.description}</Text>
      ) : null}

      {/* Expand / collapse button */}
      {formula.preview_allowed && !formula.locked && (
        <TouchableOpacity style={fc.expandBtn} onPress={() => setExpanded(v => !v)}>
          <Text style={fc.expandBtnText}>
            {expanded
              ? "▲ Collapse"
              : hasPremium
                ? (hasPremiumContent ? "▼ Show details" : "▼ Details")
                : "🔒 Premium details"}
          </Text>
        </TouchableOpacity>
      )}

      {/* Lock note */}
      {formula.locked && (
        <View style={fc.lockNote}>
          <Text style={fc.lockNoteText}>🔒 Upgrade to unlock this formula with examples and memory tips.</Text>
        </View>
      )}

      {/* ── Expanded: premium content ── */}
      {expanded && hasPremium && !formula.locked && (
        <View style={fc.expandedBox}>

          {/* Variables */}
          {formula.variables ? (
            <View style={fc.section}>
              <Text style={[fc.sectionLabel, { color: "#0891b2" }]}>🔤 Variables</Text>
              <View style={fc.varBox}>
                <Text style={fc.sectionBody}>{formula.variables}</Text>
              </View>
            </View>
          ) : null}

          {/* Worked example */}
          {formula.example ? (
            <View style={fc.section}>
              <Text style={[fc.sectionLabel, { color: "#d97706" }]}>✏️ Worked example</Text>
              <View style={fc.stepsBox}>
                <Text style={fc.stepText}>{formula.example}</Text>
              </View>
            </View>
          ) : null}

          {/* Step-by-step solution */}
          {steps.length > 0 ? (
            <View style={fc.section}>
              <Text style={[fc.sectionLabel, { color: "#16a34a" }]}>📋 Step-by-step solution</Text>
              <View style={fc.stepsBox}>
                {steps.map((step, i) => (
                  <View key={i} style={fc.stepRow}>
                    <View style={fc.stepNum}><Text style={fc.stepNumText}>{i + 1}</Text></View>
                    <Text style={fc.stepText}>{step}</Text>
                  </View>
                ))}
              </View>
            </View>
          ) : null}

          {/* Memory tip */}
          {formula.memory_tip ? (
            <View style={[fc.section, fc.tipBox]}>
              <Text style={[fc.sectionLabel, { color: "#d97706", marginBottom: 4 }]}>💡 Memory tip</Text>
              <Text style={[fc.sectionBody, { fontStyle: "italic" }]}>{formula.memory_tip}</Text>
            </View>
          ) : null}

          {/* Fallback if premium but no extra data in DB yet */}
          {!hasPremiumContent ? (
            <View style={fc.noDataBox}>
              <Text style={fc.noDataText}>Detailed notes for this formula are being added soon.</Text>
            </View>
          ) : null}

        </View>
      )}

      {/* ── Expanded: free user upgrade prompt ── */}
      {expanded && !hasPremium && !formula.locked && (
        <View style={fc.upgradeBanner}>
          <Text style={fc.upgradeBannerText}>
            🔒 Upgrade to Premium to see solved examples, step-by-step solutions, and memory tips.
          </Text>
        </View>
      )}
    </View>
  );
}

const fc = StyleSheet.create({
  card: { backgroundColor: "#fff", borderRadius: 12, padding: 14, marginBottom: 12, borderWidth: 1, borderColor: "#e5e7eb", borderLeftWidth: 3, borderLeftColor: BRAND_COLOR },
  header: { flexDirection: "row", alignItems: "flex-start", marginBottom: 8 },
  name: { fontSize: 14, fontWeight: "700", color: "#111827", marginBottom: 4, lineHeight: 20 },
  tagRow: { flexDirection: "row", flexWrap: "wrap", gap: 5 },
  badge: { paddingHorizontal: 7, paddingVertical: 2, borderRadius: 99 },
  badgeText: { fontSize: 10, fontWeight: "700" },
  exprBox: { backgroundColor: "#f8fafc", borderRadius: 8, padding: 10, marginBottom: 8, borderWidth: 1, borderColor: "#e2e8f0" },
  expr: { fontFamily: "monospace", fontSize: 15, fontWeight: "600", color: "#1e293b" },
  exprBoxLocked: { backgroundColor: "#f1f5f9", borderRadius: 8, padding: 10, marginBottom: 8 },
  exprLocked: { fontFamily: "monospace", fontSize: 15, color: "#94a3b8", letterSpacing: 4 },
  desc: { fontSize: 12, color: "#6b7280", lineHeight: 18, marginBottom: 8 },
  expandBtn: { alignSelf: "flex-start", marginTop: 2 },
  expandBtnText: { fontSize: 12, fontWeight: "700", color: BRAND_COLOR },
  lockNote: { backgroundColor: "#f8fafc", borderRadius: 7, padding: 8, marginTop: 6, borderWidth: 1, borderColor: "#e2e8f0", borderStyle: "dashed" },
  lockNoteText: { fontSize: 12, color: "#64748b", fontStyle: "italic" },
  expandedBox: { marginTop: 14, borderTopWidth: 1, borderTopColor: "#f3f4f6", paddingTop: 12 },
  section: { marginBottom: 12 },
  sectionLabel: { fontSize: 10, fontWeight: "800", textTransform: "uppercase", letterSpacing: 0.6, marginBottom: 6 },
  sectionBody: { fontSize: 13, color: "#374151", lineHeight: 20 },
  varBox: { backgroundColor: "#f8fafc", borderRadius: 8, padding: 10, borderWidth: 1, borderColor: "#e5e7eb" },
  stepsBox: { backgroundColor: "#fffbeb", borderRadius: 8, padding: 10, borderWidth: 1, borderColor: "#fde68a" },
  stepRow: { flexDirection: "row", gap: 8, marginBottom: 6, alignItems: "flex-start" },
  stepNum: { width: 20, height: 20, borderRadius: 10, backgroundColor: "#f59e0b", alignItems: "center", justifyContent: "center", flexShrink: 0, marginTop: 1 },
  stepNumText: { fontSize: 10, fontWeight: "800", color: "#fff" },
  stepText: { fontSize: 12, color: "#374151", flex: 1, lineHeight: 18 },
  tipBox: { backgroundColor: "#fefce8", borderRadius: 8, padding: 10, borderWidth: 1, borderColor: "#fde68a" },
  noDataBox: { backgroundColor: "#f8fafc", borderRadius: 8, padding: 10, borderWidth: 1, borderColor: "#e2e8f0" },
  noDataText: { fontSize: 12, color: "#9ca3af", fontStyle: "italic", textAlign: "center" },
  upgradeBanner: { backgroundColor: "#f8fafc", borderRadius: 8, padding: 10, marginTop: 8, borderWidth: 1, borderColor: "#e2e8f0", borderStyle: "dashed" },
  upgradeBannerText: { fontSize: 12, color: "#64748b", fontStyle: "italic", lineHeight: 18 },
});

// ── Main Screen ───────────────────────────────────────────────────────────────
export default function FormulaScreen() {
  const [grade, setGrade]           = useState("Grade 9");
  const [subject, setSubject]       = useState("Mathematics");
  const [data, setData]             = useState<SheetData | null>(null);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState("");
  const [search, setSearch]         = useState("");
  const [activeChapter, setChapter] = useState<string | null>(null);
  // Grade lock
  const [studentGrade, setStudentGrade]   = useState<string | null>(null);
  const [hasFullAccess, setHasFullAccess] = useState(false);
  const isGradeLocked = studentGrade !== null && !hasFullAccess;

  // Fetch enrolled grade + subscription on mount
  useEffect(() => {
    Promise.all([
      authFetch("/api/auth/me").catch(() => null),
      authFetch("/api/subscription/features").catch(() => null),
    ]).then(([me, featureData]) => {
      const enrolledGrade = me?.grade ?? "Grade 9";
      setStudentGrade(enrolledGrade);
      setGrade(enrolledGrade);
      if (featureData?.has_full_access !== undefined) {
        setHasFullAccess(featureData.has_full_access ?? false);
      }
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function loadSheet() {
    setLoading(true); setError(""); setData(null); setChapter(null);
    try {
      const params = new URLSearchParams({ grade, subject });
      const res: any = await authFetch(`/api/student/formula-sheets?${params}`);
      setData(res);
      if (res?.chapters?.length > 0) setChapter(res.chapters[0].chapter_id);
    } catch (e: any) {
      setError(e.message || "Could not load formula sheets.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadSheet(); }, [grade, subject]); // eslint-disable-line react-hooks/exhaustive-deps

  function getDisplayed(): Chapter[] {
    if (!data?.chapters) return [];
    const q = search.toLowerCase().trim();
    if (!q) return data.chapters.filter(ch => ch.chapter_id === activeChapter);
    return data.chapters.map(ch => ({
      ...ch,
      topics: ch.topics.map(t => ({
        ...t,
        formulas: t.formulas.filter(f =>
          f.name.toLowerCase().includes(q) ||
          (f.expression || "").toLowerCase().includes(q) ||
          (f.description || "").toLowerCase().includes(q)
        ),
      })).filter(t => t.formulas.length > 0),
    })).filter(ch => ch.topics.length > 0);
  }

  const displayed = getDisplayed();
  const hasPremium = !!(data?.has_premium);

  return (
    <ScrollView style={s.container} contentContainerStyle={s.content}>
      <Text style={s.pageTitle}>📐 Formulas & Concepts</Text>
      <Text style={s.pageSubtitle}>CBSE syllabus-aligned quick reference</Text>

      {/* Grade selector */}
      <GradeLabelRow isGradeLocked={isGradeLocked} studentGrade={studentGrade} />
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.chipRow}>
        {GRADES.map(g => {
          const locked = isGradeLocked && g !== studentGrade;
          const isActive = grade === g;
          return (
            <TouchableOpacity
              key={g}
              style={[s.chip, isActive && s.chipActive, locked && s.chipLocked]}
              onPress={() => !locked && setGrade(g)}
              disabled={locked}
              activeOpacity={locked ? 1 : 0.7}
            >
              <Text style={[s.chipText, isActive && s.chipTextActive, locked && s.chipTextLocked]}>
                {g.replace("Grade ", "")}
              </Text>
            </TouchableOpacity>
          );
        })}
      </ScrollView>

      {/* Subject selector */}
      <Text style={s.label}>Subject</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.chipRow}>
        {(data?.subjects?.length ? data.subjects : ["Mathematics","Science","Physics","Chemistry","Biology"]).map(sub => (
          <TouchableOpacity key={sub} style={[s.chip, subject === sub && s.chipActive]} onPress={() => setSubject(sub)}>
            <Text style={[s.chipText, subject === sub && s.chipTextActive]}>{sub}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {/* Search */}
      <TextInput
        style={s.searchInput}
        placeholder="Search formulas, chapters…"
        placeholderTextColor="#9ca3af"
        value={search}
        onChangeText={setSearch}
      />

      {/* Loading */}
      {loading && (
        <View style={s.center}>
          <ActivityIndicator color={BRAND_COLOR} size="large" />
          <Text style={s.loadingText}>Loading formulas…</Text>
        </View>
      )}

      {/* Error */}
      {!loading && error ? (
        <View style={s.errorBox}>
          <Text style={s.errorText}>❌ {error}</Text>
          <TouchableOpacity onPress={loadSheet} style={{ marginTop: 8 }}>
            <Text style={{ color: BRAND_COLOR, fontWeight: "700", fontSize: 13 }}>Retry</Text>
          </TouchableOpacity>
        </View>
      ) : null}

      {/* Not available */}
      {!loading && !error && data && !data.available ? (
        <View style={s.emptyBox}>
          <Text style={s.emptyIcon}>📋</Text>
          <Text style={s.emptyTitle}>{data.message || "Formula sheet coming soon"}</Text>
          <Text style={s.emptySubtitle}>Formula content for this subject is being added. Check back soon.</Text>
        </View>
      ) : null}

      {/* Upgrade banner */}
      {!loading && data?.available && !hasPremium && (
        <View style={s.upgradeBanner}>
          <Text style={s.upgradeBannerTitle}>🔒 Unlock Full Formula Library</Text>
          <Text style={s.upgradeBannerSub}>{data.unlocked_count} of {data.total_count} {formulaLabelFor(subject)} shown. Upgrade for examples and memory tips.</Text>
        </View>
      )}

      {/* Chapter navigation */}
      {!loading && !error && data?.available && !search && (
        <>
          <Text style={s.label}>Chapter</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.chipRow}>
            {data.chapters.map(ch => (
              <TouchableOpacity key={ch.chapter_id}
                style={[s.chip, activeChapter === ch.chapter_id && s.chipActive]}
                onPress={() => setChapter(ch.chapter_id)}>
                <Text style={[s.chipText, activeChapter === ch.chapter_id && s.chipTextActive]} numberOfLines={1}>
                  {ch.locked ? "🔒 " : ""}{ch.chapter_name.length > 22 ? ch.chapter_name.slice(0, 20) + "…" : ch.chapter_name}
                </Text>
                <Text style={[s.chipCount, activeChapter === ch.chapter_id && { color: "rgba(255,255,255,.7)" }]}>
                  {ch.unlocked_count}/{ch.total_formulas}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </>
      )}

      {/* Formula cards */}
      {!loading && !error && data?.available && (
        displayed.length === 0 ? (
          <View style={s.emptyBox}>
            <Text style={s.emptySubtitle}>{search ? "No formulas match your search." : "Select a chapter to view formulas."}</Text>
          </View>
        ) : (
          <>
            {displayed.map(ch => (
              <View key={ch.chapter_id} style={{ marginBottom: 20 }}>
                {search ? <Text style={s.chapterTitle}>{ch.chapter_name}</Text> : null}
                {ch.topics.map(t => (
                  <View key={t.topic_name}>
                    {t.topic_name !== "General" ? (
                      <Text style={s.topicTitle}>{t.topic_name}</Text>
                    ) : null}
                    {t.formulas.map((f, i) => (
                      <FormulaCard key={f.id || f.name + i} formula={f} hasPremium={hasPremium} subject={subject} />
                    ))}
                  </View>
                ))}
              </View>
            ))}
          </>
        )
      )}
    </ScrollView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f8fafc" },
  content: { padding: 16, paddingBottom: 80 },
  pageTitle: { fontSize: 22, fontWeight: "800", color: "#111827", marginBottom: 4 },
  pageSubtitle: { fontSize: 13, color: "#6b7280", marginBottom: 18, lineHeight: 19 },
  label: { fontSize: 11, fontWeight: "700", color: "#6b7280", textTransform: "uppercase", letterSpacing: 0.6, marginBottom: 8, marginTop: 14 },
  chipRow: { flexDirection: "row", marginBottom: 4 },
  chip: { paddingHorizontal: 12, paddingVertical: 7, borderRadius: 99, borderWidth: 1.5, borderColor: "#d1d5db", backgroundColor: "#fff", marginRight: 8, alignItems: "center" },
  chipActive: { borderColor: BRAND_COLOR, backgroundColor: BRAND_COLOR },
  chipLocked: { borderColor: "#e5e7eb", backgroundColor: "#f9fafb", opacity: 0.55 },
  chipText: { fontSize: 12, fontWeight: "600", color: "#374151" },
  chipTextActive: { color: "#fff" },
  chipTextLocked: { color: "#9ca3af" },
  chipCount: { fontSize: 9, color: "#9ca3af", fontWeight: "600", marginTop: 1 },
  searchInput: { backgroundColor: "#fff", borderWidth: 1.5, borderColor: "#d1d5db", borderRadius: 10, padding: 10, fontSize: 14, color: "#111827", marginBottom: 14 },
  center: { alignItems: "center", paddingVertical: 32 },
  loadingText: { color: "#6b7280", marginTop: 10, fontSize: 13 },
  errorBox: { backgroundColor: "#fef2f2", borderRadius: 10, padding: 14, marginBottom: 14 },
  errorText: { color: "#dc2626", fontSize: 14 },
  emptyBox: { alignItems: "center", paddingVertical: 32 },
  emptyIcon: { fontSize: 40, marginBottom: 10 },
  emptyTitle: { fontSize: 15, fontWeight: "700", color: "#111827", marginBottom: 6, textAlign: "center" },
  emptySubtitle: { fontSize: 13, color: "#6b7280", textAlign: "center", lineHeight: 19 },
  upgradeBanner: { backgroundColor: "rgba(99,102,241,.08)", borderRadius: 12, padding: 14, marginBottom: 14, borderWidth: 1, borderColor: "rgba(99,102,241,.2)" },
  upgradeBannerTitle: { fontSize: 13, fontWeight: "700", color: BRAND_COLOR, marginBottom: 4 },
  upgradeBannerSub: { fontSize: 12, color: "#374151", lineHeight: 18 },
  chapterTitle: { fontSize: 14, fontWeight: "800", color: BRAND_COLOR, marginBottom: 10, paddingBottom: 6, borderBottomWidth: 1, borderBottomColor: "#e0e7ff" },
  topicTitle: { fontSize: 10, fontWeight: "700", color: "#9ca3af", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 8 },
});
