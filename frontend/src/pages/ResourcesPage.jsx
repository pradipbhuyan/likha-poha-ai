import { useEffect, useState } from "react";
import {
  BookOpen,
  ClipboardList,
  FileText,
  FlaskConical,
  Globe,
  Link2,
  Loader2,
  PenLine,
  PlayCircle,
  Search,
  Target,
} from "lucide-react";

import { getSyllabus } from "../api/syllabus";
import { getResources } from "../api/resources";
import {
  getDefaultSelection,
  getUserGrade,
  getVisibleGrades,
} from "../utils/syllabusDefaults";
import { filterAllowedSubjects } from "../utils/subjectAccess";
import { useFeedbackPrompt } from "../context/FeedbackPromptContext";

const ROLE_META = {
  likhapoha: { label: "LikhaPoha AI", Icon: PlayCircle },
  indian_channel: { label: "Indian Explainer", Icon: PlayCircle },
  international_channel: { label: "International Explainer", Icon: PlayCircle },
};

/** Branded card for Indian video search links (Physics Wallah / Vedantu).
 *  Shows a styled channel thumbnail with topic name and a search-on-YouTube button.
 */
function IndianVideoCard({ title, url }) {
  const isPW = title.toLowerCase().includes("physics wallah");
  const isVedantu = title.toLowerCase().includes("vedantu");
  const isMagnetBrains = title.toLowerCase().includes("magnet brains");

  const brand = isPW
    ? { name: "Physics Wallah", short: "PW", bg: "linear-gradient(135deg, #e63946 0%, #c1121f 100%)", accent: "#ff6b6b" }
    : isVedantu
    ? { name: "Vedantu", short: "V", bg: "linear-gradient(135deg, #7209b7 0%, #480ca8 100%)", accent: "#b5179e" }
    : isMagnetBrains
    ? { name: "Magnet Brains", short: "MB", bg: "linear-gradient(135deg, #0077b6 0%, #023e8a 100%)", accent: "#48cae4" }
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
            <Search size={12} style={{ verticalAlign: "middle", marginRight: 4 }} />
            Search {brand.name} videos on YouTube
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
        Click to play inside the app
      </div>
    </div>
  );
}

