/**
 * ChapterSummaryCard — mobile renderer for the ```chapter-summary fence.
 *
 * Mirrors the web ChapterSummaryBlock.jsx: the whole-chapter revision
 * wall-chart appended to a chapter's final lesson step by
 * backend/scripts/apply_chapter_summary.py.
 *
 * Schema validation is NOT duplicated here — it comes from
 * shared/utils/chapterSummary.js, the single source of truth both platforms
 * use, so a payload that renders on the web renders here too.
 *
 * React Native's markdown renderer has no per-fence component hook (unlike
 * react-markdown on the web), so callers must run extractChapterSummaries()
 * over the markdown FIRST and render the returned summaries through this
 * component. That is what keeps a raw JSON blob off the student's screen.
 */
import { StyleSheet, Text, View } from "react-native";

// Shape returned by validateChapterSummary() in shared/utils/chapterSummary.js.
// Declared here rather than imported because that module is plain JS with no
// exported types — the same convention ChapterJourney.tsx uses for the block
// types it mirrors from the backend.
export interface SummaryPanel { heading: string; points: string[]; }
export interface SummaryPipelineStep { label: string; detail: string; }
export interface SummaryPipeline { heading: string; steps: SummaryPipelineStep[]; }
export interface SummaryTerm { term: string; meaning: string; }
export interface ChapterSummary {
  title: string;
  subtitle: string;
  definition: string;
  panels: SummaryPanel[];
  pipeline: SummaryPipeline | null;
  terms: SummaryTerm[];
  remember: string[];
}

export default function ChapterSummaryCard({ summary }: { summary: ChapterSummary }) {
  if (!summary) return null;

  return (
    <View style={csStyles.card}>
      <Text style={csStyles.eyebrow}>CHAPTER SUMMARY</Text>
      <Text style={csStyles.title}>{summary.title}</Text>
      {summary.subtitle ? <Text style={csStyles.subtitle}>{summary.subtitle}</Text> : null}

      {summary.definition ? (
        <View style={csStyles.definitionBox}>
          <Text style={csStyles.definitionText}>{summary.definition}</Text>
        </View>
      ) : null}

      {summary.panels.map((panel, i) => (
        <View key={`${panel.heading}-${i}`} style={csStyles.panel}>
          <View style={csStyles.panelHeadingRow}>
            <View style={csStyles.panelIndex}>
              <Text style={csStyles.panelIndexText}>{i + 1}</Text>
            </View>
            <Text style={csStyles.panelHeading}>{panel.heading}</Text>
          </View>
          {panel.points.map((point, j) => (
            <View key={j} style={csStyles.bulletRow}>
              <Text style={csStyles.bulletDot}>•</Text>
              <Text style={csStyles.bulletText}>{point}</Text>
            </View>
          ))}
        </View>
      ))}

      {summary.pipeline ? (
        <View style={csStyles.section}>
          <Text style={csStyles.sectionHeading}>{summary.pipeline.heading.toUpperCase()}</Text>
          {summary.pipeline.steps.map((step, i) => (
            <View key={`${step.label}-${i}`} style={csStyles.pipelineStep}>
              <Text style={csStyles.pipelineIndex}>STEP {i + 1}</Text>
              <Text style={csStyles.pipelineLabel}>{step.label}</Text>
              {step.detail ? <Text style={csStyles.pipelineDetail}>{step.detail}</Text> : null}
            </View>
          ))}
        </View>
      ) : null}

      {summary.remember.length > 0 ? (
        <View style={csStyles.section}>
          <Text style={csStyles.sectionHeading}>POINTS TO REMEMBER</Text>
          {summary.remember.map((point, i) => (
            <View key={i} style={csStyles.bulletRow}>
              <Text style={csStyles.bulletDot}>•</Text>
              <Text style={csStyles.bulletText}>{point}</Text>
            </View>
          ))}
        </View>
      ) : null}

      {summary.terms.length > 0 ? (
        <View style={csStyles.section}>
          <Text style={csStyles.sectionHeading}>KEY TERMS</Text>
          {summary.terms.map((entry, i) => (
            <View key={`${entry.term}-${i}`} style={csStyles.termRow}>
              <Text style={csStyles.termName}>{entry.term}</Text>
              <Text style={csStyles.termMeaning}>{entry.meaning}</Text>
            </View>
          ))}
        </View>
      ) : null}
    </View>
  );
}

const csStyles = StyleSheet.create({
  card: {
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#c7d2fe",
    borderRadius: 14,
    padding: 14,
    marginTop: 10,
    marginBottom: 12,
  },
  eyebrow: { fontSize: 10, fontWeight: "800", color: "#4f46e5", letterSpacing: 0.9, marginBottom: 4 },
  title: { fontSize: 17, fontWeight: "800", color: "#1e1b4b", lineHeight: 23 },
  subtitle: { fontSize: 13, color: "#4c516d", lineHeight: 19, marginTop: 4 },
  definitionBox: {
    backgroundColor: "rgba(99,102,241,.07)",
    borderLeftWidth: 3,
    borderLeftColor: "#6366f1",
    borderRadius: 8,
    padding: 10,
    marginTop: 12,
  },
  definitionText: { fontSize: 13, color: "#312e63", lineHeight: 19 },
  panel: {
    borderWidth: 1,
    borderColor: "#dbe2f5",
    borderRadius: 12,
    padding: 12,
    marginTop: 10,
  },
  panelHeadingRow: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 8 },
  panelIndex: {
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: "#4f46e5",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
  },
  panelIndexText: { color: "#fff", fontSize: 11, fontWeight: "800" },
  panelHeading: { fontSize: 14, fontWeight: "800", color: "#1e293b", lineHeight: 19, flexShrink: 1 },
  bulletRow: { flexDirection: "row", gap: 7, marginBottom: 5 },
  bulletDot: { fontSize: 13, color: "#6366f1", lineHeight: 19 },
  bulletText: { fontSize: 13, color: "#334155", lineHeight: 19, flexShrink: 1 },
  section: { marginTop: 16 },
  sectionHeading: {
    fontSize: 11,
    fontWeight: "800",
    color: "#3730a3",
    letterSpacing: 0.7,
    marginBottom: 8,
  },
  pipelineStep: {
    borderWidth: 1,
    borderColor: "#dbe2f5",
    borderLeftWidth: 3,
    borderLeftColor: "#6366f1",
    borderRadius: 10,
    padding: 10,
    marginBottom: 8,
  },
  pipelineIndex: { fontSize: 10, fontWeight: "800", color: "#4f46e5", letterSpacing: 0.5 },
  pipelineLabel: { fontSize: 13.5, fontWeight: "800", color: "#1e293b", lineHeight: 19, marginTop: 2 },
  pipelineDetail: { fontSize: 12.5, color: "#475569", lineHeight: 18, marginTop: 3 },
  termRow: { paddingVertical: 6, borderTopWidth: 1, borderTopColor: "#eef2f7" },
  termName: { fontSize: 13, fontWeight: "800", color: "#3730a3" },
  termMeaning: { fontSize: 12.5, color: "#475569", lineHeight: 18, marginTop: 2 },
});
