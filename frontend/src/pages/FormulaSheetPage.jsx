/**
 * FormulaSheetPage.jsx
 * Syllabus-aligned CBSE Formula Sheet with:
 * - KaTeX math rendering (falls back to monospace)
 * - Collapsed/expanded card UX
 * - Freemium: preview only for Free Tier; paid users can expand for examples/tips
 * - Subject + chapter filter + search
 * Data: GET /api/student/formula-sheets?grade=&subject=
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { authFetch } from "../api/authClient";

// ── KaTeX renderer (lazy) ─────────────────────────────────────────────────────
let katex = null;
async function loadKatex() {
  if (!katex) {
    try {
      const mod = await import("katex");
      katex = mod.default || mod;
      // Load KaTeX CSS once
      if (!document.getElementById("katex-css")) {
        const link = document.createElement("link");
        link.id = "katex-css";
        link.rel = "stylesheet";
        link.href = "https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css";
        document.head.appendChild(link);
      }
    } catch { katex = null; }
  }
  return katex;
}

function MathExpr({ tex, display = false }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!tex || !ref.current) return;
    loadKatex().then(k => {
      if (!k || !ref.current) return;
      try {
        k.render(tex, ref.current, { throwOnError: false, displayMode: display, output: "html" });
      } catch { if (ref.current) ref.current.textContent = tex; }
    });
  }, [tex, display]);
  // Show expression text while KaTeX loads
  return (
    <span ref={ref} style={{ fontFamily: "monospace", fontSize: display ? "1rem" : ".95rem" }}>
      {tex}
    </span>
  );
}

// ── Shared UI helpers ─────────────────────────────────────────────────────────
function Badge({ children, bg = "rgba(139,92,246,0.2)", color = "#a78bfa" }) {
  return <span style={{ fontSize: ".65rem", fontWeight: 700, padding: "1px 7px", borderRadius: 10, background: bg, color, display: "inline-block", marginRight: 3 }}>{children}</span>;
}

function CopyBtn({ text }) {
  const [copied, setCopied] = useState(false);
  return (
    <button onClick={() => { navigator.clipboard.writeText(text).catch(() => {}); setCopied(true); setTimeout(() => setCopied(false), 1500); }}
      title="Copy formula"
      style={{ background: "none", border: "1px solid var(--border,#e5e7eb)", borderRadius: 6, padding: "2px 8px", cursor: "pointer", fontSize: ".68rem", color: copied ? "#22c55e" : "#6366f1", fontFamily: "inherit", fontWeight: 600 }}>
      {copied ? "✓" : "Copy"}
    </button>
  );
}

function UpgradePrompt({ msg = "Unlock this content with Premium." }) {
  return (
    <div data-testid="upgrade-lock-prompt" style={{ background: "var(--surface2,#f8fafc)", border: "1px dashed #cbd5e1", borderRadius: 7, padding: "7px 11px", display: "flex", gap: 7, alignItems: "center", marginTop: 6 }}>
      <span>🔒</span>
      <span style={{ fontSize: ".74rem", color: "var(--text-muted,#64748b)", fontStyle: "italic" }}>{msg}</span>
    </div>
  );
}


// ── MCQ Practice component ─────────────────────────────────────────────────
// Generates 4 original MCQs from formula data (rule-based, no LLM call)
// Shows inline with detailed answer explanations — like Exemplar section

function buildMCQs(formula) {
  // Rule-based MCQ generation from formula content
  // Returns up to 4 questions with options and explanations
  var nm = formula.name || "this formula";
  var ex = formula.expression || "";
  var chapter = formula.chapter || "";
  var desc = formula.description || "";
  var examp = formula.example || "";
  // Generic template MCQs for any formula
  return [
    {
      q: "What does the formula " + nm + " calculate?",
      options: [
        desc || ("The value given by " + ex),
        "The perimeter of a shape",
        "The total surface area only",
        "The number of sides",
      ],
      correct: 0,
      explain: (desc || ("This formula computes " + nm)) + ". The expression is: " + ex,
    },
    {
      q: "Which chapter/topic does " + nm + " belong to?",
      options: [
        chapter || "Geometry",
        "Number Systems",
        "Statistics",
        "Linear Equations",
      ],
      correct: 0,
      explain: nm + " is a key formula in the " + (chapter || "Mathematics") + " chapter of CBSE Grade 9.",
    },
    {
      q: examp ? ("Given the example: " + examp + " — which formula was applied?") : ("The expression '" + ex.substring(0,30) + "' represents?"),
      options: [
        nm,
        "Pythagoras Theorem",
        "Mean Formula",
        "Ohm's Law",
      ],
      correct: 0,
      explain: "The expression " + ex + " is the " + nm + (examp ? ". In the example: " + examp : "") + ".",
    },
    {
      q: "When should you use " + nm + "?",
      options: [
        desc ? ("When you need to find: " + desc.substring(0,60)) : ("To apply " + nm + " in a " + chapter + " problem"),
        "Only in electrical circuits",
        "For calculating speed",
        "To find probability of events",
      ],
      correct: 0,
      explain: (desc || ("Use " + nm + " when solving " + chapter + " problems requiring " + ex)) + ".",
    },
  ];
}

function MCQPractice({ formula }) {
  const [open, setOpen] = useState(false);
  const [answers, setAnswers] = useState({});
  const [submitted, setSubmitted] = useState(false);

  var mcqs = buildMCQs(formula);

  function handleSelect(qi, oi) {
    if (submitted) return;
    setAnswers(prev => ({ ...prev, [qi]: oi }));
  }

  function handleSubmit() {
    if (Object.keys(answers).length < mcqs.length) return;
    setSubmitted(true);
  }

  function handleReset() {
    setAnswers({});
    setSubmitted(false);
  }

  return (
    <div style={{ marginTop: 8 }}>
      <button
        data-testid="practice-btn"
        onClick={() => setOpen(o => !o)}
        style={{ padding: "6px 14px", borderRadius: 7, border: "none",
          background: "#6366f1", color: "#fff", fontSize: ".76rem",
          fontWeight: 700, cursor: "pointer", fontFamily: "inherit" }}>
        {open ? "▲ Close Practice" : "📝 Practice ›"}
      </button>

      {open && (
        <div data-testid="mcq-practice-panel"
          style={{ marginTop: 12, background: "var(--surface2,#f8fafc)",
            border: "1px solid var(--border,#e5e7eb)", borderRadius: 10, padding: 14 }}>
          <div style={{ fontWeight: 700, fontSize: ".82rem", marginBottom: 10, color: "#6366f1" }}>
            📝 Practice Questions — {formula.name}
          </div>

          {mcqs.map((q, qi) => (
            <div key={qi} data-testid={"mcq-"+qi}
              style={{ marginBottom: 14, padding: "10px 12px",
                background: "var(--panel,#fff)", borderRadius: 8,
                border: "1px solid var(--border,#e5e7eb)" }}>
              <div style={{ fontWeight: 600, fontSize: ".8rem", marginBottom: 8 }}>
                Q{qi+1}. {q.q}
              </div>
              {q.options.map((opt, oi) => {
                var sel = answers[qi] === oi;
                var correct = oi === q.correct;
                var bg = !submitted ? (sel ? "#ede9fe" : "transparent")
                  : correct ? "#dcfce7" : (sel ? "#fee2e2" : "transparent");
                var border = !submitted ? (sel ? "1.5px solid #6366f1" : "1px solid var(--border,#e5e7eb)")
                  : correct ? "1.5px solid #22c55e" : (sel ? "1.5px solid #ef4444" : "1px solid var(--border,#e5e7eb)");
                return (
                  <div key={oi} onClick={() => handleSelect(qi, oi)}
                    style={{ display: "flex", alignItems: "center", gap: 8,
                      padding: "6px 10px", marginBottom: 5, borderRadius: 7,
                      background: bg, border: border,
                      cursor: submitted ? "default" : "pointer",
                      fontSize: ".77rem" }}>
                    <span style={{ fontWeight: 700, color: sel ? "#6366f1" : "var(--text-muted,#94a3b8)", minWidth: 16 }}>
                      {["A","B","C","D"][oi]}
                    </span>
                    <span>{opt}</span>
                    {submitted && correct && <span style={{ marginLeft: "auto", color: "#22c55e", fontSize: ".75rem" }}>✓ Correct</span>}
                    {submitted && sel && !correct && <span style={{ marginLeft: "auto", color: "#ef4444", fontSize: ".75rem" }}>✗ Wrong</span>}
                  </div>
                );
              })}

              {/* Explanation shown after submit */}
              {submitted && (
                <div data-testid={"mcq-explanation-"+qi}
                  style={{ marginTop: 8, padding: "8px 10px", background: "#f0fdf4",
                    borderRadius: 7, border: "1px solid #bbf7d0", fontSize: ".75rem",
                    lineHeight: 1.5 }}>
                  <span style={{ fontWeight: 700, color: "#16a34a" }}>💡 Explanation: </span>
                  {q.explain}
                </div>
              )}
            </div>
          ))}

          {!submitted ? (
            <button onClick={handleSubmit}
              disabled={Object.keys(answers).length < mcqs.length}
              style={{ padding: "7px 16px", borderRadius: 7, border: "none",
                background: Object.keys(answers).length < mcqs.length ? "#94a3b8" : "#6366f1",
                color: "#fff", fontWeight: 700, fontSize: ".78rem", cursor: Object.keys(answers).length < mcqs.length ? "not-allowed" : "pointer",
                fontFamily: "inherit" }}>
              Submit Answers
            </button>
          ) : (
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{ fontWeight: 700, color: "#22c55e", fontSize: ".82rem" }}>
                Score: {mcqs.filter((_,qi) => answers[qi] === 0).length}/{mcqs.length}
              </div>
              <button onClick={handleReset}
                style={{ padding: "5px 12px", borderRadius: 7, border: "1px solid #6366f1",
                  background: "transparent", color: "#6366f1", fontWeight: 600, fontSize: ".75rem",
                  cursor: "pointer", fontFamily: "inherit" }}>
                Try Again
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}


