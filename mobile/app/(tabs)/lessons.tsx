/**
 * Lessons tab — syllabus selector + lesson generation.
 *
 * Phase 1 MVP: shows lesson content as plain markdown via react-native-markdown-display.
 * Phase 2: MathText component will render LaTeX via react-native-math-view.
 *
 * Uses the same backend endpoints as the web:
 *   GET /api/syllabus
 *   POST /api/lesson/generate (same payload)
 */
import { useEffect, useState } from "react";
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity,
  ActivityIndicator, Alert,
} from "react-native";
import Markdown from "react-native-markdown-display";
import { authFetch } from "../../lib/authFetch";
import { BRAND_COLOR } from "../../constants";

type SyllabusData = Record<string, Record<string, Record<string, string[]>>>;

const LESSON_STEPS_BY_GRADE: Record<string, string[]> = {
  default: ["Concept introduction", "Core explanation", "Worked examples", "Exam-style problems", "Revision and recap"],
  "Grade 6": ["Concept introduction", "Core explanation", "Worked examples", "Revision and recap"],
  "Grade 7": ["Concept introduction", "Core explanation", "Worked examples", "Revision and recap"],
  "Grade 8": ["Concept introduction", "Core explanation", "Worked examples", "Revision and recap"],
  "Grade 10": ["Concept introduction", "Core explanation", "Worked examples", "Exam-style problems", "Revision and recap", "Exam preparation"],
  "Grade 11": ["Concept introduction", "Core explanation", "Worked examples", "Exam-style problems", "Revision and recap", "Exam preparation"],
  "Grade 12": ["Concept introduction", "Core explanation", "Worked examples", "Exam-style problems", "Revision and recap", "Exam preparation"],
};

