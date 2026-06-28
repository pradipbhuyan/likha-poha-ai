/**
 * FormulaSheetPage.jsx
 * Grade-based formula reference page for students.
 * Data from GET /api/student/formula-sheets?grade=&subject=
 * Empty state: "Formula sheet is not available for this grade yet."
 */
import { useEffect, useState, useCallback } from "react";
import { authFetch } from "../api/authClient";

const SUBJECTS = ["Mathematics", "Science"];

export default function FormulaSheetPage({ user }) {
  const grade = user?.grade || "Grade 9";
  const [subject, setSubject] = useState("Mathematics");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);

  const load = useCallback(async function () {
    setLoading(true);
    setErr(null);
    try {
      var params = new URLSearchParams({ grade, subject });
      var res = await authFetch(`/api/student/formula-sheets?${params}`);
      setData(res);
    } catch (e) {
      setErr("Could not load formula sheets. Please try again.");
    } finally {
      setLoading(false);
    }
  }, [grade, subject]);

  useEffect(function () { load(); }, [load]);

  return (
    <div data-testid="formula-sheet-page" style={{ maxWidth: 860, margin: "0 auto", padding: "0 0 60px" }}>
      {/* Header */}
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontWeight: 800, fontSize: "1.2rem", margin: "0 0 4px" }}>📐 Formula Sheet</h2>
        <div style={{ fontSize: ".85rem", color: "var(--text-muted,#64748b)" }}>
          {grade} · CBSE Reference Formulas
        </div>
      </div>

      {/* Subject filter */}
      <div style={{ display: "flex", gap: 8, marginBottom: 20, flexWrap: "wrap" }}>
        {SUBJECTS.map(function (s) {
          return (
            <button
              key={s}
              data-testid={`fs-subject-${s.toLowerCase()}`}
              onClick={function () { setSubject(s); }}
              style={{
                padding: "6px 16px", borderRadius: 20, border: "none",
                background: subject === s ? "#6366f1" : "var(--surface2,#f1f5f9)",
                color: subject === s ? "#fff" : "var(--text,#374151)",
                fontWeight: 600, fontSize: ".82rem", cursor: "pointer", fontFamily: "inherit",
              }}
            >{s}</button>
          );
        })}
      </div>

      {/* Loading */}
      {loading && (
        <div style={{ textAlign: "center", padding: 40, color: "var(--text-muted,#94a3b8)" }}>
          Loading formula sheets…
        </div>
      )}

      {/* Error */}
      {!loading && err && (
        <div style={{ padding: 20, color: "#dc2626" }}>
          {err} <button onClick={load} style={{ color: "#6366f1", background: "none", border: "none", cursor: "pointer", fontFamily: "inherit", fontWeight: 600 }}>Retry</button>
        </div>
      )}

      {/* Not available */}
      {!loading && !err && data && !data.available && (
        <div
          data-testid="formula-sheet-unavailable"
          style={{ background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 12, padding: 32, textAlign: "center" }}
        >
          <div style={{ fontSize: "2rem", marginBottom: 8 }}>📋</div>
          <div style={{ fontWeight: 700, fontSize: ".95rem", marginBottom: 6 }}>
            {data.message || `Formula sheet is not available for ${grade} yet.`}
          </div>
          <div style={{ fontSize: ".82rem", color: "var(--text-muted,#64748b)" }}>
            Formula content is added by our team regularly. Check back soon.
          </div>
        </div>
      )}

      {/* Formula sections */}
      {!loading && !err && data && data.available && (
        <div data-testid="formula-sheet-content">
          {data.sections.length === 0 ? (
            <div style={{ color: "var(--text-muted,#94a3b8)", padding: 20 }}>
              No formulas found for {subject} — {grade}.
            </div>
          ) : (
            data.sections.map(function (section) {
              return (
                <div key={section.title} style={{ marginBottom: 24 }}>
                  {/* Section heading */}
                  <div style={{
                    fontWeight: 700, fontSize: ".8rem", color: "#6366f1",
                    textTransform: "uppercase", letterSpacing: ".06em",
                    borderBottom: "2px solid #e0e7ff", paddingBottom: 6, marginBottom: 12,
                  }}>
                    {section.title}
                  </div>

                  {/* Formula cards */}
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 12 }}>
                    {section.formulas.map(function (f, i) {
                      return (
                        <div
                          key={i}
                          data-testid="formula-card"
                          style={{
                            background: "var(--panel,#fff)",
                            border: "1px solid var(--border,#e5e7eb)",
                            borderRadius: 10,
                            padding: "14px 16px",
                            borderLeft: "3px solid #6366f1",
                          }}
                        >
                          <div style={{ fontWeight: 700, fontSize: ".82rem", marginBottom: 6 }}>{f.name}</div>
                          <div style={{
                            fontFamily: "monospace", fontSize: ".95rem", fontWeight: 600,
                            color: "#1e293b", background: "var(--surface2,#f8fafc)",
                            padding: "6px 10px", borderRadius: 6, marginBottom: 8,
                            letterSpacing: ".01em",
                          }}>
                            {f.expression}
                          </div>
                          {f.explanation && (
                            <div style={{ fontSize: ".78rem", color: "var(--text-muted,#64748b)", marginBottom: f.example ? 4 : 0 }}>
                              {f.explanation}
                            </div>
                          )}
                          {f.example && (
                            <div style={{ fontSize: ".74rem", color: "#059669", fontStyle: "italic" }}>
                              eg: {f.example}
                            </div>
                          )}
                          {f.chapter && (
                            <div style={{ marginTop: 6 }}>
                              <span style={{ fontSize: ".65rem", background: "#ede9fe", color: "#7c3aed", padding: "1px 7px", borderRadius: 8, fontWeight: 600 }}>
                                {f.chapter}
                              </span>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