// ── Curated formula overrides ─────────────────────────────────────────────────
// Hand-crafted, mathematically correct content for specific CBSE formulas.
// Keys are normalised formula names (lowercase, trimmed).
// buildRichContent() checks this map first before generating fallback content.
const FORMULA_OVERRIDES = {
  "remainder theorem": {
    explanation:
      "The Remainder Theorem says: if you divide a polynomial p(x) by a linear expression (x − a), " +
      "the remainder is simply p(a). Instead of doing long polynomial division, just substitute x = a " +
      "into the polynomial and evaluate it. That result is your remainder.",
    variables: [
      { symbol: "p(x)", meaning: "The polynomial being divided" },
      { symbol: "a",    meaning: "The value obtained from the divisor — if divisor is (x − a), substitute x = a; if (x + a), substitute x = −a" },
      { symbol: "p(a)", meaning: "The remainder after dividing p(x) by (x − a)" },
      { symbol: "Note", meaning: "a is NOT always a root. a becomes a root only when p(a) = 0, which is the Factor Theorem." },
    ],
    whenToUse:
      "Use the Remainder Theorem only when the divisor is a linear expression of the form (x − a). " +
      "Examples: (x − 3) → substitute x = 3 | (x + 2) → substitute x = −2 | (x − 7) → substitute x = 7. " +
      "Do NOT use it for quadratic or higher-degree divisors.",
    steps: [
      "Find the value of a from the divisor: if divisor is (x − 2), then a = 2.",
      "Write out p(a) — substitute x = a into every term of the polynomial.",
      "Evaluate: p(2) = 2³ + 2(2) − 5",
      "Simplify step by step: = 8 + 4 − 5",
      "Final answer: Remainder = 7",
    ],
    stepContext: "Example: Find the remainder when p(x) = x³ + 2x − 5 is divided by (x − 2).",
    commonMistakes: [
      "Confusing a with a root — a is the value you substitute, not a root. p(a) = 0 only when the divisor is also a factor.",
      "Forgetting the sign: (x + 2) means (x − (−2)), so substitute x = −2, not x = +2.",
      "Applying the theorem to non-linear divisors like (x² − 1) — the Remainder Theorem only works for linear divisors (x − a).",
    ],
    memoryTip:
      "Look at what is inside the bracket. (x − 5) → plug in 5. (x + 3) → plug in −3. " +
      "The sign flips! Remainder = p(that value).",
    relatedFormulas: ["Factor Theorem", "Polynomial Division", "Synthetic Division", "Zeros of a Polynomial"],
  },

  "factor theorem": {
    explanation:
      "The Factor Theorem is a special case of the Remainder Theorem. " +
      "It states: (x − a) is a factor of p(x) if and only if p(a) = 0. " +
      "In other words, if substituting x = a gives a remainder of zero, then (x − a) divides p(x) exactly.",
    variables: [
      { symbol: "p(x)", meaning: "The polynomial being tested for divisibility" },
      { symbol: "a",    meaning: "The candidate root — comes from the factor (x − a)" },
      { symbol: "p(a) = 0", meaning: "Condition that confirms (x − a) is a factor" },
    ],
    whenToUse:
      "Use the Factor Theorem to check whether (x − a) is a factor of a polynomial, or to find factors. " +
      "Test rational candidates using the Rational Root Theorem first.",
    steps: [
      "Identify the candidate: if testing whether (x − 3) is a factor, set a = 3.",
      "Compute p(a) — substitute x = 3 into the polynomial.",
      "If p(3) = 0, then (x − 3) is a factor.",
      "If p(3) ≠ 0, then (x − 3) is NOT a factor.",
      "Use polynomial division to find the remaining factors.",
    ],
    commonMistakes: [
      "Confusing Factor Theorem with Remainder Theorem — Factor Theorem requires the remainder to be exactly zero.",
      "Forgetting to check p(−a) when the factor is (x + a).",
      "Stopping at one factor — always divide to find all factors.",
    ],
    memoryTip: "Factor Theorem = Remainder Theorem with remainder zero. p(a) = 0 → (x − a) is a factor.",
    relatedFormulas: ["Remainder Theorem", "Polynomial Division", "Zeros of a Polynomial", "Synthetic Division"],
  },

  "heron's formula": {
    explanation:
      "Heron's Formula calculates the area of a triangle when all three side lengths are known, " +
      "without needing the height. First compute the semi-perimeter s, then substitute into the formula.",
    variables: [
      { symbol: "A",    meaning: "Area of the triangle (in square units)" },
      { symbol: "a, b, c", meaning: "The three side lengths of the triangle" },
      { symbol: "s",    meaning: "Semi-perimeter = (a + b + c) / 2" },
    ],
    whenToUse:
      "Use Heron's Formula when all three side lengths are known but the height is not given. " +
      "It works for any type of triangle — scalene, isosceles, or equilateral.",
    steps: [
      "Write down the three sides: a, b, c.",
      "Calculate s (semi-perimeter): s = (a + b + c) / 2",
      "Example: a = 3, b = 4, c = 5 → s = (3 + 4 + 5) / 2 = 6",
      "Substitute into formula: A = √[s(s−a)(s−b)(s−c)]",
      "A = √[6(6−3)(6−4)(6−5)] = √[6 × 3 × 2 × 1] = √36 = 6 cm²",
    ],
    commonMistakes: [
      "Using perimeter instead of semi-perimeter — always divide the perimeter by 2 to get s.",
      "Forgetting to check the triangle inequality — the sides must satisfy a + b > c, b + c > a, a + c > b.",
      "Applying Heron's Formula when height is available — it is simpler to use A = ½ × base × height in that case.",
    ],
    memoryTip: "Semi = half. Heron starts with s (semi-perimeter). Find s first, then substitute.",
    relatedFormulas: ["Area = ½ × base × height", "Perimeter of Triangle = a + b + c", "Pythagorean Theorem"],
  },

  "pythagorean theorem": {
    explanation:
      "In a right-angled triangle, the square of the hypotenuse (the side opposite the right angle) " +
      "equals the sum of the squares of the other two sides. It is written as: c² = a² + b².",
    variables: [
      { symbol: "c", meaning: "Hypotenuse — the side opposite the right angle (always the longest side)" },
      { symbol: "a", meaning: "One leg (the perpendicular side)" },
      { symbol: "b", meaning: "Other leg (the base)" },
    ],
    whenToUse:
      "Use it in right-angled triangles to find a missing side. " +
      "It does NOT apply to non-right triangles — use the Cosine Rule instead.",
    steps: [
      "Identify the hypotenuse (side opposite the right angle) — this is c.",
      "Write: c² = a² + b²",
      "Example: a = 3, b = 4 → c² = 9 + 16 = 25",
      "Take the square root: c = √25 = 5",
      "Answer: hypotenuse = 5 units",
    ],
    commonMistakes: [
      "Treating the longest known side as the hypotenuse without checking for a right angle.",
      "Forgetting to take the square root at the end — c² = 25 does not mean c = 25.",
      "Using it in non-right triangles — always confirm a 90° angle exists first.",
    ],
    memoryTip: "3-4-5 and 5-12-13 are the most common Pythagorean triples. Memorise them to spot right triangles instantly.",
    relatedFormulas: ["Heron's Formula", "Distance Formula", "Cosine Rule", "Trigonometric Ratios"],
  },
};

