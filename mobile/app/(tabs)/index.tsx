/**
 * Student Dashboard (Home tab).
 * Calls GET /api/student/dashboard/summary.
 * Uses Feather (lucide-compatible) vector icons — no emoji.
 */
import { useEffect, useState } from "react";
import {
  View, Text, ScrollView, StyleSheet, RefreshControl,
  TouchableOpacity, ActivityIndicator, Image,
} from "react-native";
import { useRouter } from "expo-router";
import { Feather } from "@expo/vector-icons";
import { authFetch } from "../../lib/authFetch";
import { signOut } from "../../lib/auth";
import { BRAND_COLOR } from "../../constants";
import { supabase } from "../../lib/supabase";

interface DashboardSummary {
  student?: {
    username?: string;
    display_name?: string;  // may not exist — use username as fallback
    grade?: string;
    study_streak_days?: number;
    lessons_completed?: number;
  };
  subscription?: { plan_name?: string; canonical_plan_key?: string; has_full_access?: boolean };
  recent_progress?: Array<{ subject: string; chapter: string; completed_steps: number; total_steps: number }>;
  mock_tests?: { recent?: Array<{ subject: string; percentage: number; created_at: string }> };
  // legacy shape fallback
  test_history?: Array<{ subject: string; percentage: number; created_at: string }>;
  streak_days?: number;
  completed_chapters?: number;
}

// Returns "Good morning", "Good afternoon", "Good evening", or "Good night"
function getTimeGreeting(): string {
  const hour = new Date().getHours();
  if (hour >= 5 && hour < 12)  return "Good morning";
  if (hour >= 12 && hour < 17) return "Good afternoon";
  if (hour >= 17 && hour < 21) return "Good evening";
  return "Good night";
}