function ResourcesPage({ user }) {
  /** Lets students browse external learning resources for a selected syllabus topic. */
  const { triggerFeedbackPrompt } = useFeedbackPrompt();
  const [loading, setLoading] = useState(true);
  const [syllabusData, setSyllabusData] = useState(null);
  const [error, setError] = useState("");

  const mode = "CBSE";
  const [grade, setGrade] = useState("Grade 9");
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

        const { grade: defaultGrade, subject: defaultSubject, chapter: defaultChapter } =
          getDefaultSelection(data.syllabus, getUserGrade(user), "CBSE");

        const cbseSubjects = Object.keys(data.syllabus[defaultGrade]?.CBSE || {});
        const allowedSubjects = filterAllowedSubjects(user, cbseSubjects, "CBSE");
        const selectedSubject = allowedSubjects.includes(defaultSubject)
          ? defaultSubject
          : allowedSubjects[0] || "";
        const realChapters = (data.syllabus[defaultGrade]?.CBSE?.[selectedSubject] || [])
          .filter((c) => !c.startsWith("Exemplar:"));
        const selectedChapter =
          selectedSubject === defaultSubject && !defaultChapter.startsWith("Exemplar:")
            ? defaultChapter
            : realChapters[0] || "";

        setGrade(defaultGrade);
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

  function excludeExemplarChapters(chapterList) {
    /** Learn More has no Exemplar content for any grade/subject — hide those chapters. */
    return (chapterList || []).filter((c) => !c.startsWith("Exemplar:"));
  }

  const grades = getVisibleGrades(syllabusData, user);
  const subjects = filterAllowedSubjects(
    user,
    Object.keys(syllabusData[grade][mode]),
    mode
  );
  const chapters = excludeExemplarChapters(syllabusData[grade][mode][subject]);

  function getFirstAccessibleTopic(selectedGrade) {
    /** Find the first CBSE subject/chapter the student can access for a grade. */
    const modeSubjects = Object.keys(syllabusData[selectedGrade][mode] || {});
    const allowedModeSubjects = filterAllowedSubjects(user, modeSubjects, mode);
    const nextSubject = allowedModeSubjects[0] || "";
    const nextChapter = nextSubject
      ? excludeExemplarChapters(syllabusData[selectedGrade][mode][nextSubject])[0]
      : "";

    return { subject: nextSubject, chapter: nextChapter };
  }

  function handleGradeChange(value) {
    /** Reset dependent subject and chapter selections when grade changes. */
    const nextTopic = getFirstAccessibleTopic(value);

    setGrade(value);
    setSubject(nextTopic.subject);
    setChapter(nextTopic.chapter);
  }

  function handleSubjectChange(value) {
    /** Reset the chapter to the first available chapter for the selected subject. */
    const newChapter = excludeExemplarChapters(syllabusData[grade][mode][value])[0] || "";

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
    /** Return the Lucide icon component that best represents this resource. */
    if (resource.role && ROLE_META[resource.role]) return ROLE_META[resource.role].Icon;

    const title = (resource.title || "").toLowerCase();
    const url = (resource.url || "").toLowerCase();
    if (resource.type === "youtube" || url.includes("youtube")) return PlayCircle;
    if (title.includes("grammar") || title.includes("bbc") || title.includes("british council")) return PenLine;
    if (title.includes("phet") || title.includes("simulation")) return FlaskConical;
    if (title.includes("ncert")) return BookOpen;
    if (title.includes("cbse")) return ClipboardList;
    if (title.includes("sample paper")) return FileText;
    return Link2;
  }

  function getResourceLabel(resource) {
    /** Short badge label shown under the resource icon. */
    if (resource.role && ROLE_META[resource.role]) return ROLE_META[resource.role].label;

    const title = (resource.title || "").toLowerCase();
    if (resource.type === "youtube" || (resource.url || "").includes("youtube")) return "Video";
    if (title.includes("bbc") || title.includes("british council")) return "Grammar Guide";
    if (title.includes("phet")) return "Interactive Sim";
    if (title.includes("ncert")) return "NCERT Textbook";
    if (title.includes("cbse") || title.includes("sample paper")) return "CBSE Resource";
    return "Reference";
  }

  const isGrammarSubject = subject === "English";

  return (
    <div className="resources-page premium-page premium-resources-page">

      <section className="premium-section premium-resource-topic-panel">
        <div className="premium-header">
          <h3><Target size={18} style={{ verticalAlign: "middle", marginRight: 6 }} />Select Topic</h3>
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
          <h3><Globe size={18} style={{ verticalAlign: "middle", marginRight: 6 }} />Free Learning Resources</h3>
          <p>
            Videos and references matched to your selected subject and chapter.
          </p>
        </div>

        {resourcesLoading && (
          <div className="premium-resource-loading">
            <Loader2 size={18} className="spin" />
            <p>Loading resources...</p>
          </div>
        )}

        {!resourcesLoading && resources.length === 0 && (
          <div className="premium-resource-empty">
            <h3><Search size={18} style={{ verticalAlign: "middle", marginRight: 6 }} />No resources found</h3>
            <p>
              Try another chapter or subject. You can still use Lessons and Ask
              Doubt for AI-guided explanations.
            </p>
          </div>
        )}

        {!resourcesLoading && resources.length > 0 && (
          <div className="premium-resource-grid">
            {resources.map((resource, index) => {
              const Icon = getResourceIcon(resource);
              const videoId = resource.type === "youtube" ? getYoutubeVideoId(resource.url) : null;
              return (
                <div
                  key={index}
                  className="resource-card premium-resource-card"
                  onClickCapture={() => triggerFeedbackPrompt("learn_more_used", { grade, subject, chapter })}
                >
                  <div className="premium-resource-card-header">
                    <Icon size={20} />
                    <div>
                      <h4>{resource.title}</h4>
                      <p className="resource-type-badge">
                        {getResourceLabel(resource)}
                        {resource.channel ? ` · ${resource.channel}` : ""}
                      </p>
                      {resource.note && (
                        <p className="resource-note" style={{ fontSize: "0.78rem", color: "var(--muted)", fontStyle: "italic", margin: "2px 0 0" }}>
                          {resource.note}
                        </p>
                      )}
                    </div>
                  </div>

                  {resource.type === "youtube" && isEmbeddableYoutube(resource.url) ? (
                    <VideoEmbedCard
                      videoId={videoId}
                      title={resource.title}
                    />
                  ) : resource.type === "website" &&
                    (resource.title?.toLowerCase().includes("physics wallah") ||
                     resource.title?.toLowerCase().includes("vedantu") ||
                     resource.title?.toLowerCase().includes("magnet brains")) ? (
                    <IndianVideoCard title={resource.title} url={resource.url} />
                  ) : (
                    <a
                      className="premium-resource-link"
                      href={resource.url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open Resource →<span className="sr-only"> (opens in a new tab)</span>
                    </a>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* ── Grammar reference section for English ── */}
      {isGrammarSubject && !resourcesLoading && (
        <section className="premium-section premium-resource-grammar-section">
          <div className="premium-header">
            <h3><PenLine size={18} style={{ verticalAlign: "middle", marginRight: 6 }} />English Grammar Reference Library</h3>
            <p>
              Free grammar guides and exercises from trusted sources.
              Covers all CBSE {grade} grammar topics.
            </p>
          </div>
          <div className="premium-resource-grid">
            <div className="resource-card premium-resource-card">
              <div className="premium-resource-card-header">
                <PenLine size={20} />
                <div>
                  <h4>BBC Learning English — Grammar</h4>
                  <p className="resource-type-badge">Grammar Guide</p>
                </div>
              </div>
              <p style={{ fontSize: "0.875rem", color: "var(--text-muted, #666)", margin: "0.5rem 0 1rem" }}>
                Tenses, Voice, Reported Speech, Clauses, Modals — free interactive lessons with examples.
              </p>
              <a className="premium-resource-link" href="https://www.bbc.co.uk/learningenglish/grammar" target="_blank" rel="noreferrer">
                Open BBC Grammar →<span className="sr-only"> (opens in a new tab)</span>
              </a>
            </div>

            <div className="resource-card premium-resource-card">
              <div className="premium-resource-card-header">
                <PenLine size={20} />
                <div>
                  <h4>British Council — LearnEnglish Grammar</h4>
                  <p className="resource-type-badge">Grammar Guide</p>
                </div>
              </div>
              <p style={{ fontSize: "0.875rem", color: "var(--text-muted, #666)", margin: "0.5rem 0 1rem" }}>
                A1 to C1 level grammar lessons with practice exercises. Covers all CBSE grammar topics.
              </p>
              <a className="premium-resource-link" href="https://learnenglish.britishcouncil.org/grammar" target="_blank" rel="noreferrer">
                Open British Council Grammar →<span className="sr-only"> (opens in a new tab)</span>
              </a>
            </div>

            <div className="resource-card premium-resource-card">
              <div className="premium-resource-card-header">
                <ClipboardList size={20} />
                <div>
                  <h4>CBSE Sample Papers — English</h4>
                  <p className="resource-type-badge">CBSE Resource</p>
                </div>
              </div>
              <p style={{ fontSize: "0.875rem", color: "var(--text-muted, #666)", margin: "0.5rem 0 1rem" }}>
                Official CBSE sample papers with grammar and writing sections — best for board exam prep.
              </p>
              <a className="premium-resource-link" href="https://cbseacademic.nic.in/SampleQuestion_Papers.html" target="_blank" rel="noreferrer">
                Open CBSE Sample Papers →<span className="sr-only"> (opens in a new tab)</span>
              </a>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

export default ResourcesPage;