// ── Subject-aware common mistake generator ────────────────────────────────────
// Returns 3 relevant common mistakes based on subject category.
// Deliberately avoids generic "wrong units" for algebra/pure maths topics.
function getSubjectMistakes(name, subject, chapter) {
  const s = (subject || "").toLowerCase();
  const c = (chapter || "").toLowerCase();
  const n = (name || "").toLowerCase();

  // Algebra / Polynomials
  if (c.includes("polynomial") || c.includes("algebra") || c.includes("factor") || n.includes("theorem")) {
    return [
      `Misreading the sign of a — if the divisor is (x + k), substitute x = −k, not +k.`,
      `Arithmetic error when evaluating the expression — expand one term at a time and add carefully.`,
      `Assuming the result is always a root — it is only a root when the remainder equals zero.`,
    ];
  }

  // Statistics / Probability
  if (c.includes("statistic") || c.includes("probabilit") || n.includes("mean") || n.includes("median") || n.includes("mode")) {
    return [
      `Confusing mean, median, and mode — mean sums all values; median is the middle value; mode is most frequent.`,
      `Forgetting to sort data before finding the median, especially for large datasets.`,
      `Dividing by n instead of (n−1) when computing sample standard deviation.`,
    ];
  }

  // Geometry / Areas / Perimeter
  if (c.includes("area") || c.includes("geometry") || c.includes("circle") || c.includes("triangle") || c.includes("quadrilateral")) {
    return [
      "Confusing area (square units) and perimeter (linear units) — re-read the question carefully.",
      "Forgetting to square the radius when applying area = pi*r^2 — a common slip in circle problems.",
      "Assuming all angles sum to 180 degrees without checking if the shape is a triangle.",
    ];
  }

  // Physics / Science
  if (s.includes("physics") || s.includes("science") || c.includes("motion") || c.includes("force") || c.includes("energy") || c.includes("optics")) {
    return [
      "Not converting to SI units before substituting values — always check metres, kilograms, seconds.",
      "Confusing scalar and vector quantities — speed is scalar, velocity is vector; they are not interchangeable.",
      "Ignoring direction when calculating displacement or force — always specify the sign convention.",
    ];
  }

  // Chemistry
  if (s.includes("chemistry") || c.includes("mole") || c.includes("reaction") || c.includes("atomic")) {
    return [
      "Unbalanced chemical equations — always balance atoms on both sides before calculating moles.",
      "Confusing atomic mass with mass number — use the correct value from the periodic table.",
      "Forgetting to account for the molar ratio when converting between moles and grams.",
    ];
  }

  // Default — generic maths (avoids "wrong units" for pure maths contexts)
  return [
    `Misreading the question — identify exactly what ${name} is being asked to find before substituting.`,
    "Sign error — check every negative value carefully, especially when squaring or taking roots.",
    "Skipping intermediate steps — write each step clearly to avoid arithmetic mistakes under exam pressure.",
  ];
}

