/**
 * Signup screen — student or parent, email/password.
 * Grade 5–10 selector required for students.
 */
import { useState } from "react";
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  Alert, ActivityIndicator, KeyboardAvoidingView, Platform, ScrollView,
} from "react-native";
import { useRouter } from "expo-router";
import { signUpWithEmail } from "../../lib/auth";
import { BRAND_COLOR } from "../../constants";

const GRADES = ["Grade 5", "Grade 6", "Grade 7", "Grade 8", "Grade 9", "Grade 10"];

export default function SignupScreen() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"student" | "parent">("student");
  const [grade, setGrade] = useState("Grade 9");
  const [loading, setLoading] = useState(false);

  async function handleSignup() {
    if (!email.trim() || !password.trim()) {
      Alert.alert("Error", "Please fill in all fields.");
      return;
    }
    if (password.length < 8) {
      Alert.alert("Error", "Password must be at least 8 characters.");
      return;
    }
    setLoading(true);
    try {
      const { error } = await signUpWithEmail(
        email.trim(), password, role, role === "student" ? grade : undefined
      );
      if (error) throw error;
      Alert.alert(
        "Check your email",
        "We've sent a confirmation link. Please verify your email to continue.",
        [{ text: "OK", onPress: () => router.replace("/auth/login") }]
      );
    } catch (err: any) {
      Alert.alert("Sign up failed", err.message ?? "Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView contentContainerStyle={styles.inner} keyboardShouldPersistTaps="handled">
        <Text style={styles.title}>Create account</Text>
        <Text style={styles.subtitle}>Join Likha Poha AI</Text>

        {/* Role selector */}
        <View style={styles.roleRow}>
          {(["student", "parent"] as const).map((r) => (
            <TouchableOpacity
              key={r}
              style={[styles.roleBtn, role === r && styles.roleBtnActive]}
              onPress={() => setRole(r)}
            >
              <Text style={[styles.roleBtnText, role === r && styles.roleBtnTextActive]}>
                {r === "student" ? "🎓 Student" : "👪 Parent"}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Grade selector — students only */}
        {role === "student" && (
          <>
            <Text style={styles.label}>Grade</Text>
            <View style={styles.gradeRow}>
              {GRADES.map((g) => (
                <TouchableOpacity
                  key={g}
                  style={[styles.gradeChip, grade === g && styles.gradeChipActive]}
                  onPress={() => setGrade(g)}
                >
                  <Text style={[styles.gradeChipText, grade === g && styles.gradeChipTextActive]}>
                    {g.replace("Grade ", "")}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </>
        )}

        <TextInput
          style={styles.input}
          placeholder="Email address"
          placeholderTextColor="#9ca3af"
          value={email}
          onChangeText={setEmail}
          keyboardType="email-address"
          autoCapitalize="none"
          autoCorrect={false}
        />
        <TextInput
          style={styles.input}
          placeholder="Password (min 8 characters)"
          placeholderTextColor="#9ca3af"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
        />

        <TouchableOpacity
          style={[styles.btn, styles.btnPrimary]}
          onPress={handleSignup}
          disabled={loading}
        >
          {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.btnText}>Create account</Text>}
        </TouchableOpacity>

        <TouchableOpacity style={styles.linkRow} onPress={() => router.replace("/auth/login")}>
          <Text style={styles.link}>Already have an account? Sign in</Text>
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f8fafc" },
  inner: { flexGrow: 1, padding: 28, paddingTop: 60 },
  title: { fontSize: 26, fontWeight: "800", color: "#111827", marginBottom: 4 },
  subtitle: { fontSize: 14, color: "#6b7280", marginBottom: 28 },
  label: { fontSize: 13, fontWeight: "700", color: "#374151", marginBottom: 8 },
  roleRow: { flexDirection: "row", gap: 10, marginBottom: 20 },
  roleBtn: { flex: 1, padding: 12, borderRadius: 10, borderWidth: 1.5, borderColor: "#d1d5db", backgroundColor: "#fff", alignItems: "center" },
  roleBtnActive: { borderColor: BRAND_COLOR, backgroundColor: "#eef2ff" },
  roleBtnText: { fontWeight: "600", color: "#6b7280" },
  roleBtnTextActive: { color: BRAND_COLOR },
  gradeRow: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 20 },
  gradeChip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 99, borderWidth: 1.5, borderColor: "#d1d5db", backgroundColor: "#fff" },
  gradeChipActive: { borderColor: BRAND_COLOR, backgroundColor: BRAND_COLOR },
  gradeChipText: { fontWeight: "700", color: "#374151" },
  gradeChipTextActive: { color: "#fff" },
  input: { borderWidth: 1, borderColor: "#d1d5db", borderRadius: 12, padding: 14, marginBottom: 14, fontSize: 16, backgroundColor: "#fff", color: "#111827" },
  btn: { borderRadius: 12, padding: 14, alignItems: "center", marginBottom: 12 },
  btnPrimary: { backgroundColor: BRAND_COLOR },
  btnText: { color: "#fff", fontWeight: "700", fontSize: 16 },
  linkRow: { marginTop: 16, alignItems: "center" },
  link: { color: BRAND_COLOR, fontWeight: "600", fontSize: 14 },
});
