import { useEffect, useState } from "react";
import { View, Text, ScrollView, StyleSheet, TouchableOpacity, ActivityIndicator, Modal } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import { authFetch } from "../../lib/authFetch";
import { BRAND_COLOR } from "../../constants";

type YearItem    = { year: string; locked: boolean };
type SubjectItem = { subject: string; locked: boolean };
type PaperItem   = { id: string; subject: string; academic_year: string; status: string; question_count: number; question_paper_url?: string };
type Question    = { id: string; question_number: number; question_text: string; question_type: string; section: string; marks: number; options: string[] | null; diagram_dependent: boolean; answer_text?: string; answer_explanation?: string };

const C = BRAND_COLOR;

function QCard({ q }: { q: Question }) {
  const [open, setOpen] = useState(false);
  const [show, setShow] = useState(false);
  const ok = !!(q.answer_text && !q.answer_text.startsWith("NEEDS_MANUAL"));
  const badge = q.question_type === "assertion_reason" ? "A&R" : (q.question_type ?? "").replace(/_/g, " ").toUpperCase();
  return (
    <View style={ss.qCard}>
      <TouchableOpacity onPress={() => setOpen(v => !v)} activeOpacity={0.8}>
        <View style={ss.qHdr}>
          <View style={ss.qNum}><Text style={ss.qNumT}>Q{q.question_number}</Text></View>
          <View style={{ flex: 1 }}>
            <View style={ss.qMeta}>
              <Text style={ss.qBadge}>{badge}</Text>
              <Text style={ss.qM}>{q.marks}m</Text>
              {!!q.section && <Text style={ss.qSec}>§{q.section}</Text>}
              {q.diagram_dependent && <Feather name="image" size={11} color="#f59e0b" />}
            </View>
            <Text style={ss.qT} numberOfLines={open ? 12 : 3}>{q.question_text}</Text>
          </View>
          <Feather name={open ? "chevron-up" : "chevron-down"} size={16} color="#9ca3af" />
        </View>
      </TouchableOpacity>
      {open && (
        <View style={ss.qBody}>
          {(q.options ?? []).length > 0 && (q.options ?? []).map((o, i) => (
            <View key={i} style={ss.optRow}>
              <View style={ss.optK}><Text style={ss.optKT}>{["A","B","C","D"][i]}</Text></View>
              <Text style={ss.optT}>{o}</Text>
            </View>
          ))}
          {ok ? (
            !show ? (
              <TouchableOpacity style={ss.reveal} onPress={() => setShow(true)}>
                <Feather name="eye" size={14} color={C} /><Text style={ss.revealT}>Show Official Answer</Text>
              </TouchableOpacity>
            ) : (
              <View style={ss.ansBox}>
                <Text style={ss.ansLbl}>✅ Official Answer</Text>
                <Text style={ss.ansT}>{q.answer_text}</Text>
                {q.answer_explanation && q.answer_explanation !== q.answer_text && <Text style={ss.expT}>{q.answer_explanation}</Text>}
                <TouchableOpacity onPress={() => setShow(false)}><Text style={{ fontSize: 11, color: "#9ca3af", marginTop: 8 }}>Hide</Text></TouchableOpacity>
              </View>
            )
          ) : (
            <View style={ss.pendBox}>
              <Feather name="clock" size={13} color="#f59e0b" />
              <Text style={ss.pendT}>{q.diagram_dependent ? "Answer requires diagram" : "Verification pending"}</Text>
            </View>
          )}
        </View>
      )}
    </View>
  );
}

function PModal({ paper, grade, onClose }: { paper: PaperItem; grade: string; onClose: () => void }) {
  return (
    <Modal visible animationType="slide" presentationStyle="pageSheet">
      <ModalContent paper={paper} grade={grade} onClose={onClose} />
    </Modal>
  );
}

