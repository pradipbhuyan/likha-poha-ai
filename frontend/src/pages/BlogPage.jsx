import { useState } from "react";
import { getAllPosts, formatDate } from "../blog/blogUtils";
import logoImg from "../assets/AITutorLogo1.png";

export default function BlogPage({ onShowLogin, onShowSignup, onViewPost }) {
  const posts = getAllPosts();
  const [selectedTag, setSelectedTag] = useState("");

  // Collect all unique tags
  const allTags = [...new Set(posts.flatMap(p => p.tags))].sort();

  const filtered = selectedTag
    ? posts.filter(p => p.tags.includes(selectedTag))
    : posts;

  return (
    <div style={{ fontFamily: "-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif", background: "#0f172a", color: "#f8fafc", minHeight: "100vh" }}>

      {/* Nav */}
      <nav style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 40px", borderBottom: "1px solid rgba(255,255,255,.06)", background: "rgba(15,23,42,.97)", backdropFilter: "blur(12px)", position: "sticky", top: 0, zIndex: 99 }}>
        <a href="/" style={{ display: "flex", alignItems: "center", gap: 10, textDecoration: "none", color: "#f8fafc", fontWeight: 700, fontSize: "1.1rem" }}>
          <img src={logoImg} alt="LikhaPoha AI" style={{ width: 36, height: 36, borderRadius: 9, objectFit: "cover", background: "#fff" }} />
          LikhaPoha AI
        </a>
        <div style={{ display: "flex", gap: 10 }}>
          <button onClick={onShowLogin}
            style={{ background: "transparent", border: "1px solid #334155", color: "#93c5fd", padding: "7px 16px", borderRadius: 8, fontSize: ".85rem", cursor: "pointer", fontFamily: "inherit" }}>
            Login
          </button>
          <button onClick={() => onShowSignup?.("free")}
            style={{ background: "linear-gradient(135deg,#2563eb,#7c3aed)", border: "none", color: "#fff", padding: "7px 16px", borderRadius: 8, fontSize: ".85rem", fontWeight: 700, cursor: "pointer", fontFamily: "inherit" }}>
            Try Today
          </button>
        </div>
      </nav>

      {/* Header */}
      <div style={{ textAlign: "center", padding: "56px 24px 32px" }}>
        <p style={{ fontSize: ".78rem", fontWeight: 700, letterSpacing: ".12em", textTransform: "uppercase", color: "#6366f1", marginBottom: 12 }}>Learning Resources</p>
        <h1 style={{ fontSize: "clamp(2rem,5vw,3rem)", fontWeight: 900, margin: "0 0 14px" }}>
          The LikhaPoha Blog
        </h1>
        <p style={{ color: "#94a3b8", fontSize: "1.05rem", maxWidth: 560, margin: "0 auto" }}>
          CBSE study tips, exam strategies, and insights for students and parents.
        </p>
      </div>

      {/* Tag filter */}
      {allTags.length > 0 && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "center", padding: "0 24px 32px" }}>
          <button onClick={() => setSelectedTag("")}
            style={{ padding: "5px 14px", borderRadius: 20, border: `1.5px solid ${!selectedTag ? "#6366f1" : "rgba(99,102,241,.3)"}`, background: !selectedTag ? "rgba(99,102,241,.15)" : "transparent", color: !selectedTag ? "#a5b4fc" : "#64748b", fontSize: ".8rem", fontWeight: 600, cursor: "pointer", fontFamily: "inherit" }}>
            All
          </button>
          {allTags.map(tag => (
            <button key={tag} onClick={() => setSelectedTag(tag === selectedTag ? "" : tag)}
              style={{ padding: "5px 14px", borderRadius: 20, border: `1.5px solid ${selectedTag === tag ? "#6366f1" : "rgba(99,102,241,.3)"}`, background: selectedTag === tag ? "rgba(99,102,241,.15)" : "transparent", color: selectedTag === tag ? "#a5b4fc" : "#64748b", fontSize: ".8rem", fontWeight: 600, cursor: "pointer", fontFamily: "inherit" }}>
              {tag}
            </button>
          ))}
        </div>
      )}

      {/* Post grid */}
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "0 24px 80px", display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 24 }}>
        {filtered.length === 0 && (
          <p style={{ color: "#64748b", gridColumn: "1/-1", textAlign: "center", padding: "40px 0" }}>No posts found.</p>
        )}
        {filtered.map(post => (
          <article key={post.slug}
            onClick={() => onViewPost?.(post.slug)}
            style={{ background: "rgba(255,255,255,.04)", border: "1px solid rgba(255,255,255,.08)", borderRadius: 16, padding: 24, cursor: "pointer", transition: "transform .15s, border-color .15s" }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = "rgba(99,102,241,.5)"; e.currentTarget.style.transform = "translateY(-3px)"; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = "rgba(255,255,255,.08)"; e.currentTarget.style.transform = "none"; }}>

            {/* Tags */}
            {post.tags.length > 0 && (
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 12 }}>
                {post.tags.slice(0, 3).map(tag => (
                  <span key={tag} style={{ background: "rgba(99,102,241,.12)", color: "#a5b4fc", borderRadius: 10, padding: "2px 8px", fontSize: ".72rem", fontWeight: 600 }}>{tag}</span>
                ))}
              </div>
            )}

            <h2 style={{ fontSize: "1.05rem", fontWeight: 700, lineHeight: 1.4, margin: "0 0 10px", color: "#f1f5f9" }}>
              {post.title}
            </h2>

            <p style={{ color: "#94a3b8", fontSize: ".88rem", lineHeight: 1.6, margin: "0 0 16px" }}>
              {post.summary}
            </p>

            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <div style={{ fontSize: ".78rem", color: "#64748b" }}>{post.author}</div>
                <div style={{ fontSize: ".75rem", color: "#475569" }}>{formatDate(post.date)}</div>
              </div>
              <span style={{ color: "#6366f1", fontSize: ".82rem", fontWeight: 700 }}>Read →</span>
            </div>
          </article>
        ))}
      </div>

      {/* Footer CTA */}
      <div style={{ background: "linear-gradient(135deg,rgba(99,102,241,.15),rgba(16,185,129,.1))", borderTop: "1px solid rgba(99,102,241,.2)", padding: "40px 24px", textAlign: "center" }}>
        <h3 style={{ margin: "0 0 10px", fontSize: "1.4rem" }}>Ready to start learning smarter?</h3>
        <p style={{ color: "#94a3b8", marginBottom: 20 }}>AI-powered CBSE tutoring for Class 5–10</p>
        <button onClick={() => onShowSignup?.("free")}
          style={{ background: "linear-gradient(135deg,#2563eb,#7c3aed)", border: "none", color: "#fff", padding: "13px 32px", borderRadius: 11, fontSize: "1rem", fontWeight: 700, cursor: "pointer", fontFamily: "inherit" }}>
          🚀 Try LikhaPoha AI Free
        </button>
      </div>
    </div>
  );
}