export default function LessonsScreen() {
  const [syllabus, setSyllabus] = useState<SyllabusData | null>(null);
  const [grade, setGrade] = useState("Grade 9");
  const [subject, setSubject] = useState("");
  const [chapter, setChapter] = useState("");
  const [stepIndex, setStepIndex] = useState(0);
  const [lesson, setLesson] = useState("");
  const [generating, setGenerating] = useState(false);
  const [loadingSyllabus, setLoadingSyllabus] = useState(true);

  const steps = LESSON_STEPS_BY_GRADE[grade] ?? LESSON_STEPS_BY_GRADE.default;
  const stepTitle = steps[stepIndex];

  useEffect(() => {
    authFetch("/api/syllabus")
      .then((r) => {
        setSyllabus(r.syllabus);
        // Set defaults for Grade 9 CBSE
        const defaultSubject = Object.keys(r.syllabus?.["Grade 9"]?.["CBSE"] ?? {})[0] ?? "";
        const defaultChapter = r.syllabus?.["Grade 9"]?.["CBSE"]?.[defaultSubject]?.[0] ?? "";
        setSubject(defaultSubject);
        setChapter(defaultChapter);
      })
      .catch(() => Alert.alert("Error", "Could not load syllabus."))
      .finally(() => setLoadingSyllabus(false));
  }, []);

  const subjects = Object.keys(syllabus?.[grade]?.["CBSE"] ?? {});
  const chapters = syllabus?.[grade]?.["CBSE"]?.[subject] ?? [];

  async function generateLesson() {
    if (!grade || !subject || !chapter) return;
    setGenerating(true);
    setLesson("");
    try {
      const result = await authFetch("/api/lesson/generate", {
        method: "POST",
        body: JSON.stringify({
          grade, mode: "CBSE", board: "CBSE",
          subject, chapter, step_title: stepTitle,
          teacher_persona: "",
        }),
      });
      if (result.success) {
        setLesson(result.lesson ?? "");
      } else {
        Alert.alert("Error", result.message ?? "Lesson generation failed.");
      }
    } catch (err: any) {
      Alert.alert("Error", err.message ?? "Could not generate lesson.");
    } finally {
      setGenerating(false);
    }
  }

  if (loadingSyllabus) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={BRAND_COLOR} />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Selectors */}
      <Text style={styles.label}>Grade</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipRow}>
        {Object.keys(syllabus ?? {}).map((g) => (
          <TouchableOpacity
            key={g}
            style={[styles.chip, grade === g && styles.chipActive]}
            onPress={() => {
              setGrade(g);
              const firstSubject = Object.keys(syllabus?.[g]?.["CBSE"] ?? {})[0] ?? "";
              setSubject(firstSubject);
              setChapter(syllabus?.[g]?.["CBSE"]?.[firstSubject]?.[0] ?? "");
              setLesson("");
              setStepIndex(0);
            }}
          >
            <Text style={[styles.chipText, grade === g && styles.chipTextActive]}>
              {g.replace("Grade ", "")}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      <Text style={styles.label}>Subject</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipRow}>
        {subjects.map((s) => (
          <TouchableOpacity
            key={s}
            style={[styles.chip, subject === s && styles.chipActive]}
            onPress={() => {
              setSubject(s);
              setChapter(syllabus?.[grade]?.["CBSE"]?.[s]?.[0] ?? "");
              setLesson("");
            }}
          >
            <Text style={[styles.chipText, subject === s && styles.chipTextActive]}>{s}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      <Text style={styles.label}>Chapter</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipRow}>
        {chapters.map((c) => (
          <TouchableOpacity
            key={c}
            style={[styles.chip, chapter === c && styles.chipActive]}
            onPress={() => { setChapter(c); setLesson(""); }}
          >
            <Text style={[styles.chipText, chapter === c && styles.chipTextActive]} numberOfLines={1}>
              {c.length > 30 ? c.slice(0, 28) + "…" : c}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {/* Step selector */}
      <Text style={styles.label}>Step</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipRow}>
        {steps.map((s, i) => (
          <TouchableOpacity
            key={s}
            style={[styles.chip, stepIndex === i && styles.chipActive]}
            onPress={() => { setStepIndex(i); setLesson(""); }}
          >
            <Text style={[styles.chipText, stepIndex === i && styles.chipTextActive]}>
              {i + 1}. {s}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {/* Generate button */}
      <TouchableOpacity
        style={[styles.generateBtn, generating && styles.generateBtnDisabled]}
        onPress={generateLesson}
        disabled={generating}
      >
        {generating ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.generateBtnText}>✨ Generate Lesson</Text>
        )}
      </TouchableOpacity>

      {/* Lesson content */}
      {lesson ? (
        <View style={styles.lessonBox}>
          <Text style={styles.lessonStepLabel}>{stepTitle}</Text>
          {/* Phase 1: plain markdown. Phase 2: replace with MathText per formula. */}
          <Markdown style={markdownStyles}>{lesson}</Markdown>
        </View>
      ) : generating ? (
        <Text style={styles.generatingText}>Your AI tutor is preparing your lesson…</Text>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f8fafc" },
  content: { padding: 16, paddingBottom: 60 },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  label: { fontSize: 12, fontWeight: "700", color: "#6b7280", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 8, marginTop: 14 },
  chipRow: { flexDirection: "row", marginBottom: 4 },
  chip: { paddingHorizontal: 12, paddingVertical: 7, borderRadius: 99, borderWidth: 1.5, borderColor: "#d1d5db", backgroundColor: "#fff", marginRight: 8 },
  chipActive: { borderColor: BRAND_COLOR, backgroundColor: BRAND_COLOR },
  chipText: { fontSize: 13, fontWeight: "600", color: "#374151" },
  chipTextActive: { color: "#fff" },
  generateBtn: { backgroundColor: BRAND_COLOR, borderRadius: 12, padding: 14, alignItems: "center", marginTop: 20 },
  generateBtnDisabled: { opacity: 0.6 },
  generateBtnText: { color: "#fff", fontWeight: "700", fontSize: 16 },
  lessonBox: { marginTop: 20, backgroundColor: "#fff", borderRadius: 14, padding: 16, borderWidth: 1, borderColor: "#e5e7eb" },
  lessonStepLabel: { fontSize: 11, fontWeight: "700", color: BRAND_COLOR, textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 12 },
  generatingText: { textAlign: "center", color: "#6b7280", marginTop: 24, fontStyle: "italic" },
});

const markdownStyles = {
  body: { color: "#374151", fontSize: 15, lineHeight: 24 },
  heading1: { color: "#111827", fontWeight: "800" as const, marginBottom: 8 },
  heading2: { color: "#111827", fontWeight: "700" as const, marginBottom: 6 },
  strong: { fontWeight: "700" as const, color: "#111827" },
  code_inline: { backgroundColor: "#eef2ff", color: "#4338ca", borderRadius: 4, paddingHorizontal: 4 },
};
