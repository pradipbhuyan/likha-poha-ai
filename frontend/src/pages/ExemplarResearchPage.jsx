import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { answerDoubt } from "../api/doubt";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// ── NCERT Exemplar link (main browse page — more reliable than direct PDFs) ──
const EXEMPLAR_URL = "https://ncert.nic.in/exemplar-problems.php";
// Grade-specific hint text for the PDF button
const EXEMPLAR_HINTS = {
  "Grade 8":  "Class 8 Exemplar Books",
  "Grade 9":  "Class 9 Exemplar Books",
  "Grade 10": "Class 10 Exemplar Books",
};

// ── Curated topic cards — 12 per grade / subject (NCERT Exemplar focus) ──────
const TOPIC_CARDS = {
  "Grade 8": {
    Maths: [
      { topic: "Rational Numbers on Number Line", difficulty: "Tricky", emoji: "🔢", hint: "Plotting fractions and decimals between integers" },
      { topic: "Squares and Square Roots", difficulty: "Hard", emoji: "√", hint: "Long division method and patterns in perfect squares" },
      { topic: "Cubes and Cube Roots", difficulty: "Hard", emoji: "³√", hint: "Prime factorisation and cube root tricks" },
      { topic: "Algebraic Expressions and Identities", difficulty: "Tricky", emoji: "📐", hint: "(a+b)² = a²+2ab+b² and other key identities" },
      { topic: "Mensuration — Area and Volume", difficulty: "Hard", emoji: "📦", hint: "Surface area of cubes, cuboids, and cylinders" },
      { topic: "Linear Equations in One Variable", difficulty: "Tricky", emoji: "✏️", hint: "Word problems and transposing terms" },
      { topic: "Comparing Quantities — Percentage, Profit Loss", difficulty: "Tricky", emoji: "💹", hint: "Simple interest and compound interest" },
      { topic: "Data Handling — Bar Graphs and Probability", difficulty: "Medium", emoji: "📊", hint: "Reading data and computing simple probability" },
      { topic: "Direct and Inverse Proportions", difficulty: "Tricky", emoji: "⚖️", hint: "Identify direct vs inverse, cross-multiplication shortcuts" },
      { topic: "Understanding Quadrilaterals", difficulty: "Hard", emoji: "◻️", hint: "Angle sum, properties of parallelogram, rhombus, trapezium" },
      { topic: "Playing with Numbers — Divisibility", difficulty: "Medium", emoji: "🎯", hint: "Divisibility rules for 2,3,4,5,6,9,11 and puzzles" },
      { topic: "Introduction to Graphs — Line and Bar", difficulty: "Medium", emoji: "📉", hint: "Reading coordinates, plotting and interpreting bar/line graphs" },
    ],
    Science: [
      { topic: "Microorganisms — Friend and Foe", difficulty: "Tricky", emoji: "🦠", hint: "Bacteria, fungi, viruses and their roles" },
      { topic: "Cell — Structure and Functions", difficulty: "Hard", emoji: "🔬", hint: "Animal vs plant cell, organelles and their functions" },
      { topic: "Conservation of Plants and Animals", difficulty: "Medium", emoji: "🌿", hint: "Biodiversity, endangered species, deforestation" },
      { topic: "Combustion and Flame", difficulty: "Tricky", emoji: "🔥", hint: "Types of combustion, fire triangle, fire extinguishers" },
      { topic: "Force and Pressure", difficulty: "Hard", emoji: "⚡", hint: "Contact vs non-contact forces, atmospheric pressure" },
      { topic: "Sound — Nature and Propagation", difficulty: "Tricky", emoji: "🔊", hint: "Frequency, amplitude, audible range and vibrations" },
      { topic: "Light — Reflection and Refraction", difficulty: "Hard", emoji: "💡", hint: "Laws of reflection, types of mirrors and lenses" },
      { topic: "Pollution of Air and Water", difficulty: "Medium", emoji: "🌫️", hint: "Causes, effects and measures to control pollution" },
      { topic: "Reproduction in Animals", difficulty: "Medium", emoji: "🐣", hint: "Sexual vs asexual reproduction, human reproduction basics" },
      { topic: "Metals and Non-Metals", difficulty: "Tricky", emoji: "⚙️", hint: "Physical and chemical properties, uses, reactions with acids" },
      { topic: "Friction — Types and Effects", difficulty: "Tricky", emoji: "🛝", hint: "Static, sliding, rolling friction; ways to increase/decrease" },
      { topic: "Stars and the Solar System", difficulty: "Medium", emoji: "⭐", hint: "Planets, stars, constellations, moon phases, satellites" },
    ],
  },
  "Grade 9": {
    Maths: [
      { topic: "Number System — Irrational Numbers", difficulty: "Hard", emoji: "π", hint: "Representation on number line, rationalising denominators" },
      { topic: "Polynomials — Remainder & Factor Theorem", difficulty: "Hard", emoji: "📈", hint: "p(x) at x=a, factorising using the factor theorem" },
      { topic: "Coordinate Geometry — Plotting Points", difficulty: "Medium", emoji: "📍", hint: "Quadrants, x and y axis, plotting (x,y)" },
      { topic: "Lines and Angles — Parallel Lines", difficulty: "Tricky", emoji: "∠", hint: "Alternate angles, co-interior angles, transversal proofs" },
      { topic: "Triangles — Congruence Rules", difficulty: "Hard", emoji: "△", hint: "SSS, SAS, ASA, AAS, RHS congruence conditions" },
      { topic: "Surface Area and Volume of Solids", difficulty: "Hard", emoji: "📦", hint: "Cone, cylinder, sphere — curved surface vs total surface" },
      { topic: "Statistics — Mean, Median, Mode", difficulty: "Tricky", emoji: "📊", hint: "Grouped data, frequency tables, bar vs histogram" },
      { topic: "Probability — Basic Concepts", difficulty: "Medium", emoji: "🎲", hint: "Sample space, events, P(E) = n(E)/n(S)" },
      { topic: "Quadrilaterals — Properties and Proofs", difficulty: "Hard", emoji: "◻️", hint: "Mid-point theorem, properties of parallelogram, proving quadrilateral types" },
      { topic: "Circles — Arcs, Chords and Angles", difficulty: "Hard", emoji: "⭕", hint: "Equal chords, angles subtended at centre vs circumference" },
      { topic: "Heron's Formula — Area of Triangle", difficulty: "Tricky", emoji: "△", hint: "s = (a+b+c)/2, A = √[s(s-a)(s-b)(s-c)]" },
      { topic: "Constructions — Bisectors and Triangles", difficulty: "Medium", emoji: "📏", hint: "Perpendicular bisector, angle bisector, triangle constructions" },
    ],
    Science: [
      { topic: "Matter in Our Surroundings — States of Matter", difficulty: "Tricky", emoji: "🌊", hint: "Evaporation, sublimation, latent heat and inter-conversion" },
      { topic: "Structure of the Atom — Models", difficulty: "Hard", emoji: "⚛️", hint: "Thomson, Rutherford, Bohr models — electrons and nucleus" },
      { topic: "Force and Laws of Motion", difficulty: "Hard", emoji: "🏎️", hint: "Newton's 3 laws, inertia, F=ma, action-reaction pairs" },
      { topic: "Gravitation — Universal Law", difficulty: "Hard", emoji: "🌍", hint: "g = GM/R², weight vs mass, free fall" },
      { topic: "Work, Energy and Power", difficulty: "Tricky", emoji: "⚡", hint: "W=Fs·cosθ, KE = ½mv², conservation of energy" },
      { topic: "Sound — Wave Properties", difficulty: "Tricky", emoji: "🔊", hint: "Speed, frequency, wavelength, echo, ultrasound" },
      { topic: "Tissues — Plant and Animal", difficulty: "Hard", emoji: "🔬", hint: "Meristematic vs permanent, types of animal tissues" },
      { topic: "Natural Resources — Atmosphere and Water", difficulty: "Medium", emoji: "🌎", hint: "Nitrogen cycle, water cycle, air composition" },
      { topic: "Motion — Distance, Speed, Velocity", difficulty: "Hard", emoji: "🚀", hint: "Scalar vs vector, v=u+at, s=ut+½at², v²=u²+2as" },
      { topic: "Diversity in Living Organisms", difficulty: "Tricky", emoji: "🦋", hint: "Kingdoms, classification criteria, Whittaker's 5-kingdom system" },
      { topic: "Why Do We Fall Ill — Health and Disease", difficulty: "Medium", emoji: "🏥", hint: "Infectious vs non-infectious, immune system, prevention" },
      { topic: "Improvement in Food Resources", difficulty: "Medium", emoji: "🌾", hint: "Crop production, manures, irrigation, animal husbandry" },
    ],
  },
  "Grade 10": {
    Maths: [
      { topic: "Real Numbers — Euclid's Algorithm & HCF", difficulty: "Hard", emoji: "🔢", hint: "Division algorithm, HCF via Euclid, prime factorisation" },
      { topic: "Polynomials — Relationship of Zeroes", difficulty: "Hard", emoji: "📉", hint: "Sum and product of zeroes, quadratic and cubic polynomials" },
      { topic: "Quadratic Equations — Discriminant", difficulty: "Hard", emoji: "🔺", hint: "D>0 two roots, D=0 equal roots, D<0 no real roots" },
      { topic: "Arithmetic Progressions — nth Term", difficulty: "Tricky", emoji: "🔁", hint: "a_n = a+(n-1)d, sum S_n = n/2(2a+(n-1)d)" },
      { topic: "Triangles — Similarity and Pythagoras", difficulty: "Hard", emoji: "△", hint: "BPT theorem, AA, SAS, SSS similarity criteria" },
      { topic: "Coordinate Geometry — Section Formula", difficulty: "Tricky", emoji: "📍", hint: "Distance, section, midpoint formulas and area of triangle" },
      { topic: "Introduction to Trigonometry", difficulty: "Hard", emoji: "📐", hint: "sin²θ+cos²θ=1, ratios in right triangles, values at 30/45/60°" },
      { topic: "Areas Related to Circles", difficulty: "Tricky", emoji: "⭕", hint: "Sector area, arc length, segment area — mixed problems" },
      { topic: "Surface Areas and Volumes — Combined Solids", difficulty: "Hard", emoji: "📦", hint: "Cone on cylinder, hemisphere on sphere — combined SA and volume" },
      { topic: "Statistics — Grouped Data, Median, Mode", difficulty: "Tricky", emoji: "📊", hint: "Median from cumulative frequency, mode from frequency table" },
      { topic: "Probability — Playing Cards and Dice", difficulty: "Medium", emoji: "🎲", hint: "Deck of 52 cards, two-dice problems, compound events" },
      { topic: "Constructions — Tangents and Similar Triangles", difficulty: "Tricky", emoji: "📏", hint: "Tangent from external point, triangle construction with ratio" },
    ],
    Science: [
      { topic: "Chemical Reactions and Equations", difficulty: "Hard", emoji: "⚗️", hint: "Balancing equations, types of reactions — combination, displacement" },
      { topic: "Acids, Bases and Salts", difficulty: "Tricky", emoji: "🧪", hint: "pH scale, neutralisation, common salts and their uses" },
      { topic: "Life Processes — Nutrition and Respiration", difficulty: "Hard", emoji: "🌱", hint: "Autotrophic vs heterotrophic, aerobic vs anaerobic respiration" },
      { topic: "Electricity — Ohm's Law and Circuits", difficulty: "Hard", emoji: "🔌", hint: "V=IR, series and parallel circuits, power P=VI" },
      { topic: "Magnetic Effects of Current", difficulty: "Hard", emoji: "🧲", hint: "Right-hand thumb rule, motor effect, electromagnetic induction" },
      { topic: "Refraction of Light — Lenses", difficulty: "Hard", emoji: "🔭", hint: "Lens formula 1/v−1/u=1/f, magnification, power of lens" },
      { topic: "Heredity and Evolution — Mendel's Laws", difficulty: "Tricky", emoji: "🧬", hint: "Dominant/recessive traits, Punnett square, natural selection" },
      { topic: "Our Environment — Food Chains", difficulty: "Medium", emoji: "🌿", hint: "Trophic levels, biomagnification, ozone depletion" },
      { topic: "Carbon and Its Compounds", difficulty: "Hard", emoji: "⚛️", hint: "Covalent bonding, functional groups, homologous series, reactions" },
      { topic: "Control and Coordination — Nervous System", difficulty: "Tricky", emoji: "🧠", hint: "Reflex arc, brain parts, hormones and their functions" },
      { topic: "Light — Reflection and Spherical Mirrors", difficulty: "Hard", emoji: "💡", hint: "Mirror formula, sign convention, ray diagrams for concave/convex" },
      { topic: "Sources of Energy — Conventional and New", difficulty: "Medium", emoji: "☀️", hint: "Fossil fuels, solar, wind, nuclear — advantages and limitations" },
    ],
  },
};

