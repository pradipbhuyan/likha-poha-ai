import { useState } from "react";
import {
  View, Text, TextInput, TouchableOpacity, Image,
  StyleSheet, KeyboardAvoidingView, Platform, ActivityIndicator,
  ScrollView,
} from "react-native";
import { useRouter } from "expo-router";
import { supabase } from "../../lib/supabase";

export default function LoginScreen() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  async function handleLogin() {
    if (!email.trim() || !password) {
      setErrorMsg("Please enter your email and password.");
      return;
    }
    setLoading(true);
    setErrorMsg("");
    try {
      const { error } = await supabase.auth.signInWithPassword({
        email: email.trim().toLowerCase(),
        password,
      });
      if (error) setErrorMsg(error.message);
    } catch (e: any) {
      setErrorMsg(e?.message ?? "Login failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={s.outer}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView contentContainerStyle={s.container} keyboardShouldPersistTaps="handled">
        {/* Logo */}
        <Image
          source={require("../../assets/logo.png")}
          style={s.logo}
          resizeMode="contain"
        />
        <Text style={s.appName}>Likha Poha AI</Text>
        <Text style={s.tagline}>CBSE Smart Tutor for Grades 5–12</Text>

        {/* Form */}
        <View style={s.formBox}>
          <Text style={s.label}>Email</Text>
          <TextInput
            style={s.input}
            placeholder="your@email.com"
            placeholderTextColor="#9ca3af"
            value={email}
            onChangeText={setEmail}
            keyboardType="email-address"
            autoCapitalize="none"
            autoCorrect={false}
          />

          <Text style={s.label}>Password</Text>
          <TextInput
            style={s.input}
            placeholder="Password"
            placeholderTextColor="#9ca3af"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
          />

          {errorMsg ? (
            <View style={s.errorBox}>
              <Text style={s.errorText}>❌ {errorMsg}</Text>
            </View>
          ) : null}

          <TouchableOpacity style={s.btn} onPress={handleLogin} disabled={loading}>
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={s.btnText}>Sign In</Text>
            )}
          </TouchableOpacity>
        </View>

        <TouchableOpacity onPress={() => router.push("/auth/signup")} style={s.linkRow}>
          <Text style={s.linkText}>Don't have an account? </Text>
          <Text style={[s.linkText, s.linkBold]}>Sign up free</Text>
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const BRAND = "#6366f1";

const s = StyleSheet.create({
  outer: { flex: 1, backgroundColor: "#f8fafc" },
  container: { flexGrow: 1, alignItems: "center", justifyContent: "center", padding: 24, paddingTop: 48 },
  logo: { width: 100, height: 100, borderRadius: 22, marginBottom: 16 },
  appName: { fontSize: 28, fontWeight: "800", color: BRAND, letterSpacing: -0.5 },
  tagline: { fontSize: 13, color: "#6b7280", marginTop: 4, marginBottom: 32, textAlign: "center" },
  formBox: { width: "100%", maxWidth: 400 },
  label: { fontSize: 13, fontWeight: "600", color: "#374151", marginBottom: 6 },
  input: {
    borderWidth: 1, borderColor: "#e5e7eb", borderRadius: 12,
    padding: 14, marginBottom: 16, fontSize: 16,
    backgroundColor: "#fff", color: "#111827",
  },
  errorBox: {
    backgroundColor: "#fef2f2", borderRadius: 10,
    padding: 12, marginBottom: 14,
  },
  errorText: { color: "#dc2626", fontSize: 14 },
  btn: {
    backgroundColor: BRAND, borderRadius: 12,
    padding: 16, alignItems: "center", marginTop: 4,
  },
  btnText: { color: "#fff", fontSize: 16, fontWeight: "700" },
  linkRow: { flexDirection: "row", marginTop: 24 },
  linkText: { color: "#6b7280", fontSize: 14 },
  linkBold: { color: BRAND, fontWeight: "700" },
});
