/**
 * Learn More — Resources screen.
 * Mirrors the web ResourcesPage.jsx.
 * Loads curated learning resources (videos, NCERT links, grammar guides)
 * for a selected grade/subject/chapter via GET /api/resources.
 */
import { useEffect, useState } from "react";
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity,
  ActivityIndicator, Linking,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import { Stack } from "expo-router";
import AppHeader from "../components/AppHeader";
import { authFetch } from "../lib/authFetch";
import { BRAND_COLOR } from "../constants";

const GRADES = ["Grade 5","Grade 6","Grade 7","Grade 8","Grade 9","Grade 10","Grade 11","Grade 12"];

interface Resource { title: string; url: string; type?: string; }

function getResourceIcon(r: Resource): React.ComponentProps<typeof Feather>["name"] {
  const t = (r.title || "").toLowerCase();
  const u = (r.url || "").toLowerCase();
  if (r.type === "youtube" || u.includes("youtube")) return "youtube";
  if (t.includes("exemplar")) return "activity";
  if (t.includes("grammar") || t.includes("bbc") || t.includes("british")) return "edit";
  if (t.includes("phet") || t.includes("simulation")) return "zap";
  if (t.includes("ncert")) return "book";
  if (t.includes("cbse") || t.includes("sample")) return "file-text";
  return "link";
}

function getResourceLabel(r: Resource): string {
  const t = (r.title || "").toLowerCase();
  if (r.type === "youtube" || (r.url || "").includes("youtube")) return "Video";
  if (t.includes("exemplar")) return "Practice Problems";
  if (t.includes("bbc") || t.includes("british")) return "Grammar Guide";
  if (t.includes("phet")) return "Interactive Sim";
  if (t.includes("ncert")) return "NCERT Textbook";
  if (t.includes("cbse") || t.includes("sample")) return "CBSE Resource";
  return "Reference";
}