const DIFFICULTY_COLORS = {
  Hard:   { bg: "rgba(239,68,68,.1)",   border: "rgba(239,68,68,.3)",   text: "#ef4444",  label: "🔴 Hard" },
  Tricky: { bg: "rgba(245,158,11,.1)", border: "rgba(245,158,11,.3)", text: "#f59e0b", label: "🟡 Tricky" },
  Medium: { bg: "rgba(59,130,246,.1)",  border: "rgba(59,130,246,.3)",  text: "#3b82f6",  label: "🔵 Medium" },
};

const SUBJECT_COLORS = {
  Maths:   { icon: "📐", gradient: "linear-gradient(135deg,#2563eb,#7c3aed)", tag: "Mathematics" },
  Science: { icon: "🔬", gradient: "linear-gradient(135deg,#059669,#0891b2)", tag: "Science" },
};

/** Friendly upgrade prompt shown when a free/promo user clicks a topic card */
function UpgradeCard({ onClose, onUpgrade }) {
  return (
    <div style={{ textAlign: "center", padding: "20px 16px" }}>
      <div style={{ fontSize: "2.4rem", marginBottom: 10 }}>🔐</div>
      <h4 style={{ margin: "0 0 8px", fontSize: "1rem" }}>This feature is for paid subscribers</h4>
      <p style={{ fontSize: ".82rem", color: "var(--muted)", lineHeight: 1.6, marginBottom: 16 }}>
        AI-powered topic explanations, formula breakdowns, and exam tips are available with a paid plan.
        <br />Your current plan does not include this feature.
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <button onClick={onUpgrade}
          style={{ padding: "10px 20px", borderRadius: 9, border: "none", background: "linear-gradient(135deg,#6366f1,#8b5cf6)", color: "#fff", fontWeight: 700, fontSize: ".88rem", cursor: "pointer", fontFamily: "inherit" }}>
          🚀 See Plans & Upgrade
        </button>
        <button onClick={onClose}
          style={{ padding: "8px 16px", borderRadius: 9, border: "1px solid var(--border)", background: "transparent", color: "var(--muted)", fontSize: ".8rem", cursor: "pointer", fontFamily: "inherit" }}>
          Maybe later
        </button>
      </div>
    </div>
  );
}

