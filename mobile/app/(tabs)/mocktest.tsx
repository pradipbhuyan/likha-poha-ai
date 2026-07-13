/**
 * Mock Test tab — generate and take a CBSE mock test.
 * Uses POST /api/mock-test/generate — same endpoint as the web.
 *
 * Fix 2026-07-13:
 *  - Backend returns options as dict {A:"...", B:"...", C:"...", D:"..."}
 *    NOT an array. Previous code did Array.isArray(q.options) → always false
 *    → options normalized to [] → no answer options shown.
 *  - Backend answer field is "answer" (the key, e.g. "A"), not "correct_answer".
 *  - Score calculation now compares selected KEY to q.answer key.
 *  - Empty options guard added (matches web app behavior).
 */
import { useState } from "react";
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity,
  ActivityIndicator, Alert,
} from "react-native";
import { Feather } from "@expo/vector-icons";
import { authFetch } from "../../lib/authFetch";
import { BRAND_COLOR } from "../../constants";

const GRADES = ["Grade 5","Grade 6","Grade 7","Grade 8","Grade 9","Grade 10","Grade 11","Grade 12"];
const SUBJECTS = ["Science","Maths","Social Science","English","Hindi","Physics","Chemistry","Biology"];
// Must match question_bank.difficulty column values exactly (capitalized)
// so the bank-first lookup hits the pre-warmed Supabase question bank instead
// of falling through to LLM generation (which takes 5-15s vs <1s from bank).
const DIFFICULTIES = ["Easy", "Medium", "Hard"];

// Backend returns options as dict {A:"...", B:"...", C:"...", D:"..."}
// and answer as the key ("A" | "B" | "C" | "D").
interface Question {
  id: number;
  question: string;
  options: Record<string, string>; // {A: "...", B: "...", C: "...", D: "..."}
  answer: string;                   // "A" | "B" | "C" | "D"
  explanation?: string;
  marks: number;
  question_type?: string;
}

