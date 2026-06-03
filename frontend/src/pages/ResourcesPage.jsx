import { useEffect, useState } from "react";

import { getSyllabus } from "../api/syllabus";
import { getResources } from "../api/resources";

function ResourcesPage() {
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

        const defaultGrade = "Grade 9";
        const defaultMode = "CBSE";
        const defaultSubject = Object.keys(
          data.syllabus[defaultGrade][defaultMode]
        )[0];

        const defaultChapter =
          data.syllabus[defaultGrade][defaultMode][defaultSubject][0];

        setGrade(defaultGrade);
        setMode(defaultMode);
        setSubject(defaultSubject);
        setChapter(defaultChapter);
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
        const result = await getResources(subject, chapter);
        setResources(result.resources || []);
      } catch {
        setError("Could not load learning resources.");
      } finally {
        setResourcesLoading(false);
      }
    }

    loadResources();
  }, [subject, chapter]);

  if (loading) return <p>Loading resources page...</p>;
  if (error) return <p className="error">{error}</p>;

  const grades = Object.keys(syllabusData);
  const modes = Object.keys(syllabusData[grade]);
  const subjects = Object.keys(syllabusData[grade][mode]);
  const chapters = syllabusData[grade][mode][subject] || [];

  function handleGradeChange(value) {
    /** Reset dependent mode, subject, and chapter selections when grade changes. */
    const newMode = Object.keys(syllabusData[value])[0];
    const newSubject = Object.keys(syllabusData[value][newMode])[0];
    const newChapter = syllabusData[value][newMode][newSubject][0];

    setGrade(value);
    setMode(newMode);
    setSubject(newSubject);
    setChapter(newChapter);
  }

  function handleModeChange(value) {
    /** Reset subject and chapter to valid defaults for the selected learning mode. */
    const newSubject = Object.keys(syllabusData[grade][value])[0];
    const newChapter = syllabusData[grade][value][newSubject][0];

    setMode(value);
    setSubject(newSubject);
    setChapter(newChapter);
  }

  function handleSubjectChange(value) {
    /** Reset the chapter to the first available chapter for the selected subject. */
    const newChapter = syllabusData[grade][mode][value][0];

    setSubject(value);
    setChapter(newChapter);
  }

  function isEmbeddableYoutube(url) {
    /** Identify standard YouTube watch URLs that can be shown inside the page. */
    return url.includes("youtube.com/watch");
  }

  return (
    <div className="resources-page premium-page premium-resources-page">
      <section className="premium-section premium-resources-hero">
        <div className="premium-header">
          <p className="eyebrow">Learning Library</p>
          <h2>🎥 Learn More</h2>
          <p>
            Explore curated free resources for the selected chapter. Watch videos,
            open references, and strengthen concepts beyond the AI lesson.
          </p>
        </div>

        <div className="premium-resources-spotlight">
          <span>📚</span>
          <div>
            <strong>{subject}</strong>
            <p>{chapter}</p>
          </div>
        </div>
      </section>

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
          <p>
            Videos and references matched to your selected subject and chapter.
          </p>
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
                  <span>{resource.type === "youtube" ? "▶️" : "🔗"}</span>
                  <div>
                    <h4>{resource.title}</h4>
                    <p>{resource.type === "youtube" ? "Video resource" : "External resource"}</p>
                  </div>
                </div>

                {resource.type === "youtube" && isEmbeddableYoutube(resource.url) ? (
                  <div className="premium-video-frame">
                    <iframe
                      width="100%"
                      height="360"
                      src={resource.url.replace("watch?v=", "embed/")}
                      title={resource.title}
                      allowFullScreen
                    />
                  </div>
                ) : (
                  <a
                    className="premium-resource-link"
                    href={resource.url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open Free Resource →
                  </a>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

export default ResourcesPage;
