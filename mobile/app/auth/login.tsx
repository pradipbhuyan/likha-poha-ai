/**
 * Login screen — email/password + Google OAuth.
 *
 * After sign-in calls GET /api/auth/me (same backend state machine as web)
 * to determine if role selection is needed or user can go straight to dashboard.
 */
import { useState } from "react";
import {
  View, Text, TextInput, TouchableOpacity,
  StyleSheet, Alert, ActivityIndicator, KeyboardAvoidingView, Platform, ScrollView,
} from "react-native";
import { useRouter } from "expo-router";
import { signInWithEmail, signInWithGoogle, checkAuthState } from "../../lib/auth";
import { supabase } from "../../lib/supabase";
import { BRAND_COLOR } from "../../constants";

export default function LoginScreen() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleEmailLogin() {
    if (!email.trim() || !password.trim()) {
      Alert.alert("Error", "Please enter your email and password.");
      return;
    }
    setLoading(true);
    try {
      const { error, data } = await signInWithEmail(email.trim(), password);
      if (error) throw error;
      const token = data?.session?.access_token;
      if (token) {
        const me = await checkAuthState(token);
        if (me.needs_role_selection) {
          router.replace("/auth/role-select");
        } else {
          router.replace("/(tabs)");
        }
      }
    } catch (err: any) {
      Alert.alert("Sign in failed", err.message ?? "Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleGoogleLogin() {
    setLoading(true);
    try {
      await signInWithGoogle();
      // Auth state change listener in _layout.tsx handles redirect
    } catch (err: any) {
      Alert.alert("Google sign in failed", err.message ?? "Please try again.");
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
        {/* Logo / brand */}
        <Text style={styles.logo}>📚</Text>
        <Text style={styles.title}>Likha Poha AI</Text>
        <Text style={styles.subtitle}>CBSE learning powered by AI</Text>

        {/* Email/password */}
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
          placeholder="Password"
          placeholderTextColor="#9ca3af"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
        />

        <TouchableOpacity
          style={[styles.btn, styles.btnPrimary]}
          onPress={handleEmailLogin}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.btnText}>Sign in</Text>
          )}
        </TouchableOpacity>

        <View style={styles.divider}>
          <View style={styles.dividerLine} />
          <Text style={styles.dividerText}>or</Text>
          <View style={styles.dividerLine} />
        </View>

        <TouchableOpacity
          style={[styles.btn, styles.btnGoogle]}
          onPress={handleGoogleLogin}
          disabled={loading}
        >
          <Text style={[styles.btnText, { color: "#374151" }]}>
            🔑  Continue with Google
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.linkRow}
          onPress={() => router.push("/auth/signup")}
        >
          <Text style={styles.link}>Don't have an account? Sign up</Text>
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f8fafc" },
  inner: { flexGrow: 1, justifyContent: "center", padding: 28 },
  logo: { fontSize: 52, textAlign: "center", marginBottom: 8 },
  title: { fontSize: 26, fontWeight: "800", textAlign: "center", color: "#111827" },
  subtitle: { fontSize: 14, textAlign: "center", color: "#6b7280", marginBottom: 36 },
  input: {
    borderWidth: 1, borderColor: "#d1d5db", borderRadius: 12,
    padding: 14, marginBottom: 14, fontSize: 16, backgroundColor: "#fff", color: "#111827",
  },
  btn: {
    borderRadius: 12, padding: 14, alignItems: "center", marginBottom: 12,
  },
  btnPrimary: { backgroundColor: BRAND_COLOR },
  btnGoogle: { backgroundColor: "#fff", borderWidth: 1, borderColor: "#d1d5db" },
  btnText: { color: "#fff", fontWeight: "700", fontSize: 16 },
  divider: { flexDirection: "row", alignItems: "center", marginVertical: 8 },
  dividerLine: { flex: 1, height: 1, backgroundColor: "#e5e7eb" },
  dividerText: { marginHorizontal: 12, color: "#9ca3af", fontSize: 13 },
  linkRow: { marginTop: 20, alignItems: "center" },
  link: { color: BRAND_COLOR, fontWeight: "600", fontSize: 14 },
});
