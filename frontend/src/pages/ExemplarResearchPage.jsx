import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { answerDoubt } from "../api/doubt";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// ── NCERT Exemplar PDF links ──────────────────────────────────────────────────
const EXEMPLAR_PDFS = {
  "Grade 8": {
    Maths:   "https://ncert.nic.in/pdf/publication/exemplarproblem/classviii/mathematics/gemh1dd.pdf",
    Science: "https://ncert.nic.in/pdf/publication/exemplarproblem/classviii/science/gesc1dd.pdf",
  },
  "Grade 9": {
    Maths:   "https://ncert.nic.in/pdf/publication/exemplarproblem/classix/mathematics/gemh1dd.pdf",
    Science: "https://ncert.nic.in/pdf/publication/exemplarproblem/classix/science/gesc1dd.pdf",
  },
  "Grade 10": {
    Maths:   "https://ncert.nic.in/pdf/publication/exemplarproblem/classx/mathematics/gemh1dd.pdf",
    Science: "https://ncert.nic.in/pdf/publication/exemplarproblem/classx/science/gesc1dd.pdf",
  },
};

// ── Curated topic cards by grade / subject ────────────────────────────────────
const TOPIC_CARDS = {
  "Grade 8": {
    Maths: [
      { topic: "Rational Numbers on Number Line", difficulty: "Tricky", emoji: "🔢", hint: "Plotting fractions and decimals between integers" },
      { topic: "Squares and Square Roots", difficulty: "Hard", emoji: "√", hint: "Long division method and patterns in perfect squares" },
      { topic: "Cubes and Cube Roots", difficulty: "Hard", emoji: "³√", hint: "Prime factorisation and cube root tricks" },
      { topic: "Algebraic Expressions and Identities", difficulty: "Tricky", emoji: "📐", hint: "(a+b)² = a²+2ab+b² and other key identities" },
      { topic: "Mensuration — Area and Volume", difficulty: "Hard", emoji: "📦", hint: "Surface area of cubes, cuboids, and cylinders" },
      { topic: "Linear Equations in One Variable", difficulty: "Tricky", emoji: "x", hint: "Word problems involving equations" },
      { topic: "Comparing Quantities — Percentage, Profit Loss", difficulty: "Tricky", emoji: "💹", hint: "Simple interest and compound interest" },
      { topic: "Data Handling — Bar Graphs and Probability", difficulty: "Medium", emoji: "📊", hint: "Reading data and computing simple probability" },
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
    ],
  },
  "Grade 10": {
    Maths: [
      { topic: "Real Numbers — Euclid's Algorithm & HCF", difficulty: "Hard", emoji: "🔢", hint: "Division algorithm, HCF via Euclid, prime factorisation" },
      { topic: "Polynomials — Relationship of Zeroes", difficulty: "Hard", emoji: "📉", hint: "Sum and product of zeroes, quadratic and cubic polynomials" },
      { topic: "Quadratic Equations — Discriminant", difficulty: "Hard", emoji: "b²-4ac", hint: "D>0 two roots, D=0 equal roots, D<0 no real roots" },
      { topic: "Arithmetic Progressions — nth Term", difficulty: "Tricky", emoji: "…", hint: "a_n = a+(n-1)d, sum S_n = n/2(2a+(n-1)d)" },
      { topic: "Triangles — Similarity and Pythagoras", difficulty: "Hard", emoji: "△", hint: "BPT theorem, AA, SAS, SSS similarity criteria" },
      { topic: "Coordinate Geometry — Section Formula", difficulty: "Tricky", emoji: "📍", hint: "Distance, section, midpoint formulas and area of triangle" },
      { topic: "Introduction to Trigonometry", difficulty: "Hard", emoji: "sin/cos", hint: "sin²θ+cos²θ=1, ratios in right triangles, values at 30/45/60°" },
      { topic: "Areas Related to Circles", difficulty: "Tricky", emoji: "⭕", hint: "Sector area, arc length, segment area — mixed problems" },
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

export default function ExemplarResearchPage({ user }) {
  const isTeacher = user?.role === "teacher";
  const userGrade = user?.grade || "Grade 9";

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

  const exemplarLinks = EXEMPLAR_PDFS[selectedGrade] || {};

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

        {/* Exemplar PDF links */}
        {exemplarLinks[selectedSubject] && (
          <a href={exemplarLinks[selectedSubject]} target="_blank" rel="noreferrer"
            style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "8px 14px", borderRadius: 8,
              background: "rgba(16,185,129,.1)", border: "1px solid rgba(16,185,129,.3)",
              color: "#10b981", fontWeight: 700, fontSize: ".82rem", textDecoration: "none" }}>
            📄 Open Exemplar Book PDF
          </a>
        )}
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

      {/* Search result */}
      {searchResult && (
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

      {/* ── Main layout: cards + explanation panel ── */}
      <div style={{ display: "grid", gridTemplateColumns: activeTopic ? "1fr 420px" : "1fr", gap: 20, alignItems: "flex-start" }}>

        {/* Topic cards grid */}
        <div>
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

        {/* Explanation panel */}
        {activeTopic && (
          <div style={{ position: "sticky", top: 80 }}>
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

              {loading ? (
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
                    {exemplarLinks[selectedSubject] && (
                      <a href={exemplarLinks[selectedSubject]} target="_blank" rel="noreferrer"
                        style={{ display: "inline-flex", alignItems: "center", gap: 5, padding: "7px 12px", borderRadius: 8,
                          background: "rgba(16,185,129,.1)", border: "1px solid rgba(16,185,129,.3)",
                          color: "#10b981", fontWeight: 700, fontSize: ".78rem", textDecoration: "none" }}>
                        📄 Practice in Exemplar
                      </a>
                    )}
                    <button onClick={() => explainTopic(activeTopic)}
                      style={{ padding: "7px 12px", borderRadius: 8, border: "1px solid rgba(99,102,241,.3)", background: "rgba(99,102,241,.08)", color: "#a5b4fc", fontWeight: 700, fontSize: ".78rem", cursor: "pointer", fontFamily: "inherit" }}>
                      🔄 Refresh
                    </button>
                  </div>
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
