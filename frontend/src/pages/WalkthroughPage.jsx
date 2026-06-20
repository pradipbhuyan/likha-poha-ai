import { useState } from "react";

const VIDEOS = {
  english: {
    label: "🇬🇧 English",
    embedId: "N82gfHBJm00",
    title: "LikhaPoha AI — Student Platform Walkthrough (English)",
  },
  hindi: {
    label: "🇮🇳 Hindi",
    embedId: "y0YHnMrmR3k",
    title: "LikhaPoha AI — Student Platform Walkthrough (Hindi)",
  },
};

function WalkthroughPage() {
  /** Platform Walkthrough — embedded YouTube videos with English / Hindi toggle. */
  const [lang, setLang] = useState("english");
  const video = VIDEOS[lang];

  return (
    <div className="premium-page">
      <section className="premium-section">
        <div className="premium-header">
          <p className="eyebrow">Getting Started</p>
          <h2>🎬 Platform Walkthrough</h2>
          <p>
            Watch the full walkthrough to learn how to use LikhaPoha AI —
            lessons, doubts, mock tests, analytics, and more.
          </p>
        </div>

        {/* Language toggle */}
        <div style={{ display: "flex", gap: 10, marginBottom: 28 }}>
          {Object.entries(VIDEOS).map(([key, v]) => (
            <button
              key={key}
              onClick={() => setLang(key)}
              style={{
                padding: "8px 22px",
                borderRadius: 24,
                border: lang === key
                  ? "2px solid #6366f1"
                  : "2px solid rgba(99,102,241,.25)",
                background: lang === key
                  ? "rgba(99,102,241,.18)"
                  : "transparent",
                color: lang === key ? "#c7d2fe" : "var(--muted)",
                fontWeight: lang === key ? 700 : 500,
                fontSize: ".9rem",
                cursor: "pointer",
                fontFamily: "inherit",
                transition: "all .15s",
              }}
            >
              {v.label}
            </button>
          ))}
        </div>

        {/* YouTube embed */}
        <div
          style={{
            maxWidth: 900,
            width: "100%",
            borderRadius: 16,
            overflow: "hidden",
            boxShadow: "0 8px 40px rgba(0,0,0,.45)",
            aspectRatio: "16/9",
            marginBottom: 36,
            background: "#000",
          }}
        >
          <iframe
            key={video.embedId}
            width="100%"
            height="100%"
            src={`https://www.youtube.com/embed/${video.embedId}?rel=0&modestbranding=1`}
            title={video.title}
            frameBorder="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            allowFullScreen
            style={{ display: "block", width: "100%", height: "100%" }}
          />
        </div>

        {/* Quick tips */}
        <div
          className="premium-card"
          style={{ maxWidth: 900, padding: "28px 32px" }}
        >
          <h4 style={{ marginBottom: 16 }}>📋 Quick Tips to Get Started</h4>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 12 }}>
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
                icon: "✅",
                title: "Mark Steps Complete",
                desc: "Read each lesson section and click Mark Step Complete to unlock the next step.",
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
      </section>
    </div>
  );
}

export default WalkthroughPage;
