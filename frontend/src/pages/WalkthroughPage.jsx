function WalkthroughPage() {
  /** Platform Walkthrough — Coming Soon placeholder page. */
  return (
    <div className="premium-page">
      <section className="premium-section">
        <div className="premium-header">
          <p className="eyebrow">Getting Started</p>
          <h2>🎬 Platform Walkthrough</h2>
          <p>
            Learn how to get the most out of LikhaPoha AI — lessons, doubts,
            mock tests, and more.
          </p>
        </div>

        {/* Coming Soon hero */}
        <div
          className="premium-card"
          style={{
            maxWidth: 640,
            textAlign: "center",
            padding: "48px 32px",
          }}
        >
          {/* Video placeholder */}
          <div
            style={{
              background: "rgba(99,102,241,.08)",
              border: "2px dashed rgba(99,102,241,.35)",
              borderRadius: 16,
              padding: "48px 24px",
              marginBottom: 32,
            }}
          >
            <div style={{ fontSize: "4rem", marginBottom: 12 }}>▶️</div>
            <h3 style={{ margin: "0 0 8px", color: "var(--primary)" }}>
              Platform Walkthrough Video
            </h3>
            <p style={{ color: "var(--muted)", fontSize: ".9rem", margin: 0 }}>
              A 3-minute video guide is being produced to help you and your
              child navigate LikhaPoha AI with confidence.
            </p>
          </div>

          {/* Coming soon badge */}
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              background: "rgba(251,191,36,.12)",
              border: "1px solid rgba(251,191,36,.35)",
              borderRadius: 24,
              padding: "6px 18px",
              marginBottom: 32,
              color: "#fbbf24",
              fontWeight: 700,
              fontSize: ".88rem",
            }}
          >
            🚧 Coming Soon
          </div>

          {/* Quick tips */}
          <div style={{ textAlign: "left" }}>
            <h4 style={{ marginBottom: 14 }}>📋 Quick Tips to Get Started</h4>
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 12,
              }}
            >
              {[
                {
                  icon: "📚",
                  title: "Start with Lessons",
                  desc: "Go to Lessons → pick your subject and chapter → AI generates a step-by-step lesson.",
                },
                {
                  icon: "🤔",
                  title: "Ask a Doubt",
                  desc: "Stuck on a concept? Use Ask Doubt — type your question and get an instant AI answer.",
                },
                {
                  icon: "📝",
                  title: "Take a Mock Test",
                  desc: "Practice with Mock Tests — choose chapter, difficulty, and number of questions.",
                },
                {
                  icon: "📊",
                  title: "Track Progress",
                  desc: "Check Analytics to see lessons completed, doubts asked, and mock test scores.",
                },
                {
                  icon: "🔑",
                  title: "Login Tip",
                  desc: "You can sign in using your username OR email address — both work at likhapoha.in.",
                },
              ].map((tip) => (
                <div
                  key={tip.title}
                  style={{
                    display: "flex",
                    gap: 12,
                    background: "var(--surface2, rgba(0,0,0,.06))",
                    borderRadius: 10,
                    padding: "10px 14px",
                  }}
                >
                  <span style={{ fontSize: "1.4rem", flexShrink: 0 }}>
                    {tip.icon}
                  </span>
                  <div>
                    <strong style={{ fontSize: ".88rem" }}>{tip.title}</strong>
                    <p
                      style={{
                        margin: "2px 0 0",
                        fontSize: ".82rem",
                        color: "var(--muted)",
                      }}
                    >
                      {tip.desc}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

export default WalkthroughPage;
