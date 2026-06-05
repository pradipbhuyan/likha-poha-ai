import { useEffect, useState } from "react";

import { getSyllabus } from "../api/syllabus";
import { getResources } from "../api/resources";
import {
  getDefaultSelection,
  getUserGrade,
  getVisibleGrades,
} from "../utils/syllabusDefaults";
import { filterAllowedSubjects } from "../utils/subjectAccess";

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
        } = getDefaultSelection(data.syllabus, getUserGrade(user));
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
  const chapters = syllabusData[grade][mode][subject] || [];

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
      ? syllabusData[selectedGrade][selectedMode][nextSubject][0]
      : "";

    return {
      subject: nextSubject,
      chapter: nextChapter,
    };
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
