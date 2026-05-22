import { useEffect, useState } from "react";

import { getSyllabus } from "../api/syllabus";
import { getResources } from "../api/resources";

function ResourcesPage() {
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
    const newMode = Object.keys(syllabusData[value])[0];
    const newSubject = Object.keys(syllabusData[value][newMode])[0];
    const newChapter = syllabusData[value][newMode][newSubject][0];

    setGrade(value);
    setMode(newMode);
    setSubject(newSubject);
    setChapter(newChapter);
  }

  function handleModeChange(value) {
    const newSubject = Object.keys(syllabusData[grade][value])[0];
    const newChapter = syllabusData[grade][value][newSubject][0];

    setMode(value);
    setSubject(newSubject);
    setChapter(newChapter);
  }

  function handleSubjectChange(value) {
    const newChapter = syllabusData[grade][mode][value][0];

    setSubject(value);
    setChapter(newChapter);
  }

  function isEmbeddableYoutube(url) {
    return url.includes("youtube.com/watch");
  }

  return (
    <div className="resources-page">
      <h2>🎥 Learn More</h2>

      <div className="card">
        <h3>Select Topic</h3>

        <div className="form-grid">
          <label>
            Grade
            <select value={grade} onChange={(e) => handleGradeChange(e.target.value)}>
              {grades.map((g) => (
                <option key={g} value={g}>{g}</option>
              ))}
            </select>
          </label>

          <label>
            Mode
            <select value={mode} onChange={(e) => handleModeChange(e.target.value)}>
              {modes.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </label>

          <label>
            Subject
            <select value={subject} onChange={(e) => handleSubjectChange(e.target.value)}>
              {subjects.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </label>

          <label>
            Chapter / Section
            <select value={chapter} onChange={(e) => setChapter(e.target.value)}>
              {chapters.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </label>
        </div>
      </div>

      <div className="card">
        <h3>Free Learning Resources</h3>

        {resourcesLoading && <p>Loading resources...</p>}

        {!resourcesLoading && resources.length === 0 && (
          <p>No resources found.</p>
        )}

        {!resourcesLoading &&
          resources.map((resource, index) => (
            <div key={index} className="resource-card">
              <h4>{resource.title}</h4>

              {resource.type === "youtube" && isEmbeddableYoutube(resource.url) ? (
                <iframe
                  width="100%"
                  height="360"
                  src={resource.url.replace("watch?v=", "embed/")}
                  title={resource.title}
                  allowFullScreen
                />
              ) : (
                <a href={resource.url} target="_blank" rel="noreferrer">
                  Open Free Resource
                </a>
              )}
            </div>
          ))}
      </div>
    </div>
  );
}

export default ResourcesPage;