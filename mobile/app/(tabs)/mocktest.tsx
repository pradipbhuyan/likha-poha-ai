/**
 * Mock Test tab — generate and take a CBSE mock test.
 * Uses POST /api/mock-test/generate — same endpoint as the web.
 */
import { useState } from "react";
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity,
  ActivityIndicator, Alert,
} from "react-native";
import { authFetch } from "../../lib/authFetch";
import { BRAND_COLOR } from "../../constants";

const GRADES = ["Grade 6","Grade 7","Grade 8","Grade 9","Grade 10","Grade 11","Grade 12"];
const SUBJECTS = ["Science","Maths","Social Science","English","Hindi","Physics","Chemistry","Biology"];

interface Question {
  question: string;
  options: string[];
  correct_answer: string;
  explanation?: string;
}

export default function MockTestScreen() {
  const [grade, setGrade] = useState("Grade 9");
  const [subject, setSubject] = useState("Science");
  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [submitted, setSubmitted] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [score, setScore] = useState(0);

  async function generateTest() {
    setGenerating(true);
    setQuestions([]);
    setAnswers({});
    setSubmitted(false);
    try {
      const result = await authFetch("/api/mock-test/generate", {
        method: "POST",
        body: JSON.stringify({ grade, subject, num_questions: 5 }),
      });
      if (result.questions?.length) {
        setQuestions(result.questions);
      } else {
        Alert.alert("Error", result.message ?? "Could not generate test.");
      }
    } catch (err: any) {
      Alert.alert("Error", err.message ?? "Could not generate test.");
    } finally {
      setGenerating(false);
    }
  }

  function submitTest() {
    if (Object.keys(answers).length < questions.length) {
      Alert.alert("Incomplete", "Please answer all questions before submitting.");
      return;
    }
    let correct = 0;
    questions.forEach((q, i) => { if (answers[i] === q.correct_answer) correct++; });
    setScore(correct);
    setSubmitted(true);
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.pageTitle}>✍️ Mock Test</Text>

      <Text style={styles.label}>Grade</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipRow}>
        {GRADES.map((g) => (
          <TouchableOpacity key={g} style={[styles.chip, grade === g && styles.chipActive]} onPress={() => setGrade(g)}>
            <Text style={[styles.chipText, grade === g && styles.chipTextActive]}>{g.replace("Grade ", "")}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      <Text style={styles.label}>Subject</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipRow}>
        {SUBJECTS.map((s) => (
          <TouchableOpacity key={s} style={[styles.chip, subject === s && styles.chipActive]} onPress={() => setSubject(s)}>
            <Text style={[styles.chipText, subject === s && styles.chipTextActive]}>{s}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      <TouchableOpacity
        style={[styles.generateBtn, generating && styles.btnDisabled]}
        onPress={generateTest}
        disabled={generating}
      >
        {generating ? <ActivityIndicator color="#fff" /> : <Text style={styles.btnText}>Generate 5 Questions</Text>}
      </TouchableOpacity>

      {questions.map((q, i) => (
        <View key={i} style={styles.questionCard}>
          <Text style={styles.questionNum}>Q{i + 1}</Text>
          <Text style={styles.questionText}>{q.question}</Text>
          {q.options.map((opt) => {
            const isSelected = answers[i] === opt;
            const isCorrect = submitted && opt === q.correct_answer;
            const isWrong = submitted && isSelected && opt !== q.correct_answer;
            return (
              <TouchableOpacity
                key={opt}
                style={[styles.optionBtn, isSelected && !submitted && styles.optionSelected, isCorrect && styles.optionCorrect, isWrong && styles.optionWrong]}
                onPress={() => !submitted && setAnswers((prev) => ({ ...prev, [i]: opt }))}
                disabled={submitted}
              >
                <Text style={[styles.optionText, (isCorrect || isWrong) && { color: "#fff" }]}>{opt}</Text>
              </TouchableOpacity>
            );
          })}
          {submitted && q.explanation ? <Text style={styles.explanation}>💡 {q.explanation}</Text> : null}
        </View>
      ))}

      {questions.length > 0 && !submitted && (
        <TouchableOpacity style={styles.submitBtn} onPress={submitTest}>
          <Text style={styles.btnText}>Submit Test</Text>
        </TouchableOpacity>
      )}

      {submitted && (
        <View style={[styles.scoreBox, score >= 3 ? styles.scoreGood : styles.scoreLow]}>
          <Text style={styles.scoreText}>Score: {score}/{questions.length} ({Math.round((score / questions.length) * 100)}%)</Text>
          <Text style={styles.scoreEmoji}>{score >= 3 ? "🎉 Great job!" : "📖 Keep practising!"}</Text>
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
  questionCard: { backgroundColor: "#fff", borderRadius: 14, padding: 16, marginBottom: 14, borderWidth: 1, borderColor: "#e5e7eb" },
  questionNum: { fontSize: 11, fontWeight: "700", color: BRAND_COLOR, marginBottom: 6, textTransform: "uppercase" },
  questionText: { fontSize: 15, fontWeight: "600", color: "#111827", marginBottom: 12, lineHeight: 22 },
  optionBtn: { borderWidth: 1.5, borderColor: "#d1d5db", borderRadius: 10, padding: 12, marginBottom: 8 },
  optionSelected: { borderColor: BRAND_COLOR, backgroundColor: "#eef2ff" },
  optionCorrect: { borderColor: "#16a34a", backgroundColor: "#16a34a" },
  optionWrong: { borderColor: "#dc2626", backgroundColor: "#dc2626" },
  optionText: { fontSize: 14, color: "#374151", fontWeight: "500" },
  explanation: { fontSize: 13, color: "#6b7280", marginTop: 10, lineHeight: 19, fontStyle: "italic" },
  submitBtn: { backgroundColor: "#16a34a", borderRadius: 12, padding: 14, alignItems: "center", marginBottom: 20 },
  scoreBox: { borderRadius: 14, padding: 20, alignItems: "center", marginBottom: 20 },
  scoreGood: { backgroundColor: "#dcfce7", borderWidth: 1, borderColor: "#86efac" },
  scoreLow: { backgroundColor: "#fff7ed", borderWidth: 1, borderColor: "#fed7aa" },
  scoreText: { fontSize: 20, fontWeight: "800", color: "#111827", marginBottom: 6 },
  scoreEmoji: { fontSize: 15, color: "#374151" },
});
