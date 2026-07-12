/**
 * Student Dashboard (Home tab).
 * Calls GET /api/student/dashboard/summary.
 * Shows a welcome screen for new students who don't have a profile yet.
 */
import { useEffect, useState } from "react";
import {
  View, Text, ScrollView, StyleSheet, RefreshControl,
  TouchableOpacity, ActivityIndicator, Image,
} from "react-native";
import { useRouter } from "expo-router";
import { authFetch } from "../../lib/authFetch";
import { signOut } from "../../lib/auth";
import { BRAND_COLOR } from "../../constants";
import { supabase } from "../../lib/supabase";

interface DashboardSummary {
  student?: {
    display_name?: string;
    grade?: string;
    subscription_plan?: string;
  };
  recent_progress?: Array<{ subject: string; chapter: string; completed_steps: number; total_steps: number }>;
  test_history?: Array<{ subject: string; percentage: number; created_at: string }>;
  streak_days?: number;
  completed_chapters?: number;
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
      // Get current user email
      const { data: { session } } = await supabase.auth.getSession();
      setUserEmail(session?.user?.email ?? "");

      const result = await authFetch("/api/student/dashboard/summary");
      setData(result);
    } catch (err: any) {
      // Don't show scary error for new students — they just don't have a profile yet
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
      <ScrollView
        style={s.container}
        contentContainerStyle={s.content}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadDashboard(); }} tintColor={BRAND_COLOR} />
        }
      >
        {/* Welcome card */}
        <View style={s.welcomeCard}>
          <Image source={require("../../assets/icon.png")} style={s.welcomeLogo} resizeMode="contain" />
          <Text style={s.welcomeTitle}>Welcome to Likha Poha AI! 🎉</Text>
          <Text style={s.welcomeSub}>
            Your AI-powered CBSE tutor for Grades 5–12.{"\n"}
            Start learning right away — no setup needed.
          </Text>
        </View>

        {/* Quick action: start a lesson */}
        <Text style={s.sectionTitle}>⚡ Get Started</Text>

        <TouchableOpacity style={s.bigBtn} onPress={() => router.push("/(tabs)/lessons")}>
          <Text style={s.bigBtnEmoji}>📚</Text>
          <View>
            <Text style={s.bigBtnTitle}>Start a Lesson</Text>
            <Text style={s.bigBtnSub}>Pick any subject, chapter, and let AI teach you</Text>
          </View>
        </TouchableOpacity>

        <TouchableOpacity style={[s.bigBtn, { marginTop: 10 }]} onPress={() => router.push("/(tabs)/mocktest")}>
          <Text style={s.bigBtnEmoji}>✍️</Text>
          <View>
            <Text style={s.bigBtnTitle}>Take a Mock Test</Text>
            <Text style={s.bigBtnSub}>Practice with AI-generated CBSE questions</Text>
          </View>
        </TouchableOpacity>

        <TouchableOpacity onPress={handleSignOut} style={s.signOutRow}>
          <Text style={s.signOutText}>Sign out ({userEmail})</Text>
        </TouchableOpacity>
      </ScrollView>
    );
  }

  // Existing student with profile
  const student = data.student;
  const recentProgress = data.recent_progress ?? [];
  const testHistory = data.test_history ?? [];

  return (
    <ScrollView
      style={s.container}
      contentContainerStyle={s.content}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadDashboard(); }} tintColor={BRAND_COLOR} />
      }
    >
      {/* Header */}
      <View style={s.header}>
        <View>
          <Text style={s.greeting}>👋 Hello, {student.display_name ?? "Student"}!</Text>
          <Text style={s.gradeText}>
            {student.grade ?? ""} · {student.subscription_plan === "free" ? "Free Plan" : "Premium"}
          </Text>
        </View>
        <TouchableOpacity onPress={handleSignOut} style={s.signOutBtn}>
          <Text style={s.signOutText}>Sign out</Text>
        </TouchableOpacity>
      </View>

      {/* Stats */}
      <View style={s.statsRow}>
        <StatCard emoji="🔥" label="Day streak" value={String(data.streak_days ?? 0)} />
        <StatCard emoji="✅" label="Chapters done" value={String(data.completed_chapters ?? 0)} />
        <StatCard emoji="📊" label="Tests taken" value={String(testHistory.length)} />
      </View>

      {recentProgress.length > 0 && (
        <Section title="📚 Continue Learning">
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
        <Section title="🎯 Recent Test Scores">
          {testHistory.slice(0, 3).map((t, i) => (
            <View key={i} style={s.scoreRow}>
              <Text style={s.scoreSubject}>{t.subject}</Text>
              <Text style={[s.scoreValue, t.percentage >= 70 ? s.scoreGood : s.scoreWeak]}>{t.percentage}%</Text>
            </View>
          ))}
        </Section>
      )}

      <Section title="⚡ Quick Actions">
        <View style={s.actionsRow}>
          <QuickAction emoji="📖" label="Lessons" onPress={() => router.push("/(tabs)/lessons")} />
          <QuickAction emoji="✍️" label="Mock Test" onPress={() => router.push("/(tabs)/mocktest")} />
        </View>
      </Section>
    </ScrollView>
  );
}

