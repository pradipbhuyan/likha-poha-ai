import { useState } from "react";
import {
  View, Text, TextInput, TouchableOpacity,
  StyleSheet, KeyboardAvoidingView, Platform, Alert, ActivityIndicator,
} from "react-native";
import { useRouter } from "expo-router";
import { supabase } from "../../lib/supabase";
import { API_BASE_URL } from "../../constants";

export default function LoginScreen() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleLogin() {
    if (!email || !password) {
      Alert.alert("Error", "Please enter email and password");
      return;
    }
    setLoading(true);
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    setLoading(false);
    if (error) Alert.alert("Login failed", error.message);
  }

  return (
    <KeyboardAvoidingView
      style={s.container}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <View style={s.inner}>
        <Text style={s.logo}>📚</Text>
        <Text style={s.title}>Likha Poha AI</Text>
        <Text style={s.sub}>CBSE Tutor · Login</Text>

        <TextInput
          style={s.input}
          placeholder="Email"
          placeholderTextColor="#9ca3af"
          value={email}
          onChangeText={setEmail}
          keyboardType="email-address"
          autoCapitalize="none"
        />
        <TextInput
          style={s.input}
          placeholder="Password"
          placeholderTextColor="#9ca3af"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
        />

        <TouchableOpacity style={s.btn} onPress={handleLogin} disabled={loading}>
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={s.btnText}>Sign In</Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity onPress={() => router.push("/auth/signup")}>
          <Text style={s.link}>Don't have an account? Sign up</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f8fafc" },
  inner: { flex: 1, justifyContent: "center", padding: 28 },
  logo: { fontSize: 64, textAlign: "center", marginBottom: 12 },
  title: { fontSize: 30, fontWeight: "800", color: "#6366f1", textAlign: "center", marginBottom: 4 },
  sub: { fontSize: 14, color: "#6b7280", textAlign: "center", marginBottom: 32 },
  input: {
    borderWidth: 1, borderColor: "#e5e7eb", borderRadius: 12,
    padding: 14, marginBottom: 14, fontSize: 16,
    backgroundColor: "#fff", color: "#111827",
  },
  btn: {
    backgroundColor: "#6366f1", borderRadius: 12,
    padding: 16, alignItems: "center", marginTop: 4, marginBottom: 16,
  },
  btnText: { color: "#fff", fontSize: 16, fontWeight: "700" },
  link: { color: "#6366f1", textAlign: "center", fontSize: 14, marginTop: 4 },
});
