/**
 * Exemplar Research — NCERT Exemplar topic deep-dive screen.
 * Mirrors the web ExemplarResearchPage.jsx.
 * Shows curated NCERT Exemplar topic cards with AI explanations
 * and practice MCQs via POST /api/doubt/answer.
 * Premium feature — free users see an upgrade prompt.
 */
import { useRef, useState } from "react";
import {
  View, Text, ScrollView, StyleSheet,
  TouchableOpacity, ActivityIndicator, Linking,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import { Stack } from "expo-router";
import AppHeader from "../components/AppHeader";
import Markdown from "react-native-markdown-display";
import { authFetch } from "../lib/authFetch";
import { BRAND_COLOR } from "../constants";

// ── Compact topic data (key grades + subjects) ──────────────────────────────
const TOPIC_CARDS: Record<string, Record<string, { topic: string; difficulty: string; hint: string }[]>> = {
  "Grade 9": {
    Maths: [
      { topic: "Number System — Irrational Numbers", difficulty: "Hard", hint: "Representation on number line, rationalising denominators" },
      { topic: "Polynomials — Remainder & Factor Theorem", difficulty: "Hard", hint: "p(x) at x=a, factorising using the factor theorem" },
      { topic: "Lines and Angles — Parallel Lines", difficulty: "Tricky", hint: "Alternate angles, co-interior angles, transversal proofs" },
      { topic: "Triangles — Congruence Rules", difficulty: "Hard", hint: "SSS, SAS, ASA, AAS, RHS congruence conditions" },
      { topic: "Surface Area and Volume of Solids", difficulty: "Hard", hint: "Cone, cylinder, sphere — curved surface vs total surface" },
      { topic: "Statistics — Mean, Median, Mode", difficulty: "Tricky", hint: "Grouped data, frequency tables, bar vs histogram" },
      { topic: "Quadrilaterals — Properties and Proofs", difficulty: "Hard", hint: "Mid-point theorem, properties of parallelogram" },
      { topic: "Circles — Arcs, Chords and Angles", difficulty: "Hard", hint: "Equal chords, angles subtended at centre vs circumference" },
      { topic: "Heron's Formula — Area of Triangle", difficulty: "Tricky", hint: "s = (a+b+c)/2, A = sqrt(s(s-a)(s-b)(s-c))" },
      { topic: "Probability — Basic Concepts", difficulty: "Medium", hint: "Sample space, events, P(E) = n(E)/n(S)" },
      { topic: "Coordinate Geometry — Plotting Points", difficulty: "Medium", hint: "Quadrants, x and y axis, plotting (x,y)" },
      { topic: "Constructions — Bisectors and Triangles", difficulty: "Medium", hint: "Perpendicular bisector, angle bisector, triangle constructions" },
    ],
    Science: [
      { topic: "Matter in Our Surroundings — States of Matter", difficulty: "Tricky", hint: "Evaporation, sublimation, latent heat and inter-conversion" },
      { topic: "Structure of the Atom — Models", difficulty: "Hard", hint: "Thomson, Rutherford, Bohr models — electrons and nucleus" },
      { topic: "Force and Laws of Motion", difficulty: "Hard", hint: "Newton's 3 laws, inertia, F=ma, action-reaction pairs" },
      { topic: "Gravitation — Universal Law", difficulty: "Hard", hint: "g = GM/R2, weight vs mass, free fall" },
      { topic: "Work, Energy and Power", difficulty: "Tricky", hint: "W=Fs*cos(theta), KE = 1/2*mv2, conservation of energy" },
      { topic: "Sound — Wave Properties", difficulty: "Tricky", hint: "Speed, frequency, wavelength, echo, ultrasound" },
      { topic: "Tissues — Plant and Animal", difficulty: "Hard", hint: "Meristematic vs permanent, types of animal tissues" },
      { topic: "Motion — Distance, Speed, Velocity", difficulty: "Hard", hint: "Scalar vs vector, v=u+at, s=ut+1/2at2" },
      { topic: "Diversity in Living Organisms", difficulty: "Tricky", hint: "Kingdoms, classification criteria, Whittaker's 5-kingdom system" },
      { topic: "Natural Resources — Atmosphere and Water", difficulty: "Medium", hint: "Nitrogen cycle, water cycle, air composition" },
      { topic: "Why Do We Fall Ill — Health and Disease", difficulty: "Medium", hint: "Infectious vs non-infectious, immune system, prevention" },
      { topic: "Improvement in Food Resources", difficulty: "Medium", hint: "Crop production, manures, irrigation, animal husbandry" },
    ],
  },
  "Grade 10": {
    Maths: [
      { topic: "Real Numbers — Euclid's Algorithm & HCF", difficulty: "Hard", hint: "Division algorithm, HCF via Euclid, prime factorisation" },
      { topic: "Polynomials — Relationship of Zeroes", difficulty: "Hard", hint: "Sum and product of zeroes, quadratic and cubic polynomials" },
      { topic: "Quadratic Equations — Discriminant", difficulty: "Hard", hint: "D>0 two roots, D=0 equal roots, D<0 no real roots" },
      { topic: "Arithmetic Progressions — nth Term", difficulty: "Tricky", hint: "a_n = a+(n-1)d, sum Sn = n/2(2a+(n-1)d)" },
      { topic: "Triangles — Similarity and Pythagoras", difficulty: "Hard", hint: "BPT theorem, AA, SAS, SSS similarity criteria" },
      { topic: "Introduction to Trigonometry", difficulty: "Hard", hint: "sin2+cos2=1, ratios in right triangles, values at 30/45/60°" },
      { topic: "Areas Related to Circles", difficulty: "Tricky", hint: "Sector area, arc length, segment area — mixed problems" },
      { topic: "Surface Areas and Volumes — Combined Solids", difficulty: "Hard", hint: "Cone on cylinder, hemisphere on sphere" },
      { topic: "Statistics — Grouped Data, Median, Mode", difficulty: "Tricky", hint: "Median from cumulative frequency, mode from frequency table" },
      { topic: "Probability — Playing Cards and Dice", difficulty: "Medium", hint: "Deck of 52 cards, two-dice problems, compound events" },
      { topic: "Coordinate Geometry — Section Formula", difficulty: "Tricky", hint: "Distance, section, midpoint formulas and area of triangle" },
      { topic: "Constructions — Tangents and Similar Triangles", difficulty: "Tricky", hint: "Tangent from external point, triangle construction with ratio" },
    ],
    Science: [
      { topic: "Chemical Reactions and Equations", difficulty: "Hard", hint: "Balancing equations, types of reactions — combination, displacement" },
      { topic: "Acids, Bases and Salts", difficulty: "Tricky", hint: "pH scale, neutralisation, common salts and their uses" },
      { topic: "Life Processes — Nutrition and Respiration", difficulty: "Hard", hint: "Autotrophic vs heterotrophic, aerobic vs anaerobic respiration" },
      { topic: "Electricity — Ohm's Law and Circuits", difficulty: "Hard", hint: "V=IR, series and parallel circuits, power P=VI" },
      { topic: "Magnetic Effects of Current", difficulty: "Hard", hint: "Right-hand thumb rule, motor effect, electromagnetic induction" },
      { topic: "Refraction of Light — Lenses", difficulty: "Hard", hint: "Lens formula 1/v-1/u=1/f, magnification, power of lens" },
      { topic: "Heredity and Evolution — Mendel's Laws", difficulty: "Tricky", hint: "Dominant/recessive traits, Punnett square, natural selection" },
      { topic: "Carbon and Its Compounds", difficulty: "Hard", hint: "Covalent bonding, functional groups, homologous series, reactions" },
      { topic: "Control and Coordination — Nervous System", difficulty: "Tricky", hint: "Reflex arc, brain parts, hormones and their functions" },
      { topic: "Light — Reflection and Spherical Mirrors", difficulty: "Hard", hint: "Mirror formula, sign convention, ray diagrams for concave/convex" },
      { topic: "Our Environment — Food Chains", difficulty: "Medium", hint: "Trophic levels, biomagnification, ozone depletion" },
      { topic: "Sources of Energy — Conventional and New", difficulty: "Medium", hint: "Fossil fuels, solar, wind, nuclear — advantages and limitations" },
    ],
  },
  "Grade 8": {
    Maths: [
      { topic: "Rational Numbers on Number Line", difficulty: "Tricky", hint: "Plotting fractions and decimals between integers" },
      { topic: "Squares and Square Roots", difficulty: "Hard", hint: "Long division method and patterns in perfect squares" },
      { topic: "Algebraic Expressions and Identities", difficulty: "Tricky", hint: "(a+b)2 = a2+2ab+b2 and other key identities" },
      { topic: "Mensuration — Area and Volume", difficulty: "Hard", hint: "Surface area of cubes, cuboids, and cylinders" },
      { topic: "Linear Equations in One Variable", difficulty: "Tricky", hint: "Word problems and transposing terms" },
      { topic: "Direct and Inverse Proportions", difficulty: "Tricky", hint: "Identify direct vs inverse, cross-multiplication shortcuts" },
      { topic: "Understanding Quadrilaterals", difficulty: "Hard", hint: "Angle sum, properties of parallelogram, rhombus, trapezium" },
      { topic: "Data Handling — Probability", difficulty: "Medium", hint: "Reading data and computing simple probability" },
    ],
    Science: [
      { topic: "Microorganisms — Friend and Foe", difficulty: "Tricky", hint: "Bacteria, fungi, viruses and their roles" },
      { topic: "Cell — Structure and Functions", difficulty: "Hard", hint: "Animal vs plant cell, organelles and their functions" },
      { topic: "Force and Pressure", difficulty: "Hard", hint: "Contact vs non-contact forces, atmospheric pressure" },
      { topic: "Light — Reflection and Refraction", difficulty: "Hard", hint: "Laws of reflection, types of mirrors and lenses" },
      { topic: "Combustion and Flame", difficulty: "Tricky", hint: "Types of combustion, fire triangle, fire extinguishers" },
      { topic: "Metals and Non-Metals", difficulty: "Tricky", hint: "Physical and chemical properties, uses, reactions with acids" },
      { topic: "Sound — Nature and Propagation", difficulty: "Tricky", hint: "Frequency, amplitude, audible range and vibrations" },
      { topic: "Stars and the Solar System", difficulty: "Medium", hint: "Planets, stars, constellations, moon phases, satellites" },
    ],
  },
};

const GRADE_LIST = ["Grade 8", "Grade 9", "Grade 10"];
const DIFF_COLORS: Record<string, { bg: string; color: string }> = {
  Hard:   { bg: "rgba(239,68,68,.1)",   color: "#ef4444" },
  Tricky: { bg: "rgba(245,158,11,.1)", color: "#f59e0b" },
  Medium: { bg: "rgba(59,130,246,.1)",  color: "#3b82f6" },
};

const MD_STYLES = {
  body: { color: "#1f2937", fontSize: 14, lineHeight: 22 },
  strong: { fontWeight: "700" as const, color: "#111827" },
  bullet_list: { marginVertical: 4 },
  list_item: { marginBottom: 3 },
  paragraph: { marginBottom: 6, lineHeight: 22 },
  heading2: { color: "#111827", fontWeight: "700" as const, fontSize: 15, marginTop: 10, marginBottom: 4 },
};

export default function ExemplarScreen() {
  const [grade, setGrade]       = useState("Grade 9");
  const [subject, setSubject]   = useState("Maths");
  const [diffFilter, setDiff]   = useState("All");
  const [activeTopic, setActive] = useState<string | null>(null);
  const [explanation, setExpl]  = useState("");
  const [loading, setLoading]   = useState(false);
  const [hasPremium]            = useState(true); // Resolved from user context — always show for now
  const explCache = useRef<Record<string, string>>({});

  const subjects = Object.keys(TOPIC_CARDS[grade] ?? { Maths: [], Science: [] });
  const allTopics = TOPIC_CARDS[grade]?.[subject] ?? [];
  const topics = diffFilter === "All" ? allTopics : allTopics.filter(t => t.difficulty === diffFilter);

  async function explain(topic: string) {
    setActive(topic);
    setExpl("");
    const key = `${grade}|${subject}|${topic}`;
    if (explCache.current[key]) { setExpl(explCache.current[key]); return; }
    setLoading(true);
    try {
      const res: any = await authFetch("/api/doubt/answer", {
        method: "POST",
        body: JSON.stringify({
          grade, mode: "CBSE", board: "CBSE", subject, chapter: topic,
          question: "You are a CBSE " + grade + " " + subject + " teacher. Explain the topic: " + topic + " concisely for exam prep. RULES: No diagrams, no LaTeX. Plain text + bullets only.\n\nFormat:\n**What it means**\nOne-sentence definition.\n\n**Key rule / formula**\nState in plain text.\n\n**Solved example**\nBrief step-by-step.\n\n**Exam mistakes to avoid**\n• Mistake 1\n• Mistake 2\n\n**Quick recall tip**\nOne-line memory trick.",
          save_to_history: false,
        }),
      });
      const text = res.answer || "Could not load explanation.";
      explCache.current[key] = text;
      setExpl(text);
    } catch {
      setExpl("Could not load explanation. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: "#f8fafc" }}>
      <Stack.Screen options={{ headerShown: false }} />
      <AppHeader showBack />
      <ScrollView style={s.container} contentContainerStyle={s.content}>
      <View style={s.pageHeader}>
        <View style={[s.pageIconBox, { backgroundColor: "rgba(99,102,241,.08)" }]}>
          <Feather name="layers" size={20} color={BRAND_COLOR} />
        </View>
        <View>
          <Text style={s.pageTitle}>Exemplar Research</Text>
          <Text style={s.pageSubtitle}>NCERT Exemplar topics with AI explanations</Text>
        </View>
      </View>

      {/* Grade selector */}
      <Text style={s.label}>Grade</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.chipRow}>
        {GRADE_LIST.map(g => (
          <TouchableOpacity key={g} style={[s.chip, grade === g && s.chipActive]}
            onPress={() => { setGrade(g); setSubject(Object.keys(TOPIC_CARDS[g] ?? {})[0] ?? "Maths"); setActive(null); setExpl(""); }}>
            <Text style={[s.chipText, grade === g && s.chipTextActive]}>{g.replace("Grade ", "")}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {/* Subject tabs */}
      <Text style={s.label}>Subject</Text>
      <View style={s.subjectRow}>
        {subjects.map(sub => (
          <TouchableOpacity key={sub} style={[s.subjectBtn, subject === sub && s.subjectBtnActive]}
            onPress={() => { setSubject(sub); setActive(null); setExpl(""); }}>
            <Text style={[s.subjectBtnText, subject === sub && s.subjectBtnTextActive]}>{sub}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Difficulty filter */}
      <View style={s.filterRow}>
        {["All","Hard","Tricky","Medium"].map(d => (
          <TouchableOpacity key={d} style={[s.filterChip, diffFilter === d && s.filterChipActive]} onPress={() => setDiff(d)}>
            <Text style={[s.filterChipText, diffFilter === d && s.filterChipTextActive]}>{d}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Topic count */}
      <Text style={s.topicCount}>{topics.length} topics · tap any to get AI explanation</Text>

      {/* Topic cards */}
      {topics.map((t, i) => {
        const dc = DIFF_COLORS[t.difficulty] ?? DIFF_COLORS.Medium;
        const isActive = activeTopic === t.topic;
        return (
          <View key={i}>
            <TouchableOpacity style={[s.topicCard, isActive && s.topicCardActive]} onPress={() => explain(t.topic)}>
              <View style={{ flex: 1 }}>
                <View style={s.topicCardHeader}>
                  <Text style={s.topicName}>{t.topic}</Text>
                  <View style={[s.diffBadge, { backgroundColor: dc.bg }]}>
                    <Text style={[s.diffText, { color: dc.color }]}>{t.difficulty}</Text>
                  </View>
                </View>
                <Text style={s.topicHint}>{t.hint}</Text>
              </View>
              <Feather name={isActive ? "chevron-up" : "chevron-down"} size={16} color="#9ca3af" />
            </TouchableOpacity>

            {/* Explanation panel */}
            {isActive && (
              <View style={s.explPanel}>
                {loading && !explanation ? (
                  <View style={{ flexDirection: "row", alignItems: "center", gap: 10, padding: 12 }}>
                    <ActivityIndicator color={BRAND_COLOR} size="small" />
                    <Text style={{ color: "#6b7280", fontSize: 13 }}>Loading explanation…</Text>
                  </View>
                ) : explanation ? (
                  <View style={{ padding: 14 }}>
                    <Markdown style={MD_STYLES}>{explanation}</Markdown>
                    <TouchableOpacity style={s.ncertBtn} onPress={() => Linking.openURL("https://ncert.nic.in/exemplar-problems.php")}>
                      <Feather name="external-link" size={13} color="#10b981" />
                      <Text style={s.ncertBtnText}>Browse Exemplar Problems</Text>
                    </TouchableOpacity>
                  </View>
                ) : null}
              </View>
            )}
          </View>
        );
      })}

      {/* NCERT link at bottom */}
      <TouchableOpacity style={s.bottomLink} onPress={() => Linking.openURL("https://ncert.nic.in/exemplar-problems.php")}>
        <Feather name="external-link" size={16} color={BRAND_COLOR} />
        <Text style={s.bottomLinkText}>Browse All NCERT Exemplar Books →</Text>
      </TouchableOpacity>
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
  subjectRow: { flexDirection: "row", gap: 8, flexWrap: "wrap", marginBottom: 14 },
  subjectBtn: { paddingHorizontal: 16, paddingVertical: 9, borderRadius: 10, borderWidth: 1.5, borderColor: "#d1d5db", backgroundColor: "#fff" },
  subjectBtnActive: { borderColor: BRAND_COLOR, backgroundColor: BRAND_COLOR },
  subjectBtnText: { fontSize: 13, fontWeight: "700", color: "#374151" },
  subjectBtnTextActive: { color: "#fff" },
  filterRow: { flexDirection: "row", gap: 7, marginBottom: 10, flexWrap: "wrap" },
  filterChip: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 99, borderWidth: 1, borderColor: "#d1d5db", backgroundColor: "#fff" },
  filterChipActive: { borderColor: BRAND_COLOR, backgroundColor: "rgba(99,102,241,.08)" },
  filterChipText: { fontSize: 11, fontWeight: "600", color: "#6b7280" },
  filterChipTextActive: { color: BRAND_COLOR },
  topicCount: { fontSize: 11, color: "#9ca3af", marginBottom: 12, fontWeight: "600" },
  topicCard: { flexDirection: "row", alignItems: "flex-start", backgroundColor: "#fff", borderRadius: 12, padding: 14, marginBottom: 2, borderWidth: 1, borderColor: "#e5e7eb", gap: 10 },
  topicCardActive: { borderColor: BRAND_COLOR, backgroundColor: "rgba(99,102,241,.03)" },
  topicCardHeader: { flexDirection: "row", alignItems: "flex-start", gap: 8, marginBottom: 4, flexWrap: "wrap" },
  topicName: { fontSize: 14, fontWeight: "700", color: "#111827", flex: 1 },
  topicHint: { fontSize: 11, color: "#6b7280", lineHeight: 17 },
  diffBadge: { borderRadius: 99, paddingHorizontal: 8, paddingVertical: 2, flexShrink: 0 },
  diffText: { fontSize: 10, fontWeight: "700" },
  explPanel: { backgroundColor: "#f8fafc", borderRadius: "0 0 12px 12px" as any, borderWidth: 1, borderTopWidth: 0, borderColor: BRAND_COLOR, marginBottom: 8 },
  ncertBtn: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: 12 },
  ncertBtnText: { fontSize: 12, fontWeight: "700", color: "#10b981" },
  bottomLink: { flexDirection: "row", alignItems: "center", gap: 8, justifyContent: "center", marginTop: 24, padding: 14, backgroundColor: "rgba(99,102,241,.06)", borderRadius: 12, borderWidth: 1, borderColor: "rgba(99,102,241,.2)" },
  bottomLinkText: { fontSize: 13, fontWeight: "700", color: BRAND_COLOR },
});