function StatCard({ emoji, label, value }: { emoji: string; label: string; value: string }) {
  return (
    <View style={s.statCard}>
      <Text style={s.statEmoji}>{emoji}</Text>
      <Text style={s.statValue}>{value}</Text>
      <Text style={s.statLabel}>{label}</Text>
    </View>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={s.section}>
      <Text style={s.sectionTitle}>{title}</Text>
      {children}
    </View>
  );
}

function QuickAction({ emoji, label, onPress }: { emoji: string; label: string; onPress: () => void }) {
  return (
    <TouchableOpacity style={s.quickActionBtn} onPress={onPress}>
      <Text style={s.quickActionEmoji}>{emoji}</Text>
      <Text style={s.quickActionLabel}>{label}</Text>
    </TouchableOpacity>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f8fafc" },
  content: { padding: 16, paddingBottom: 40 },
  center: { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "#f8fafc" },
  loadingText: { marginTop: 12, color: "#6b7280" },

  // Welcome state for new students
  welcomeCard: {
    backgroundColor: "#fff", borderRadius: 16, padding: 24,
    alignItems: "center", marginBottom: 24,
    borderWidth: 1, borderColor: "#e5e7eb",
  },
  welcomeLogo: { width: 72, height: 72, borderRadius: 16, marginBottom: 12 },
  welcomeTitle: { fontSize: 18, fontWeight: "800", color: "#111827", textAlign: "center", marginBottom: 8 },
  welcomeSub: { fontSize: 14, color: "#6b7280", textAlign: "center", lineHeight: 22 },

  bigBtn: {
    flexDirection: "row", alignItems: "center", gap: 14,
    backgroundColor: "#fff", borderRadius: 14, padding: 18,
    borderWidth: 1, borderColor: "#e5e7eb",
  },
  bigBtnEmoji: { fontSize: 36 },
  bigBtnTitle: { fontSize: 16, fontWeight: "700", color: "#111827", marginBottom: 2 },
  bigBtnSub: { fontSize: 13, color: "#6b7280" },
  signOutRow: { marginTop: 32, alignItems: "center" },

  // Dashboard state
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 },
  greeting: { fontSize: 20, fontWeight: "800", color: "#111827" },
  gradeText: { fontSize: 13, color: "#6b7280", marginTop: 2 },
  signOutBtn: { padding: 6 },
  signOutText: { color: "#ef4444", fontSize: 13, fontWeight: "600" },
  statsRow: { flexDirection: "row", gap: 10, marginBottom: 20 },
  statCard: { flex: 1, backgroundColor: "#fff", borderRadius: 14, padding: 14, alignItems: "center", borderWidth: 1, borderColor: "#e5e7eb" },
  statEmoji: { fontSize: 22, marginBottom: 4 },
  statValue: { fontSize: 22, fontWeight: "800", color: "#111827" },
  statLabel: { fontSize: 11, color: "#6b7280", marginTop: 2, textAlign: "center" },
  section: { marginBottom: 20 },
  sectionTitle: { fontSize: 15, fontWeight: "700", color: "#111827", marginBottom: 10 },
  progressCard: { backgroundColor: "#fff", borderRadius: 12, padding: 14, marginBottom: 10, borderWidth: 1, borderColor: "#e5e7eb" },
  progressSubject: { fontSize: 11, fontWeight: "700", color: BRAND_COLOR, textTransform: "uppercase", letterSpacing: 0.5 },
  progressChapter: { fontSize: 14, fontWeight: "600", color: "#111827", marginTop: 2, marginBottom: 8 },
  progressBarBg: { height: 6, backgroundColor: "#e5e7eb", borderRadius: 99 },
  progressBarFill: { height: 6, backgroundColor: BRAND_COLOR, borderRadius: 99 },
  progressPct: { fontSize: 11, color: "#6b7280", marginTop: 4 },
  scoreRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", backgroundColor: "#fff", borderRadius: 10, padding: 12, marginBottom: 8, borderWidth: 1, borderColor: "#e5e7eb" },
  scoreSubject: { fontSize: 14, fontWeight: "600", color: "#374151" },
  scoreValue: { fontSize: 16, fontWeight: "800" },
  scoreGood: { color: "#16a34a" },
  scoreWeak: { color: "#dc2626" },
  actionsRow: { flexDirection: "row", gap: 10 },
  quickActionBtn: { flex: 1, backgroundColor: "#fff", borderRadius: 14, padding: 18, alignItems: "center", borderWidth: 1, borderColor: "#e5e7eb" },
  quickActionEmoji: { fontSize: 28, marginBottom: 6 },
  quickActionLabel: { fontSize: 13, fontWeight: "700", color: "#374151" },
});