// ── buildRichContent — merges overrides + subject fallbacks ───────────────────
// Priority: backend fields > FORMULA_OVERRIDES > subject-aware fallbacks.
function buildRichContent(formula) {
  const name    = (formula.name || "").trim();
  const nameKey = name.toLowerCase();
  const expr    = formula.expression || "";
  const chapter = formula.chapter || "Mathematics";
  const subject = formula.subject || "";

  // Check for a hand-crafted override first
  const override = FORMULA_OVERRIDES[nameKey];

  // ── 1. Explanation ─────────────────────────────────────────────────────────
  const explanation = formula.explanation
    || (override && override.explanation)
    || formula.description
    || `${name} is used in ${chapter}. It gives us a way to calculate a specific quantity by substituting known values into the expression ${expr}.`;

  // ── 2. Variables ───────────────────────────────────────────────────────────
  let variables = [];
  if (Array.isArray(formula.variables_list)) {
    variables = formula.variables_list;
  } else if (override && Array.isArray(override.variables)) {
    variables = override.variables;
  } else if (formula.variables && typeof formula.variables === "string") {
    variables = formula.variables.split(/[,;\n]+/).map(v => {
      const parts = v.split(/\s*=\s*/);
      return parts.length >= 2
        ? { symbol: parts[0].trim(), meaning: parts.slice(1).join("=").trim() }
        : { symbol: v.trim(), meaning: "" };
    }).filter(v => v.symbol);
  }
  if (!variables.length && expr) {
    const symbols = [...new Set((expr.match(/\b[A-Z][a-z]?\b/g) || []))];
    variables = symbols.map(sym => ({ symbol: sym, meaning: `${sym} — see formula definition` }));
  }

  // ── 3. When to use ─────────────────────────────────────────────────────────
  const whenToUse = formula.when_to_use
    || (override && override.whenToUse)
    || formula.use_case
    || formula.description
    || `Use ${name} when you are given the values needed for ${expr} and need to find the result.`;

  // ── 4. Step-by-step example ────────────────────────────────────────────────
  let steps;
  if (Array.isArray(formula.steps)) {
    steps = formula.steps;
  } else if (override && Array.isArray(override.steps)) {
    steps = override.steps;
  } else if (formula.step_by_step && typeof formula.step_by_step === "string") {
    steps = formula.step_by_step.split(/\n+/).filter(Boolean);
  } else if (formula.example) {
    const raw = formula.example;
    const arrowIdx = raw.indexOf("->");
    if (arrowIdx > -1) {
      const given  = raw.slice(0, arrowIdx).trim();
      const result = raw.slice(arrowIdx + 2).trim();
      steps = [
        `Given: ${given}`,
        `Apply formula: ${expr}`,
        `Substitute values: ${given}`,
        `Result: ${result}`,
      ];
    } else {
      steps = [`Apply ${name}: ${expr}`, `Example: ${raw}`];
    }
  } else {
    steps = [
      `Write down the formula: ${expr}`,
      "Identify all given values from the problem.",
      "Substitute each value into the formula.",
      "Simplify step by step.",
      "State the final answer clearly.",
    ];
  }

  // ── 5. Common mistakes ─────────────────────────────────────────────────────
  const commonMistakes = Array.isArray(formula.common_mistakes)
    ? formula.common_mistakes
    : (override && Array.isArray(override.commonMistakes))
      ? override.commonMistakes
      : getSubjectMistakes(name, subject, chapter);

  // ── 6. Memory tip ──────────────────────────────────────────────────────────
  const memoryTip = formula.memory_tip
    || (override && override.memoryTip)
    || `Remember: write out ${name} and its key variables before substituting any values.`;

  // ── 7. Related formulas ────────────────────────────────────────────────────
  const relatedFormulas = Array.isArray(formula.related_formulas)
    ? formula.related_formulas
    : (override && Array.isArray(override.relatedFormulas))
      ? override.relatedFormulas
      : (formula.tags || []).map(t => `See also: ${t}`);

  return { explanation, variables, whenToUse, steps, commonMistakes, memoryTip, relatedFormulas };
}

