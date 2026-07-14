/**
 * Signup screen — two-zone layout with dark mode support.
 *   FIXED:    title, subtitle, role buttons, grade chips
 *   SCROLL:   stream picker (Grade 11/12), email, password, button
 */
import { useState } from "react";
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  Alert, ActivityIndicator, KeyboardAvoidingView, Platform, ScrollView,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { StatusBar } from "expo-status-bar";
import { useRouter } from "expo-router";
import { useTheme } from "../../lib/theme";
import { BRAND_COLOR, API_BASE_URL } from "../../constants";
import { supabase } from "../../lib/supabase";

const GRADES = ["5", "6", "7", "8", "9", "10", "11", "12"];
const GRADE_11_12 = new Set(["Grade 11", "Grade 12"]);
const STREAMS = [
  { key: "PCM",        label: "Science — PCM",  desc: "Physics · Chemistry · Maths · English" },
  { key: "PCB",        label: "Science — PCB",  desc: "Physics · Chemistry · Biology · English" },
  { key: "PCMB",       label: "Science — PCMB", desc: "Physics · Chemistry · Maths · Biology · English" },
  { key: "Commerce",   label: "Commerce",       desc: "Accountancy · Business · Economics · English" },
  { key: "Humanities", label: "Humanities",     desc: "History · Polsci · Geography · Economics · English" },
];

