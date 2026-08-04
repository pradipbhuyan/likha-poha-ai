import { useState } from "react";

const WALKTHROUGH_BUCKET_URL =
  "https://dpivlbbyzlbpwnwgajso.supabase.co/storage/v1/object/public/platform-walkthrough-videos";

const VIDEOS = {
  english: {
    label: "🇬🇧 English",
    src: `${WALKTHROUGH_BUCKET_URL}/walkthrough-en.mp4`,
    title: "Likha Poha AI — Student Platform Walkthrough (English)",
  },
  hindi: {
    label: "🇮🇳 Hindi",
    src: `${WALKTHROUGH_BUCKET_URL}/walkthrough-hi.mp4`,
    title: "Likha Poha AI — Student Platform Walkthrough (Hindi)",
  },
};

function WalkthroughPage() {
  /** Platform Walkthrough — self-hosted videos (Supabase Storage) with English / Hindi toggle. */
  const [lang, setLang] = useState("english");
  const video = VIDEOS[lang];

  return (
    <div className="premium-page">
      <section className="premium-section">
        {/* Language toggle */}
        <div style={{ display: "flex", gap: 10, marginBottom: 28 }}>
          {Object.entries(VIDEOS).map(([key, v]) => (
            <button
              key={key}
              onClick={() => setLang(key)}
              aria-pressed={lang === key}
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

        {/* Self-hosted video (Supabase Storage) */}
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
          <video
            key={video.src}
            width="100%"
            height="100%"
            src={video.src}
            title={video.title}
            controls
            playsInline
            preload="metadata"
            style={{ display: "block", width: "100%", height: "100%" }}
          >
            Sorry, your browser doesn't support embedded videos.
          </video>
        </div>
      </section>
    </div>
  );
}

export default WalkthroughPage;
