/**
 * Account tab — profile info and sign out.
 * Uses GET /api/auth/profile — same endpoint as the web.
 */
import { useEffect, useState } from "react";
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity,
  ActivityIndicator, Alert, Platform,
} from "react-native";
import { useRouter } from "expo-router";
import Constants from "expo-constants";
import * as Application from "expo-application";
import { authFetch } from "../../lib/authFetch";
import { signOut } from "../../lib/auth";
import { BRAND_COLOR } from "../../constants";

interface Profile {
  username?: string;
  display_name?: string;
  email?: string;
  role?: string;
  grade?: string;
  subscription_plan?: string;
  access_cbse?: boolean;
}

export default function AccountScreen() {
  const router = useRouter();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    authFetch("/api/auth/profile")
      .then(setProfile)
      .catch(() => setProfile(null))
      .finally(() => setLoading(false));
  }, []);

  async function handleSignOut() {
    Alert.alert("Sign out", "Are you sure you want to sign out?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Sign out",
        style: "destructive",
        onPress: async () => {
          await signOut();
          router.replace("/auth/login");
        },
      },
    ]);
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={BRAND_COLOR} />
      </View>
    );
  }

  const isPaid = profile?.access_cbse === true;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Avatar */}
      <View style={styles.avatarRow}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>
            {(profile?.display_name ?? profile?.username ?? "U")[0].toUpperCase()}
          </Text>
        </View>
        <View style={styles.avatarInfo}>
          <Text style={styles.displayName}>{profile?.display_name ?? profile?.username ?? "User"}</Text>
          <Text style={styles.email}>{profile?.email ?? ""}</Text>
          <View style={[styles.planBadge, isPaid ? styles.planBadgePaid : styles.planBadgeFree]}>
            <Text style={styles.planBadgeText}>{isPaid ? "✨ Premium" : "Free Plan"}</Text>
          </View>
        </View>
      </View>

      {/* Details */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Account Details</Text>
        <InfoRow label="Role" value={profile?.role ?? "—"} />
        <InfoRow label="Grade" value={profile?.grade ?? "—"} />
        <InfoRow label="Plan" value={profile?.subscription_plan ?? "free"} />
      </View>

      {/* Upgrade CTA for free users */}
      {!isPaid && (
        <View style={styles.upgradeCard}>
          <Text style={styles.upgradeTitle}>🚀 Unlock Full Access</Text>
          <Text style={styles.upgradeDesc}>
            Get unlimited lessons, mock tests, exemplar practice, and more.
          </Text>
          <Text style={styles.upgradeNote}>
            Visit likhapoha.in to subscribe.
          </Text>
        </View>
      )}

      {/* Sign out */}
      <TouchableOpacity style={styles.signOutBtn} onPress={handleSignOut}>
        <Text style={styles.signOutText}>Sign out</Text>
      </TouchableOpacity>

      <Text style={styles.versionText}>
        {(() => {
          const version = Constants.expoConfig?.version ?? "1.1.0";
          const os = Platform.OS === "ios" ? "iOS" : "Android";
          // In Expo Go, nativeBuildVersion is Expo Go's own build number (irrelevant).
          // Constants.appOwnership === "expo" means running inside Expo Go.
          const isExpoGo = Constants.appOwnership === "expo";
          const buildInfo = isExpoGo
            ? "dev"
            : (Application.nativeBuildVersion ?? "—");
          return `Likha Poha AI v${version} (${os} ${isExpoGo ? "Expo Go" : `build ${buildInfo}`})`;
        })()}
      </Text>
    </ScrollView>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.infoRow}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={styles.infoValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f8fafc" },
  content: { padding: 20, paddingBottom: 60 },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  avatarRow: { flexDirection: "row", alignItems: "center", marginBottom: 28 },
  avatar: { width: 64, height: 64, borderRadius: 32, backgroundColor: BRAND_COLOR, justifyContent: "center", alignItems: "center", marginRight: 16 },
  avatarText: { fontSize: 28, fontWeight: "800", color: "#fff" },
  avatarInfo: { flex: 1 },
  displayName: { fontSize: 20, fontWeight: "800", color: "#111827" },
  email: { fontSize: 13, color: "#6b7280", marginTop: 2 },
  planBadge: { marginTop: 6, alignSelf: "flex-start", paddingHorizontal: 10, paddingVertical: 3, borderRadius: 99 },
  planBadgePaid: { backgroundColor: "#fef9c3", borderWidth: 1, borderColor: "#fde047" },
  planBadgeFree: { backgroundColor: "#f1f5f9", borderWidth: 1, borderColor: "#e2e8f0" },
  planBadgeText: { fontSize: 12, fontWeight: "700", color: "#374151" },
  section: { backgroundColor: "#fff", borderRadius: 14, padding: 16, marginBottom: 20, borderWidth: 1, borderColor: "#e5e7eb" },
  sectionTitle: { fontSize: 13, fontWeight: "700", color: "#6b7280", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 12 },
  infoRow: { flexDirection: "row", justifyContent: "space-between", paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: "#f1f5f9" },
  infoLabel: { fontSize: 14, color: "#6b7280", fontWeight: "500" },
  infoValue: { fontSize: 14, color: "#111827", fontWeight: "600", textTransform: "capitalize" },
  upgradeCard: { backgroundColor: "#eef2ff", borderRadius: 14, padding: 18, marginBottom: 20, borderWidth: 1, borderColor: "#c7d2fe" },
  upgradeTitle: { fontSize: 16, fontWeight: "800", color: "#3730a3", marginBottom: 6 },
  upgradeDesc: { fontSize: 14, color: "#4338ca", lineHeight: 20, marginBottom: 8 },
  upgradeNote: { fontSize: 12, color: "#6366f1", fontStyle: "italic" },
  signOutBtn: { backgroundColor: "#fff", borderRadius: 12, padding: 14, alignItems: "center", borderWidth: 1.5, borderColor: "#fca5a5", marginBottom: 16 },
  signOutText: { color: "#ef4444", fontWeight: "700", fontSize: 15 },
  versionText: { textAlign: "center", color: "#9ca3af", fontSize: 12 },
});