export default function SignupScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { colors } = useTheme();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"student" | "parent">("student");
  const [grade, setGrade] = useState("Grade 9");
  const [stream, setStream] = useState("");
  const [loading, setLoading] = useState(false);
  const [scrollY, setScrollY] = useState(0);
  const [contentH, setContentH] = useState(0);
  const [viewH, setViewH] = useState(0);

  const needs1112Stream = role === "student" && GRADE_11_12.has(grade);
  const isScrollable = contentH > viewH && viewH > 0;
  const TRACK_H = viewH - 16;
  const thumbH = isScrollable ? Math.max(36, (viewH / contentH) * TRACK_H) : 0;
  const maxScroll = Math.max(1, contentH - viewH);
  const thumbTop = 8 + Math.min(scrollY / maxScroll, 1) * (TRACK_H - thumbH);

  function handleGradeChange(g: string) { setGrade(g); setStream(""); }

  async function handleSignup() {
    if (!name.trim()) { Alert.alert("Error", "Please enter your name."); return; }
    if (!email.trim() || !password.trim()) { Alert.alert("Error", "Please fill in all fields."); return; }
    if (password.length < 8) { Alert.alert("Error", "Password must be at least 8 characters."); return; }
    if (needs1112Stream && !stream) { Alert.alert("Error", "Please choose your academic stream."); return; }
    setLoading(true);
    try {
      // Call backend signup-free — creates account immediately (no email confirmation),
      // sets up profile with username, and sends welcome email via Resend API
      const res = await fetch(`${API_BASE_URL}/api/auth/signup-free`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          role,
          name: name.trim(),
          email: email.trim().toLowerCase(),
          grade: role === "student" ? grade : undefined,
          stream: needs1112Stream ? stream : undefined,
          password: password.trim(),
        }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(body?.detail ?? body?.message ?? `Signup failed (${res.status})`);
      }

      // Account created — auto-login immediately (no email confirmation needed)
      const { error: loginErr } = await supabase.auth.signInWithPassword({
        email: email.trim().toLowerCase(),
        password: password.trim(),
      });
      if (loginErr) throw loginErr;
      // _layout.tsx onAuthStateChange will route to /(tabs) automatically
    } catch (err: any) { Alert.alert("Sign up failed", err.message ?? "Please try again."); }
    finally { setLoading(false); }
  }

  return (
    <KeyboardAvoidingView style={[s.container, { backgroundColor: colors.bg }]} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <StatusBar style={colors.statusBar} />

      {/* ── FIXED HEADER ── */}
      <View style={[s.header, { paddingTop: insets.top + 12, backgroundColor: colors.bg }]}>
        <Text style={[s.title, { color: colors.text }]}>Create account</Text>
        <Text style={[s.subtitle, { color: colors.textMuted }]}>Join Likha Poha AI</Text>

        <View style={s.roleRow}>
          {(["student", "parent"] as const).map((r) => (
            <TouchableOpacity key={r}
              style={[s.roleBtn, { backgroundColor: colors.surface, borderColor: colors.borderInput },
                role === r && { borderColor: BRAND_COLOR, backgroundColor: colors.brandLight }]}
              onPress={() => setRole(r)}
            >
              <Text style={[s.roleBtnText, { color: colors.textMuted }, role === r && { color: BRAND_COLOR }]}>
                {r === "student" ? "🎓 Student" : "👪 Parent"}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {role === "student" && (
          <>
            <Text style={[s.label, { color: colors.textSubtle }]}>Grade</Text>
            <View style={s.gradeRow}>
              {GRADES.map((g) => {
                const fullGrade = `Grade ${g}`;
                const active = grade === fullGrade;
                return (
                  <TouchableOpacity key={g}
                    style={[s.gradeChip, { borderColor: colors.borderInput, backgroundColor: colors.surface },
                      active && { borderColor: BRAND_COLOR, backgroundColor: BRAND_COLOR }]}
                    onPress={() => handleGradeChange(fullGrade)}
                  >
                    <Text style={[s.gradeChipText, { color: colors.textSubtle }, active && { color: "#fff" }]}>{g}</Text>
                  </TouchableOpacity>
                );
              })}
            </View>
          </>
        )}
      </View>

      {/* ── SCROLLABLE SECTION ── */}
      <View style={s.scrollWrapper}>
        <ScrollView
          contentContainerStyle={s.scrollContent}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
          bounces={false}
          scrollEventThrottle={16}
          onScroll={(e) => setScrollY(e.nativeEvent.contentOffset.y)}
          onContentSizeChange={(_w, h) => setContentH(h)}
          onLayout={(e) => setViewH(e.nativeEvent.layout.height)}
        >
          {needs1112Stream && (
            <>
              <Text style={[s.label, { color: colors.textSubtle }]}>
                Stream <Text style={{ color: "#ef4444" }}>*</Text>
                <Text style={[s.labelSub, { color: colors.textMuted }]}> — Choose your stream for {grade}</Text>
              </Text>
              {STREAMS.map((st) => {
                const active = stream === st.key;
                return (
                  <TouchableOpacity key={st.key}
                    style={[s.streamCard, { borderColor: colors.border, backgroundColor: colors.surface },
                      active && { borderColor: BRAND_COLOR, backgroundColor: colors.brandLight }]}
                    onPress={() => setStream(st.key)}
                  >
                    <View style={s.streamRow}>
                      <View style={[s.radioOuter, { borderColor: colors.borderInput }, active && { borderColor: BRAND_COLOR }]}>
                        {active && <View style={s.radioDot} />}
                      </View>
                      <View style={{ flex: 1 }}>
                        <Text style={[s.streamLabel, { color: colors.textSubtle }, active && { color: BRAND_COLOR }]}>{st.label}</Text>
                        <Text style={[s.streamDesc, { color: colors.textMuted }]}>{st.desc}</Text>
                      </View>
                    </View>
                  </TouchableOpacity>
                );
              })}
              <View style={{ height: 8 }} />
            </>
          )}

          <TextInput
            style={[s.input, { backgroundColor: colors.surface, borderColor: colors.borderInput, color: colors.text }]}
            placeholder="Your name (used as login username)" placeholderTextColor={colors.textMuted}
            value={name} onChangeText={setName} autoCapitalize="words" autoCorrect={false}
          />
          <TextInput
            style={[s.input, { backgroundColor: colors.surface, borderColor: colors.borderInput, color: colors.text }]}
            placeholder="Email address" placeholderTextColor={colors.textMuted}
            value={email} onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none" autoCorrect={false}
          />
          <TextInput
            style={[s.input, { backgroundColor: colors.surface, borderColor: colors.borderInput, color: colors.text }]}
            placeholder="Password (min 8 characters)" placeholderTextColor={colors.textMuted}
            value={password} onChangeText={setPassword} secureTextEntry
          />

          <TouchableOpacity style={s.btn} onPress={handleSignup} disabled={loading}>
            {loading ? <ActivityIndicator color="#fff" /> : <Text style={s.btnText}>Create account</Text>}
          </TouchableOpacity>

          <TouchableOpacity style={s.linkRow} onPress={() => router.replace("/auth/login")}>
            <Text style={[s.link, { color: BRAND_COLOR }]}>Already have an account? Sign in</Text>
          </TouchableOpacity>
        </ScrollView>

        {isScrollable && (
          <View style={s.scrollTrack} pointerEvents="none">
            <View style={[s.scrollThumb, { height: thumbH, top: thumbTop }]} />
          </View>
        )}
      </View>
    </KeyboardAvoidingView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1 },
  header: { paddingHorizontal: 24, paddingBottom: 12 },
  title: { fontSize: 26, fontWeight: "800", marginBottom: 4 },
  subtitle: { fontSize: 13, marginBottom: 20 },
  label: { fontSize: 13, fontWeight: "700", marginBottom: 8 },
  labelSub: { fontSize: 12, fontWeight: "500" },
  roleRow: { flexDirection: "row", gap: 10, marginBottom: 16 },
  roleBtn: { flex: 1, padding: 12, borderRadius: 10, borderWidth: 1.5, alignItems: "center" },
  roleBtnText: { fontWeight: "600" },
  gradeRow: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  gradeChip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 99, borderWidth: 1.5 },
  gradeChipText: { fontWeight: "700" },
  scrollWrapper: { flex: 1, position: "relative" },
  scrollContent: { paddingHorizontal: 24, paddingTop: 16, paddingBottom: 40 },
  scrollTrack: { position: "absolute", right: 3, top: 0, bottom: 0, width: 4, backgroundColor: "rgba(0,0,0,0.07)", borderRadius: 2 },
  scrollThumb: { position: "absolute", right: 0, width: 4, backgroundColor: "rgba(99,102,241,0.55)", borderRadius: 2 },
  streamCard: { borderWidth: 1.5, borderRadius: 12, padding: 12, marginBottom: 8 },
  streamRow: { flexDirection: "row", alignItems: "center", gap: 12 },
  radioOuter: { width: 20, height: 20, borderRadius: 10, borderWidth: 2, alignItems: "center", justifyContent: "center" },
  radioDot: { width: 10, height: 10, borderRadius: 5, backgroundColor: BRAND_COLOR },
  streamLabel: { fontSize: 14, fontWeight: "700" },
  streamDesc: { fontSize: 11, marginTop: 2 },
  input: { borderWidth: 1, borderRadius: 12, padding: 14, marginBottom: 14, fontSize: 16 },
  btn: { backgroundColor: BRAND_COLOR, borderRadius: 12, padding: 14, alignItems: "center", marginBottom: 12 },
  btnText: { color: "#fff", fontWeight: "700", fontSize: 16 },
  linkRow: { marginTop: 16, alignItems: "center" },
  link: { fontWeight: "600", fontSize: 14 },
});