// Returns true if the user has a paid subscription.
// Teachers and all other roles on a FREE plan are also gated.
// Only admin always bypasses.
function hasPaidAccess(user) {
  if (!user) return false;
  if (user.role === "admin") return true;                              // admin only
  if (user.subscriptionPlan && user.subscriptionPlan !== "free") return true; // paid plan
  if (user.accessCbse) return true;                                    // admin-granted CBSE access
  if (user.parentId) return true;                                      // parent-linked child
  return false;
}

export default function ExemplarResearchPage({ user, setActivePage }) {
  const isTeacher = user?.role === "teacher";
  const userGrade = user?.grade || "Grade 9";
  const paidAccess = hasPaidAccess(user);

  // Grade selector — teachers can view any grade; students see only their own
  const [selectedGrade, setSelectedGrade] = useState(isTeacher ? "Grade 10" : userGrade);
  const [selectedSubject, setSelectedSubject] = useState("Maths");
  const [activeTopic, setActiveTopic] = useState(null);
  const [explanation, setExplanation] = useState("");
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResult, setSearchResult] = useState("");
  const [searchLoading, setSearchLoading] = useState(false);
  const [filterDifficulty, setFilterDifficulty] = useState("All");

  const cards = TOPIC_CARDS[selectedGrade]?.[selectedSubject] || [];
  const filteredCards = filterDifficulty === "All"
    ? cards
    : cards.filter(c => c.difficulty === filterDifficulty);

  async function explainTopic(topic) {
    setActiveTopic(topic);
    setExplanation("");
    if (!paidAccess) return; // gate — upgrade card shown in panel
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/doubt/answer`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${user?.accessToken}`,
        },
        body: JSON.stringify({
          username: user?.username,
          grade: selectedGrade,
          mode: "CBSE",
          board: "CBSE",
          subject: selectedSubject,
          chapter: topic.topic,
          question: `Explain "${topic.topic}" clearly for a CBSE ${selectedGrade} ${selectedSubject} student. Include:
- Simple definition or concept
- Key formula or rule (if any)
- One real-world or solved example
- 2-3 common exam mistakes to avoid
Make it concise, exam-focused and easy to understand.`,
          save_to_history: false,
        }),
      });
      const data = await res.json();
      setExplanation(data.answer || "Could not load explanation.");
    } catch {
      setExplanation("Could not load explanation. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSearch(e) {
    e?.preventDefault();
    if (!searchQuery.trim()) return;
    if (!paidAccess) {
      setSearchResult("__upgrade__");
      return;
    }
    setSearchResult("");
    setSearchLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/doubt/answer`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${user?.accessToken}`,
        },
        body: JSON.stringify({
          username: user?.username,
          grade: selectedGrade,
          mode: "CBSE",
          board: "CBSE",
          subject: selectedSubject,
          chapter: searchQuery,
          question: `Explain "${searchQuery}" for a CBSE ${selectedGrade} ${selectedSubject} student in detail. Include definition, key concept, example, and what to watch out for in exams.`,
          save_to_history: false,
        }),
      });
      const data = await res.json();
      setSearchResult(data.answer || "No explanation found.");
    } catch {
      setSearchResult("Search failed. Please try again.");
    } finally {
      setSearchLoading(false);
    }
  }

  const exemplarHint = EXEMPLAR_HINTS[selectedGrade] || "NCERT Exemplar Books";

  // ── Inline practice questions state ──────────────────────────────────────
  const [practiceQs, setPracticeQs] = useState([]);
  const [practiceLoading, setPracticeLoading] = useState(false);
  const [practiceAnswers, setPracticeAnswers] = useState({});
  const [practiceRevealed, setPracticeRevealed] = useState({});

  async function generatePractice(topic) {
    if (!paidAccess) { setActiveTopic(topic); return; }
    setPracticeQs([]);
    setPracticeAnswers({});
    setPracticeRevealed({});
    setPracticeLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/doubt/answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${user?.accessToken}` },
        body: JSON.stringify({
          username: user?.username,
          grade: selectedGrade,
          mode: "CBSE",
          board: "CBSE",
          subject: selectedSubject,
          chapter: topic.topic,
          question: `Generate exactly 4 NCERT Exemplar-level MCQ practice questions on "${topic.topic}" for CBSE ${selectedGrade} ${selectedSubject}. Each must be a tricky/HOTS question.

IMPORTANT RULES:
- Do NOT use LaTeX, dollar signs, or math notation like $x^2$. Write all math in plain text (e.g. x squared, x^2, or x² using Unicode).
- Each question MUST have a detailed step-by-step explanation showing HOW to arrive at the correct answer.

Respond ONLY with a valid JSON array (no markdown, no extra text):
[{"q":"...","options":["A) ...","B) ...","C) ...","D) ..."],"answer":"A) ...","explanation":"Step-by-step solution: ..."}]`,
          save_to_history: false,
        }),
      });
      const data = await res.json();
      const raw = (data.answer || "").trim();
      const start = raw.indexOf("["), end = raw.lastIndexOf("]");
      if (start !== -1 && end !== -1) {
        try { setPracticeQs(JSON.parse(raw.slice(start, end + 1))); } catch { setPracticeQs([]); }
      }
    } catch { setPracticeQs([]); }
    finally { setPracticeLoading(false); }
  }

  return (
    <div className="premium-page" style={{ maxWidth: 1100 }}>

      {/* ── Header ── */}
      <div style={{ marginBottom: 24 }}>
        <p style={{ fontSize: ".72rem", fontWeight: 700, letterSpacing: ".1em", textTransform: "uppercase", color: "#6366f1", marginBottom: 6 }}>
          NCERT Exemplar · Research Station
        </p>
        <h2 style={{ fontSize: "1.8rem", fontWeight: 900, marginBottom: 6 }}>
          🔬 Science & Maths Deep Dive
        </h2>
        <p style={{ color: "var(--muted)", fontSize: ".9rem", maxWidth: 620 }}>
          Explore difficult and tricky CBSE topics from NCERT Exemplar books.
          Click any card to get an instant AI explanation — formula, example, and exam tips included.
        </p>
      </div>

      {/* ── Controls row ── */}
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center", marginBottom: 20 }}>

        {/* Grade picker — teachers see all, students see their own only */}
        {isTeacher ? (
          <select value={selectedGrade} onChange={e => { setSelectedGrade(e.target.value); setActiveTopic(null); setExplanation(""); }}
            style={{ padding: "8px 12px", borderRadius: 8, border: "1.5px solid var(--border)", background: "var(--card-bg)", color: "var(--text)", fontFamily: "inherit", fontSize: ".85rem" }}>
            {["Grade 8","Grade 9","Grade 10"].map(g => <option key={g}>{g}</option>)}
          </select>
        ) : (
          <span style={{ padding: "8px 14px", borderRadius: 8, background: "rgba(99,102,241,.1)", border: "1px solid rgba(99,102,241,.3)", color: "#a5b4fc", fontSize: ".85rem", fontWeight: 700 }}>
            📚 {selectedGrade}
          </span>
        )}

        {/* Subject tabs */}
        {["Maths","Science"].map(subj => (
          <button key={subj} onClick={() => { setSelectedSubject(subj); setActiveTopic(null); setExplanation(""); setFilterDifficulty("All"); }}
            style={{ padding: "8px 18px", borderRadius: 8, cursor: "pointer", fontFamily: "inherit", fontSize: ".85rem", fontWeight: 700,
              background: selectedSubject === subj ? SUBJECT_COLORS[subj].gradient : "var(--card-bg)",
              color: selectedSubject === subj ? "#fff" : "var(--muted)",
              border: selectedSubject === subj ? "none" : "1.5px solid var(--border)",
            }}>
            {SUBJECT_COLORS[subj].icon} {subj}
          </button>
        ))}

        {/* Difficulty filter */}
        <select value={filterDifficulty} onChange={e => setFilterDifficulty(e.target.value)}
          style={{ padding: "8px 12px", borderRadius: 8, border: "1.5px solid var(--border)", background: "var(--card-bg)", color: "var(--text)", fontFamily: "inherit", fontSize: ".85rem" }}>
          <option value="All">All Difficulty</option>
          <option value="Hard">🔴 Hard Only</option>
          <option value="Tricky">🟡 Tricky Only</option>
          <option value="Medium">🔵 Medium Only</option>
        </select>

        {/* Exemplar link — main NCERT browse page (reliable) */}
        <a href={EXEMPLAR_URL} target="_blank" rel="noreferrer"
          style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "8px 14px", borderRadius: 8,
            background: "rgba(16,185,129,.1)", border: "1px solid rgba(16,185,129,.3)",
            color: "#10b981", fontWeight: 700, fontSize: ".82rem", textDecoration: "none" }}>
          📄 Browse {exemplarHint}
        </a>
      </div>

      {/* ── Search bar ── */}
      <form onSubmit={handleSearch} style={{ display: "flex", gap: 10, marginBottom: 24 }}>
        <input
          placeholder={`Search any ${selectedSubject} topic… e.g. "Ohm's Law" or "Quadratic Formula"`}
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          style={{ flex: 1, padding: "11px 16px", borderRadius: 10, border: "1.5px solid var(--border)", background: "var(--card-bg)", color: "var(--text)", fontFamily: "inherit", fontSize: ".9rem", outline: "none" }}
        />
        <button type="submit" className="primary-btn" disabled={searchLoading || !searchQuery.trim()} style={{ maxWidth: 180 }}>
          {searchLoading ? "Searching…" : "🔍 Explain This"}
        </button>
      </form>

      {/* Search result (or upgrade gate) */}
      {searchResult && searchResult !== "__upgrade__" && (
        <div className="premium-card" style={{ marginBottom: 24, borderLeft: "4px solid #6366f1" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
            <h4 style={{ margin: 0, color: "#6366f1" }}>🔍 Research Result: {searchQuery}</h4>
            <button onClick={() => { setSearchResult(""); setSearchQuery(""); }}
              style={{ background: "none", border: "none", cursor: "pointer", color: "var(--muted)", fontSize: "1.1rem" }}>×</button>
          </div>
          <div className="markdown-content" style={{ fontSize: ".88rem" }}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{searchResult}</ReactMarkdown>
          </div>
        </div>
      )}
      {searchResult === "__upgrade__" && (
        <UpgradeCard onClose={() => { setSearchResult(""); }} onUpgrade={() => setActivePage?.("subscriptionPlans")} />
      )}

      {/* ── Main layout: cards + explanation panel — flex-wrap for mobile ── */}
      <div className="exemplar-layout">

        {/* Topic cards grid */}
        <div className="exemplar-card-panel">
          <p style={{ fontSize: ".75rem", fontWeight: 700, color: "var(--muted)", marginBottom: 12, textTransform: "uppercase", letterSpacing: ".08em" }}>
            {filteredCards.length} topics · click any card to get instant AI explanation
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: 14 }}>
            {filteredCards.map((card, i) => {
              const dc = DIFFICULTY_COLORS[card.difficulty] || DIFFICULTY_COLORS.Medium;
              const isActive = activeTopic?.topic === card.topic;
              return (
                <button key={i} onClick={() => explainTopic(card)}
                  style={{
                    display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 8,
                    padding: "16px 18px", borderRadius: 14, cursor: "pointer", textAlign: "left",
                    border: `2px solid ${isActive ? "#6366f1" : "var(--border)"}`,
                    background: isActive ? "rgba(99,102,241,.08)" : "var(--card-bg)",
                    fontFamily: "inherit", transition: "all .15s",
                    boxShadow: isActive ? "0 0 0 3px rgba(99,102,241,.2)" : "none",
                  }}
                  onMouseEnter={e => { if (!isActive) { e.currentTarget.style.borderColor = "#6366f1"; e.currentTarget.style.transform = "translateY(-2px)"; } }}
                  onMouseLeave={e => { if (!isActive) { e.currentTarget.style.borderColor = "var(--border)"; e.currentTarget.style.transform = "none"; } }}
                >
                  <div style={{ display: "flex", width: "100%", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <span style={{ fontSize: "1.6rem", lineHeight: 1 }}>{card.emoji}</span>
                    <span style={{ fontSize: ".68rem", fontWeight: 700, padding: "3px 8px", borderRadius: 20, background: dc.bg, color: dc.text, border: `1px solid ${dc.border}` }}>
                      {dc.label}
                    </span>
                  </div>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: ".9rem", marginBottom: 4, color: "var(--text)" }}>{card.topic}</div>
                    <div style={{ fontSize: ".75rem", color: "var(--muted)", lineHeight: 1.4 }}>{card.hint}</div>
                  </div>
                  {isActive && <div style={{ fontSize: ".72rem", fontWeight: 700, color: "#6366f1", marginTop: 2 }}>✦ Viewing explanation →</div>}
                </button>
              );
            })}
          </div>
        </div>

        {/* Explanation panel — sticky on desktop, stacks below cards on mobile */}
        {activeTopic && (
          <div className="exemplar-expl-panel">
            <div className="premium-card" style={{ borderLeft: "4px solid #6366f1" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 14 }}>
                <div>
                  <div style={{ fontSize: "1.5rem", marginBottom: 4 }}>{activeTopic.emoji}</div>
                  <h3 style={{ margin: 0, fontSize: "1rem", color: "var(--text)" }}>{activeTopic.topic}</h3>
                  <div style={{ fontSize: ".72rem", color: "var(--muted)", marginTop: 2 }}>{selectedGrade} · {selectedSubject}</div>
                </div>
                <button onClick={() => { setActiveTopic(null); setExplanation(""); }}
                  style={{ background: "none", border: "none", cursor: "pointer", color: "var(--muted)", fontSize: "1.3rem", lineHeight: 1 }}>×</button>
              </div>

              {!paidAccess ? (
                <UpgradeCard onClose={() => setActiveTopic(null)} onUpgrade={() => setActivePage?.("subscriptionPlans")} />
              ) : loading ? (
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10, padding: "24px 0" }}>
                  <div style={{ width: 32, height: 32, border: "3px solid rgba(99,102,241,.2)", borderTopColor: "#6366f1", borderRadius: "50%", animation: "spin 0.9s linear infinite" }} />
                  <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
                  <p style={{ color: "var(--muted)", fontSize: ".82rem" }}>Loading explanation…</p>
                </div>
              ) : explanation ? (
                <>
                  <div className="markdown-content" style={{ fontSize: ".85rem", maxHeight: 480, overflowY: "auto" }}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{explanation}</ReactMarkdown>
                  </div>
                  <div style={{ marginTop: 14, paddingTop: 14, borderTop: "1px solid var(--border)", display: "flex", gap: 8, flexWrap: "wrap" }}>
                    <button
                      onClick={() => generatePractice(activeTopic)}
                      disabled={practiceLoading}
                      style={{ padding: "7px 12px", borderRadius: 8, border: "none", background: "linear-gradient(135deg,#059669,#0891b2)", color: "#fff", fontWeight: 700, fontSize: ".78rem", cursor: "pointer", fontFamily: "inherit" }}>
                      {practiceLoading ? "Generating…" : "🎯 Generate Practice Questions"}
                    </button>
                    <button onClick={() => explainTopic(activeTopic)}
                      style={{ padding: "7px 12px", borderRadius: 8, border: "1px solid rgba(99,102,241,.3)", background: "rgba(99,102,241,.08)", color: "#a5b4fc", fontWeight: 700, fontSize: ".78rem", cursor: "pointer", fontFamily: "inherit" }}>
                      🔄 Refresh
                    </button>
                  </div>

                  {/* ── Inline MCQ practice panel ── */}
                  {practiceLoading && (
                    <div style={{ marginTop: 14, display: "flex", alignItems: "center", gap: 8 }}>
                      <div style={{ width: 18, height: 18, border: "2px solid rgba(16,185,129,.3)", borderTopColor: "#10b981", borderRadius: "50%", animation: "spin 0.9s linear infinite", flexShrink: 0 }} />
                      <span style={{ color: "var(--muted)", fontSize: ".8rem" }}>Generating Exemplar-level practice questions…</span>
                    </div>
                  )}
                  {practiceQs.length > 0 && (
                    <div style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 14 }}>
                      <div style={{ fontSize: ".72rem", fontWeight: 700, color: "#10b981", textTransform: "uppercase", letterSpacing: ".07em" }}>
                        🎯 {practiceQs.length} Practice Questions · {activeTopic.topic}
                      </div>
                      {practiceQs.map((q, qi) => {
                        const selected = practiceAnswers[qi];
                        const revealed = practiceRevealed[qi];
                        return (
                          <div key={qi} style={{ padding: "12px 14px", borderRadius: 10, background: "rgba(16,185,129,.06)", border: "1px solid rgba(16,185,129,.2)" }}>
                            <div style={{ fontWeight: 700, fontSize: ".83rem", marginBottom: 8, color: "var(--text)", lineHeight: 1.4 }}>
                              Q{qi + 1}. {q.q}
                            </div>
                            <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
                              {(q.options || []).map((opt, oi) => {
                                const isCorrect = opt === q.answer;
                                const isSelected = selected === opt;
                                let bg = "transparent", border = "1px solid var(--border)", color = "var(--text)";
                                if (revealed) {
                                  if (isCorrect) { bg = "rgba(16,185,129,.15)"; border = "1px solid #10b981"; color = "#10b981"; }
                                  else if (isSelected && !isCorrect) { bg = "rgba(239,68,68,.1)"; border = "1px solid #ef4444"; color = "#ef4444"; }
                                } else if (isSelected) {
                                  bg = "rgba(99,102,241,.12)"; border = "1px solid #6366f1"; color = "#a5b4fc";
                                }
                                return (
                                  <button key={oi}
                                    onClick={() => { if (!revealed) setPracticeAnswers(p => ({...p, [qi]: opt})); }}
                                    style={{ textAlign: "left", padding: "7px 10px", borderRadius: 7, cursor: revealed ? "default" : "pointer", fontFamily: "inherit", fontSize: ".8rem", background: bg, border, color, transition: "all .12s" }}>
                                    {opt}
                                  </button>
                                );
                              })}
                            </div>
                            {!revealed && selected && (
                              <button
                                onClick={() => setPracticeRevealed(p => ({...p, [qi]: true}))}
                                style={{ marginTop: 8, padding: "5px 12px", borderRadius: 7, border: "none", background: "#10b981", color: "#fff", fontWeight: 700, fontSize: ".76rem", cursor: "pointer", fontFamily: "inherit" }}>
                                Check Answer
                              </button>
                            )}
                            {revealed && (
                              <div style={{ marginTop: 7 }}>
                                <div style={{ fontSize: ".76rem", fontWeight: 700, color: selected === q.answer ? "#10b981" : "#ef4444", marginBottom: q.explanation ? 6 : 0 }}>
                                  {selected === q.answer ? "✅ Correct!" : `❌ Incorrect — correct: ${q.answer}`}
                                </div>
                                {q.explanation && (
                                  <div style={{ padding: "10px 12px", borderRadius: 8, background: "rgba(16,185,129,.06)", border: "1px solid rgba(16,185,129,.2)", fontSize: ".78rem", color: "var(--text)", lineHeight: 1.55 }}>
                                    <strong style={{ color: "#059669", display: "block", marginBottom: 4 }}>💡 Explanation</strong>
                                    {q.explanation}
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                      <button onClick={() => { setPracticeQs([]); setPracticeAnswers({}); setPracticeRevealed({}); }}
                        style={{ alignSelf: "flex-start", padding: "6px 12px", borderRadius: 8, border: "1px solid var(--border)", background: "transparent", color: "var(--muted)", fontSize: ".76rem", cursor: "pointer", fontFamily: "inherit" }}>
                        Clear practice
                      </button>
                    </div>
                  )}
                </>
              ) : null}
            </div>
          </div>
        )}
      </div>

      {/* ── Bottom: tip banner ── */}
      <div style={{ marginTop: 32, padding: "14px 18px", borderRadius: 12, background: "rgba(99,102,241,.06)", border: "1px solid rgba(99,102,241,.2)", display: "flex", gap: 12, alignItems: "flex-start" }}>
        <span style={{ fontSize: "1.4rem", flexShrink: 0 }}>💡</span>
        <div>
          <div style={{ fontWeight: 700, fontSize: ".85rem", marginBottom: 3 }}>How to use this page</div>
          <div style={{ fontSize: ".78rem", color: "var(--muted)", lineHeight: 1.6 }}>
            Click any topic card to get an AI-powered explanation with formula, example, and exam tips. Use the Search bar to research any topic not in the list. Download the Exemplar PDF for practice problems at HOTS (higher-order thinking) level.
          </div>
        </div>
      </div>

    </div>
  );
}
