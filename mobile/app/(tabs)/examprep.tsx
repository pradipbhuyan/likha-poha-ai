/**
 * Exam Prep Center — JEE / NEET / CUET / SAT / IELTS / TOEFL
 * Tabs: Quick Reference | Practice Questions | Simulated Test
 */
import { useEffect, useRef, useState } from "react";
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity,
  ActivityIndicator, Alert,
} from "react-native";
import { useRouter } from "expo-router";
import { Feather } from "@expo/vector-icons";
import { authFetch } from "../../lib/authFetch";
import { BRAND_COLOR } from "../../constants";
import { EXAMS, SC, QR } from "../../lib/examprep-data";

interface Question {
  id: string;
  question_text: string;
  options_json: {key:string;text:string}[];
  difficulty?: string;
  topic?: string;
}

// ── Countdown Timer ───────────────────────────────────────────────────────────
function CountdownTimer({ durationMins, startTime, onExpire }: {
  durationMins: number; startTime: number; onExpire: () => void;
}) {
  const [secsLeft, setSecsLeft] = useState(() => {
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    return Math.max(0, durationMins * 60 - elapsed);
  });
  const ref = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    ref.current = setInterval(() => {
      setSecsLeft(s => {
        if (s <= 1) { clearInterval(ref.current!); onExpire(); return 0; }
        return s - 1;
      });
    }, 1000);
    return () => clearInterval(ref.current!);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const h = Math.floor(secsLeft / 3600);
  const m = Math.floor((secsLeft % 3600) / 60);
  const s = secsLeft % 60;
  const isLow = secsLeft < 300;
  const fmt = `${h > 0 ? h + ":" : ""}${String(m).padStart(2,"0")}:${String(s).padStart(2,"0")}`;

  return (
    <View style={[tm.box, isLow && tm.boxLow]}>
      <Feather name="clock" size={14} color={isLow ? "#ef4444" : "#374151"} />
      <Text style={[tm.txt, isLow && tm.txtLow]}>{fmt}</Text>
    </View>
  );
}
const tm = StyleSheet.create({
  box: { flexDirection:"row", alignItems:"center", gap:5, backgroundColor:"#f0fdf4", borderRadius:20, paddingHorizontal:12, paddingVertical:6, borderWidth:1, borderColor:"#22c55e" },
  boxLow: { backgroundColor:"#fef2f2", borderColor:"#ef4444" },
  txt: { fontSize:15, fontWeight:"800", color:"#374151" },
  txtLow: { color:"#ef4444" },
});

