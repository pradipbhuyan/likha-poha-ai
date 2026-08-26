/**
 * Learn More — Resources screen.
 * Mirrors the web ResourcesPage.jsx.
 * Loads curated learning resources (videos, NCERT links, grammar guides)
 * for a selected grade/subject/chapter via GET /api/resources.
 */
import { useEffect, useState } from "react";
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity,
  ActivityIndicator, Linking, Image,
} from "react-native";
import { Feather } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { authFetch } from "../../lib/authFetch";
import { useUserProfile } from "../../lib/UserProfileContext";
import { BRAND_COLOR } from "../../constants";
import { isGradeLocked } from "@likhapoha/shared/utils/resolveSubscription";

const GRADES = ["Grade 5","Grade 6","Grade 7","Grade 8","Grade 9","Grade 10","Grade 11","Grade 12"];

interface Resource { title: string; url: string; type?: string; }

function getYouTubeId(url: string): string | null {
  const match = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)/);
  return match ? match[1] : null;
}

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
  const router = useRouter();
  const [grade, setGrade]       = useState("Grade 9");
  const [subject, setSubject]   = useState("");
  const [chapter, setChapter]   = useState("");
  const [syllabus, setSyllabus] = useState<any>(null);
  const [resources, setResources] = useState<Resource[]>([]);
  const [loading, setLoading]   = useState(false);
  const [syllabusLoading, setSyllabusLoading] = useState(true);
  // Grade lock — enrolled grade + subscription come from the shared profile
  // context (fetched once at the tabs layout); the syllabus fetch below
  // waits for it to resolve since it needs the enrolled grade.
  const { profile, hasFullAccess } = useUserProfile();
  const studentGrade = profile ? (profile.grade ?? "Grade 9") : null;
  const gradeLocked = isGradeLocked(studentGrade, hasFullAccess);

  useEffect(() => {
    if (!profile) return;
    const enrolledGrade = studentGrade ?? "Grade 9";
    setGrade(enrolledGrade);

    authFetch("/api/syllabus").catch(() => null).then((syllabusRes: any) => {
      if (syllabusRes?.syllabus) {
        setSyllabus(syllabusRes.syllabus);
        const firstSubject = Object.keys(syllabusRes.syllabus?.[enrolledGrade]?.["CBSE"] ?? {})[0] ?? "";
        const firstChapter = syllabusRes.syllabus?.[enrolledGrade]?.["CBSE"]?.[firstSubject]?.[0] ?? "";
        setSubject(firstSubject);
        setChapter(firstChapter);
      }
    }).catch(() => {}).finally(() => setSyllabusLoading(false));
  }, [profile]); // eslint-disable-line react-hooks/exhaustive-deps

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

  const subjectList = Object.keys(syllabus?.[grade]?.["CBSE"] ?? {});
  const chapters = syllabus?.[grade]?.["CBSE"]?.[subject] ?? [];

  function handleGradeChange(g: string) {
    setGrade(g);
    const firstSubject = Object.keys(syllabus?.[g]?.["CBSE"] ?? {})[0] ?? "";
    setSubject(firstSubject);
    setChapter(syllabus?.[g]?.["CBSE"]?.[firstSubject]?.[0] ?? "");
    setResources([]);
  }

  const isEnglish = subject === "English";

  return (
    <ScrollView style={s.container} contentContainerStyle={s.content}>
      <View style={s.pageHeader}>
        <TouchableOpacity style={s.backBtn} onPress={() => router.back()}>
          <Feather name="arrow-left" size={18} color={BRAND_COLOR} />
        </TouchableOpacity>
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
          <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: 14, marginBottom: 8 }}>
            <Text style={s.label}>Grade</Text>
            {gradeLocked && studentGrade && (
              <Text style={{ fontSize: 10, fontWeight: "600", color: "#6366f1" }}>🔒 Locked to {studentGrade}</Text>
            )}
          </View>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.chipRow}>
            {GRADES.map(g => {
              const locked = gradeLocked && g !== studentGrade;
              const isActive = grade === g;
              return (
                <TouchableOpacity
                  key={g}
                  style={[s.chip, isActive && s.chipActive, locked && s.chipLocked]}
                  onPress={() => !locked && handleGradeChange(g)}
                  disabled={locked}
                  activeOpacity={locked ? 1 : 0.7}
                >
                  <Text style={[s.chipText, isActive && s.chipTextActive, locked && s.chipTextLocked]}>
                    {g.replace("Grade ", "")}
                  </Text>
                </TouchableOpacity>
              );
            })}
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
            resources.map((r, i) => {
              const ytId = (r.type === "youtube" || (r.url || "").includes("youtube") || (r.url || "").includes("youtu.be"))
                ? getYouTubeId(r.url) : null;
              return (
                <TouchableOpacity key={i} style={s.resourceCard} onPress={() => Linking.openURL(r.url)}>
                  {ytId ? (
                    <Image
                      source={{ uri: `https://img.youtube.com/vi/${ytId}/mqdefault.jpg` }}
                      style={s.resourceThumb}
                      resizeMode="cover"
                    />
                  ) : (
                    <View style={[s.resourceIconBox, { backgroundColor: "rgba(99,102,241,.08)" }]}>
                      <Feather name={getResourceIcon(r)} size={20} color={BRAND_COLOR} />
                    </View>
                  )}
                  <View style={{ flex: 1 }}>
                    <Text style={s.resourceTitle}>{r.title}</Text>
                    <Text style={s.resourceLabel}>{getResourceLabel(r)}</Text>
                  </View>
                  <Feather name="chevron-right" size={16} color="#9ca3af" />
                </TouchableOpacity>
              );
            })
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
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f8fafc" },
  content: { padding: 16, paddingBottom: 60 },
  pageHeader: { flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 20 },
  backBtn: { padding: 8, borderRadius: 8, backgroundColor: "rgba(99,102,241,.08)" },
  pageIconBox: { width: 44, height: 44, borderRadius: 12, alignItems: "center", justifyContent: "center" },
  pageTitle: { fontSize: 20, fontWeight: "800", color: "#111827" },
  pageSubtitle: { fontSize: 13, color: "#6b7280", lineHeight: 19 },
  label: { fontSize: 11, fontWeight: "700", color: "#6b7280", textTransform: "uppercase", letterSpacing: 0.6, marginBottom: 8, marginTop: 14 },
  chipRow: { flexDirection: "row", marginBottom: 4 },
  chip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 99, borderWidth: 1.5, borderColor: "#d1d5db", backgroundColor: "#fff", marginRight: 8 },
  chipActive: { borderColor: BRAND_COLOR, backgroundColor: BRAND_COLOR },
  chipLocked: { borderColor: "#e5e7eb", backgroundColor: "#f9fafb", opacity: 0.55 },
  chipText: { fontSize: 12, fontWeight: "600", color: "#374151" },
  chipTextActive: { color: "#fff" },
  chipTextLocked: { color: "#9ca3af" },
  center: { alignItems: "center", paddingVertical: 32, gap: 10 },
  loadingText: { color: "#6b7280", fontSize: 13 },
  emptyBox: { alignItems: "center", paddingVertical: 40, gap: 10 },
  emptyTitle: { fontSize: 16, fontWeight: "700", color: "#374151" },
  emptySubtitle: { fontSize: 13, color: "#6b7280", textAlign: "center", lineHeight: 20, paddingHorizontal: 20 },
  resourceCard: { flexDirection: "row", alignItems: "center", gap: 12, backgroundColor: "#fff", borderRadius: 14, padding: 14, marginBottom: 10, borderWidth: 1, borderColor: "#e5e7eb" },
  resourceIconBox: { width: 44, height: 44, borderRadius: 12, alignItems: "center", justifyContent: "center", flexShrink: 0 },
  resourceThumb: { width: 80, height: 52, borderRadius: 8, flexShrink: 0, backgroundColor: "#e5e7eb" },
  resourceTitle: { fontSize: 14, fontWeight: "700", color: "#111827", marginBottom: 3 },
  resourceLabel: { fontSize: 11, fontWeight: "600", color: "#6b7280", textTransform: "uppercase", letterSpacing: 0.4 },
  calloutBox: { flexDirection: "row", alignItems: "center", gap: 12, backgroundColor: "rgba(16,185,129,.06)", borderRadius: 14, padding: 14, marginTop: 10, borderWidth: 1, borderColor: "rgba(16,185,129,.25)" },
  calloutTitle: { fontSize: 13, fontWeight: "700", color: "#065f46", marginBottom: 2 },
  calloutSub: { fontSize: 11, color: "#047857", lineHeight: 17 },
  calloutBtn: { backgroundColor: "#10b981", borderRadius: 8, paddingHorizontal: 14, paddingVertical: 7 },
  calloutBtnText: { color: "#fff", fontSize: 12, fontWeight: "700" },
});