// Inner component so useSafeAreaInsets works inside Modal
function ModalContent({ paper, grade, onClose }: { paper: PaperItem; grade: string; onClose: () => void }) {
  const insets = useSafeAreaInsets();
  const [qs, setQs] = useState<Question[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  useEffect(() => {
    authFetch(`/api/board-papers/${paper.id}/questions?grade=${encodeURIComponent(grade)}`)
      .then((d: any) => setQs(d.questions ?? []))
      .catch((e: any) => setErr(e.message ?? "Error"))
      .finally(() => setLoading(false));
  }, []); // eslint-disable-line
  const ans = qs.filter(q => q.answer_text && !q.answer_text.startsWith("NEEDS_MANUAL")).length;
  return (
      <View style={[ss.modal, { paddingTop: insets.top }]}>
        <View style={ss.mHdr}>
          <TouchableOpacity onPress={onClose} style={ss.mBackBtn}>
            <Feather name="arrow-left" size={20} color={BRAND_COLOR} />
            <Text style={ss.mBackTxt}>Back</Text>
          </TouchableOpacity>
          <View style={{ flex: 1, marginLeft: 8 }}>
            <Text style={ss.mTtl} numberOfLines={1}>{paper.subject}</Text>
            <Text style={ss.mSub}>{paper.academic_year} · {grade}</Text>
          </View>
          {ans > 0 && <View style={ss.ansBadge}><Feather name="check-circle" size={12} color="#22c55e" /><Text style={ss.ansBadgeT}>{ans}/{qs.length}</Text></View>}
        </View>
        {loading && <View style={ss.ctr}><ActivityIndicator color={C} size="large" /><Text style={ss.loadT}>Loading…</Text></View>}
        {!!err && <View style={ss.ctr}><Text style={{ fontSize: 32 }}>⚠️</Text><Text style={ss.emTtl}>Error</Text><Text style={ss.emSub}>{err}</Text></View>}
        {!loading && !err && qs.length === 0 && <View style={ss.ctr}><Text style={{ fontSize: 32 }}>📄</Text><Text style={ss.emTtl}>No questions yet</Text></View>}
        {!loading && !err && qs.length > 0 && (
          <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 80 }}>
            <View style={ss.statsBar}>
              <View style={ss.stat}><Feather name="help-circle" size={13} color="#6b7280" /><Text style={ss.statT}>{qs.length} Questions</Text></View>
              <View style={ss.stat}><Feather name="check-circle" size={13} color="#22c55e" /><Text style={ss.statT}>{ans} Answered</Text></View>
            </View>
            <View style={ss.disclaimer}>
              <Feather name="info" size={12} color="#6b7280" style={{ marginTop: 1, flexShrink: 0 }} />
              <Text style={ss.disclaimerT}>
                Official CBSE question papers and marking schemes, sourced from cbseacademic.nic.in. Answers verified against the marking scheme. Questions with{" "}
                <Feather name="image" size={11} color="#f59e0b" />{" "}
                require the official PDF for complete context — tap the PDF link above to verify.
              </Text>
            </View>
            {qs.map(q => <QCard key={q.id} q={q} />)}
          </ScrollView>
        )}
      </View>
  );
}

function PCard({ paper, onPress }: { paper: PaperItem; onPress: () => void }) {
  const live = paper.status === "active";
  return (
    <TouchableOpacity style={ss.pCard} onPress={onPress} activeOpacity={0.85}>
      <View style={[ss.pIco, { backgroundColor: live ? "#f0fdf4" : "#fef3c7" }]}>
        <Feather name={live ? "book-open" : "clock"} size={20} color={live ? "#22c55e" : "#f59e0b"} />
      </View>
      <View style={{ flex: 1 }}>
        <Text style={ss.pSubj}>{paper.subject}</Text>
        <View style={ss.pMeta}>
          <Text style={ss.pQ}>{paper.question_count}q</Text>
          <View style={[ss.pBadge, { backgroundColor: live ? "#f0fdf4" : "#fef3c7" }]}>
            <Text style={[ss.pBadgeT, { color: live ? "#16a34a" : "#d97706" }]}>{live ? "✓ Answered" : "Pending"}</Text>
          </View>
        </View>
      </View>
      <Feather name="chevron-right" size={16} color="#9ca3af" />
    </TouchableOpacity>
  );
}