// ── NTA-Style Test Interface ──────────────────────────────────────────────────
function SimulatedTestView({
  questions, testId, durationMins, startTime, examLabel,
  onSubmit,
}: {
  questions: Question[]; testId: string; durationMins: number;
  startTime: number; examLabel: string; onSubmit: (score: any) => void;
}) {
  const [qIdx, setQIdx] = useState(0);
  const [answers, setAnswers] = useState<Record<string,string>>({});
  const [marked, setMarked] = useState<Record<string,boolean>>({});
  const [submitting, setSubmitting] = useState(false);

  const q = questions[qIdx];
  const answered = Object.keys(answers).length;

  async function handleSubmit() {
    const left = questions.length - answered;
    if (left > 0) {
      Alert.alert(
        "Submit Test?",
        `${left} question${left>1?"s":""} unanswered. Submit anyway?`,
        [
          { text: "Cancel", style: "cancel" },
          { text: "Submit", style: "destructive", onPress: doSubmit },
        ]
      );
    } else {
      doSubmit();
    }
  }

  async function doSubmit() {
    setSubmitting(true);
    try {
      const timeSpent = Math.floor((Date.now() - startTime) / 1000);
      // Backend expects snake_case for all fields
      const ans = Object.entries(answers).map(([question_id, selected_option]) => ({ question_id, selected_option }));
      const result = await authFetch(`/api/exam-prep/simulated-tests/${testId}/submit`, {
        method: "POST",
        body: JSON.stringify({ answers: ans, time_spent_seconds: timeSpent }),
      });
      onSubmit(result);
    } catch (e: any) {
      Alert.alert("Error", e?.message ?? "Could not submit test.");
    } finally {
      setSubmitting(false);
    }
  }

  // Palette button color
  function paletteBg(i: number) {
    const qid = questions[i]?.id;
    if (!qid) return "#f3f4f6";
    if (marked[qid] && answers[qid]) return "#8b5cf6";
    if (marked[qid]) return "rgba(139,92,246,.25)";
    if (answers[qid]) return "#22c55e";
    if (i === qIdx) return BRAND_COLOR;
    return "#f3f4f6";
  }
  function paletteTxt(i: number) {
    const qid = questions[i]?.id;
    if (!qid) return "#374151";
    if (marked[qid] || answers[qid]) return "#fff";
    if (i === qIdx) return "#fff";
    return "#374151";
  }

  if (!q) return null;

  return (
    <View style={{ flex: 1 }}>
      {/* Test header */}
      <View style={ts.header}>
        <Text style={ts.examLabel}>{examLabel}</Text>
        <CountdownTimer durationMins={durationMins} startTime={startTime} onExpire={handleSubmit} />
        <Text style={ts.progress}>{answered}/{questions.length} answered</Text>
      </View>

      {/* Question */}
      <ScrollView style={{ flex: 1 }} contentContainerStyle={ts.qContainer}>
        <View style={ts.qNumRow}>
          <Text style={ts.qNum}>Q.{qIdx + 1} / {questions.length}</Text>
          {q.topic && <Text style={ts.qTopic}>{q.topic}</Text>}
        </View>
        <Text style={ts.qText}>{q.question_text}</Text>

        {/* Options */}
        {(q.options_json || []).map(o => {
          const sel = answers[q.id] === o.key;
          return (
            <TouchableOpacity key={o.key}
              style={[ts.opt, sel && ts.optSel]}
              onPress={() => setAnswers(p => ({ ...p, [q.id]: o.key }))}
            >
              <View style={[ts.optKey, sel && ts.optKeyActive]}>
                <Text style={[ts.optKeyTxt, sel && { color: "#fff" }]}>{o.key}</Text>
              </View>
              <Text style={[ts.optTxt, sel && ts.optTxtActive]}>{o.text}</Text>
            </TouchableOpacity>
          );
        })}

        {/* Question navigation buttons */}
        <View style={ts.navRow}>
          <TouchableOpacity style={ts.navBtn}
            onPress={() => { setMarked(m => ({...m, [q.id]: !m[q.id]})); if (qIdx < questions.length-1) setQIdx(qIdx+1); }}>
            <Text style={ts.navBtnTxt}>⚑ Mark & Next</Text>
          </TouchableOpacity>
          <TouchableOpacity style={ts.navBtn}
            onPress={() => setAnswers(p => { const n = {...p}; delete n[q.id]; return n; })}>
            <Text style={ts.navBtnTxt}>✕ Clear</Text>
          </TouchableOpacity>
          {qIdx < questions.length - 1 ? (
            <TouchableOpacity style={[ts.navBtn, ts.navBtnPrimary]}
              onPress={() => setQIdx(qIdx + 1)}>
              <Text style={ts.navBtnPrimaryTxt}>Save & Next ▶</Text>
            </TouchableOpacity>
          ) : (
            <TouchableOpacity style={[ts.navBtn, { backgroundColor: "#ef4444", borderColor: "#ef4444" }]}
              onPress={handleSubmit} disabled={submitting}>
              {submitting ? <ActivityIndicator color="#fff" size="small" /> : <Text style={{ color:"#fff", fontWeight:"700", fontSize:13 }}>Submit Test</Text>}
            </TouchableOpacity>
          )}
        </View>
      </ScrollView>

      {/* Question palette */}
      <View style={ts.palette}>
        <Text style={ts.paletteTitle}>Question Palette</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false}>
          <View style={ts.paletteBtns}>
            {questions.map((_, i) => (
              <TouchableOpacity key={i} style={[ts.palBtn, { backgroundColor: paletteBg(i) }]}
                onPress={() => setQIdx(i)}>
                <Text style={[ts.palBtnTxt, { color: paletteTxt(i) }]}>{i+1}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </ScrollView>
        <TouchableOpacity style={ts.submitBtn} onPress={handleSubmit} disabled={submitting}>
          {submitting ? <ActivityIndicator color="#fff" size="small" /> : <Text style={ts.submitBtnTxt}>📝 Submit Test</Text>}
        </TouchableOpacity>
      </View>
    </View>
  );
}

const ts = StyleSheet.create({
  header: { flexDirection:"row", alignItems:"center", justifyContent:"space-between", padding:12, backgroundColor:"#fff", borderBottomWidth:1, borderBottomColor:"#e5e7eb", gap:8, flexWrap:"wrap" },
  examLabel: { fontSize:13, fontWeight:"700", color:"#374151" },
  progress: { fontSize:12, color:"#6b7280" },
  qContainer: { padding:16, paddingBottom:8 },
  qNumRow: { flexDirection:"row", alignItems:"center", gap:8, marginBottom:10 },
  qNum: { fontSize:13, fontWeight:"800", color:BRAND_COLOR },
  qTopic: { fontSize:11, color:"#6b7280", backgroundColor:"rgba(0,0,0,.04)", borderRadius:20, paddingHorizontal:8, paddingVertical:2 },
  qText: { fontSize:15, color:"#111827", lineHeight:24, marginBottom:16, fontWeight:"500" },
  opt: { flexDirection:"row", alignItems:"center", gap:12, padding:12, borderRadius:10, borderWidth:1.5, borderColor:"#e5e7eb", backgroundColor:"#f9fafb", marginBottom:8 },
  optSel: { borderColor:BRAND_COLOR, backgroundColor:"rgba(99,102,241,.06)" },
  optKey: { width:28, height:28, borderRadius:6, backgroundColor:"#e5e7eb", alignItems:"center", justifyContent:"center" },
  optKeyActive: { backgroundColor:BRAND_COLOR },
  optKeyTxt: { fontSize:12, fontWeight:"800", color:"#374151" },
  optTxt: { fontSize:14, color:"#374151", flex:1, lineHeight:20 },
  optTxtActive: { color:"#111827", fontWeight:"600" },
  navRow: { flexDirection:"row", gap:8, marginTop:16, flexWrap:"wrap" },
  navBtn: { flex:1, paddingVertical:9, borderRadius:8, borderWidth:1.5, borderColor:"#d1d5db", alignItems:"center", backgroundColor:"#fff" },
  navBtnTxt: { fontSize:12, fontWeight:"600", color:"#374151" },
  navBtnPrimary: { backgroundColor:BRAND_COLOR, borderColor:BRAND_COLOR },
  navBtnPrimaryTxt: { fontSize:12, fontWeight:"700", color:"#fff" },
  palette: { backgroundColor:"#fff", borderTopWidth:1, borderTopColor:"#e5e7eb", padding:10 },
  paletteTitle: { fontSize:11, fontWeight:"700", color:"#6b7280", marginBottom:8, textTransform:"uppercase", letterSpacing:0.5 },
  paletteBtns: { flexDirection:"row", flexWrap:"wrap", gap:6 },
  palBtn: { width:34, height:34, borderRadius:6, alignItems:"center", justifyContent:"center" },
  palBtnTxt: { fontSize:12, fontWeight:"700" },
  submitBtn: { backgroundColor:"#ef4444", borderRadius:10, padding:12, alignItems:"center", marginTop:10 },
  submitBtnTxt: { color:"#fff", fontWeight:"700", fontSize:14 },
});

// ── Score Result Screen ────────────────────────────────────────────────────────
function TestScoreScreen({ result, examLabel, onRetake }: { result: any; examLabel: string; onRetake: () => void }) {
  const score = result?.score ?? result?.total_score ?? 0;
  const total = result?.total_marks ?? result?.max_score ?? 100;
  const pct = Math.round((score / total) * 100);
  const correct = result?.correct ?? result?.correct_count ?? 0;
  const wrong = result?.wrong ?? result?.wrong_count ?? 0;
  const unanswered = result?.unanswered ?? result?.skipped ?? 0;

  return (
    <ScrollView contentContainerStyle={sc.container}>
      <Text style={sc.trophy}>🏆</Text>
      <Text style={sc.title}>Test Completed!</Text>
      <Text style={sc.exam}>{examLabel}</Text>
      <View style={sc.scoreBox}>
        <Text style={[sc.scoreVal, { color: pct >= 60 ? "#22c55e" : pct >= 40 ? "#f59e0b" : "#ef4444" }]}>{score}</Text>
        <Text style={sc.scoreOf}>/ {total}</Text>
        <Text style={[sc.scorePct, { color: pct >= 60 ? "#22c55e" : pct >= 40 ? "#f59e0b" : "#ef4444" }]}>{pct}%</Text>
      </View>
      <View style={sc.statsRow}>
        <View style={sc.stat}><Text style={[sc.statVal, { color:"#22c55e" }]}>{correct}</Text><Text style={sc.statLbl}>Correct</Text></View>
        <View style={sc.stat}><Text style={[sc.statVal, { color:"#ef4444" }]}>{wrong}</Text><Text style={sc.statLbl}>Wrong</Text></View>
        <View style={sc.stat}><Text style={[sc.statVal, { color:"#6b7280" }]}>{unanswered}</Text><Text style={sc.statLbl}>Skipped</Text></View>
      </View>
      <TouchableOpacity style={sc.btn} onPress={onRetake}>
        <Text style={sc.btnTxt}>🔄 Take Another Test</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}
const sc = StyleSheet.create({
  container: { alignItems:"center", padding:24, paddingTop:48 },
  trophy: { fontSize:56, marginBottom:12 },
  title: { fontSize:24, fontWeight:"800", color:"#111827", marginBottom:4 },
  exam: { fontSize:14, color:"#6b7280", marginBottom:24 },
  scoreBox: { flexDirection:"row", alignItems:"baseline", gap:8, marginBottom:24 },
  scoreVal: { fontSize:56, fontWeight:"900" },
  scoreOf: { fontSize:24, color:"#6b7280", fontWeight:"600" },
  scorePct: { fontSize:28, fontWeight:"800" },
  statsRow: { flexDirection:"row", gap:24, marginBottom:32 },
  stat: { alignItems:"center", gap:4 },
  statVal: { fontSize:24, fontWeight:"800" },
  statLbl: { fontSize:12, color:"#6b7280", fontWeight:"600" },
  btn: { backgroundColor:BRAND_COLOR, borderRadius:12, paddingHorizontal:28, paddingVertical:14 },
  btnTxt: { color:"#fff", fontWeight:"700", fontSize:16 },
});

// ── Main Screen ────────────────────────────────────────────────────────────────
export default function ExamPrepScreen() {
  const router = useRouter();
  const [examKey, setExamKey] = useState("jee_main");
  const [access, setAccess] = useState<any>(null);
  const [accessLoading, setAccessLoading] = useState(true);
  const [subjects, setSubjects] = useState<{name:string}[]>([]);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<Record<string,string>>({});
  const [feedbacks, setFeedbacks] = useState<Record<string,any>>({});
  const [loadingQ, setLoadingQ] = useState(false);
  const [tab, setTab] = useState<"reference"|"practice"|"test">("reference");
  const [refSubject, setRefSubject] = useState("");
  // Test simulator state
  const [testState, setTestState] = useState<"idle"|"loading"|"active"|"result">("idle");
  const [testSession, setTestSession] = useState<any>(null);
  const [testQuestions, setTestQuestions] = useState<Question[]>([]);
  const [testResult, setTestResult] = useState<any>(null);

  useEffect(() => {
    authFetch("/api/exam-prep/access-check")
      .then((d:any) => setAccess(d))
      .catch(() => setAccess({ has_access: false }))
      .finally(() => setAccessLoading(false));
  }, []);

  useEffect(() => {
    const keys = Object.keys(QR[examKey] ?? {});
    setRefSubject(keys[0] ?? "");
    if (!access?.has_access) return;
    authFetch(`/api/exam-prep/subjects?exam=${examKey}`)
      .then((d:any) => setSubjects(d.subjects || []))
      .catch(() => setSubjects([]));
  }, [examKey, access]);

  async function loadQ(subj: string) {
    setLoadingQ(true); setAnswers({}); setFeedbacks({});
    try {
      const d:any = await authFetch(`/api/exam-prep/questions?exam=${examKey}&subject=${encodeURIComponent(subj)}&limit=10`);
      setQuestions(d.questions || []);
    } catch { setQuestions([]); } finally { setLoadingQ(false); }
  }

  async function doAnswer(qid: string, opt: string) {
    if (feedbacks[qid]) return;
    setAnswers(p => ({ ...p, [qid]: opt }));
    try {
      const d:any = await authFetch(`/api/exam-prep/questions/${qid}/answer`, { method: "POST", body: JSON.stringify({ selected_option: opt }) });
      setFeedbacks(p => ({ ...p, [qid]: d }));
    } catch {}
  }

  async function startTest() {
    setTestState("loading");
    // Exam subjects + per-subject limits (mirrors web EXAM_SIM_CONFIG)
    const EXAM_SUBJECTS: Record<string, { subjects: string[]; perSubject: number }> = {
      jee_main:  { subjects: ["Physics","Chemistry","Mathematics"], perSubject: 25 },
      neet_ug:   { subjects: ["Physics","Chemistry","Biology"],     perSubject: 45 },
      cuet_ug:   { subjects: ["English","General Test"],           perSubject: 40 },
      sat:       { subjects: ["Reading & Writing","Mathematics"],   perSubject: 27 },
      ielts:     { subjects: ["Listening","Reading"],              perSubject: 20 },
      toefl_ibt: { subjects: ["Reading","Listening"],              perSubject: 20 },
    };
    try {
      // 1. Start the test session (gets test_id + question_ids)
      const d:any = await authFetch(`/api/exam-prep/simulated-tests/start`, {
        method: "POST",
        body: JSON.stringify({ exam: examKey }),
      });
      setTestSession(d);

      // 2. Fetch full question objects per subject (API returns IDs only)
      const cfg = EXAM_SUBJECTS[examKey] ?? { subjects: subjects.map(s => s.name), perSubject: 20 };
      const allQ: Question[] = [];
      for (const subj of cfg.subjects) {
        try {
          const qData:any = await authFetch(
            `/api/exam-prep/questions?exam=${examKey}&subject=${encodeURIComponent(subj)}&limit=${cfg.perSubject}`
          );
          allQ.push(...(qData.questions || []));
        } catch { /* skip subject if no questions */ }
      }

      if (allQ.length === 0) {
        Alert.alert(
          "No Questions Available",
          "The question bank for this exam is empty. Admin needs to add questions first.",
          [{ text: "OK" }]
        );
        setTestState("idle");
        return;
      }

      setTestQuestions(allQ);
      setTestState("active");
    } catch (e: any) {
      Alert.alert("Error", e?.message ?? "Could not start test.");
      setTestState("idle");
    }
  }

  const rd = QR[examKey] ?? {};
  const rSubjs = Object.keys(rd);
  const ar = rd[refSubject];
  const ei = EXAMS.find(e => e.key === examKey) ?? EXAMS[0];

  if (accessLoading) return <View style={s.center}><ActivityIndicator color={BRAND_COLOR} size="large" /></View>;

  // Active test — full screen
  if (tab === "test" && testState === "active" && testSession) {
    return (
      <View style={{ flex:1, backgroundColor:"#f8fafc" }}>
        <SimulatedTestView
          questions={testQuestions}
          testId={testSession.test_id ?? testSession.id}
          durationMins={testSession.duration_minutes ?? 180}
          startTime={Date.now()}
          examLabel={ei.label}
          onSubmit={(result) => { setTestResult(result); setTestState("result"); }}
        />
      </View>
    );
  }

  if (tab === "test" && testState === "result" && testResult) {
    return (
      <View style={{ flex:1, backgroundColor:"#f8fafc" }}>
        <View style={{ flexDirection:"row", alignItems:"center", padding:12, borderBottomWidth:1, borderBottomColor:"#e5e7eb", backgroundColor:"#fff" }}>
          <TouchableOpacity onPress={() => { setTestState("idle"); setTestResult(null); }} style={{ padding:6, marginRight:10 }}>
            <Feather name="arrow-left" size={18} color={BRAND_COLOR} />
          </TouchableOpacity>
          <Text style={{ fontWeight:"700", fontSize:16, color:"#111827" }}>Test Result</Text>
        </View>
        <TestScoreScreen result={testResult} examLabel={ei.label} onRetake={() => { setTestState("idle"); setTestResult(null); }} />
      </View>
    );
  }

  return (
    <ScrollView style={s.container} contentContainerStyle={s.content}>
      {/* Header */}
      <View style={s.hdr}>
        <TouchableOpacity style={s.back} onPress={() => router.back()}>
          <Feather name="arrow-left" size={18} color={BRAND_COLOR} />
        </TouchableOpacity>
        <View style={s.ibox}><Text style={{ fontSize: 18 }}>🎓</Text></View>
        <View>
          <Text style={s.ttl}>Exam Prep Center</Text>
          <Text style={s.sbl}>JEE · NEET · CUET · SAT · IELTS · TOEFL</Text>
        </View>
      </View>

      {/* Access gate */}
      {!access?.has_access && (
        <View style={s.gate}>
          <Text style={{ fontSize: 36, textAlign: "center", marginBottom: 8 }}>🔐</Text>
          <Text style={s.gtTtl}>Premium Feature</Text>
          <Text style={s.gtSub}>Available for Grade 11 & 12 students on Premium plan. Covers JEE Main, NEET UG, CUET UG, SAT, IELTS and TOEFL.</Text>
        </View>
      )}

      {access?.has_access && (
        <>
          {/* Exam selector */}
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.cRow}>
            {EXAMS.map(e => (
              <TouchableOpacity key={e.key} style={[s.chip, examKey === e.key && { borderColor: e.color, backgroundColor: e.color + "18" }]} onPress={() => { setExamKey(e.key); setTestState("idle"); }}>
                <Text style={[s.cTxt, examKey === e.key && { color: e.color, fontWeight: "700" as const }]}>{e.label}</Text>
              </TouchableOpacity>
            ))}
          </ScrollView>

          {/* Tab switch: Reference | Practice | Simulated Test */}
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 14 }}>
            <View style={{ flexDirection:"row", gap:8 }}>
              {([
                { key:"reference", label:"📋 Quick Reference" },
                { key:"practice",  label:"⚡ Practice" },
                { key:"test",      label:"📝 Simulated Test" },
              ] as const).map(t => (
                <TouchableOpacity key={t.key} style={[s.tBtn, tab === t.key && s.tBtnA]} onPress={() => { setTab(t.key); setTestState("idle"); }}>
                  <Text style={[s.tTxt, tab === t.key && s.tTxtA]}>{t.label}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </ScrollView>

          {/* ── Quick Reference tab ── */}
          {tab === "reference" && (
            <>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.cRow}>
                {rSubjs.map(rs => {
                  const c = SC[rs] || BRAND_COLOR;
                  return (
                    <TouchableOpacity key={rs} style={[s.chip, refSubject === rs && { borderColor: c, backgroundColor: c + "18" }]} onPress={() => setRefSubject(rs)}>
                      <Text style={[s.cTxt, refSubject === rs && { color: c, fontWeight: "700" as const }]}>{rs}</Text>
                    </TouchableOpacity>
                  );
                })}
              </ScrollView>
              {ar && (
                <>
                  <View style={s.card}><Text style={s.cTtl}>📐 Key Formulas</Text>
                    {ar.formulas.map((f, i) => (<View key={i} style={s.fRow}><Text style={s.fExpr}>{f.expr}</Text><Text style={s.fDesc}>{f.desc}</Text></View>))}
                  </View>
                  <View style={s.card}><Text style={s.cTtl}>⚠️ Exam Traps</Text>
                    {ar.traps.map((t, i) => (<View key={i} style={s.trapRow}><Text style={s.trapDot}>•</Text><Text style={s.trapTxt}>{t}</Text></View>))}
                  </View>
                  <View style={s.card}><Text style={s.cTtl}>🧠 Memory Mnemonics</Text>
                    {ar.mnemonics.map((m, i) => (<Text key={i} style={s.mnem}>{m}</Text>))}
                  </View>
                </>
              )}
              {!ar && rSubjs.length === 0 && (<View style={s.empty}><Feather name="book-open" size={32} color="#9ca3af" /><Text style={s.emTxt}>No reference data for this exam yet.</Text></View>)}
            </>
          )}

          {/* ── Practice tab ── */}
          {tab === "practice" && (
            <>
              <Text style={s.hint}>Tap a subject to load 10 practice questions</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.cRow}>
                {subjects.map(sub => {
                  const c = SC[sub.name] || BRAND_COLOR;
                  return (<TouchableOpacity key={sub.name} style={[s.chip, { borderColor: c }]} onPress={() => loadQ(sub.name)}><Text style={[s.cTxt, { color: c, fontWeight: "700" as const }]}>{sub.name}</Text></TouchableOpacity>);
                })}
              </ScrollView>
              {loadingQ && <View style={s.center}><ActivityIndicator color={BRAND_COLOR} /></View>}
              {!loadingQ && questions.length === 0 && (<View style={s.empty}><Feather name="edit-3" size={32} color="#9ca3af" /><Text style={s.emTxt}>Select a subject above to start practising</Text></View>)}
              {questions.map(q => {
                const fb = feedbacks[q.id]; const sel = answers[q.id];
                return (
                  <View key={q.id} style={s.qCard}>
                    <Text style={s.qTxt}>{q.question_text}</Text>
                    {q.options_json.map(o => {
                      const isSel = sel === o.key; const isCorrect = fb && fb.correct_option === o.key; const isWrong = fb && sel === o.key && !fb.is_correct;
                      return (
                        <TouchableOpacity key={o.key} style={[s.opt2, isCorrect && s.optCorrect, isWrong && s.optWrong, isSel && !fb && s.optSel2]} onPress={() => doAnswer(q.id, o.key)} disabled={!!fb}>
                          <Text style={[s.optKey2, isCorrect && { color:"#22c55e" }, isWrong && { color:"#ef4444" }, isSel && !fb && { color:BRAND_COLOR }]}>{o.key}</Text>
                          <Text style={s.optTxt2}>{o.text}</Text>
                        </TouchableOpacity>
                      );
                    })}
                    {fb && (<View style={[s.fbBox, { borderColor: fb.is_correct ? "#22c55e44" : "#ef444444", backgroundColor: fb.is_correct ? "rgba(34,197,94,.06)" : "rgba(239,68,68,.06)" }]}><Text style={[s.fbLabel, { color: fb.is_correct ? "#22c55e" : "#ef4444" }]}>{fb.is_correct ? "✅ Correct!" : `❌ Incorrect — Answer: ${fb.correct_option}`}</Text>{fb.explanation && <Text style={s.fbExp}>{fb.explanation}</Text>}</View>)}
                  </View>
                );
              })}
            </>
          )}

          {/* ── Simulated Test tab ── */}
          {tab === "test" && testState === "idle" && (
            <View style={s.testStart}>
              <Text style={{ fontSize:48, textAlign:"center", marginBottom:16 }}>📝</Text>
              <Text style={s.testTitle}>NTA-Style {ei.label} Simulator</Text>
              <Text style={s.testDesc}>Full-length timed exam with question palette, mark for review, and instant results. Matches real exam format.</Text>
              <View style={s.testInfo}>
                <View style={s.testInfoRow}><Feather name="clock" size={16} color="#6b7280" /><Text style={s.testInfoTxt}>3 hours (180 min)</Text></View>
                <View style={s.testInfoRow}><Feather name="help-circle" size={16} color="#6b7280" /><Text style={s.testInfoTxt}>~75 questions</Text></View>
                <View style={s.testInfoRow}><Feather name="award" size={16} color="#6b7280" /><Text style={s.testInfoTxt}>Score + analysis on submit</Text></View>
              </View>
              <TouchableOpacity style={s.startBtn} onPress={startTest}>
                <Text style={s.startBtnTxt}>▶ Start Simulated Test</Text>
              </TouchableOpacity>
            </View>
          )}
          {tab === "test" && testState === "loading" && (
            <View style={s.center}><ActivityIndicator color={BRAND_COLOR} size="large" /><Text style={{ color:"#6b7280", marginTop:12 }}>Loading test questions…</Text></View>
          )}
        </>
      )}
    </ScrollView>
  );
}

const s = StyleSheet.create({
  container: { flex:1, backgroundColor:"#f8fafc" },
  content: { padding:16, paddingBottom:60 },
  center: { alignItems:"center", paddingVertical:40, gap:10 },
  hdr: { flexDirection:"row", alignItems:"center", gap:10, marginBottom:16 },
  back: { padding:8, borderRadius:8, backgroundColor:"rgba(99,102,241,.08)" },
  ibox: { width:40, height:40, borderRadius:10, backgroundColor:"rgba(99,102,241,.08)", alignItems:"center", justifyContent:"center" },
  ttl: { fontSize:20, fontWeight:"800", color:"#111827" },
  sbl: { fontSize:12, color:"#6b7280" },
  gate: { backgroundColor:"#fff", borderRadius:16, padding:20, borderWidth:1, borderColor:"rgba(99,102,241,.2)", alignItems:"center" },
  gtTtl: { fontSize:18, fontWeight:"800", color:"#111827", marginBottom:8, textAlign:"center" },
  gtSub: { fontSize:13, color:"#6b7280", textAlign:"center", lineHeight:20 },
  cRow: { flexDirection:"row", marginBottom:10 },
  chip: { paddingHorizontal:14, paddingVertical:8, borderRadius:99, borderWidth:1.5, borderColor:"#d1d5db", backgroundColor:"#fff", marginRight:8 },
  cTxt: { fontSize:12, fontWeight:"600", color:"#374151" },
  tBtn: { paddingHorizontal:14, paddingVertical:10, borderRadius:10, borderWidth:1.5, borderColor:"#d1d5db", backgroundColor:"#fff", alignItems:"center" },
  tBtnA: { borderColor:BRAND_COLOR, backgroundColor:BRAND_COLOR },
  tTxt: { fontSize:13, fontWeight:"700", color:"#374151" },
  tTxtA: { color:"#fff" },
  card: { backgroundColor:"#fff", borderRadius:14, padding:16, marginBottom:12, borderWidth:1, borderColor:"#e5e7eb" },
  cTtl: { fontSize:14, fontWeight:"800", color:"#111827", marginBottom:12 },
  fRow: { flexDirection:"row", gap:10, marginBottom:8, alignItems:"flex-start" },
  fExpr: { fontSize:12, fontFamily:"monospace" as any, color:"#6366f1", fontWeight:"700", flex:1, lineHeight:18 },
  fDesc: { fontSize:11, color:"#6b7280", width:90, lineHeight:17 },
  trapRow: { flexDirection:"row", gap:6, marginBottom:6 },
  trapDot: { fontSize:14, color:"#ef4444", lineHeight:20 },
  trapTxt: { fontSize:12, color:"#374151", flex:1, lineHeight:20 },
  mnem: { fontSize:12, color:"#6366f1", fontWeight:"600", marginBottom:6, lineHeight:18 },
  empty: { alignItems:"center", paddingVertical:40, gap:12 },
  emTxt: { fontSize:13, color:"#6b7280", textAlign:"center" },
  hint: { fontSize:12, color:"#6b7280", marginBottom:10 },
  qCard: { backgroundColor:"#fff", borderRadius:14, padding:14, marginBottom:12, borderWidth:1, borderColor:"#e5e7eb" },
  qTxt: { fontSize:14, color:"#111827", lineHeight:22, marginBottom:12 },
  opt2: { flexDirection:"row", alignItems:"center", gap:10, padding:12, borderRadius:10, borderWidth:1.5, borderColor:"#e5e7eb", backgroundColor:"#f9fafb", marginBottom:8 },
  optSel2: { borderColor:BRAND_COLOR, backgroundColor:"rgba(99,102,241,.06)" },
  optCorrect: { borderColor:"#22c55e", backgroundColor:"rgba(34,197,94,.06)" },
  optWrong: { borderColor:"#ef4444", backgroundColor:"rgba(239,68,68,.06)" },
  optKey2: { fontSize:12, fontWeight:"800", color:"#374151", width:20, textAlign:"center" },
  optTxt2: { fontSize:13, color:"#374151", flex:1, lineHeight:20 },
  fbBox: { borderRadius:10, padding:12, borderWidth:1, marginTop:4 },
  fbLabel: { fontSize:13, fontWeight:"700", marginBottom:4 },
  fbExp: { fontSize:12, color:"#374151", lineHeight:20 },
  // Test start card
  testStart: { backgroundColor:"#fff", borderRadius:16, padding:24, borderWidth:1, borderColor:"#e5e7eb", alignItems:"center" },
  testTitle: { fontSize:18, fontWeight:"800", color:"#111827", marginBottom:8, textAlign:"center" },
  testDesc: { fontSize:13, color:"#6b7280", textAlign:"center", lineHeight:20, marginBottom:20 },
  testInfo: { width:"100%", gap:10, marginBottom:24 },
  testInfoRow: { flexDirection:"row", alignItems:"center", gap:10 },
  testInfoTxt: { fontSize:14, color:"#374151", fontWeight:"500" },
  startBtn: { backgroundColor:BRAND_COLOR, borderRadius:12, paddingVertical:14, paddingHorizontal:32, alignItems:"center", width:"100%" },
  startBtnTxt: { color:"#fff", fontWeight:"700", fontSize:16 },
});