export default function MockTestScreen() {
  const [grade, setGrade] = useState("Grade 9");
  const [subject, setSubject] = useState("Science");
  const [difficulty, setDifficulty] = useState("Medium");
  const [questions, setQuestions] = useState<Question[]>([]);
  // answers[questionIndex] = selected option KEY (e.g. "A", "B", "C", "D")
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [submitted, setSubmitted] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [score, setScore] = useState(0);
  const [error, setError] = useState("");

  async function generateTest() {
    setGenerating(true);
    setQuestions([]);
    setAnswers({});
    setSubmitted(false);
    setError("");
    try {
      const result = await authFetch("/api/mock-test/generate", {
        method: "POST",
        body: JSON.stringify({
          grade,
          subject,
          mode: "CBSE",
          board: "CBSE",
          mock_type: "CBSE Chapter Test",
          exam_type: "Class Test",
          difficulty,
          question_count: 5,
          question_format: "mcq",
        }),
      });

      // Backend returns MockTestQuestion objects with options as dict
      const qs: Question[] = (result.questions ?? []).map((q: any) => {
        // options is always a dict from backend {A:"...", B:"...", ...}
        // Guard: if somehow an array arrives, convert to dict with A/B/C/D keys
        let optionsDict: Record<string, string> = {};
        if (q.options && typeof q.options === "object" && !Array.isArray(q.options)) {
          optionsDict = Object.fromEntries(
            Object.entries(q.options).map(([k, v]) => [String(k), String(v ?? "")])
          );
        } else if (Array.isArray(q.options)) {
          // Legacy fallback: convert array to A/B/C/D keyed dict
          const keys = ["A", "B", "C", "D", "E", "F"];
          q.options.forEach((v: any, idx: number) => {
            if (idx < keys.length) optionsDict[keys[idx]] = String(v ?? "");
          });
        }
        return {
          id: Number(q.id ?? 0),
          question: String(q.question ?? ""),
          options: optionsDict,
          answer: String(q.answer ?? ""),      // "A" | "B" | "C" | "D"
          explanation: q.explanation ? String(q.explanation) : undefined,
          marks: Number(q.marks ?? 1),
          question_type: q.question_type ?? "mcq",
        };
      }).filter((q: Question) => q.question_type === "mcq" || !q.question_type);

      if (qs.length > 0) {
        setQuestions(qs);
      } else {
        setError(
          result.detail ?? result.message ?? "Could not generate test. Please try again."
        );
      }
    } catch (err: any) {
      setError(err.message ?? "Could not generate test.");
    } finally {
      setGenerating(false);
    }
  }

  function submitTest() {
    const answeredCount = Object.keys(answers).length;
    if (answeredCount < questions.length) {
      Alert.alert(
        "Incomplete",
        `Please answer all ${questions.length} questions before submitting. (${answeredCount}/${questions.length} answered)`
      );
      return;
    }
    let correct = 0;
    // Compare selected KEY to answer KEY (both are "A", "B", "C", or "D")
    questions.forEach((q, i) => {
      if (answers[i] === q.answer) correct++;
    });
    setScore(correct);
    setSubmitted(true);
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 4 }}>
        <View style={{ width: 36, height: 36, borderRadius: 10, backgroundColor: "rgba(99,102,241,.1)", alignItems: "center", justifyContent: "center" }}>
          <Feather name="edit-3" size={20} color={BRAND_COLOR} />
        </View>
        <Text style={styles.pageTitle}>Mock Test</Text>
      </View>

      <Text style={styles.label}>Grade</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipRow}>
        {GRADES.map((g) => (
          <TouchableOpacity
            key={g}
            style={[styles.chip, grade === g && styles.chipActive]}
            onPress={() => setGrade(g)}
          >
            <Text style={[styles.chipText, grade === g && styles.chipTextActive]}>
              {g.replace("Grade ", "")}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      <Text style={styles.label}>Subject</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipRow}>
        {SUBJECTS.map((s) => (
          <TouchableOpacity
            key={s}
            style={[styles.chip, subject === s && styles.chipActive]}
            onPress={() => setSubject(s)}
          >
            <Text style={[styles.chipText, subject === s && styles.chipTextActive]}>{s}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      <Text style={styles.label}>Difficulty</Text>
      <View style={{ flexDirection: "row", gap: 8, marginBottom: 4 }}>
        {DIFFICULTIES.map((d) => (
          <TouchableOpacity
            key={d}
            style={[styles.chip, difficulty === d && styles.chipActive]}
            onPress={() => setDifficulty(d)}
          >
            <Text style={[styles.chipText, difficulty === d && styles.chipTextActive]}>
              {d}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <TouchableOpacity
        style={[styles.generateBtn, generating && styles.btnDisabled]}
        onPress={generateTest}
        disabled={generating}
      >
        {generating
          ? <ActivityIndicator color="#fff" />
          : <Text style={styles.btnText}>Generate 5 Questions</Text>}
      </TouchableOpacity>

      {error ? (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>❌ {error}</Text>
        </View>
      ) : null}

      {questions.map((q, i) => {
        const optionEntries = Object.entries(q.options);
        const hasOptions = optionEntries.length > 0;
        return (
          <View key={i} style={styles.questionCard}>
            <Text style={styles.questionNum}>Q{i + 1} • {q.marks} mark{q.marks !== 1 ? "s" : ""}</Text>
            <Text style={styles.questionText}>{q.question}</Text>

            {/* Guard: show warning if MCQ options are missing */}
            {!hasOptions && (
              <View style={styles.noOptionsBox}>
                <Text style={styles.noOptionsText}>⚠ Answer options unavailable for this question.</Text>
              </View>
            )}

            {/* Options rendered from dict keys A/B/C/D */}
            {hasOptions && optionEntries.map(([key, val]) => {
              const isSelected = answers[i] === key;
              const isCorrect = submitted && key === q.answer;
              const isWrong = submitted && isSelected && key !== q.answer;
              return (
                <TouchableOpacity
                  key={key}
                  style={[
                    styles.optionBtn,
                    isSelected && !submitted && styles.optionSelected,
                    isCorrect && styles.optionCorrect,
                    isWrong && styles.optionWrong,
                  ]}
                  onPress={() => !submitted && setAnswers((prev) => ({ ...prev, [i]: key }))}
                  disabled={submitted}
                >
                  <Text style={[styles.optionText, (isCorrect || isWrong) && styles.optionTextInvert]}>
                    <Text style={styles.optionKey}>{key}. </Text>{val}
                  </Text>
                </TouchableOpacity>
              );
            })}

            {submitted && q.explanation ? (
              <Text style={styles.explanation}>💡 {q.explanation}</Text>
            ) : null}
          </View>
        );
      })}

      {questions.length > 0 && !submitted && (
        <TouchableOpacity style={styles.submitBtn} onPress={submitTest}>
          <Text style={styles.btnText}>Submit Test</Text>
        </TouchableOpacity>
      )}

      {submitted && (
        <View style={[styles.scoreBox, score >= 3 ? styles.scoreGood : styles.scoreLow]}>
          <Text style={styles.scoreText}>
            Score: {score}/{questions.length} ({Math.round((score / questions.length) * 100)}%)
          </Text>
          <Text style={styles.scoreEmoji}>{score >= 3 ? "🎉 Great job!" : "📖 Keep practising!"}</Text>
          <TouchableOpacity
            style={[styles.generateBtn, { marginTop: 16, marginBottom: 0 }]}
            onPress={generateTest}
          >
            <Text style={styles.btnText}>🔄 Try Another Test</Text>
          </TouchableOpacity>
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f8fafc" },
  content: { padding: 16, paddingBottom: 60 },
  pageTitle: { fontSize: 22, fontWeight: "800", color: "#111827", marginBottom: 16 },
  label: { fontSize: 12, fontWeight: "700", color: "#6b7280", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 8, marginTop: 14 },
  chipRow: { flexDirection: "row", marginBottom: 4 },
  chip: { paddingHorizontal: 12, paddingVertical: 7, borderRadius: 99, borderWidth: 1.5, borderColor: "#d1d5db", backgroundColor: "#fff", marginRight: 8 },
  chipActive: { borderColor: BRAND_COLOR, backgroundColor: BRAND_COLOR },
  chipText: { fontSize: 13, fontWeight: "600", color: "#374151" },
  chipTextActive: { color: "#fff" },
  generateBtn: { backgroundColor: BRAND_COLOR, borderRadius: 12, padding: 14, alignItems: "center", marginTop: 20, marginBottom: 16 },
  btnDisabled: { opacity: 0.6 },
  btnText: { color: "#fff", fontWeight: "700", fontSize: 16 },
  errorBox: { backgroundColor: "#fef2f2", borderRadius: 10, padding: 12, marginBottom: 14 },
  errorText: { color: "#dc2626", fontSize: 14 },
  questionCard: { backgroundColor: "#fff", borderRadius: 14, padding: 16, marginBottom: 14, borderWidth: 1, borderColor: "#e5e7eb" },
  questionNum: { fontSize: 11, fontWeight: "700", color: BRAND_COLOR, marginBottom: 6, textTransform: "uppercase" },
  questionText: { fontSize: 15, fontWeight: "600", color: "#111827", marginBottom: 12, lineHeight: 22 },
  noOptionsBox: { backgroundColor: "#fef2f2", borderRadius: 8, padding: 10, marginBottom: 8 },
  noOptionsText: { color: "#dc2626", fontSize: 13 },
  optionBtn: { borderWidth: 1.5, borderColor: "#d1d5db", borderRadius: 10, padding: 12, marginBottom: 8 },
  optionSelected: { borderColor: BRAND_COLOR, backgroundColor: "#eef2ff" },
  optionCorrect: { borderColor: "#16a34a", backgroundColor: "#16a34a" },
  optionWrong: { borderColor: "#dc2626", backgroundColor: "#dc2626" },
  optionText: { fontSize: 14, color: "#374151", fontWeight: "500" },
  optionTextInvert: { color: "#fff" },
  optionKey: { fontWeight: "700" },
  explanation: { fontSize: 13, color: "#6b7280", marginTop: 10, lineHeight: 19, fontStyle: "italic" },
  submitBtn: { backgroundColor: "#16a34a", borderRadius: 12, padding: 14, alignItems: "center", marginBottom: 20 },
  scoreBox: { borderRadius: 14, padding: 20, alignItems: "center", marginBottom: 20 },
  scoreGood: { backgroundColor: "#dcfce7", borderWidth: 1, borderColor: "#86efac" },
  scoreLow: { backgroundColor: "#fff7ed", borderWidth: 1, borderColor: "#fed7aa" },
  scoreText: { fontSize: 20, fontWeight: "800", color: "#111827", marginBottom: 6 },
  scoreEmoji: { fontSize: 15, color: "#374151" },
});
