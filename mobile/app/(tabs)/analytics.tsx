/**
 * Analytics — Student performance dashboard.
 * Mirrors the web AnalyticsPage.jsx.
 * Loads test history via GET /api/analytics/test-history/:username.
 * Shows: AI insight · stats cards · subject performance bars · recent history.
 * Uses native progress bars (no chart library required).
 */
import { useEffect, useState } from "react";
import {
  View, Text, ScrollView, StyleSheet,
  ActivityIndicator, TouchableOpacity,
} from "react-native";
import { useRouter } from "expo-router";
import { Feather } from "@expo/vector-icons";
import { authFetch } from "../../lib/authFetch";
import { BRAND_COLOR } from "../../constants";
import { supabase } from "../../lib/supabase";

interface HistoryItem {
  subject: string;
  chapter?: string;
  mockType?: string;
  difficulty?: string;
  percentage: number | string;
  submittedAt?: string;
  saved_at?: string;
}

interface SubjectStat {
  subject: string;
  best: number;
  average: number;
  latest: number;
  count: number;
}

const SUBJECT_COLORS = [
  "#3b82f6", "#10b981", "#f59e0b", "#ef4444",
  "#8b5cf6", "#06b6d4", "#ec4899", "#f97316",
];

function buildSubjectStats(history: HistoryItem[]): SubjectStat[] {
  const map: Record<string, number[]> = {};
  history.forEach((item) => {
    const subj = item.subject || "Unknown";
    const score = Number(item.percentage || 0);
    if (!map[subj]) map[subj] = [];
    map[subj].push(score);
  });
  return Object.entries(map).map(([subject, scores]) => ({
    subject,
    best: Math.max(...scores),
    average: Math.round(scores.reduce((a, b) => a + b, 0) / scores.length),
    latest: scores[scores.length - 1],
    count: scores.length,
  }));
}

function getInsight(avg: number): string {
  if (avg >= 85)
    return "Excellent consistency. You are ready for harder questions and Hard-level practice.";
  if (avg >= 65)
    return "Good progress. Focus on weaker subjects and review mistakes after every mock test.";
  return "Revision needed. Start with concept review, then attempt short quizzes before mock tests.";
}

function ScoreBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <View style={sb.row}>
      <Text style={sb.label}>{label}</Text>
      <View style={sb.track}>
        <View style={[sb.fill, { width: `${value}%` as any, backgroundColor: color }]} />
      </View>
      <Text style={[sb.val, { color }]}>{value}%</Text>
    </View>
  );
}