export default function LearnScreen() {
  const [grade, setGrade]       = useState("Grade 9");
  const [subject, setSubject]   = useState("");
  const [chapter, setChapter]   = useState("");
  const [syllabus, setSyllabus] = useState<any>(null);
  const [resources, setResources] = useState<Resource[]>([]);
  const [loading, setLoading]   = useState(false);
  const [syllabusLoading, setSyllabusLoading] = useState(true);

  // Load syllabus
  useEffect(() => {
    authFetch("/api/syllabus")
      .then((r: any) => {
        setSyllabus(r.syllabus);
        const firstSubject = Object.keys(r.syllabus?.["Grade 9"]?.["CBSE"] ?? {})[0] ?? "";
        const firstChapter = r.syllabus?.["Grade 9"]?.["CBSE"]?.[firstSubject]?.[0] ?? "";
        setSubject(firstSubject);
        setChapter(firstChapter);
      })
      .catch(() => {})
      .finally(() => setSyllabusLoading(false));
  }, []);

  // Load resources when grade/subject/chapter change
  useEffect(() => {
    if (!subject || !chapter) return;
    setLoading(true);
    const params = new URLSearchParams({ subject, chapter, grade });
    authFetch(`/api/resources?${params}`)
      .then((r: any) => setResources(r.resources || []))
      .catch(() => setResources([]))
      .finally(() => setLoading(false));
  }, [grade, subject, chapter]);

  const subjects = Object.keys(syllabus?.[grade]?.["CBSE"] ?? {}).filter(g => {
    const num = parseInt(g.replace("Grade ", ""), 10);
    return !isNaN(num) && num >= 5;
  });
  const subjectList = Object.keys(syllabus?.[grade]?.["CBSE"] ?? {});
  const chapters = syllabus?.[grade]?.["CBSE"]?.[subject] ?? [];

  function handleGradeChange(g: string) {
    setGrade(g);
    const firstSubject = Object.keys(syllabus?.[g]?.["CBSE"] ?? {})[0] ?? "";
    setSubject(firstSubject);
    setChapter(syllabus?.[g]?.["CBSE"]?.[firstSubject]?.[0] ?? "");
    setResources([]);
  }

  const isExemplarSubject = (subject === "Maths" || subject === "Science") &&
    ["Grade 8","Grade 9","Grade 10"].includes(grade);
  const isEnglish = subject === "English";

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: "#f8fafc" }}>
      <Stack.Screen options={{ headerShown: false }} />
      <AppHeader showBack />
      <ScrollView style={s.container} contentContainerStyle={s.content}>
      <View style={s.pageHeader}>
        <View style={[s.pageIconBox, { backgroundColor: "rgba(99,102,241,.08)" }]}>
          <Feather name="external-link" size={20} color={BRAND_COLOR} />
        </View>
        <View>
          <Text style={s.pageTitle}>Learn More</Text>
          <Text style={s.pageSubtitle}>Videos, NCERT links & chapter references</Text>
        </View>
      </View>

      {syllabusLoading ? (
        <View style={s.center}><ActivityIndicator color={BRAND_COLOR} size="large" /></View>
      ) : (
        <>
          {/* Grade selector */}
          <Text style={s.label}>Grade</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.chipRow}>
            {GRADES.map(g => (
              <TouchableOpacity key={g} style={[s.chip, grade === g && s.chipActive]} onPress={() => handleGradeChange(g)}>
                <Text style={[s.chipText, grade === g && s.chipTextActive]}>{g.replace("Grade ", "")}</Text>
              </TouchableOpacity>
            ))}
          </ScrollView>

          {/* Subject selector */}
          <Text style={s.label}>Subject</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.chipRow}>
            {subjectList.map(sub => (
              <TouchableOpacity key={sub} style={[s.chip, subject === sub && s.chipActive]}
                onPress={() => { setSubject(sub); setChapter(syllabus?.[grade]?.["CBSE"]?.[sub]?.[0] ?? ""); setResources([]); }}>
                <Text style={[s.chipText, subject === sub && s.chipTextActive]}>{sub}</Text>
              </TouchableOpacity>
            ))}
          </ScrollView>

          {/* Chapter selector */}
          <Text style={s.label}>Chapter</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.chipRow}>
            {chapters.map((c: string) => (
              <TouchableOpacity key={c} style={[s.chip, chapter === c && s.chipActive]}
                onPress={() => { setChapter(c); setResources([]); }}>
                <Text style={[s.chipText, chapter === c && s.chipTextActive]} numberOfLines={1}>
                  {c.length > 28 ? c.slice(0, 26) + "…" : c}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>

          {/* Resources */}
          {loading ? (
            <View style={s.center}><ActivityIndicator color={BRAND_COLOR} /><Text style={s.loadingText}>Loading resources…</Text></View>
          ) : resources.length === 0 && subject && chapter ? (
            <View style={s.emptyBox}>
              <Feather name="search" size={36} color="#9ca3af" />
              <Text style={s.emptyTitle}>No resources found</Text>
              <Text style={s.emptySubtitle}>Try another chapter. You can use Lessons or Ask Doubt for AI-guided help.</Text>
            </View>
          ) : (
            resources.map((r, i) => (
              <TouchableOpacity key={i} style={s.resourceCard} onPress={() => Linking.openURL(r.url)}>
                <View style={[s.resourceIconBox, { backgroundColor: "rgba(99,102,241,.08)" }]}>
                  <Feather name={getResourceIcon(r)} size={20} color={BRAND_COLOR} />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={s.resourceTitle}>{r.title}</Text>
                  <Text style={s.resourceLabel}>{getResourceLabel(r)}</Text>
                </View>
                <Feather name="chevron-right" size={16} color="#9ca3af" />
              </TouchableOpacity>
            ))
          )}

          {/* Exemplar callout */}
          {isExemplarSubject && !loading && (
            <View style={s.calloutBox}>
              <Feather name="activity" size={20} color="#10b981" />
              <View style={{ flex: 1 }}>
                <Text style={s.calloutTitle}>NCERT Exemplar — {grade} {subject}</Text>
                <Text style={s.calloutSub}>Official higher-order thinking practice problems. Free from NCERT.</Text>
              </View>
              <TouchableOpacity style={s.calloutBtn} onPress={() => Linking.openURL("https://ncert.nic.in/exemplar-problems.php")}>
                <Text style={s.calloutBtnText}>Open</Text>
              </TouchableOpacity>
            </View>
          )}

          {/* Grammar callout for English */}
          {isEnglish && !loading && (
            <>
              {[
                { title: "BBC Learning English — Grammar", url: "https://www.bbc.co.uk/learningenglish/grammar", desc: "Tenses, Voice, Reported Speech, Clauses, Modals" },
                { title: "British Council — LearnEnglish Grammar", url: "https://learnenglish.britishcouncil.org/grammar", desc: "A1 to C1 grammar lessons with exercises" },
                { title: "CBSE Sample Papers — English", url: "https://cbseacademic.nic.in/SampleQuestion_Papers.html", desc: "Official CBSE sample papers for board exam prep" },
              ].map((item, i) => (
                <TouchableOpacity key={i} style={s.resourceCard} onPress={() => Linking.openURL(item.url)}>
                  <View style={[s.resourceIconBox, { backgroundColor: "rgba(16,185,129,.08)" }]}>
                    <Feather name="edit" size={20} color="#10b981" />
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text style={s.resourceTitle}>{item.title}</Text>
                    <Text style={s.resourceLabel}>{item.desc}</Text>
                  </View>
                  <Feather name="chevron-right" size={16} color="#9ca3af" />
                </TouchableOpacity>
              ))}
            </>
          )}
        </>
      )}
    </ScrollView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f8fafc" },
  content: { padding: 16, paddingBottom: 60 },
  pageHeader: { flexDirection: "row", alignItems: "center", gap: 12, marginBottom: 20 },
  pageIconBox: { width: 44, height: 44, borderRadius: 12, alignItems: "center", justifyContent: "center" },
  pageTitle: { fontSize: 20, fontWeight: "800", color: "#111827" },
  pageSubtitle: { fontSize: 13, color: "#6b7280", lineHeight: 19 },
  label: { fontSize: 11, fontWeight: "700", color: "#6b7280", textTransform: "uppercase", letterSpacing: 0.6, marginBottom: 8, marginTop: 14 },
  chipRow: { flexDirection: "row", marginBottom: 4 },
  chip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 99, borderWidth: 1.5, borderColor: "#d1d5db", backgroundColor: "#fff", marginRight: 8 },
  chipActive: { borderColor: BRAND_COLOR, backgroundColor: BRAND_COLOR },
  chipText: { fontSize: 12, fontWeight: "600", color: "#374151" },
  chipTextActive: { color: "#fff" },
  center: { alignItems: "center", paddingVertical: 32, gap: 10 },
  loadingText: { color: "#6b7280", fontSize: 13 },
  emptyBox: { alignItems: "center", paddingVertical: 40, gap: 10 },
  emptyTitle: { fontSize: 16, fontWeight: "700", color: "#374151" },
  emptySubtitle: { fontSize: 13, color: "#6b7280", textAlign: "center", lineHeight: 20, paddingHorizontal: 20 },
  resourceCard: { flexDirection: "row", alignItems: "center", gap: 12, backgroundColor: "#fff", borderRadius: 14, padding: 14, marginBottom: 10, borderWidth: 1, borderColor: "#e5e7eb" },
  resourceIconBox: { width: 44, height: 44, borderRadius: 12, alignItems: "center", justifyContent: "center", flexShrink: 0 },
  resourceTitle: { fontSize: 14, fontWeight: "700", color: "#111827", marginBottom: 3 },
  resourceLabel: { fontSize: 11, fontWeight: "600", color: "#6b7280", textTransform: "uppercase", letterSpacing: 0.4 },
  calloutBox: { flexDirection: "row", alignItems: "center", gap: 12, backgroundColor: "rgba(16,185,129,.06)", borderRadius: 14, padding: 14, marginTop: 10, borderWidth: 1, borderColor: "rgba(16,185,129,.25)" },
  calloutTitle: { fontSize: 13, fontWeight: "700", color: "#065f46", marginBottom: 2 },
  calloutSub: { fontSize: 11, color: "#047857", lineHeight: 17 },
  calloutBtn: { backgroundColor: "#10b981", borderRadius: 8, paddingHorizontal: 14, paddingVertical: 7 },
  calloutBtnText: { color: "#fff", fontSize: 12, fontWeight: "700" },
});
