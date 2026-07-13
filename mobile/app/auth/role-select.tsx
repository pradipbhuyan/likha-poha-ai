/**
 * Role Selection Screen — shown once for new Google OAuth users.
 * Supports light and dark mode via useTheme().
 */
import { useState } from "react";
import {
  View, Text, TouchableOpacity, StyleSheet,
  ActivityIndicator, ScrollView, Image,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { StatusBar } from "expo-status-bar";
import { useRouter } from "expo-router";
import { supabase } from "../../lib/supabase";
import { completeOAuthProfile } from "../../lib/auth";
import { useTheme } from "../../lib/theme";
import { BRAND_COLOR } from "../../constants";

const GRADES = ["5", "6", "7", "8", "9", "10", "11", "12"];
const GRADE_11_12 = new Set(["Grade 11", "Grade 12"]);
const STREAMS = [
  { key: "PCM",        label: "Science — PCM",  desc: "Physics · Chemistry · Maths · English" },
  { key: "PCB",        label: "Science — PCB",  desc: "Physics · Chemistry · Biology · English" },
  { key: "PCMB",       label: "Science — PCMB", desc: "Physics · Chemistry · Maths · Biology · English" },
  { key: "Commerce",   label: "Commerce",       desc: "Accountancy · Business · Economics · English" },
  { key: "Humanities", label: "Humanities",     desc: "History · Polsci · Geography · Economics · English" },
];

export default function RoleSelectScreen() {
  const router = useRouter();
  const { colors } = useTheme();
  const [role, setRole] = useState<"student" | "parent">("student");
  const [grade, setGrade] = useState("Grade 9");
  const [stream, setStream] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const needs1112Stream = role === "student" && GRADE_11_12.has(grade);

  function handleGradeChange(g: string) { setGrade(g); setStream(""); }

  async function handleConfirm() {
    if (needs1112Stream && !stream) { setErrorMsg("Please choose your academic stream."); return; }
    setLoading(true); setErrorMsg("");
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) throw new Error("Session expired. Please sign in again.");
      await completeOAuthProfile(session.access_token, role,
        role === "student" ? grade : undefined, needs1112Stream ? stream : undefined);
      await supabase.auth.refreshSession();
    } catch (e: any) {
      const msg: string = e?.message ?? "Something went wrong.";
      if (msg.includes("409") || msg.toLowerCase().includes("conflict")) {
        setErrorMsg("This Google account already has a different role. Please use a different account.");
      } else if (msg.includes("401") || msg.toLowerCase().includes("session expired")) {
        setErrorMsg("Session expired. Please go back and sign in again.");
      } else { setErrorMsg(msg); }
    } finally { setLoading(false); }
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={["top", "bottom"]}>
      <StatusBar style={colors.statusBar} />
      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={[s.container, { backgroundColor: colors.bg }]}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={true}
      >
        <Image source={require("../../assets/logo.png")} style={s.logo} resizeMode="contain" />
        <Text style={[s.title, { color: colors.text }]}>Almost there!</Text>
        <Text style={[s.subtitle, { color: colors.textMuted }]}>Tell us who you are so we can personalise your experience.</Text>

        <Text style={[s.label, { color: colors.textSubtle }]}>I am a…</Text>
        <View style={s.roleRow}>
          {([{ key: "student", emoji: "🎓", label: "Student" }, { key: "parent", emoji: "👪", label: "Parent" }] as const).map(({ key, emoji, label }) => (
            <TouchableOpacity key={key}
              style={[s.roleBtn, { backgroundColor: colors.surface, borderColor: colors.borderInput },
                role === key && { borderColor: BRAND_COLOR, backgroundColor: colors.brandLight }]}
              onPress={() => { setRole(key); setStream(""); }}
            >
              <Text style={s.roleEmoji}>{emoji}</Text>
              <Text style={[s.roleTxt, { color: colors.textMuted }, role === key && { color: BRAND_COLOR }]}>{label}</Text>
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
                    <Text style={[s.gradeChipTxt, { color: colors.textSubtle }, active && { color: "#fff" }]}>{g}</Text>
                  </TouchableOpacity>
                );
              })}
            </View>
          </>
        )}

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

        {errorMsg ? (
          <View style={[s.errorBox, { backgroundColor: colors.errorBg }]}>
            <Text style={[s.errorTxt, { color: colors.errorText }]}>❌ {errorMsg}</Text>
          </View>
        ) : null}

        <TouchableOpacity style={s.btn} onPress={handleConfirm} disabled={loading}>
          {loading ? <ActivityIndicator color="#fff" /> : <Text style={s.btnTxt}>Continue →</Text>}
        </TouchableOpacity>

        <TouchableOpacity style={s.back} onPress={() => router.replace("/auth/login")}>
          <Text style={[s.backTxt, { color: colors.textMuted }]}>← Use a different account</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container: { flexGrow: 1, alignItems: "center", padding: 24, paddingTop: 40, paddingBottom: 40 },
  logo: { width: 80, height: 80, borderRadius: 18, marginBottom: 20 },
  title: { fontSize: 26, fontWeight: "800", marginBottom: 6, textAlign: "center" },
  subtitle: { fontSize: 14, textAlign: "center", lineHeight: 22, marginBottom: 32, maxWidth: 320 },
  label: { alignSelf: "flex-start", fontSize: 13, fontWeight: "700", marginBottom: 10, width: "100%" },
  labelSub: { fontSize: 12, fontWeight: "500" },
  roleRow: { flexDirection: "row", gap: 12, marginBottom: 24, width: "100%" },
  roleBtn: { flex: 1, padding: 16, borderRadius: 14, borderWidth: 1.5, alignItems: "center", gap: 6 },
  roleEmoji: { fontSize: 28 },
  roleTxt: { fontSize: 15, fontWeight: "700" },
  gradeRow: { flexDirection: "row", flexWrap: "wrap", gap: 10, marginBottom: 24, width: "100%" },
  gradeChip: { width: 52, height: 52, borderRadius: 26, borderWidth: 1.5, alignItems: "center", justifyContent: "center" },
  gradeChipTxt: { fontSize: 15, fontWeight: "700" },
  streamCard: { width: "100%", borderWidth: 1.5, borderRadius: 12, padding: 12, marginBottom: 8 },
  streamRow: { flexDirection: "row", alignItems: "center", gap: 12 },
  radioOuter: { width: 20, height: 20, borderRadius: 10, borderWidth: 2, alignItems: "center", justifyContent: "center" },
  radioDot: { width: 10, height: 10, borderRadius: 5, backgroundColor: BRAND_COLOR },
  streamLabel: { fontSize: 14, fontWeight: "700" },
  streamDesc: { fontSize: 11, marginTop: 2 },
  errorBox: { borderRadius: 10, padding: 12, marginBottom: 16, width: "100%" },
  errorTxt: { fontSize: 13, lineHeight: 20 },
  btn: { backgroundColor: BRAND_COLOR, borderRadius: 14, paddingVertical: 16, paddingHorizontal: 32, alignItems: "center", width: "100%", marginBottom: 16 },
  btnTxt: { color: "#fff", fontSize: 16, fontWeight: "700" },
  back: { marginTop: 8 },
  backTxt: { fontSize: 13, fontWeight: "600" },
});
