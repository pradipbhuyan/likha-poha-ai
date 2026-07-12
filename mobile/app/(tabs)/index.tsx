/**
 * Student Dashboard (Home tab).
 *
 * Calls GET /api/student/dashboard/summary — same endpoint as the web app.
 * Uses hasPaidAccess() from @likhapoha/shared for subscription checks.
 */
import { useEffect, useState } from "react";
import {
  View, Text, ScrollView, StyleSheet, RefreshControl,
  TouchableOpacity, ActivityIndicator,
} from "react-native";
import { useRouter } from "expo-router";
import { authFetch } from "../../lib/authFetch";
import { signOut } from "../../lib/auth";
import { BRAND_COLOR } from "../../constants";

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

  async function loadDashboard() {
    try {
      setError("");
      const result = await authFetch("/api/student/dashboard/summary");
      setData(result);
    } catch (err: any) {
      setError(err.message ?? "Could not load dashboard.");
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
      <View style={styles.center}>
        <ActivityIndicator size="large" color={BRAND_COLOR} />
        <Text style={styles.loadingText}>Loading your dashboard…</Text>
      </View>
    );
  }

  const student = data?.student;
  const recentProgress = data?.recent_progress ?? [];
  const testHistory = data?.test_history ?? [];

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={() => { setRefreshing(true); loadDashboard(); }}
          tintColor={BRAND_COLOR}
        />
      }
    >
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.greeting}>
            👋 Hello, {student?.display_name ?? "Student"}!
          </Text>
          <Text style={styles.gradeText}>
            {student?.grade ?? ""} · {student?.subscription_plan === "free" ? "Free Plan" : "Premium"}
          </Text>
        </View>
        <TouchableOpacity onPress={handleSignOut} style={styles.signOutBtn}>
          <Text style={styles.signOutText}>Sign out</Text>
        </TouchableOpacity>
      </View>

      {error ? (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      ) : null}

      {/* Stats row */}
      <View style={styles.statsRow}>
        <StatCard emoji="🔥" label="Day streak" value={String(data?.streak_days ?? 0)} />
        <StatCard emoji="✅" label="Chapters done" value={String(data?.completed_chapters ?? 0)} />
        <StatCard emoji="📊" label="Tests taken" value={String(testHistory.length)} />
      </View>

      {/* Recent progress */}
      {recentProgress.length > 0 && (
        <Section title="📚 Continue Learning">
          {recentProgress.slice(0, 3).map((item, i) => (
            <TouchableOpacity
              key={i}
              style={styles.progressCard}
              onPress={() => router.push("/(tabs)/lessons")}
            >
              <Text style={styles.progressSubject}>{item.subject}</Text>
              <Text style={styles.progressChapter} numberOfLines={1}>{item.chapter}</Text>
              <View style={styles.progressBarBg}>
                <View
                  style={[
                    styles.progressBarFill,
                    { width: `${Math.round((item.completed_steps / item.total_steps) * 100)}%` },
                  ]}
                />
              </View>
              <Text style={styles.progressPct}>
                {item.completed_steps}/{item.total_steps} steps
              </Text>
            </TouchableOpacity>
          ))}
        </Section>
      )}

      {/* Recent test scores */}
      {testHistory.length > 0 && (
        <Section title="🎯 Recent Test Scores">
          {testHistory.slice(0, 3).map((t, i) => (
            <View key={i} style={styles.scoreRow}>
              <Text style={styles.scoreSubject}>{t.subject}</Text>
              <Text style={[styles.scoreValue, t.percentage >= 70 ? styles.scoreGood : styles.scoreWeak]}>
                {t.percentage}%
              </Text>
            </View>
          ))}
        </Section>
      )}

      {/* Quick actions */}
      <Section title="⚡ Quick Actions">
        <View style={styles.actionsRow}>
          <QuickAction emoji="📖" label="Lessons" onPress={() => router.push("/(tabs)/lessons")} />
          <QuickAction emoji="✍️" label="Mock Test" onPress={() => router.push("/(tabs)/mocktest")} />
        </View>
      </Section>
    </ScrollView>
  );
}

function StatCard({ emoji, label, value }: { emoji: string; label: string; value: string }) {
  return (
    <View style={styles.statCard}>
      <Text style={styles.statEmoji}>{emoji}</Text>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {children}
    </View>
  );
}

function QuickAction({ emoji, label, onPress }: { emoji: string; label: string; onPress: () => void }) {
  return (
    <TouchableOpacity style={styles.quickActionBtn} onPress={onPress}>
      <Text style={styles.quickActionEmoji}>{emoji}</Text>
      <Text style={styles.quickActionLabel}>{label}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f8fafc" },
  content: { padding: 16, paddingBottom: 40 },
  center: { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "#f8fafc" },
  loadingText: { marginTop: 12, color: "#6b7280" },
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 },
  greeting: { fontSize: 20, fontWeight: "800", color: "#111827" },
  gradeText: { fontSize: 13, color: "#6b7280", marginTop: 2 },
  signOutBtn: { padding: 6 },
  signOutText: { color: "#ef4444", fontSize: 13, fontWeight: "600" },
  errorBox: { backgroundColor: "#fef2f2", borderRadius: 10, padding: 12, marginBottom: 16 },
  errorText: { color: "#dc2626", fontSize: 14 },
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