export default function BoardPapersScreen() {
  const [grade, setGrade] = useState("Grade 10");
  const [years, setYears] = useState<YearItem[]>([]);
  const [subjects, setSubjects] = useState<SubjectItem[]>([]);
  const [papers, setPapers] = useState<PaperItem[]>([]);
  const [selY, setSelY] = useState<YearItem | null>(null);
  const [selS, setSelS] = useState<SubjectItem | null>(null);
  const [openP, setOpenP] = useState<PaperItem | null>(null);
  const [loadY, setLoadY] = useState(false);
  const [loadS, setLoadS] = useState(false);
  const [loadP, setLoadP] = useState(false);
  const [full, setFull] = useState(false);

  useEffect(() => {
    setYears([]); setSubjects([]); setPapers([]); setSelY(null); setSelS(null); setLoadY(true);
    authFetch(`/api/board-papers/years?grade=${encodeURIComponent(grade)}`)
      .then((d: any) => { setYears(d.years ?? []); setFull(!!d.full_access); const f = (d.years ?? []).find((y: YearItem) => !y.locked); if (f) setSelY(f); })
      .catch(() => {}).finally(() => setLoadY(false));
  }, [grade]); // eslint-disable-line

  useEffect(() => {
    if (!selY) return;
    setSubjects([]); setPapers([]); setSelS(null); setLoadS(true);
    authFetch(`/api/board-papers/subjects?grade=${encodeURIComponent(grade)}&academic_year=${encodeURIComponent(selY.year)}`)
      .then((d: any) => { setSubjects(d.subjects ?? []); const f = (d.subjects ?? []).find((s: SubjectItem) => !s.locked); if (f) setSelS(f); })
      .catch(() => {}).finally(() => setLoadS(false));
  }, [selY]); // eslint-disable-line

  useEffect(() => {
    if (!selY || !selS) return;
    setPapers([]); setLoadP(true);
    authFetch(`/api/board-papers/list?grade=${encodeURIComponent(grade)}&academic_year=${encodeURIComponent(selY.year)}&subject=${encodeURIComponent(selS.subject)}`)
      .then((d: any) => setPapers(d.papers ?? []))
      .catch(() => {}).finally(() => setLoadP(false));
  }, [selS]); // eslint-disable-line

  const chip = (label: string, active: boolean, locked: boolean, onPress: () => void) => (
    <TouchableOpacity key={label} style={[ss.chip, active && { borderColor: C, backgroundColor: C + "18" }, locked && ss.chipLocked]} onPress={onPress} disabled={locked}>
      {locked && <Feather name="lock" size={10} color="#9ca3af" style={{ marginRight: 3 }} />}
      <Text style={[ss.chipT, active && { color: C, fontWeight: "700" as const }, locked && { color: "#9ca3af" }]}>{label}</Text>
    </TouchableOpacity>
  );

  return (
    <ScrollView style={ss.screen} contentContainerStyle={ss.content}>
      <View style={ss.hdr}>
        <View style={ss.hIco}><Text style={{ fontSize: 22 }}>📋</Text></View>
        <View>
          <Text style={ss.hTtl}>Board Papers</Text>
          <Text style={ss.hSub}>CBSE Sample Papers · Official Answers</Text>
        </View>
      </View>

      {!full && (
        <View style={ss.freeBanner}>
          <Feather name="info" size={14} color={C} />
          <Text style={ss.freeT}>Free plan: 1 year · 1 subject. Upgrade to access all 115+ papers.</Text>
        </View>
      )}

      <Text style={ss.lbl}>Grade</Text>
      <View style={ss.gradeRow}>
        {["Grade 10", "Grade 12"].map(g => (
          <TouchableOpacity key={g} style={[ss.gradeBtn, grade === g && ss.gradeActive]} onPress={() => setGrade(g)}>
            <Text style={[ss.gradeT, grade === g && ss.gradeActiveT]}>{g}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <Text style={ss.lbl}>Academic Year</Text>
      {loadY ? <ActivityIndicator color={C} style={{ marginBottom: 12 }} /> : (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 12 }}>
          {years.map(y => chip(y.year, selY?.year === y.year && !y.locked, y.locked, () => setSelY(y)))}
        </ScrollView>
      )}

      {selY && (
        <>
          <Text style={ss.lbl}>Subject</Text>
          {loadS ? <ActivityIndicator color={C} style={{ marginBottom: 12 }} /> : (
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 12 }}>
              {subjects.map(s => chip(s.subject, selS?.subject === s.subject && !s.locked, s.locked, () => setSelS(s)))}
            </ScrollView>
          )}
        </>
      )}

      {selS && (
        <>
          <Text style={ss.lbl}>Papers{selY ? ` — ${selY.year}` : ""}</Text>
          {loadP ? (
            <View style={ss.ctr}><ActivityIndicator color={C} /></View>
          ) : papers.length === 0 ? (
            <View style={ss.ctr}><Text style={{ fontSize: 32, marginBottom: 8 }}>📭</Text><Text style={ss.emTtl}>No papers found</Text></View>
          ) : (
            papers.map(p => <PCard key={p.id} paper={p} onPress={() => setOpenP(p)} />)
          )}
        </>
      )}

      {openP && <PModal paper={openP} grade={grade} onClose={() => setOpenP(null)} />}
    </ScrollView>
  );
}