export default function HomeScreen() {
  const router = useRouter();
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [userEmail, setUserEmail] = useState("");

  async function loadDashboard() {
    try {
      setError("");
      const { data: { session } } = await supabase.auth.getSession();
      setUserEmail(session?.user?.email ?? "");
      const result = await authFetch("/api/student/dashboard/summary");
      setData(result);
    } catch (err: any) {
      setError(err.message ?? "");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => { loadDashboard(); }, []);

  async function handleSignOut() {
    await signOut();
    router.replace("/auth/login");
  }

  if (loading) {
    return (
      <View style={s.center}>
        <ActivityIndicator size="large" color={BRAND_COLOR} />
        <Text style={s.loadingText}>Loading…</Text>
      </View>
    );
  }

  // New student — no backend profile yet
  if (error || !data?.student) {
    return (
      <ScrollView style={s.container} contentContainerStyle={s.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadDashboard(); }} tintColor={BRAND_COLOR} />}>

        <View style={s.welcomeCard}>
          <Image source={require("../../assets/icon.png")} style={s.welcomeLogo} resizeMode="contain" />
          <Text style={s.welcomeTitle}>Welcome to Likha Poha AI</Text>
          <Text style={s.welcomeSub}>AI-powered CBSE tutor for Grades 5–12.{"\n"}Start learning right away — no setup needed.</Text>
        </View>

        <Text style={s.sectionTitle}>Get Started</Text>

        {[
          { icon: "book-open" as const, title: "Start a Lesson", sub: "Pick any subject and let AI teach you", route: "/(tabs)/lessons" },
          { icon: "edit-3" as const, title: "Take a Mock Test", sub: "Practice with AI-generated CBSE questions", route: "/(tabs)/mocktest" },
          { icon: "message-circle" as const, title: "Ask AI Tutor", sub: "Get instant answers to any CBSE doubt", route: "/(tabs)/doubt" },
          { icon: "grid" as const, title: "Formula Sheet", sub: "CBSE syllabus formulas with examples", route: "/(tabs)/formula" },
          { icon: "award" as const, title: "Exam Prep", sub: "JEE · NEET · CUET · SAT · IELTS · TOEFL", route: "/(tabs)/examprep" },
        ].map(item => (
          <TouchableOpacity key={item.route} style={[s.bigBtn, { marginTop: 10 }]} onPress={() => router.push(item.route as any)}>
            <View style={s.bigBtnIcon}><Feather name={item.icon} size={26} color={BRAND_COLOR} /></View>
            <View style={{ flex: 1 }}>
              <Text style={s.bigBtnTitle}>{item.title}</Text>
              <Text style={s.bigBtnSub}>{item.sub}</Text>
            </View>
            <Feather name="chevron-right" size={16} color="#9ca3af" />
          </TouchableOpacity>
        ))}

        <TouchableOpacity onPress={handleSignOut} style={s.signOutRow}>
          <Feather name="log-out" size={14} color="#ef4444" />
          <Text style={[s.signOutText, { marginLeft: 6 }]}>Sign out ({userEmail})</Text>
        </TouchableOpacity>
      </ScrollView>
    );
  }

  const student = data.student;
  const recentProgress = data.recent_progress ?? [];
  const testHistory = data.test_history ?? data.mock_tests?.recent ?? [];
  // Resolve name: prefer display_name, fallback to username, fallback to "Student"
  const studentName = student?.display_name || student?.username || "Student";
  // Resolve plan label
  const planLabel = data.subscription?.plan_name ?? (data.subscription?.has_full_access ? "Premium" : "Free Plan");
  // Resolve stats
  const streakDays = student?.study_streak_days ?? (data as any).streak_days ?? 0;
  const lessonsCompleted = student?.lessons_completed ?? (data as any).completed_chapters ?? 0;

  return (
    <ScrollView style={s.container} contentContainerStyle={s.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadDashboard(); }} tintColor={BRAND_COLOR} />}>

      {/* Header */}
      <View style={s.header}>
        <View style={{ flex: 1 }}>
          <Text style={s.greetingTime}>{getTimeGreeting()},</Text>
          <Text style={s.greeting}>{studentName}</Text>
          <Text style={s.gradeText}>{student?.grade ?? ""} · {planLabel}</Text>
        </View>
        <TouchableOpacity onPress={handleSignOut} style={s.signOutBtn}>
          <Feather name="log-out" size={16} color="#ef4444" />
        </TouchableOpacity>
      </View>

      {/* Stats */}
      <View style={s.statsRow}>
        <StatCard icon="zap" label="Day streak" value={String(streakDays)} color="#f59e0b" />
        <StatCard icon="check-circle" label="Lessons done" value={String(lessonsCompleted)} color="#16a34a" />
        <StatCard icon="bar-chart-2" label="Tests taken" value={String(testHistory.length)} color={BRAND_COLOR} />
      </View>

      {recentProgress.length > 0 && (
        <Section icon="book-open" title="Continue Learning">
          {recentProgress.slice(0, 3).map((item, i) => (
            <TouchableOpacity key={i} style={s.progressCard} onPress={() => router.push("/(tabs)/lessons")}>
              <Text style={s.progressSubject}>{item.subject}</Text>
              <Text style={s.progressChapter} numberOfLines={1}>{item.chapter}</Text>
              <View style={s.progressBarBg}>
                <View style={[s.progressBarFill, { width: `${Math.round((item.completed_steps / item.total_steps) * 100)}%` as any }]} />
              </View>
              <Text style={s.progressPct}>{item.completed_steps}/{item.total_steps} steps</Text>
            </TouchableOpacity>
          ))}
        </Section>
      )}

      {testHistory.length > 0 && (
        <Section icon="target" title="Recent Test Scores">
          {testHistory.slice(0, 3).map((t, i) => (
            <View key={i} style={s.scoreRow}>
              <Text style={s.scoreSubject}>{t.subject}</Text>
              <Text style={[s.scoreValue, t.percentage >= 70 ? s.scoreGood : s.scoreWeak]}>{t.percentage}%</Text>
            </View>
          ))}
        </Section>
      )}

      <Section icon="zap" title="Quick Actions">
        <View style={s.actionsGrid}>
          <QuickAction icon="book-open" label="Lessons" onPress={() => router.push("/(tabs)/lessons")} />
          <QuickAction icon="edit-3" label="Mock Test" onPress={() => router.push("/(tabs)/mocktest")} />
          <QuickAction icon="message-circle" label="Ask Doubt" onPress={() => router.push("/(tabs)/doubt")} />
          <QuickAction icon="grid" label="Formulas" onPress={() => router.push("/(tabs)/formula")} />
          <QuickAction icon="external-link" label="Learn More" onPress={() => router.navigate("/(tabs)/learn" as any)} />
          <QuickAction icon="layers" label="Exemplar" onPress={() => router.navigate("/(tabs)/exemplar" as any)} />
          <QuickAction icon="bar-chart-2" label="Analytics" onPress={() => router.navigate("/(tabs)/analytics" as any)} />
          <QuickAction icon="award" label="Exam Prep" onPress={() => router.navigate("/(tabs)/examprep" as any)} />
        </View>
      </Section>
    </ScrollView>
  );
}

function StatCard({ icon, label, value, color }: { icon: React.ComponentProps<typeof Feather>["name"]; label: string; value: string; color: string }) {
  return (
    <View style={s.statCard}>
      <Feather name={icon} size={20} color={color} />
      <Text style={[s.statValue, { color }]}>{value}</Text>
      <Text style={s.statLabel}>{label}</Text>
    </View>
  );
}

function Section({ icon, title, children }: { icon: React.ComponentProps<typeof Feather>["name"]; title: string; children: React.ReactNode }) {
  return (
    <View style={s.section}>
      <View style={s.sectionHeader}>
        <Feather name={icon} size={15} color="#374151" />
        <Text style={s.sectionTitle}>{title}</Text>
      </View>
      {children}
    </View>
  );
}

