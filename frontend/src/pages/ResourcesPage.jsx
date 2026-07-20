import { useEffect, useState } from "react";

import { getSyllabus } from "../api/syllabus";
import { getResources } from "../api/resources";
import {
  getDefaultSelection,
  getUserBoard,
  getUserGrade,
  getVisibleGrades,
} from "../utils/syllabusDefaults";
import { filterAllowedSubjects } from "../utils/subjectAccess";

/** Branded card for Indian video search links (Physics Wallah / Vedantu).
 *  Shows a styled channel thumbnail with topic name and a search-on-YouTube button.
 */
function IndianVideoCard({ title, url }) {
  const isPW = title.toLowerCase().includes("physics wallah");
  const isVedantu = title.toLowerCase().includes("vedantu");

  const brand = isPW
    ? { name: "Physics Wallah", short: "PW", bg: "linear-gradient(135deg, #e63946 0%, #c1121f 100%)", accent: "#ff6b6b" }
    : isVedantu
    ? { name: "Vedantu", short: "V", bg: "linear-gradient(135deg, #7209b7 0%, #480ca8 100%)", accent: "#b5179e" }
    : { name: "Indian Video", short: "▶", bg: "linear-gradient(135deg, #333 0%, #555 100%)", accent: "#888" };

  // Extract topic from title: "Physics Wallah — TOPIC | Class 11 (India)"
  const topicMatch = title.match(/—\s*(.+?)\s*\|/);
  const topic = topicMatch ? topicMatch[1] : title;

  return (
    <div style={{ marginTop: "0.75rem" }}>
      <a
        href={url}
        target="_blank"
        rel="noreferrer"
        style={{ textDecoration: "none", display: "block" }}
        aria-label={`Search ${brand.name} videos: ${topic}`}
      >
        <div
          style={{
            position: "relative",
            borderRadius: "6px",
            overflow: "hidden",
            background: brand.bg,
            height: "140px",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: "8px",
            cursor: "pointer",
          }}
        >
          {/* Channel badge */}
          <div
            style={{
              position: "absolute",
              top: 8,
              left: 10,
              background: "rgba(0,0,0,0.45)",
              borderRadius: "4px",
              padding: "2px 8px",
              fontSize: "0.7rem",
              fontWeight: 700,
              color: "#fff",
              letterSpacing: "0.04em",
            }}
          >
            {brand.name.toUpperCase()}
          </div>

          {/* Big play button */}
          <div
            style={{
              width: 52,
              height: 52,
              borderRadius: "50%",
              background: "rgba(255,255,255,0.22)",
              border: "2px solid rgba(255,255,255,0.6)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="white">
              <path d="M8 5v14l11-7z" />
            </svg>
          </div>

          {/* Topic label */}
          <div
            style={{
              color: "#fff",
              fontSize: "0.78rem",
              fontWeight: 600,
              textAlign: "center",
              padding: "0 12px",
              lineHeight: 1.3,
              textShadow: "0 1px 3px rgba(0,0,0,0.5)",
            }}
          >
            {topic}
          </div>

          {/* Bottom bar */}
          <div
            style={{
              position: "absolute",
              bottom: 0,
              left: 0,
              right: 0,
              background: "rgba(0,0,0,0.5)",
              padding: "5px 10px",
              color: "#fff",
              fontSize: "0.72rem",
              fontWeight: 600,
            }}
          >
            🔍 Search {brand.name} videos on YouTube
          </div>
        </div>
      </a>
    </div>
  );
}

/** Click-to-play YouTube embed with thumbnail preview.
 *  Shows the video thumbnail + play overlay; loads the iframe only on click
 *  so videos play inside the platform instead of opening a new browser window.
 */
function VideoEmbedCard({ videoId, title }) {
  const [playing, setPlaying] = useState(false);
  if (!videoId) return null;

  if (playing) {
    return (
      <div style={{ marginTop: "0.75rem" }}>
        <iframe
          width="100%"
          height="220"
          src={`https://www.youtube.com/embed/${videoId}?autoplay=1`}
          title={title}
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
          style={{ borderRadius: "6px", border: "none", display: "block" }}
        />
      </div>
    );
  }

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`Play: ${title}`}
      onClick={() => setPlaying(true)}
      onKeyDown={(e) => e.key === "Enter" && setPlaying(true)}
      style={{
        position: "relative",
        marginTop: "0.75rem",
        cursor: "pointer",
        borderRadius: "6px",
        overflow: "hidden",
        lineHeight: 0,
      }}
    >
      <img
        src={`https://img.youtube.com/vi/${videoId}/hqdefault.jpg`}
        alt={title}
        style={{ width: "100%", display: "block", borderRadius: "6px" }}
      />
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "rgba(0,0,0,0.22)",
        }}
      >
        <div
          style={{
            width: 56,
            height: 56,
            borderRadius: "50%",
            background: "rgba(220,38,38,0.92)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 2px 12px rgba(0,0,0,0.35)",
          }}
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="white">
            <path d="M8 5v14l11-7z" />
          </svg>
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          background: "linear-gradient(transparent, rgba(0,0,0,0.62))",
          padding: "18px 10px 8px",
          color: "#fff",
          fontSize: "0.78rem",
          fontWeight: 600,
          lineHeight: 1.3,
          borderBottomLeftRadius: "6px",
          borderBottomRightRadius: "6px",
        }}
      >
        ▶ Click to play inside the app
      </div>
    </div>
  );
}

