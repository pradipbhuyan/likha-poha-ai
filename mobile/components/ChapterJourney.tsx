/**
 * ChapterJourney — mobile renderer for typed-block chapter docs (Phase 2).
 *
 * Mirrors the web Chapter Journey:
 *   - Grades 5-8 (Journey): colourful card feed, tap-to-answer quick checks
 *     with XP, tap-to-reveal "Students also ask", finish card.
 *   - Grades 9-12 (Study): muted document cards, attempt-first worked-example
 *     reveals, same quick checks without the XP framing.
 *
 * Zero LLM cost: the doc arrives fully prewarmed from GET /api/lesson/chapter-doc.
 * Quick-check progress is session-state (no AsyncStorage dependency).
 *
 * Markdown rendering is injected via renderMarkdown so the existing
 * MathAwareMarkdown (LaTeX → Unicode) in lessons.tsx is reused untouched.
 */
import { ReactNode, useMemo, useState } from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { Feather } from "@expo/vector-icons";

// ── Block / doc types (mirror backend app/models/lesson_blocks.py) ───────────
export interface KeyTerm { term: string; meaning: string; }
export interface ChapterBlock {
  type: "hook" | "concept" | "example" | "quickcheck" | "watchout" | "vocab" | "students_ask" | "recap";
  // hook
  text?: string;
  // concept
  title?: string;
  body_md?: string;
  key_terms?: KeyTerm[];
  // example / quickcheck / students_ask
  question?: string;
  // quickcheck
  format?: "mcq" | "truefalse";
  options?: string[];
  answer_index?: number;
  explanation?: string;
  // vocab
  words?: KeyTerm[];
  // students_ask
  answer_md?: string;
}
export interface ChapterMilestone { title: string; blocks: ChapterBlock[]; }
export interface ChapterDocData {
  grade: string;
  subject: string;
  chapter: string;
  milestones: ChapterMilestone[];
  recap?: { body_md: string } | null;
}

type RenderMarkdown = (content: string, accent: string) => ReactNode;

const JUNIOR_GRADES = new Set(["Grade 5", "Grade 6", "Grade 7", "Grade 8"]);

// Card palettes — Journey (vivid) vs Study (muted)
const JOURNEY_CARDS: Record<string, { bg: string; border: string; accent: string; icon: keyof typeof Feather.glyphMap; label: string }> = {
  hook:         { bg: "rgba(14,148,136,.09)", border: "rgba(14,148,136,.4)",  accent: "#0e9488", icon: "zap",            label: "Did you know?" },
  concept:      { bg: "rgba(59,130,246,.07)", border: "rgba(59,130,246,.3)",  accent: "#3b82f6", icon: "book-open",      label: "Concept" },
  example:      { bg: "rgba(34,197,94,.07)",  border: "rgba(34,197,94,.3)",   accent: "#16a34a", icon: "edit-3",         label: "Worked example" },
  quickcheck:   { bg: "rgba(232,96,76,.07)",  border: "rgba(232,96,76,.35)",  accent: "#e8604c", icon: "check-circle",   label: "Quick check" },
  watchout:     { bg: "rgba(242,169,34,.09)", border: "rgba(242,169,34,.4)",  accent: "#d97706", icon: "alert-triangle", label: "Watch out" },
  vocab:        { bg: "rgba(124,92,214,.07)", border: "rgba(124,92,214,.3)",  accent: "#7c5cd6", icon: "bookmark",       label: "New words" },
  students_ask: { bg: "rgba(124,92,214,.07)", border: "rgba(124,92,214,.3)",  accent: "#7c5cd6", icon: "help-circle",    label: "Students also ask" },
  recap:        { bg: "rgba(14,148,136,.09)", border: "rgba(14,148,136,.4)",  accent: "#0e9488", icon: "star",           label: "Recap" },
};