export default function AnalyticsScreen() {
  const router = useRouter();
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [username, setUsername] = useState("");

  useEffect(() => {
    (async () => {
      const { data: { session } } = await supabase.auth.getSession();
      const uname = session?.user?.user_metadata?.username
        || session?.user?.email?.split("@")[0]
        || "user";
      setUsername(uname);
      try {
        const res: any = await authFetch(`/api/analytics/test-history/${uname}`);
        setHistory(res.history || []);
      } catch {
        setHistory([]);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const totalTests = history.length;
  const averageScore = totalTests > 0
    ? Math.round(history.reduce((s, i) => s + Number(i.percentage || 0), 0) / totalTests)
    : 0;
  const bestScore = totalTests > 0
    ? Math.max(...history.map((i) => Number(i.percentage || 0)))
    : 0;
  const latestScore = totalTests > 0
    ? Number(history[history.length - 1].percentage || 0)
    : 0;

  const subjectStats = buildSubjectStats(history);
  const insight = getInsight(averageScore);
  const insightColor = averageScore >= 85 ? "#10b981" : averageScore >= 65 ? "#f59e0b" : "#ef4444";

  return (
    <ScrollView style={s.container} contentContainerStyle={s.content}>

      {/* Page header */}
      <View style={s.pageHeader}>
        <TouchableOpacity style={s.backBtn} onPress={() => router.back()}>
          <Feather name="arrow-left" size={18} color={BRAND_COLOR} />
        </TouchableOpacity>
        <View style={[s.pageIconBox, { backgroundColor: "rgba(99,102,241,.08)" }]}>
          <Feather name="bar-chart-2" size={20} color={BRAND_COLOR} />
        </View>
        <View>
          <Text style={s.pageTitle}>Analytics</Text>
          <Text style={s.pageSubtitle}>Your performance insights</Text>
        </View>
      </View>

      {loading ? (
        <View style={s.center}><ActivityIndicator color={BRAND_COLOR} size="large" /></View>
      ) : totalTests === 0 ? (
        <>
          {/* AI Insight */}
          <View style={[s.insightBox, { borderColor: "rgba(99,102,241,.2)" }]}>
            <Text style={s.insightIcon}>🧠</Text>
            <View style={{ flex: 1 }}>
              <Text style={[s.insightTitle, { color: "#818cf8" }]}>AI Insight</Text>
              <Text style={s.insightText}>Submit a mock test to unlock analytics.</Text>
            </View>
          </View>
          <View style={s.emptyBox}>
            <Feather name="bar-chart-2" size={40} color="#9ca3af" />
            <Text style={s.emptyTitle}>No test data yet</Text>
            <Text style={s.emptySub}>Complete a mock test to see score trends, subject performance, and AI learning insights.</Text>
            <TouchableOpacity style={s.ctaBtn} onPress={() => router.push("/(tabs)/mocktest")}>
              <Feather name="edit-3" size={16} color="#fff" />
              <Text style={s.ctaBtnText}>Take a Mock Test</Text>
            </TouchableOpacity>
          </View>
        </>
      ) : (
        <>
          {/* AI Insight banner */}
          <View style={[s.insightBox, { borderColor: `${insightColor}40` }]}>
            <Text style={s.insightIcon}>🧠</Text>
            <View style={{ flex: 1 }}>
              <Text style={[s.insightTitle, { color: insightColor }]}>AI Insight</Text>
              <Text style={s.insightText}>{insight}</Text>
            </View>
          </View>

          {/* Stats cards */}
          <View style={s.statsGrid}>
            <StatCard label="Tests" value={String(totalTests)} icon="edit-3" color="#3b82f6" />
            <StatCard label="Average" value={`${averageScore}%`} icon="trending-up" color={BRAND_COLOR} />
            <StatCard label="Best" value={`${bestScore}%`} icon="award" color="#10b981" />
            <StatCard label="Latest" value={`${latestScore}%`} icon="clock" color="#f59e0b" />
          </View>

          {/* Subject performance */}
          {subjectStats.length > 0 && (
            <View style={s.card}>
              <Text style={s.cardTitle}>📚 Subject Performance</Text>
              <Text style={s.cardSubtitle}>Best · Average · Latest per subject</Text>
              {subjectStats.map((stat, i) => {
                const col = SUBJECT_COLORS[i % SUBJECT_COLORS.length];
                return (
                  <View key={stat.subject} style={s.subjectBlock}>
                    <Text style={[s.subjectName, { color: col }]}>{stat.subject}</Text>
                    <ScoreBar label="Best" value={stat.best} color="#10b981" />
                    <ScoreBar label="Avg" value={stat.average} color="#3b82f6" />
                    <ScoreBar label="Last" value={stat.latest} color="#f59e0b" />
                  </View>
                );
              })}
            </View>
          )}

          {/* Recent history */}
          <View style={s.card}>
            <Text style={s.cardTitle}>🕘 Recent Test History</Text>
            <Text style={s.cardSubtitle}>Last 10 mock test results</Text>
            {[...history].reverse().slice(0, 10).map((item, i) => {
              const score = Number(item.percentage || 0);
              const scoreColor = score >= 75 ? "#10b981" : score >= 50 ? "#f59e0b" : "#ef4444";
              const date = (item.submittedAt || item.saved_at || "").slice(0, 10);
              return (
                <View key={i} style={s.historyRow}>
                  <View style={{ flex: 1 }}>
                    <Text style={s.historySubject}>{item.subject}</Text>
                    <Text style={s.historyDetail}>
                      {item.chapter || item.mockType || "—"}{item.difficulty ? ` · ${item.difficulty}` : ""}{date ? ` · ${date}` : ""}
                    </Text>
                  </View>
                  <Text style={[s.historyScore, { color: scoreColor }]}>{score}%</Text>
                </View>
              );
            })}
          </View>
        </>
      )}
    </ScrollView>
  );
}

function StatCard({ label, value, icon, color }: { label: string; value: string; icon: any; color: string }) {
  return (
    <View style={[sc.card, { borderColor: `${color}30` }]}>
      <Feather name={icon} size={18} color={color} />
      <Text style={[sc.value, { color }]}>{value}</Text>
      <Text style={sc.label}>{label}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f8fafc" },
  content: { padding: 16, paddingBottom: 60 },
  pageHeader: { flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 16 },
  backBtn: { padding: 8, borderRadius: 8, backgroundColor: "rgba(99,102,241,.08)" },
  pageIconBox: { width: 44, height: 44, borderRadius: 12, alignItems: "center", justifyContent: "center" },
  pageTitle: { fontSize: 20, fontWeight: "800", color: "#111827" },
  pageSubtitle: { fontSize: 13, color: "#6b7280" },
  center: { alignItems: "center", paddingVertical: 60 },
  // Insight banner
  insightBox: { flexDirection: "row", alignItems: "flex-start", gap: 10, padding: 14, borderRadius: 12, backgroundColor: "rgba(99,102,241,.06)", borderWidth: 1, marginBottom: 14 },
  insightIcon: { fontSize: 20, marginTop: 1 },
  insightTitle: { fontSize: 12, fontWeight: "700", letterSpacing: 0.3, marginBottom: 2 },
  insightText: { fontSize: 13, color: "#374151", lineHeight: 19 },
  // Stats grid
  statsGrid: { flexDirection: "row", flexWrap: "wrap", gap: 10, marginBottom: 14 },
  // Card
  card: { backgroundColor: "#fff", borderRadius: 14, padding: 16, marginBottom: 14, borderWidth: 1, borderColor: "#e5e7eb" },
  cardTitle: { fontSize: 15, fontWeight: "700", color: "#111827", marginBottom: 2 },
  cardSubtitle: { fontSize: 12, color: "#6b7280", marginBottom: 14 },
  // Subject block
  subjectBlock: { marginBottom: 14, paddingBottom: 14, borderBottomWidth: 1, borderBottomColor: "#f3f4f6" },
  subjectName: { fontSize: 13, fontWeight: "700", marginBottom: 6 },
  // History
  historyRow: { flexDirection: "row", alignItems: "center", paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: "#f3f4f6" },
  historySubject: { fontSize: 14, fontWeight: "700", color: "#111827" },
  historyDetail: { fontSize: 11, color: "#6b7280", marginTop: 2 },
  historyScore: { fontSize: 18, fontWeight: "800" },
  // Empty state
  emptyBox: { alignItems: "center", paddingVertical: 40, gap: 12 },
  emptyTitle: { fontSize: 18, fontWeight: "700", color: "#374151" },
  emptySub: { fontSize: 13, color: "#6b7280", textAlign: "center", lineHeight: 20, paddingHorizontal: 20 },
  ctaBtn: { flexDirection: "row", alignItems: "center", gap: 8, backgroundColor: BRAND_COLOR, borderRadius: 10, paddingHorizontal: 20, paddingVertical: 12, marginTop: 8 },
  ctaBtnText: { color: "#fff", fontWeight: "700", fontSize: 14 },
});

const sc = StyleSheet.create({
  card: { width: "47%", backgroundColor: "#fff", borderRadius: 12, padding: 14, alignItems: "center", borderWidth: 1, gap: 4 },
  value: { fontSize: 22, fontWeight: "800", marginTop: 4 },
  label: { fontSize: 11, color: "#6b7280", fontWeight: "600" },
});

const sb = StyleSheet.create({
  row: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 5 },
  label: { fontSize: 10, color: "#6b7280", width: 28, fontWeight: "600" },
  track: { flex: 1, height: 6, backgroundColor: "#e5e7eb", borderRadius: 99, overflow: "hidden" },
  fill: { height: 6, borderRadius: 99 },
  val: { fontSize: 11, fontWeight: "700", width: 36, textAlign: "right" },
});