const ss = StyleSheet.create({
  screen: { flex: 1, backgroundColor: "#f8fafc" },
  content: { padding: 16, paddingBottom: 60 },
  hdr: { flexDirection: "row", alignItems: "center", gap: 12, marginBottom: 16 },
  hIco: { width: 44, height: 44, borderRadius: 12, backgroundColor: "rgba(99,102,241,.1)", alignItems: "center", justifyContent: "center" },
  hTtl: { fontSize: 20, fontWeight: "800", color: "#111827" },
  hSub: { fontSize: 12, color: "#6b7280" },
  freeBanner: { flexDirection: "row", alignItems: "center", gap: 8, backgroundColor: "rgba(99,102,241,.08)", borderRadius: 10, padding: 12, marginBottom: 16, borderWidth: 1, borderColor: "rgba(99,102,241,.2)" },
  freeT: { fontSize: 12, color: "#4f46e5", flex: 1, lineHeight: 18 },
  lbl: { fontSize: 11, fontWeight: "700", color: "#6b7280", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 8 },
  gradeRow: { flexDirection: "row", gap: 10, marginBottom: 16 },
  gradeBtn: { flex: 1, paddingVertical: 12, borderRadius: 12, borderWidth: 1.5, borderColor: "#d1d5db", backgroundColor: "#fff", alignItems: "center" },
  gradeActive: { borderColor: BRAND_COLOR, backgroundColor: BRAND_COLOR },
  gradeT: { fontSize: 14, fontWeight: "700", color: "#374151" },
  gradeActiveT: { color: "#fff" },
  chip: { flexDirection: "row", alignItems: "center", paddingHorizontal: 14, paddingVertical: 9, borderRadius: 99, borderWidth: 1.5, borderColor: "#d1d5db", backgroundColor: "#fff", marginRight: 8 },
  chipLocked: { backgroundColor: "#f9fafb", borderColor: "#e5e7eb" },
  chipT: { fontSize: 12, fontWeight: "600", color: "#374151" },
  // Question card
  qCard: { backgroundColor: "#fff", borderRadius: 12, borderWidth: 1, borderColor: "#e5e7eb", marginBottom: 10, overflow: "hidden" },
  qHdr: { flexDirection: "row", alignItems: "flex-start", padding: 12, gap: 10 },
  qNum: { width: 32, height: 32, borderRadius: 8, backgroundColor: "rgba(99,102,241,.1)", alignItems: "center", justifyContent: "center" },
  qNumT: { fontSize: 11, fontWeight: "800", color: BRAND_COLOR },
  qMeta: { flexDirection: "row", alignItems: "center", gap: 6, marginBottom: 4, flexWrap: "wrap" },
  qBadge: { fontSize: 10, fontWeight: "700", color: "#6366f1", backgroundColor: "rgba(99,102,241,.1)", paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6 },
  qM: { fontSize: 11, color: "#6b7280", fontWeight: "600" },
  qSec: { fontSize: 10, color: "#9ca3af", backgroundColor: "#f3f4f6", paddingHorizontal: 5, paddingVertical: 2, borderRadius: 4 },
  qT: { fontSize: 13, color: "#111827", lineHeight: 20 },
  qBody: { borderTopWidth: 1, borderTopColor: "#f3f4f6", padding: 12 },
  optRow: { flexDirection: "row", alignItems: "flex-start", gap: 8, marginBottom: 6 },
  optK: { width: 24, height: 24, borderRadius: 6, backgroundColor: "#f3f4f6", alignItems: "center", justifyContent: "center", flexShrink: 0 },
  optKT: { fontSize: 11, fontWeight: "800", color: "#374151" },
  optT: { fontSize: 13, color: "#374151", flex: 1, lineHeight: 20 },
  reveal: { flexDirection: "row", alignItems: "center", gap: 6, padding: 10, backgroundColor: "rgba(99,102,241,.06)", borderRadius: 8, borderWidth: 1, borderColor: "rgba(99,102,241,.2)" },
  revealT: { fontSize: 13, fontWeight: "600", color: BRAND_COLOR },
  ansBox: { backgroundColor: "#f0fdf4", borderRadius: 8, padding: 12, borderWidth: 1, borderColor: "#bbf7d0" },
  ansLbl: { fontSize: 12, fontWeight: "700", color: "#16a34a", marginBottom: 6 },
  ansT: { fontSize: 13, color: "#111827", lineHeight: 20 },
  expT: { fontSize: 12, color: "#6b7280", lineHeight: 18, marginTop: 6, fontStyle: "italic" },
  pendBox: { flexDirection: "row", alignItems: "center", gap: 6, backgroundColor: "#fef3c7", borderRadius: 8, padding: 10 },
  pendT: { fontSize: 12, color: "#92400e", flex: 1 },
  // Paper card
  pCard: { flexDirection: "row", alignItems: "center", gap: 12, backgroundColor: "#fff", borderRadius: 12, padding: 14, borderWidth: 1, borderColor: "#e5e7eb", marginBottom: 10 },
  pIco: { width: 44, height: 44, borderRadius: 10, alignItems: "center", justifyContent: "center" },
  pSubj: { fontSize: 15, fontWeight: "700", color: "#111827", marginBottom: 4 },
  pMeta: { flexDirection: "row", alignItems: "center", gap: 8 },
  pQ: { fontSize: 12, color: "#6b7280" },
  pBadge: { borderRadius: 99, paddingHorizontal: 8, paddingVertical: 3 },
  pBadgeT: { fontSize: 11, fontWeight: "700" },
  // Modal
  modal: { flex: 1, backgroundColor: "#fff" },
  mHdr: { flexDirection: "row", alignItems: "center", paddingHorizontal: 14, paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: "#e5e7eb", backgroundColor: "#fff" },
  mBackBtn: { flexDirection: "row", alignItems: "center", gap: 4, paddingHorizontal: 10, paddingVertical: 8, borderRadius: 10, backgroundColor: "rgba(99,102,241,.08)", marginRight: 4 },
  mBackTxt: { fontSize: 14, fontWeight: "700", color: BRAND_COLOR },
  mTtl: { fontSize: 15, fontWeight: "800", color: "#111827" },
  mSub: { fontSize: 11, color: "#6b7280" },
  ansBadge: { flexDirection: "row", alignItems: "center", gap: 4, backgroundColor: "#f0fdf4", borderRadius: 99, paddingHorizontal: 10, paddingVertical: 5 },
  ansBadgeT: { fontSize: 12, fontWeight: "700", color: "#16a34a" },
  statsBar: { flexDirection: "row", gap: 16, backgroundColor: "#fff", borderRadius: 10, padding: 12, marginBottom: 10, borderWidth: 1, borderColor: "#e5e7eb" },
  disclaimer: { flexDirection: "row", alignItems: "flex-start", gap: 6, backgroundColor: "#f8fafc", borderRadius: 8, padding: 10, marginBottom: 14, borderWidth: 1, borderColor: "#e5e7eb" },
  disclaimerT: { fontSize: 11, color: "#6b7280", lineHeight: 17, flex: 1 },
  stat: { flexDirection: "row", alignItems: "center", gap: 5 },
  statT: { fontSize: 12, color: "#374151", fontWeight: "600" },
  // Utility
  ctr: { alignItems: "center", paddingVertical: 40, gap: 8 },
  loadT: { fontSize: 13, color: "#6b7280", marginTop: 8 },
  emTtl: { fontSize: 16, fontWeight: "700", color: "#374151" },
  emSub: { fontSize: 13, color: "#6b7280", textAlign: "center" },
});