const STUDY_CARDS: typeof JOURNEY_CARDS = {
  hook:         JOURNEY_CARDS.hook, // unused — Study skips hooks
  concept:      { bg: "#ffffff", border: "#e2e8f0", accent: "#2d4a8a", icon: "book-open",      label: "Concept" },
  example:      { bg: "#ffffff", border: "#e2e8f0", accent: "#2d4a8a", icon: "edit-3",         label: "Worked example" },
  quickcheck:   { bg: "#ffffff", border: "#e2e8f0", accent: "#2d4a8a", icon: "check-circle",   label: "Quick check" },
  watchout:     { bg: "rgba(245,158,11,.06)", border: "rgba(245,158,11,.35)", accent: "#b45309", icon: "alert-triangle", label: "Watch out" },
  vocab:        { bg: "#ffffff", border: "#e2e8f0", accent: "#2d4a8a", icon: "bookmark",       label: "Key vocabulary" },
  students_ask: { bg: "#ffffff", border: "#e2e8f0", accent: "#2d4a8a", icon: "help-circle",    label: "Students also ask" },
  recap:        { bg: "#ffffff", border: "#e2e8f0", accent: "#16a34a", icon: "star",           label: "Recap" },
};

// ── Card shell ────────────────────────────────────────────────────────────────
function CardShell({ palette, type, title, children }: {
  palette: typeof JOURNEY_CARDS; type: string; title?: string; children: ReactNode;
}) {
  const card = palette[type] ?? palette.concept;
  return (
    <View style={[cjStyles.card, { backgroundColor: card.bg, borderColor: card.border, borderLeftColor: card.accent }]}>
      <View style={cjStyles.cardHeader}>
        <View style={[cjStyles.iconBox, { backgroundColor: card.accent + "22" }]}>
          <Feather name={card.icon} size={15} color={card.accent} />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={[cjStyles.typeLabel, { color: card.accent }]}>{card.label}</Text>
          {title ? <Text style={cjStyles.cardTitle}>{title}</Text> : null}
        </View>
      </View>
      {children}
    </View>
  );
}

// ── Quick check (typed options — no text parsing) ─────────────────────────────
function QuickCheck({ block, accent, junior, onCorrect }: {
  block: ChapterBlock; accent: string; junior: boolean; onCorrect: () => void;
}) {
  const [picked, setPicked] = useState<number | null>(null);
  const answered = picked !== null;
  const correct = answered && picked === block.answer_index;

  function pick(index: number) {
    if (answered) return;
    setPicked(index);
    if (index === block.answer_index) onCorrect();
  }

  return (
    <View>
      <Text style={cjStyles.question}>{block.question}</Text>
      {(block.options ?? []).map((option, index) => {
        const isRight = index === block.answer_index;
        const isPicked = picked === index;
        let bg = "#fff"; let borderColor = "#d1d5db"; let color = "#374151";
        if (answered && isRight) { bg = "#dcfce7"; borderColor = "#16a34a"; color = "#15803d"; }
        else if (answered && isPicked) { bg = "#fef2f2"; borderColor = "#ef4444"; color = "#dc2626"; }
        else if (answered) { bg = "#f9fafb"; borderColor = "#e5e7eb"; color = "#9ca3af"; }
        return (
          <TouchableOpacity
            key={index}
            style={[cjStyles.optionBtn, { backgroundColor: bg, borderColor }]}
            onPress={() => pick(index)}
            disabled={answered}
            activeOpacity={answered ? 1 : 0.7}
          >
            <View style={[cjStyles.optionKeyBox, { backgroundColor: answered && isRight ? "#16a34a" : answered && isPicked ? "#ef4444" : accent + "20" }]}>
              <Text style={[cjStyles.optionKey, { color: answered && (isRight || isPicked) ? "#fff" : accent }]}>
                {String.fromCharCode(65 + index)}
              </Text>
            </View>
            <Text style={[cjStyles.optionText, { color }]}>{option}</Text>
          </TouchableOpacity>
        );
      })}
      {answered && (
        <View style={[cjStyles.feedback, correct ? cjStyles.feedbackRight : cjStyles.feedbackWrong]}>
          <Text style={[cjStyles.feedbackTitle, { color: correct ? "#15803d" : "#dc2626" }]}>
            {correct
              ? junior ? "Correct! +10 XP" : "Correct."
              : "Not quite — the highlighted answer is correct."}
          </Text>
          {block.explanation ? <Text style={cjStyles.feedbackText}>{block.explanation}</Text> : null}
        </View>
      )}
    </View>
  );
}