function QuickAction({ icon, label, onPress }: { icon: React.ComponentProps<typeof Feather>["name"]; label: string; onPress: () => void }) {
  return (
    <TouchableOpacity style={s.quickActionBtn} onPress={onPress}>
      <View style={s.quickActionIconBox}>
        <Feather name={icon} size={22} color={BRAND_COLOR} />
      </View>
      <Text style={s.quickActionLabel}>{label}</Text>
    </TouchableOpacity>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f8fafc" },
  content: { padding: 16, paddingBottom: 40 },
  center: { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "#f8fafc" },
  loadingText: { marginTop: 12, color: "#6b7280" },
  // Welcome
  welcomeCard: { backgroundColor: "#fff", borderRadius: 16, padding: 24, alignItems: "center", marginBottom: 20, borderWidth: 1, borderColor: "#e5e7eb" },
  welcomeLogo: { width: 64, height: 64, borderRadius: 14, marginBottom: 12 },
  welcomeTitle: { fontSize: 18, fontWeight: "800", color: "#111827", textAlign: "center", marginBottom: 6 },
  welcomeSub: { fontSize: 13, color: "#6b7280", textAlign: "center", lineHeight: 20 },
  bigBtn: { flexDirection: "row", alignItems: "center", gap: 14, backgroundColor: "#fff", borderRadius: 14, padding: 16, borderWidth: 1, borderColor: "#e5e7eb" },
  bigBtnIcon: { width: 44, height: 44, borderRadius: 12, backgroundColor: "rgba(99,102,241,.08)", alignItems: "center", justifyContent: "center" },
  bigBtnTitle: { fontSize: 15, fontWeight: "700", color: "#111827", marginBottom: 2 },
  bigBtnSub: { fontSize: 12, color: "#6b7280" },
  signOutRow: { marginTop: 28, flexDirection: "row", alignItems: "center", justifyContent: "center" },
  signOutText: { color: "#ef4444", fontSize: 13, fontWeight: "600" },
  // Dashboard header
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 20 },
  greetingTime: { fontSize: 13, fontWeight: "600", color: "#6b7280", marginBottom: 2 },
  greeting: { fontSize: 22, fontWeight: "800", color: "#111827", letterSpacing: -0.3 },
  gradeText: { fontSize: 13, color: "#6b7280", marginTop: 3 },
  signOutBtn: { padding: 8, borderRadius: 8, backgroundColor: "#fef2f2" },
  // Stats
  statsRow: { flexDirection: "row", gap: 10, marginBottom: 20 },
  statCard: { flex: 1, backgroundColor: "#fff", borderRadius: 14, padding: 14, alignItems: "center", borderWidth: 1, borderColor: "#e5e7eb", gap: 4 },
  statValue: { fontSize: 22, fontWeight: "800", color: "#111827" },
  statLabel: { fontSize: 10, color: "#6b7280", textAlign: "center", fontWeight: "600" },
  // Section
  section: { marginBottom: 20 },
  sectionHeader: { flexDirection: "row", alignItems: "center", gap: 6, marginBottom: 12 },
  sectionTitle: { fontSize: 15, fontWeight: "700", color: "#111827" },
  // Progress cards
  progressCard: { backgroundColor: "#fff", borderRadius: 12, padding: 14, marginBottom: 10, borderWidth: 1, borderColor: "#e5e7eb" },
  progressSubject: { fontSize: 10, fontWeight: "700", color: BRAND_COLOR, textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 3 },
  progressChapter: { fontSize: 14, fontWeight: "600", color: "#111827", marginBottom: 8 },
  progressBarBg: { height: 5, backgroundColor: "#e5e7eb", borderRadius: 99 },
  progressBarFill: { height: 5, backgroundColor: BRAND_COLOR, borderRadius: 99 },
  progressPct: { fontSize: 11, color: "#6b7280", marginTop: 5 },
  // Score rows
  scoreRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", backgroundColor: "#fff", borderRadius: 10, padding: 12, marginBottom: 8, borderWidth: 1, borderColor: "#e5e7eb" },
  scoreSubject: { fontSize: 14, fontWeight: "600", color: "#374151" },
  scoreValue: { fontSize: 16, fontWeight: "800" },
  scoreGood: { color: "#16a34a" },
  scoreWeak: { color: "#dc2626" },
  // Quick actions — 2×2 grid
  actionsGrid: { flexDirection: "row", flexWrap: "wrap", gap: 10 },
  quickActionBtn: { width: "47%", backgroundColor: "#fff", borderRadius: 14, padding: 16, alignItems: "center", borderWidth: 1, borderColor: "#e5e7eb" },
  quickActionIconBox: { width: 48, height: 48, borderRadius: 12, backgroundColor: "rgba(99,102,241,.08)", alignItems: "center", justifyContent: "center", marginBottom: 8 },
  quickActionLabel: { fontSize: 13, fontWeight: "700", color: "#374151" },
});