function ResourcesPage({ user }) {
  /** Lets students browse external learning resources for a selected syllabus topic. */
  const [loading, setLoading] = useState(true);
  const [syllabusData, setSyllabusData] = useState(null);
  const [error, setError] = useState("");

  const [grade, setGrade] = useState("Grade 9");
  const [mode, setMode] = useState("CBSE");
  const [subject, setSubject] = useState("");
  const [chapter, setChapter] = useState("");

  const [resources, setResources] = useState([]);
  const [resourcesLoading, setResourcesLoading] = useState(false);

  useEffect(() => {
    async function loadSyllabus() {
      /** Load syllabus metadata and initialize the resource filters to a valid topic. */
      try {
        const data = await getSyllabus();
        setSyllabusData(data.syllabus);

        const {
          grade: defaultGrade,
          mode: defaultMode,
          subject: defaultSubject,
          chapter: defaultChapter,
        } = getDefaultSelection(
          data.syllabus,
          getUserGrade(user),
          getUserBoard(user)
        );
        const defaultSubjects = Object.keys(
          data.syllabus[defaultGrade]?.[defaultMode] || {}
        );
        const allowedDefaultSubjects = filterAllowedSubjects(
          user,
          defaultSubjects,
          defaultMode
        );
        let selectedMode = defaultMode;
        let selectedSubject = allowedDefaultSubjects.includes(defaultSubject)
          ? defaultSubject
          : allowedDefaultSubjects[0] || "";

        if (!selectedSubject) {
          selectedMode =
            Object.keys(data.syllabus[defaultGrade] || {}).find((modeName) => {
              const modeSubjects = Object.keys(
                data.syllabus[defaultGrade]?.[modeName] || {}
              );
              return filterAllowedSubjects(user, modeSubjects, modeName).length > 0;
            }) || defaultMode;
          selectedSubject =
            filterAllowedSubjects(
              user,
              Object.keys(data.syllabus[defaultGrade]?.[selectedMode] || {}),
              selectedMode
            )[0] || "";
        }
        const selectedChapter =
          selectedSubject === defaultSubject
            ? defaultChapter
            : data.syllabus[defaultGrade]?.[selectedMode]?.[selectedSubject]?.[0] || "";

        setGrade(defaultGrade);
        setMode(selectedMode);
        setSubject(selectedSubject);
        setChapter(selectedChapter);
      } catch {
        setError("Could not load resources page.");
      } finally {
        setLoading(false);
      }
    }

    loadSyllabus();
  }, []);

  useEffect(() => {
    async function loadResources() {
      /** Fetch chapter resources whenever the selected subject or chapter changes. */
      if (!subject || !chapter) return;

      setResourcesLoading(true);
      setError("");

      try {
        const result = await getResources(subject, chapter, grade);
        setResources(result.resources || []);
      } catch {
        setError("Could not load learning resources.");
      } finally {
        setResourcesLoading(false);
      }
    }

    loadResources();
  }, [grade, subject, chapter]);

  if (loading) return <p>Loading resources page...</p>;
  if (error) return <p className="error">{error}</p>;

  const grades = getVisibleGrades(syllabusData, user);
  const modes = Object.keys(syllabusData[grade]);
  const subjects = filterAllowedSubjects(
    user,
    Object.keys(syllabusData[grade][mode]),
    mode
  );
  const chapters = (syllabusData[grade][mode][subject] || []).filter(
    (c) => !c.startsWith("Exemplar:")
  );

  /** Return the first non-Exemplar chapter for a subject, or the raw first as fallback. */
  function firstChapter(selectedGrade, selectedMode, subj) {
    const all = syllabusData[selectedGrade][selectedMode][subj] || [];
    return all.find((c) => !c.startsWith("Exemplar:")) || all[0] || "";
  }

  function getFirstAccessibleTopic(selectedGrade, selectedMode) {
    /** Find the first subject/chapter the student can access for a grade and mode. */
    const modeSubjects = Object.keys(syllabusData[selectedGrade][selectedMode] || {});
    const allowedModeSubjects = filterAllowedSubjects(
      user,
      modeSubjects,
      selectedMode
    );
    const nextSubject = allowedModeSubjects[0] || "";
    const nextChapter = nextSubject
      ? firstChapter(selectedGrade, selectedMode, nextSubject)
      : "";

    return { subject: nextSubject, chapter: nextChapter };
  }

  function handleGradeChange(value) {
    /** Reset dependent mode, subject, and chapter selections when grade changes. */
    const gradeModes = Object.keys(syllabusData[value]);
    const newMode =
      gradeModes.find((modeName) => {
        const topic = getFirstAccessibleTopic(value, modeName);
        return !!topic.subject;
      }) || gradeModes[0];
    const nextTopic = getFirstAccessibleTopic(value, newMode);

    setGrade(value);
    setMode(newMode);
    setSubject(nextTopic.subject);
    setChapter(nextTopic.chapter);
  }

  function handleModeChange(value) {
    /** Reset subject and chapter to valid defaults for the selected learning mode. */
    const nextTopic = getFirstAccessibleTopic(grade, value);
    setMode(value);
    setSubject(nextTopic.subject);
    setChapter(nextTopic.chapter);
  }

  function handleSubjectChange(value) {
    /** Reset the chapter to the first available non-Exemplar chapter for the selected subject. */
    const newChapter = firstChapter(grade, mode, value);
    setSubject(value);
    setChapter(newChapter);
  }

  function getYoutubeVideoId(url) {
    /** Extract the YouTube video ID from both watch and short-link URL formats. */
    if (!url) return null;
    const watchMatch = url.match(/youtube\.com\/watch\?(?:.*&)?v=([^&]+)/);
    if (watchMatch) return watchMatch[1];
    const shortMatch = url.match(/youtu\.be\/([^?&]+)/);
    if (shortMatch) return shortMatch[1];
    return null;
  }

  function isEmbeddableYoutube(url) {
    /** Identify YouTube URLs (watch or short-link) that can be embedded inside the page. */
    return !!(getYoutubeVideoId(url));
  }

  function getResourceIcon(resource) {
    /** Return an emoji icon based on the resource title/URL for quick visual identification. */
    const title = (resource.title || "").toLowerCase();
    const url = (resource.url || "").toLowerCase();
    if (resource.type === "youtube" || url.includes("youtube")) return "▶️";
    if (title.includes("exemplar")) return "🔬";
    if (title.includes("grammar") || title.includes("bbc") || title.includes("british council")) return "✍️";
    if (title.includes("phet") || title.includes("simulation")) return "🧪";
    if (title.includes("ncert")) return "📚";
    if (title.includes("cbse")) return "📋";
    if (title.includes("sample paper")) return "📝";
    return "🔗";
  }

  function getResourceLabel(resource) {
    /** Short badge label shown under the resource icon. */
    const title = (resource.title || "").toLowerCase();
    if (resource.type === "youtube" || (resource.url || "").includes("youtube")) return "Video";
    if (title.includes("exemplar")) return "Practice Problems";
    if (title.includes("bbc") || title.includes("british council")) return "Grammar Guide";
    if (title.includes("phet")) return "Interactive Sim";
    if (title.includes("ncert")) return "NCERT Textbook";
    if (title.includes("cbse") || title.includes("sample paper")) return "CBSE Resource";
    return "Reference";
  }

  const isGrammarSubject = subject === "English";
  const isExemplarSubject =
    (subject === "Maths" || subject === "Science") &&
    ["Grade 8", "Grade 9", "Grade 10"].includes(grade);

  return (
    <div className="resources-page premium-page premium-resources-page">
      {/* Compact context bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          padding: "14px 0 4px",
          flexWrap: "wrap",
        }}
      >
        <span style={{ fontSize: "1.1rem" }}>📚</span>
        <div>
          <span style={{ fontWeight: 700, fontSize: "0.9rem" }}>
            {subject || "All Subjects"}
          </span>
          {chapter && (
            <span
              style={{
                fontSize: "0.82rem",
                color: "var(--muted)",
                marginLeft: 6,
              }}
            >
              · {chapter.slice(0, 60)}
              {chapter.length > 60 ? "…" : ""}
            </span>
          )}
        </div>
        <span
          style={{
            marginLeft: "auto",
            fontSize: "0.75rem",
            color: "var(--muted)",
            fontStyle: "italic",
          }}
        >
          Videos, references and resources for this chapter
        </span>
      </div>

      <section className="premium-section premium-resource-topic-panel">
        <div className="premium-header">
          <h3>🎯 Select Topic</h3>
          <p>Choose the exact context for resource discovery.</p>
        </div>

        <div className="form-grid premium-resource-form-grid">
          <label>
            Grade
            <select
              value={grade}
              onChange={(e) => handleGradeChange(e.target.value)}
            >
              {grades.map((g) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))}
            </select>
          </label>

          <label>
            Mode
            <select
              value={mode}
              onChange={(e) => handleModeChange(e.target.value)}
            >
              {modes.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </label>

          <label>
            Subject
            <select
              value={subject}
              onChange={(e) => handleSubjectChange(e.target.value)}
            >
              {subjects.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>

          <label>
            Chapter / Section
            <select
              value={chapter}
              onChange={(e) => setChapter(e.target.value)}
            >
              {chapters.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>
        </div>
      </section>

      <section className="premium-section premium-resource-results">
        <div className="premium-header">
          <h3>🌐 Free Learning Resources</h3>
          <p>Videos and references matched to your selected subject and chapter.</p>
        </div>

        {resourcesLoading && (
          <div className="premium-resource-loading">
            <span>⏳</span>
            <p>Loading resources...</p>
          </div>
        )}

        {!resourcesLoading && resources.length === 0 && (
          <div className="premium-resource-empty">
            <h3>🔎 No resources found</h3>
            <p>
              Try another chapter or subject. You can still use Lessons and Ask
              Doubt for AI-guided explanations.
            </p>
          </div>
        )}

        {!resourcesLoading && resources.length > 0 && (
          <div className="premium-resource-grid">
            {resources.map((resource, index) => (
              <div key={index} className="resource-card premium-resource-card">
                <div className="premium-resource-card-header">
                  <span>{getResourceIcon(resource)}</span>
                  <div>
                    <h4>{resource.title}</h4>
                    <p className="resource-type-badge">{getResourceLabel(resource)}</p>
                  </div>
                </div>

                {resource.type === "youtube" && isEmbeddableYoutube(resource.url) ? (
                  <VideoEmbedCard
                    videoId={getYoutubeVideoId(resource.url)}
                    title={resource.title}
                  />
                ) : resource.type === "website" &&
                  (resource.title?.toLowerCase().includes("physics wallah") ||
                   resource.title?.toLowerCase().includes("vedantu")) ? (
                  <IndianVideoCard title={resource.title} url={resource.url} />
                ) : (
                  <a
                    className="premium-resource-link"
                    href={resource.url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open Resource →
                  </a>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {isExemplarSubject && !resourcesLoading && (
        <section className="premium-section premium-resource-exemplar-section">
          <div className="premium-header">
            <h3>🔬 NCERT Exemplar Practice Problems</h3>
            <p>
              Official NCERT higher-order thinking problems for {grade} {subject}.
              These are ideal for board exam preparation and advanced practice.
            </p>
          </div>
          <div className="premium-resource-grid">
            <div className="resource-card premium-resource-card premium-resource-card--exemplar">
              <div className="premium-resource-card-header">
                <span>🔬</span>
                <div>
                  <h4>NCERT Exemplar — {grade} {subject} (Full Book)</h4>
                  <p className="resource-type-badge">Practice Problems</p>
                </div>
              </div>
              <p style={{ fontSize: "0.875rem", color: "var(--text-muted, #666)", margin: "0.5rem 0 1rem" }}>
                Official NCERT exemplar with MCQs, short-answer and long-answer problems with solutions.
                Free from NCERT — no login required.
              </p>
              <a
                className="premium-resource-link"
                href="https://ncert.nic.in/exemplar-problems.php"
                target="_blank"
                rel="noreferrer"
              >
                Browse All Exemplar Problems →
              </a>
            </div>
          </div>
        </section>
      )}

      {isGrammarSubject && !resourcesLoading && (
        <section className="premium-section premium-resource-grammar-section">
          <div className="premium-header">
            <h3>✍️ English Grammar Reference Library</h3>
            <p>
              Free grammar guides and exercises from trusted sources.
              Covers all CBSE {grade} grammar topics.
            </p>
          </div>
          <div className="premium-resource-grid">
            <div className="resource-card premium-resource-card">
              <div className="premium-resource-card-header">
                <span>✍️</span>
                <div>
                  <h4>BBC Learning English — Grammar</h4>
                  <p className="resource-type-badge">Grammar Guide</p>
                </div>
              </div>
              <p style={{ fontSize: "0.875rem", color: "var(--text-muted, #666)", margin: "0.5rem 0 1rem" }}>
                Tenses, Voice, Reported Speech, Clauses, Modals — free interactive lessons with examples.
              </p>
              <a className="premium-resource-link" href="https://www.bbc.co.uk/learningenglish/grammar" target="_blank" rel="noreferrer">
                Open BBC Grammar →
              </a>
            </div>

            <div className="resource-card premium-resource-card">
              <div className="premium-resource-card-header">
                <span>✍️</span>
                <div>
                  <h4>British Council — LearnEnglish Grammar</h4>
                  <p className="resource-type-badge">Grammar Guide</p>
                </div>
              </div>
              <p style={{ fontSize: "0.875rem", color: "var(--text-muted, #666)", margin: "0.5rem 0 1rem" }}>
                A1 to C1 level grammar lessons with practice exercises. Covers all CBSE grammar topics.
              </p>
              <a className="premium-resource-link" href="https://learnenglish.britishcouncil.org/grammar" target="_blank" rel="noreferrer">
                Open British Council Grammar →
              </a>
            </div>

            <div className="resource-card premium-resource-card">
              <div className="premium-resource-card-header">
                <span>📋</span>
                <div>
                  <h4>CBSE Sample Papers — English</h4>
                  <p className="resource-type-badge">CBSE Resource</p>
                </div>
              </div>
              <p style={{ fontSize: "0.875rem", color: "var(--text-muted, #666)", margin: "0.5rem 0 1rem" }}>
                Official CBSE sample papers with grammar and writing sections — best for board exam prep.
              </p>
              <a className="premium-resource-link" href="https://cbseacademic.nic.in/SampleQuestion_Papers.html" target="_blank" rel="noreferrer">
                Open CBSE Sample Papers →
              </a>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

export default ResourcesPage;