// ── Reveal blocks ─────────────────────────────────────────────────────────────
function StudentsAsk({ block, accent, renderMarkdown }: {
  block: ChapterBlock; accent: string; renderMarkdown: RenderMarkdown;
}) {
  const [open, setOpen] = useState(false);
  return (
    <View>
      <TouchableOpacity onPress={() => setOpen(o => !o)} style={cjStyles.revealRow} activeOpacity={0.7}>
        <Text style={cjStyles.question}>{block.question}</Text>
        <Text style={[cjStyles.revealTag, { color: accent }]}>{open ? "HIDE" : "REVEAL"}</Text>
      </TouchableOpacity>
      {open && <View style={{ marginTop: 6 }}>{renderMarkdown(block.answer_md ?? "", accent)}</View>}
    </View>
  );
}

function ExampleBlockView({ block, accent, junior, renderMarkdown }: {
  block: ChapterBlock; accent: string; junior: boolean; renderMarkdown: RenderMarkdown;
}) {
  // Study mode gates the solution behind attempt-first; Journey shows it inline.
  const [revealed, setRevealed] = useState(junior);
  return (
    <View>
      <Text style={cjStyles.question}>Question: {block.question}</Text>
      {revealed ? (
        renderMarkdown(block.body_md ?? "", accent)
      ) : (
        <TouchableOpacity style={[cjStyles.revealBtn, { borderColor: accent }]} onPress={() => setRevealed(true)}>
          <Text style={[cjStyles.revealBtnText, { color: accent }]}>Attempt it first, then show the solution</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export default function ChapterJourney({ doc, grade, renderMarkdown }: {
  doc: ChapterDocData; grade: string; renderMarkdown: RenderMarkdown;
}) {
  const junior = JUNIOR_GRADES.has(grade);
  const palette = junior ? JOURNEY_CARDS : STUDY_CARDS;
  const [xp, setXp] = useState(0);
  const [checksDone, setChecksDone] = useState(0);

  const totalChecks = useMemo(
    () => doc.milestones.reduce((n, m) => n + m.blocks.filter(b => b.type === "quickcheck").length, 0),
    [doc]
  );

  function handleCorrect() {
    setXp(x => x + 10);
  }

  function renderBlock(block: ChapterBlock, key: string) {
    const accent = (palette[block.type] ?? palette.concept).accent;
    switch (block.type) {
      case "hook":
        if (!junior) return null;
        return (
          <CardShell key={key} palette={palette} type="hook">
            <Text style={cjStyles.hookText}>{block.text}</Text>
          </CardShell>
        );
      case "concept":
        return (
          <CardShell key={key} palette={palette} type="concept" title={block.title}>
            {renderMarkdown(block.body_md ?? "", accent)}
          </CardShell>
        );
      case "example":
        return (
          <CardShell key={key} palette={palette} type="example">
            <ExampleBlockView block={block} accent={accent} junior={junior} renderMarkdown={renderMarkdown} />
          </CardShell>
        );
      case "quickcheck":
        return (
          <CardShell key={key} palette={palette} type="quickcheck">
            <QuickCheck
              block={block}
              accent={accent}
              junior={junior}
              onCorrect={() => { handleCorrect(); setChecksDone(c => c + 1); }}
            />
          </CardShell>
        );
      case "watchout":
        return (
          <CardShell key={key} palette={palette} type="watchout">
            {renderMarkdown(block.body_md ?? "", accent)}
          </CardShell>
        );
      case "vocab":
        return (
          <CardShell key={key} palette={palette} type="vocab">
            {(block.words ?? []).map(word => (
              <Text key={word.term} style={cjStyles.vocabLine}>
                <Text style={{ fontWeight: "700", color: accent }}>{word.term}</Text>
                <Text style={{ color: "#4b5563" }}> — {word.meaning}</Text>
              </Text>
            ))}
          </CardShell>
        );
      case "students_ask":
        return (
          <CardShell key={key} palette={palette} type="students_ask">
            <StudentsAsk block={block} accent={accent} renderMarkdown={renderMarkdown} />
          </CardShell>
        );
      default:
        return null;
    }
  }

  return (
    <View style={{ marginTop: 16 }}>
      {/* Header: chapter + XP / checks summary */}
      <View style={cjStyles.headerCard}>
        <Text style={cjStyles.headerSubject}>{doc.subject}</Text>
        <Text style={cjStyles.headerChapter} numberOfLines={2}>{doc.chapter}</Text>
        <View style={cjStyles.headerBadges}>
          <View style={cjStyles.headerBadge}>
            <Feather name="map" size={11} color="#0e9488" />
            <Text style={[cjStyles.headerBadgeText, { color: "#0e9488" }]}>
              {doc.milestones.length} milestones
            </Text>
          </View>
          {totalChecks > 0 && (
            <View style={cjStyles.headerBadge}>
              <Feather name="check-circle" size={11} color="#6366f1" />
              <Text style={[cjStyles.headerBadgeText, { color: "#6366f1" }]}>
                {checksDone}/{totalChecks} checks
              </Text>
            </View>
          )}
          {junior && (
            <View style={[cjStyles.headerBadge, { backgroundColor: "rgba(242,169,34,.14)" }]}>
              <Feather name="zap" size={11} color="#b45309" />
              <Text style={[cjStyles.headerBadgeText, { color: "#b45309" }]}>{xp} XP</Text>
            </View>
          )}
        </View>
      </View>

      {/* Milestones */}
      {doc.milestones.map((milestone, mi) => (
        <View key={mi}>
          <View style={cjStyles.milestoneRow}>
            <View style={[cjStyles.milestoneDot, { backgroundColor: junior ? "#0e9488" : "#2d4a8a" }]}>
              <Text style={cjStyles.milestoneDotText}>{mi + 1}</Text>
            </View>
            <Text style={cjStyles.milestoneTitle}>{milestone.title}</Text>
          </View>
          {milestone.blocks.map((block, bi) => renderBlock(block, `${mi}:${bi}`))}
        </View>
      ))}

      {/* Recap */}
      {doc.recap?.body_md ? (
        <CardShell palette={palette} type="recap">
          {renderMarkdown(doc.recap.body_md, (palette.recap ?? palette.concept).accent)}
        </CardShell>
      ) : null}

      {/* Finish card */}
      <View style={[cjStyles.finishCard, { backgroundColor: junior ? "#0e9488" : "#2d4a8a" }]}>
        <Feather name="award" size={26} color="#fff" />
        <Text style={cjStyles.finishTitle}>Chapter complete — great work!</Text>
        <Text style={cjStyles.finishText}>
          {junior
            ? `You earned ${xp} XP. Try a mock test or pick your next chapter!`
            : "Try a mock test or move to the next chapter to keep progressing."}
        </Text>
      </View>
    </View>
  );
}

const cjStyles = StyleSheet.create({
  card: { borderRadius: 14, borderWidth: 1, borderLeftWidth: 4, padding: 14, marginBottom: 12 },
  cardHeader: { flexDirection: "row", alignItems: "flex-start", gap: 10, marginBottom: 8 },
  iconBox: { width: 30, height: 30, borderRadius: 8, alignItems: "center", justifyContent: "center", flexShrink: 0 },
  typeLabel: { fontSize: 10, fontWeight: "800", textTransform: "uppercase", letterSpacing: 0.8 },
  cardTitle: { fontSize: 15, fontWeight: "700", color: "#111827", lineHeight: 20, marginTop: 2 },
  hookText: { fontSize: 16, fontWeight: "700", color: "#0f766e", lineHeight: 24 },
  question: { fontSize: 15, fontWeight: "600", color: "#111827", lineHeight: 22, marginBottom: 10, flex: 1 },
  optionBtn: { flexDirection: "row", alignItems: "center", borderWidth: 1.5, borderRadius: 10, padding: 11, marginBottom: 8, gap: 10 },
  optionKeyBox: { width: 28, height: 28, borderRadius: 7, alignItems: "center", justifyContent: "center", flexShrink: 0 },
  optionKey: { fontSize: 13, fontWeight: "800" },
  optionText: { fontSize: 14, fontWeight: "500", lineHeight: 20, flex: 1 },
  feedback: { borderWidth: 1, borderRadius: 10, padding: 12, marginTop: 4 },
  feedbackRight: { backgroundColor: "rgba(34,197,94,.08)", borderColor: "rgba(34,197,94,.3)" },
  feedbackWrong: { backgroundColor: "rgba(239,68,68,.08)", borderColor: "rgba(239,68,68,.3)" },
  feedbackTitle: { fontSize: 14, fontWeight: "700", marginBottom: 4 },
  feedbackText: { fontSize: 13, color: "#374151", lineHeight: 19 },
  revealRow: { flexDirection: "row", alignItems: "flex-start", gap: 8 },
  revealTag: { fontSize: 11, fontWeight: "800", letterSpacing: 0.5, marginTop: 3 },
  revealBtn: { alignSelf: "flex-start", borderWidth: 1, borderRadius: 8, paddingHorizontal: 12, paddingVertical: 7, marginTop: 2 },
  revealBtnText: { fontSize: 12, fontWeight: "700" },
  vocabLine: { fontSize: 14, lineHeight: 22, marginBottom: 6 },
  headerCard: { backgroundColor: "#fff", borderRadius: 14, padding: 14, marginBottom: 16, borderWidth: 1, borderColor: "#e5e7eb" },
  headerSubject: { fontSize: 11, fontWeight: "700", color: "#6366f1", textTransform: "uppercase", letterSpacing: 0.6, marginBottom: 4 },
  headerChapter: { fontSize: 17, fontWeight: "800", color: "#111827", lineHeight: 23, marginBottom: 10 },
  headerBadges: { flexDirection: "row", gap: 8, flexWrap: "wrap" },
  headerBadge: { flexDirection: "row", alignItems: "center", gap: 5, backgroundColor: "rgba(99,102,241,.08)", borderRadius: 99, paddingHorizontal: 10, paddingVertical: 4 },
  headerBadgeText: { fontSize: 11, fontWeight: "700", letterSpacing: 0.3 },
  milestoneRow: { flexDirection: "row", alignItems: "center", gap: 10, marginTop: 10, marginBottom: 10 },
  milestoneDot: { width: 26, height: 26, borderRadius: 13, alignItems: "center", justifyContent: "center" },
  milestoneDotText: { color: "#fff", fontSize: 12, fontWeight: "800" },
  milestoneTitle: { fontSize: 16, fontWeight: "800", color: "#111827", flex: 1 },
  finishCard: { borderRadius: 16, padding: 20, alignItems: "center", marginTop: 6, marginBottom: 10 },
  finishTitle: { color: "#fff", fontSize: 16, fontWeight: "800", marginTop: 8, textAlign: "center" },
  finishText: { color: "rgba(255,255,255,.9)", fontSize: 13, textAlign: "center", marginTop: 4, lineHeight: 19 },
});
