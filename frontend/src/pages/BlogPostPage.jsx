import { getPostBySlug, formatDate } from "../blog/blogUtils";
import logoImg from "../assets/AITutorLogo1.png";

export default function BlogPostPage({ slug, onShowLogin, onShowSignup, onBack }) {
  const post = getPostBySlug(slug);

  if (!post) {
    return (
      <div style={{ fontFamily: "-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif", background: "#0f172a", color: "#f8fafc", minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: "3rem", marginBottom: 16 }}>📄</div>
          <h2>Post not found</h2>
          <button onClick={onBack}
            style={{ marginTop: 16, background: "#6366f1", border: "none", color: "#fff", padding: "10px 24px", borderRadius: 8, cursor: "pointer", fontFamily: "inherit", fontWeight: 700 }}>
            ← Back to Blog
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ fontFamily: "-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif", background: "#0f172a", color: "#f8fafc", minHeight: "100vh" }}>

      {/* Nav */}
      <nav style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 40px", borderBottom: "1px solid rgba(255,255,255,.06)", background: "rgba(15,23,42,.97)", backdropFilter: "blur(12px)", position: "sticky", top: 0, zIndex: 99 }}>
        <a href="/" style={{ display: "flex", alignItems: "center", gap: 10, textDecoration: "none", color: "#f8fafc", fontWeight: 700, fontSize: "1.1rem" }}>
          <img src={logoImg} alt="Likha Poha AI" style={{ width: 36, height: 36, borderRadius: 9, objectFit: "cover", background: "#fff" }} />
          Likha Poha AI
        </a>
        <div style={{ display: "flex", gap: 10 }}>
          <button onClick={onShowLogin}
            style={{ background: "transparent", border: "1px solid #334155", color: "#93c5fd", padding: "7px 16px", borderRadius: 8, fontSize: ".85rem", cursor: "pointer", fontFamily: "inherit" }}>
            Login
          </button>
          <button onClick={() => onShowSignup?.("free")}
            style={{ background: "linear-gradient(135deg,#2563eb,#7c3aed)", border: "none", color: "#fff", padding: "7px 16px", borderRadius: 8, fontSize: ".85rem", fontWeight: 700, cursor: "pointer", fontFamily: "inherit" }}>
            Try for Free
          </button>
        </div>
      </nav>

      {/* Article */}
      <article style={{ maxWidth: 760, margin: "0 auto", padding: "48px 24px 80px" }}>

        {/* Back link */}
        <button onClick={onBack}
          style={{ background: "none", border: "none", color: "#6366f1", cursor: "pointer", fontFamily: "inherit", fontSize: ".88rem", fontWeight: 600, padding: "0 0 24px", display: "flex", alignItems: "center", gap: 6 }}>
          ← Back to Blog
        </button>

        {/* Tags */}
        {post.tags.length > 0 && (
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 16 }}>
            {post.tags.map(tag => (
              <span key={tag} style={{ background: "rgba(99,102,241,.12)", color: "#a5b4fc", borderRadius: 10, padding: "3px 10px", fontSize: ".75rem", fontWeight: 600 }}>{tag}</span>
            ))}
          </div>
        )}

        {/* Title */}
        <h1 style={{ fontSize: "clamp(1.6rem,4vw,2.4rem)", fontWeight: 900, lineHeight: 1.25, margin: "0 0 16px", color: "#f1f5f9" }}>
          {post.title}
        </h1>

        {/* Meta */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 32, color: "#64748b", fontSize: ".85rem", borderBottom: "1px solid rgba(255,255,255,.07)", paddingBottom: 20 }}>
          <span>✍️ {post.author}</span>
          <span>·</span>
          <span>📅 {formatDate(post.date)}</span>
        </div>

        {/* Summary */}
        <div style={{ background: "rgba(99,102,241,.08)", border: "1px solid rgba(99,102,241,.2)", borderRadius: 10, padding: "14px 18px", marginBottom: 32, color: "#c7d2fe", fontSize: ".95rem", fontStyle: "italic", lineHeight: 1.6 }}>
          {post.summary}
        </div>

        {/* Content */}
        <div
          className="blog-content"
          dangerouslySetInnerHTML={{ __html: post.html }}
          style={{
            lineHeight: 1.8,
            fontSize: "1rem",
            color: "#cbd5e1",
          }}
        />

        {/* CTA */}
        <div style={{ marginTop: 48, background: "linear-gradient(135deg,rgba(99,102,241,.15),rgba(16,185,129,.1))", border: "1px solid rgba(99,102,241,.25)", borderRadius: 16, padding: "28px 24px", textAlign: "center" }}>
          <h3 style={{ margin: "0 0 8px", color: "#f1f5f9" }}>Start Learning with Likha Poha AI</h3>
          <p style={{ color: "#94a3b8", marginBottom: 18, fontSize: ".9rem" }}>AI-powered CBSE tutoring for Grade 5–12 · ₹299/month</p>
          <button onClick={() => onShowSignup?.("free")}
            style={{ background: "linear-gradient(135deg,#2563eb,#7c3aed)", border: "none", color: "#fff", padding: "12px 28px", borderRadius: 10, fontSize: ".95rem", fontWeight: 700, cursor: "pointer", fontFamily: "inherit" }}>
            🚀 Try for Free
          </button>
        </div>
      </article>

      {/* Blog content styles injected as a style tag */}
      <style>{`
        .blog-content h1 { font-size: 1.7rem; font-weight: 800; color: #f1f5f9; margin: 32px 0 14px; }
        .blog-content h2 { font-size: 1.35rem; font-weight: 700; color: #f1f5f9; margin: 28px 0 12px; border-bottom: 1px solid rgba(255,255,255,.07); padding-bottom: 8px; }
        .blog-content h3 { font-size: 1.1rem; font-weight: 700; color: #e2e8f0; margin: 22px 0 10px; }
        .blog-content p { margin: 0 0 16px; line-height: 1.8; }
        .blog-content ul, .blog-content ol { margin: 0 0 16px; padding-left: 24px; }
        .blog-content li { margin-bottom: 6px; line-height: 1.7; }
        .blog-content strong { color: #e2e8f0; font-weight: 700; }
        .blog-content em { color: #a5b4fc; font-style: italic; }
        .blog-content a { color: #6366f1; text-decoration: underline; }
        .blog-content a:hover { color: #818cf8; }
        .blog-content hr { border: none; border-top: 1px solid rgba(255,255,255,.1); margin: 28px 0; }
        .blog-content pre { background: #111827; border: 1px solid rgba(255,255,255,.1); border-radius: 8px; padding: 16px; overflow-x: auto; margin: 16px 0; }
        .blog-content code { font-family: monospace; font-size: .9rem; color: #a5b4fc; }
      `}</style>
    </div>
  );
}