// ── PremiumExpandedContent — the rich expanded card body ─────────────────────
function PremiumExpandedContent({ formula }) {
  const { explanation, variables, whenToUse, steps, commonMistakes, memoryTip, relatedFormulas } =
    buildRichContent(formula);

  const sectionStyle = { marginBottom: 14 };
  const headingStyle = {
    fontSize: ".72rem", fontWeight: 800, textTransform: "uppercase",
    letterSpacing: ".06em", marginBottom: 6,
  };
  const bodyStyle = { fontSize: ".8rem", lineHeight: 1.6, color: "var(--text,#374151)" };
  const itemStyle = {
    display: "flex", alignItems: "flex-start", gap: 8,
    fontSize: ".79rem", lineHeight: 1.55, color: "var(--text,#374151)",
    marginBottom: 4,
  };

  return (
    <div data-testid="premium-expanded-content"
      style={{ marginTop: 12, borderTop: "1px solid var(--border,#e5e7eb)", paddingTop: 12 }}>

      {/* 1 — Formula explanation */}
      <div style={sectionStyle}>
        <div style={{ ...headingStyle, color: "#6366f1" }}>📖 What this formula means</div>
        <p style={{ ...bodyStyle, margin: 0 }}>{explanation}</p>
      </div>

      {/* 2 — Variables / symbols */}
      {variables.length > 0 && (
        <div style={sectionStyle}>
          <div style={{ ...headingStyle, color: "#0891b2" }}>🔤 Variables & Symbols</div>
          <div style={{
            background: "var(--surface2,#f8fafc)", borderRadius: 8,
            padding: "8px 12px", border: "1px solid var(--border,#e5e7eb)",
          }}>
            {variables.map((v, i) => (
              <div key={i} style={itemStyle}>
                <code style={{
                  minWidth: 30, fontWeight: 700, fontSize: ".82rem",
                  color: "#6366f1", fontFamily: "monospace",
                }}>{v.symbol}</code>
                <span style={{ color: "var(--text-muted,#64748b)", fontSize: ".78rem" }}>=</span>
                <span>{v.meaning}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3 — When to use */}
      <div style={sectionStyle}>
        <div style={{ ...headingStyle, color: "#16a34a" }}>🎯 When to use</div>
        <p style={{ ...bodyStyle, margin: 0 }}>{whenToUse}</p>
      </div>

      {/* 4 — Step-by-step example */}
      <div style={sectionStyle}>
        <div style={{ ...headingStyle, color: "#d97706" }}>✏️ Step-by-step solved example</div>
        <div style={{
          background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 8, padding: "10px 12px",
        }}>
          {steps.map((step, i) => (
            <div key={i} style={{ ...itemStyle, marginBottom: i < steps.length - 1 ? 6 : 0 }}>
              <span style={{
                minWidth: 22, height: 22, borderRadius: "50%",
                background: "#f59e0b", color: "#fff",
                display: "inline-flex", alignItems: "center", justifyContent: "center",
                fontSize: ".68rem", fontWeight: 800, flexShrink: 0, marginTop: 1,
              }}>{i + 1}</span>
              <span style={{ fontSize: ".79rem" }}>{step}</span>
            </div>
          ))}
        </div>
      </div>

      {/* 5 — Common mistakes */}
      <div style={sectionStyle}>
        <div style={{ ...headingStyle, color: "#dc2626" }}>⚠️ Common mistakes</div>
        <div style={{
          background: "#fff1f2", border: "1px solid #fecdd3", borderRadius: 8, padding: "8px 12px",
        }}>
          {commonMistakes.map((m, i) => (
            <div key={i} style={{ ...itemStyle, marginBottom: i < commonMistakes.length - 1 ? 5 : 0 }}>
              <span style={{ color: "#dc2626", flexShrink: 0, marginTop: 2 }}>✗</span>
              <span style={{ fontSize: ".79rem" }}>{m}</span>
            </div>
          ))}
        </div>
      </div>

      {/* 6 — Memory tip */}
      <div style={{
        ...sectionStyle,
        background: "#fefce8", borderRadius: 8,
        border: "1px solid #fde68a", padding: "8px 12px",
      }}>
        <div style={{ ...headingStyle, color: "#d97706", marginBottom: 4 }}>💡 Quick memory tip</div>
        <p style={{ ...bodyStyle, margin: 0, fontSize: ".79rem", fontStyle: "italic" }}>{memoryTip}</p>
      </div>

      {/* 7 — Related formulas */}
      {relatedFormulas.length > 0 && (
        <div style={sectionStyle}>
          <div style={{ ...headingStyle, color: "#7c3aed" }}>🔗 Related formulas</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {relatedFormulas.map((r, i) => (
              <span key={i} style={{
                fontSize: ".75rem", padding: "3px 10px", borderRadius: 20,
                background: "rgba(124,58,237,0.08)", border: "1px solid rgba(124,58,237,0.2)",
                color: "#7c3aed", fontWeight: 500,
              }}>{r}</span>
            ))}
          </div>
        </div>
      )}

      {/* 8 — Practice CTA */}
      <MCQPractice formula={formula} />
    </div>
  );
}

// ── Formula Upgrade Modal — matches Exemplar Research upgrade card ────────────
function FormulaUpgradeModal({ formula, onClose, onUpgrade }) {
  return (
    <div
      data-testid="formula-upgrade-modal"
      onClick={onClose}
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.5)", zIndex: 600,
        display: "flex", alignItems: "center", justifyContent: "center", padding: 16 }}>
      <div onClick={e => e.stopPropagation()}
        style={{ background: "var(--panel,#fff)", borderRadius: 14, padding: "24px 20px",
          width: "100%", maxWidth: 380, boxShadow: "0 8px 40px rgba(0,0,0,.3)",
          borderTop: "4px solid #6366f1", position: "relative", textAlign: "center" }}>
        {/* Close */}
        <button onClick={onClose}
          style={{ position: "absolute", top: 12, right: 14, background: "none",
            border: "none", cursor: "pointer", fontSize: "1.1rem", color: "var(--text-muted,#94a3b8)" }}>
          ×
        </button>

        {/* Icon */}
        <div style={{ fontSize: "2.4rem", marginBottom: 8 }}>🔐</div>

        {/* Title + context */}
        {formula && (
          <div style={{ fontSize: ".82rem", color: "var(--text-muted,#64748b)", marginBottom: 6 }}>
            <strong style={{ color: "var(--text,#1e293b)", fontSize: ".92rem" }}>{formula.name}</strong>
            <br />{formula.chapter}
          </div>
        )}

        <h4 style={{ margin: "8px 0", fontSize: "1rem", fontWeight: 800 }}>
          This feature is for paid subscribers
        </h4>
        <p style={{ fontSize: ".82rem", color: "var(--text-muted,#64748b)", lineHeight: 1.6, marginBottom: 18 }}>
          Solved examples, step-by-step solutions, memory tips, and practice MCQs
          are available with a paid plan.
          <br />Your current plan does not include this feature.
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <button onClick={onUpgrade}
            style={{ padding: "11px 20px", borderRadius: 9, border: "none",
              background: "linear-gradient(135deg,#6366f1,#8b5cf6)", color: "#fff",
              fontWeight: 700, fontSize: ".88rem", cursor: "pointer", fontFamily: "inherit" }}>
            🚀 See Plans & Upgrade
          </button>
          <button onClick={onClose}
            style={{ padding: "8px 16px", borderRadius: 9, border: "1px solid var(--border,#e5e7eb)",
              background: "transparent", color: "var(--text-muted,#64748b)",
              fontSize: ".8rem", cursor: "pointer", fontFamily: "inherit" }}>
            Maybe later
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Formula Card ─────────────────────────────────────────────────────────────
function FormulaCard({ formula, hasPremium, onUpgrade }) {
  const [expanded, setExpanded] = useState(false);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);

  const canExpand = hasPremium && formula.preview_allowed && !formula.locked;

  function handleExpand() {
    if (!canExpand) {
      setShowUpgradeModal(true);
      return;
    }
    setExpanded(e => !e);
  }

  const diffColor = formula.difficulty === "easy" ? "#4ade80" : formula.difficulty === "hard" ? "#f87171" : "#a78bfa";
  const diffBg   = "rgba(0,0,0,0.15)";

  return (
    <div data-testid="formula-card"
      style={{ background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 10, padding: "12px 14px", borderLeft: `3px solid ${formula.locked ? "#94a3b8" : "#6366f1"}`, opacity: formula.locked ? 0.8 : 1 }}>

      {/* Card header — always visible */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: ".82rem", marginBottom: 3 }}>
            {formula.locked && <span style={{ color: "#94a3b8" }}>🔒 </span>}
            {formula.name}
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 3, marginBottom: 4 }}>
            {formula.difficulty && <Badge bg={diffBg} color={diffColor}>{formula.difficulty}</Badge>}
            {formula.chapter && <Badge bg="rgba(74,222,128,0.15)" color="#4ade80">{formula.chapter}</Badge>}
            {(formula.tags || []).map(t => <Badge key={t}>{t}</Badge>)}
          </div>
        </div>
        {formula.preview_allowed && !formula.locked && <CopyBtn text={formula.expression} />}
      </div>

      {/* Expression — visible for preview formulas, blurred for fully locked */}
      {formula.preview_allowed ? (
        <div data-testid="formula-expression"
          style={{ fontFamily: "monospace", fontSize: ".93rem", fontWeight: 600, background: "var(--surface2,#f8fafc)", padding: "6px 10px", borderRadius: 6, marginBottom: 6, userSelect: "all" }}>
          <MathExpr tex={formula.expression_latex || formula.expression} />
        </div>
      ) : (
        <div style={{ fontFamily: "monospace", fontSize: ".88rem", background: "#f1f5f9", padding: "5px 10px", borderRadius: 6, marginBottom: 6, filter: "blur(4px)", userSelect: "none", pointerEvents: "none" }}>
          {formula.expression?.substring(0, 10)}•••
        </div>
      )}

      {/* Short description — preview */}
      {formula.preview_allowed && formula.description && (
        <div style={{ fontSize: ".77rem", color: "var(--text-muted,#64748b)", marginBottom: 4, lineHeight: 1.4 }}>{formula.description}</div>
      )}

      {/* Expand / collapse button */}
      {formula.preview_allowed && (
        <button
          data-testid={canExpand ? "expand-btn" : "expand-locked-btn"}
          onClick={handleExpand}
          style={{ background: "none", border: "none", color: canExpand ? "#6366f1" : "#94a3b8", fontSize: ".72rem", fontWeight: 600, cursor: "pointer", fontFamily: "inherit", padding: 0, marginBottom: 2 }}>
          {expanded ? "▲ Collapse" : (canExpand ? "▼ Show details" : "🔒 Upgrade to expand")}
        </button>
      )}

      {/* Expanded content — premium rich view */}
      {expanded && canExpand && (
        <PremiumExpandedContent formula={formula} />
      )}

      {/* Locked upgrade inline prompt */}
      {formula.locked && <UpgradePrompt msg="Upgrade to unlock this formula with examples and memory tips." />}
      {showUpgradeModal && (
        <FormulaUpgradeModal formula={formula} onClose={() => setShowUpgradeModal(false)} onUpgrade={() => { setShowUpgradeModal(false); if (onUpgrade) onUpgrade(); }} />
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function FormulaSheetPage({ user, setActivePage }) {
  const grade = user?.grade || "Grade 9";
  const [subject, setSubject]         = useState("Mathematics");
  const [data, setData]               = useState(null);
  const [loading, setLoading]         = useState(false);
  const [err, setErr]                 = useState(null);
  const [search, setSearch]           = useState("");
  const [activeChapter, setActiveChapter] = useState(null);

  const hasPremium = !!(data?.has_premium);

  const load = useCallback(async () => {
    setLoading(true); setErr(null); setActiveChapter(null);
    try {
      const params = new URLSearchParams({ grade, subject });
      const res = await authFetch(`/api/student/formula-sheets?${params}`);
      setData(res);
      if (res?.chapters?.length > 0) setActiveChapter(res.chapters[0].chapter_id);
    } catch { setErr("Could not load formula sheets. Please try again."); }
    finally { setLoading(false); }
  }, [grade, subject]);

  useEffect(() => { load(); }, [load]);

  function nav(page) { if (setActivePage) setActivePage(page); }
  function handleUpgrade() { nav("subscriptionPlans"); }

  // Filter formulas by search
  function getFiltered() {
    if (!data?.chapters) return [];
    const q = search.toLowerCase().trim();
    if (!q) return data.chapters;
    return data.chapters.map(ch => ({
      ...ch,
      topics: ch.topics.map(t => ({
        ...t,
        formulas: t.formulas.filter(f =>
          f.name.toLowerCase().includes(q) ||
          f.expression?.toLowerCase().includes(q) ||
          (f.description || "").toLowerCase().includes(q) ||
          ch.chapter_name.toLowerCase().includes(q)
        ),
      })).filter(t => t.formulas.length > 0),
    })).filter(ch => ch.topics.length > 0);
  }

  const filteredChapters = getFiltered();
  const displayed = search ? filteredChapters : filteredChapters.filter(ch => ch.chapter_id === activeChapter);

  return (
    <div data-testid="formula-sheet-page" style={{ maxWidth: 1100, margin: "0 auto", padding: "0 0 60px" }}>

      {/* Header */}
      <div style={{ marginBottom: 14 }}>
        <h2 style={{ fontWeight: 800, fontSize: "1.15rem", margin: "0 0 3px" }}>📐 Formula Sheet</h2>
        <div style={{ fontSize: ".85rem", color: "var(--text-muted,#64748b)" }}>
          {grade} · CBSE Reference
          {data && (
            <span style={{ marginLeft: 10, fontWeight: 600, color: hasPremium ? "#22c55e" : "#f59e0b", fontSize: ".77rem" }}>
              {hasPremium ? `✓ ${data.total_count} formulas unlocked` : `🔒 ${data.unlocked_count} of ${data.total_count} preview`}
            </span>
          )}
        </div>
      </div>

      {/* Subject selector */}
      <div style={{ display: "flex", gap: 7, marginBottom: 12, flexWrap: "wrap" }}>
        {(data?.subjects || ["Mathematics","Science","Physics","Chemistry"]).map(s => (
          <button key={s} data-testid={"fs-subject-"+s.toLowerCase().replace(/ /g,"-")}
            onClick={() => setSubject(s)}
            style={{ padding: "6px 16px", borderRadius: 20, border: "none",
              background: subject===s ? "#6366f1" : "var(--surface2,#f1f5f9)",
              color: subject===s ? "#fff" : "var(--text,#374151)",
              fontWeight: 600, fontSize: ".82rem", cursor: "pointer", fontFamily: "inherit" }}>
            {s}
          </button>
        ))}
      </div>

      {/* Search */}
      <input data-testid="formula-search" placeholder="Search formulas, chapters..." value={search}
        onChange={e => setSearch(e.target.value)}
        style={{ width: "100%", padding: "8px 14px", borderRadius: 8, border: "1px solid var(--border,#e5e7eb)",
          fontFamily: "inherit", fontSize: ".85rem", boxSizing: "border-box", marginBottom: 12 }}/>

      {/* Upgrade banner for free users */}
      {!loading && data && data.available && !hasPremium && (
        <div data-testid="upgrade-banner"
          style={{ background: "linear-gradient(135deg,#6366f1 0%,#818cf8 100%)", color: "#fff",
            borderRadius: 10, padding: "10px 16px", marginBottom: 12,
            display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: ".88rem" }}>Unlock Full Formula Library</div>
            <div style={{ fontSize: ".75rem", opacity: .9 }}>
              You have {data.unlocked_count} preview formulas. Upgrade to unlock all {data.total_count} with examples and memory tips.
            </div>
          </div>
          <button data-testid="upgrade-cta" onClick={handleUpgrade}
            style={{ background: "#fff", color: "#6366f1", border: "none", borderRadius: 8,
              padding: "7px 16px", fontWeight: 700, fontSize: ".8rem", cursor: "pointer",
              fontFamily: "inherit", whiteSpace: "nowrap" }}>
            Upgrade
          </button>
        </div>
      )}

      {/* Loading */}
      {loading && <div style={{ textAlign: "center", padding: 40, color: "var(--text-muted,#94a3b8)" }}>Loading...</div>}

      {/* Error */}
      {!loading && err && (
        <div style={{ padding: 20, color: "#dc2626" }}>{err}
          <button onClick={load} style={{ color: "#6366f1", background: "none", border: "none", cursor: "pointer", fontFamily: "inherit", fontWeight: 600, marginLeft: 8 }}>Retry</button>
        </div>
      )}

      {/* Unavailable */}
      {!loading && !err && data && !data.available && (
        <div data-testid="formula-sheet-unavailable"
          style={{ background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 12, padding: 32, textAlign: "center" }}>
          <div style={{ fontSize: "2rem", marginBottom: 8 }}>📋</div>
          <div style={{ fontWeight: 700, fontSize: ".95rem", marginBottom: 6 }}>{data.message}</div>
          <div style={{ fontSize: ".82rem", color: "var(--text-muted,#64748b)" }}>Formula content is being added. Check back soon.</div>
        </div>
      )}

      {/* Main layout */}
      {!loading && !err && data && data.available && (
        <div data-testid="formula-sheet-content" style={{ display: "flex", gap: 16, alignItems: "flex-start", flexWrap: "wrap" }}>

          {/* Chapter sidebar */}
          {!search && (
            <div data-testid="chapter-sidebar" style={{ width: 190, flexShrink: 0, minWidth: 140 }}>
              <div style={{ fontWeight: 700, fontSize: ".7rem", color: "var(--text-muted,#94a3b8)", textTransform: "uppercase", letterSpacing: ".05em", marginBottom: 8 }}>Chapters</div>
              {data.chapters.map(ch => (
                <button key={ch.chapter_id} data-testid={"chapter-btn-"+ch.chapter_id}
                  onClick={() => setActiveChapter(ch.chapter_id)}
                  style={{ display: "block", width: "100%", textAlign: "left", padding: "6px 10px",
                    borderRadius: 7, border: "none", marginBottom: 3, cursor: "pointer",
                    fontFamily: "inherit",
                    fontWeight: activeChapter===ch.chapter_id ? 700 : 400,
                    fontSize: ".77rem",
                    background: activeChapter===ch.chapter_id ? "#6366f1" : "var(--surface2,#f1f5f9)",
                    color: activeChapter===ch.chapter_id ? "#fff" : "var(--text,#374151)" }}>
                  {ch.chapter_name}
                  {ch.locked && <span style={{ marginLeft: 4, fontSize: ".62rem", opacity: .7 }}>🔒</span>}
                  <span style={{ float: "right", fontSize: ".62rem", opacity: .55 }}>{ch.unlocked_count}/{ch.total_formulas}</span>
                </button>
              ))}
            </div>
          )}

          {/* Formula cards */}
          <div style={{ flex: 1, minWidth: 0 }}>
            {displayed.length === 0 ? (
              <div style={{ color: "var(--text-muted,#94a3b8)", padding: 20 }}>
                {search ? "No formulas match your search." : "Select a chapter to view formulas."}
              </div>
            ) : displayed.map(ch => (
              <div key={ch.chapter_id} style={{ marginBottom: 24 }}>
                <div style={{ fontWeight: 700, fontSize: ".88rem", color: "#6366f1",
                  borderBottom: "2px solid #e0e7ff", paddingBottom: 6, marginBottom: 12 }}>
                  {ch.chapter_name}
                  {!hasPremium && ch.total_formulas > ch.unlocked_count && (
                    <span style={{ marginLeft: 8, fontSize: ".7rem", color: "#f59e0b" }}>
                      ({ch.unlocked_count} of {ch.total_formulas} shown)
                    </span>
                  )}
                </div>
                {ch.topics.map(t => (
                  <div key={t.topic_name} style={{ marginBottom: 14 }}>
                    {t.topic_name !== "General" && (
                      <div style={{ fontSize: ".7rem", fontWeight: 600, color: "var(--text-muted,#94a3b8)",
                        textTransform: "uppercase", letterSpacing: ".04em", marginBottom: 8 }}>{t.topic_name}</div>
                    )}
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(270px,1fr))", gap: 10 }}>
                      {t.formulas.map(f => (
                        <FormulaCard key={f.id || f.name} formula={f} hasPremium={hasPremium}
                          onUpgrade={handleUpgrade} />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
