import { useEffect, useMemo, useState } from "react";
import { ArrowDown, ArrowUp, Plus, Save, Trash2 } from "lucide-react";

import {
  getAdminSyllabusReview,
  saveAdminSubjectOverride,
  saveAdminSyllabusOverride,
} from "../api/syllabus";

function optionKey(grade, mode, subject) {
  /** Build a stable key for one reviewed dropdown list. */
  return `${grade}__${mode}__${subject}`;
}

function normalizeChapterKey(chapter) {
  /** Match backend duplicate/content checks without changing display labels. */
  return String(chapter || "").trim().replace(/\s+/g, " ").toLowerCase();
}

function contentKey(grade, mode, subject, chapter) {
  /** Build a stable key for one chapter's live RAG content status. */
  return `${optionKey(grade, mode, subject)}__${normalizeChapterKey(chapter)}`;
}

function createDraftItem(chapter, index) {
  /** Preserve the original RAG label beside the admin-editable label. */
  return {
    id: `${index}-${chapter}`,
    original_chapter: chapter,
    chapter,
  };
}

function AdminSyllabusReviewPage({ user }) {
  /** Admin page for validating student-facing syllabus dropdowns after RAG upload. */
  const [syllabus, setSyllabus] = useState(null);
  const [overrides, setOverrides] = useState([]);
  const [subjectOverrides, setSubjectOverrides] = useState([]);
  const [contentStatus, setContentStatus] = useState([]);
  const [grade, setGrade] = useState("");
  const [mode, setMode] = useState("");
  const [activeSubject, setActiveSubject] = useState("");
  const [draftItems, setDraftItems] = useState([]);
  const [subjectDraft, setSubjectDraft] = useState([]);
  const [newSubjectName, setNewSubjectName] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savingSubjects, setSavingSubjects] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadReview() {
      /** Load the effective student dropdowns and existing admin approvals. */
      try {
        const result = await getAdminSyllabusReview(user.accessToken);
        const loadedSyllabus = result.syllabus || {};
        const firstGrade = Object.keys(loadedSyllabus)[0] || "";
        const firstMode = Object.keys(loadedSyllabus[firstGrade] || {})[0] || "";

        setSyllabus(loadedSyllabus);
        setOverrides(result.overrides || []);
        setSubjectOverrides(result.subject_overrides || []);
        setContentStatus(result.content_status || []);
        setGrade(firstGrade);
        setMode(firstMode);
        setSubjectDraft(Object.keys(loadedSyllabus?.[firstGrade]?.[firstMode] || {}));
      } catch (err) {
        console.error(err);
        setError(err.message || "Unable to load syllabus review.");
      } finally {
        setLoading(false);
      }
    }

    if (user?.accessToken) {
      loadReview();
    }
  }, [user?.accessToken]);

  const overrideKeys = useMemo(() => {
    /** Mark grade/mode/subject combinations that already have a saved review. */
    return new Set(
      overrides.map((item) => optionKey(item.grade, item.mode, item.subject))
    );
  }, [overrides]);

  const subjectOverrideKeys = useMemo(() => {
    /** Mark class/mode combinations that have reviewed visible subjects. */
    return new Set(
      subjectOverrides.map((item) => optionKey(item.grade, item.mode, "__subjects"))
    );
  }, [subjectOverrides]);

  const contentStatusByKey = useMemo(() => {
    /** Index live RAG document availability for quick UI status checks. */
    const statusMap = new Map();

    contentStatus.forEach((item) => {
      statusMap.set(
        contentKey(item.grade, item.mode, item.subject, item.chapter),
        item
      );
    });

    return statusMap;
  }, [contentStatus]);

  function getChapterStatus(subjectName, chapterName) {
    /** Return the live RAG status for one currently selected chapter label. */
    return contentStatusByKey.get(contentKey(
      grade,
      mode,
      subjectName,
      chapterName
    ));
  }

  if (user.role !== "admin") {
    return (
      <div className="premium-page">
        <section className="premium-section">
          <p className="error">Admin access required.</p>
        </section>
      </div>
    );
  }

  if (loading) {
    return <p>Loading syllabus review...</p>;
  }

  const gradeOptions = Object.keys(syllabus || {});
  const modeOptions = Object.keys(syllabus?.[grade] || {});
  const subjectEntries = Object.entries(syllabus?.[grade]?.[mode] || {});
  const subjectsReviewed = subjectOverrideKeys.has(optionKey(
    grade,
    mode,
    "__subjects"
  ));

  function handleGradeChange(value) {
    /** Reset mode/subject editor when changing class. */
    const nextMode = Object.keys(syllabus?.[value] || {})[0] || "";

    setGrade(value);
    setMode(nextMode);
    setActiveSubject("");
    setDraftItems([]);
    setSubjectDraft(Object.keys(syllabus?.[value]?.[nextMode] || {}));
  }

  function handleModeChange(value) {
    /** Reset the editor when switching CBSE/SOF. */
    setMode(value);
    setActiveSubject("");
    setDraftItems([]);
    setSubjectDraft(Object.keys(syllabus?.[grade]?.[value] || {}));
  }

  function removeSubject(subjectName) {
    /** Hide one subject from the selected grade/mode. */
    setSubjectDraft((currentSubjects) =>
      currentSubjects.filter((subject) => subject !== subjectName)
    );

    if (activeSubject === subjectName) {
      setActiveSubject("");
      setDraftItems([]);
    }
  }

  function addSubject() {
    /** Add a new visible subject for the selected grade/mode. */
    const subjectName = newSubjectName.trim();

    if (!subjectName) {
      return;
    }

    setSubjectDraft((currentSubjects) => {
      if (
        currentSubjects.some(
          (subject) => subject.toLowerCase() === subjectName.toLowerCase()
        )
      ) {
        return currentSubjects;
      }

      return [...currentSubjects, subjectName];
    });
    setNewSubjectName("");
  }

  async function saveSubjects() {
    /** Persist the visible subject list and update the preview immediately. */
    setSavingSubjects(true);
    setMessage("");
    setError("");

    try {
      const cleanedSubjects = subjectDraft
        .map((subject) => subject.trim())
        .filter(Boolean);
      const result = await saveAdminSubjectOverride(
        {
          grade,
          mode,
          subjects: cleanedSubjects,
        },
        user.accessToken
      );

      setSyllabus((currentSyllabus) => {
        const currentModeData = currentSyllabus?.[grade]?.[mode] || {};
        const nextModeData = {};

        cleanedSubjects.forEach((subject) => {
          nextModeData[subject] = currentModeData[subject] || [
            mode === "CBSE" ? "Uploaded Book Content" : "Uploaded SOF Chapter Content",
          ];
        });

        return {
          ...currentSyllabus,
          [grade]: {
            ...currentSyllabus[grade],
            [mode]: nextModeData,
          },
        };
      });
      setSubjectOverrides((currentOverrides) => [
        ...currentOverrides.filter(
          (item) => optionKey(item.grade, item.mode, "__subjects") !==
            optionKey(grade, mode, "__subjects")
        ),
        {
          grade,
          mode,
          subjects: cleanedSubjects,
        },
      ]);
      setActiveSubject("");
      setDraftItems([]);
      setMessage(result.message || "Subject list saved.");
    } catch (err) {
      console.error(err);
      setError(err.message || "Unable to save subject list.");
    } finally {
      setSavingSubjects(false);
    }
  }

  function startReview(subject, chapters) {
    /** Open one subject dropdown list for editing. */
    setActiveSubject(subject);
    setDraftItems(chapters.map(createDraftItem));
    setMessage("");
    setError("");
  }

  function updateDraftItem(itemId, chapter) {
    /** Rename one visible dropdown option while keeping its original mapping. */
    setDraftItems((currentItems) =>
      currentItems.map((item) =>
        item.id === itemId
          ? {
              ...item,
              chapter,
            }
          : item
      )
    );
  }

  function moveDraftItem(index, direction) {
    /** Move a dropdown option up or down in the student-facing order. */
    setDraftItems((currentItems) => {
      const nextIndex = index + direction;

      if (nextIndex < 0 || nextIndex >= currentItems.length) {
        return currentItems;
      }

      const nextItems = [...currentItems];
      [nextItems[index], nextItems[nextIndex]] = [
        nextItems[nextIndex],
        nextItems[index],
      ];

      return nextItems;
    });
  }

  function removeDraftItem(itemId) {
    /** Hide one dropdown option from the approved student list. */
    setDraftItems((currentItems) =>
      currentItems.filter((item) => item.id !== itemId)
    );
  }

  function addDraftItem() {
    /** Add a manually curated option when upload labels missed a section. */
    const nextIndex = draftItems.length + 1;
    const chapter = `New Chapter ${nextIndex}`;

    setDraftItems((currentItems) => [
      ...currentItems,
      {
        id: `new-${Date.now()}`,
        original_chapter: "",
        chapter,
      },
    ]);
  }

  async function saveReview() {
    /** Persist this subject's reviewed list and reconcile the local dropdown preview. */
    setSaving(true);
    setMessage("");
    setError("");

    try {
      const cleanedItems = draftItems
        .map((item) => ({
          original_chapter: item.original_chapter,
          chapter: item.chapter.trim(),
        }))
        .filter((item) => item.chapter);

      const result = await saveAdminSyllabusOverride(
        {
          grade,
          mode,
          subject: activeSubject,
          items: cleanedItems,
        },
        user.accessToken
      );

      setSyllabus((currentSyllabus) => ({
        ...currentSyllabus,
        [grade]: {
          ...currentSyllabus[grade],
          [mode]: {
            ...currentSyllabus[grade][mode],
            [activeSubject]: cleanedItems.map((item) => item.chapter),
          },
        },
      }));
      setOverrides((currentOverrides) => [
        ...currentOverrides.filter(
          (item) =>
            optionKey(item.grade, item.mode, item.subject) !==
            optionKey(grade, mode, activeSubject)
        ),
        {
          grade,
          mode,
          subject: activeSubject,
          chapters: cleanedItems.map((item) => item.chapter),
        },
      ]);
      setDraftItems(cleanedItems.map((item, index) =>
        createDraftItem(item.chapter, index)
      ));
      setMessage(
        result.renamed?.length
          ? `Saved. ${result.renamed.length} RAG label(s) renamed to match the dropdown.`
          : "Saved. Students will see this reviewed dropdown."
      );
    } catch (err) {
      console.error(err);
      setError(err.message || "Unable to save dropdown review.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="premium-page admin-syllabus-review-page">
      <section className="premium-section premium-rag-hero">
        <div className="premium-header">
          <p className="eyebrow">RAG Dropdown Validation</p>
          <h2>Syllabus Review</h2>
          <p>
            Preview the exact chapter dropdowns students will see after RAG upload.
            Review each class and subject, then save a clean approved list.
          </p>
        </div>
      </section>

      {message && <div className="info-box">{message}</div>}
      {error && <div className="error-box">{error}</div>}

      <section className="premium-section admin-syllabus-review-controls">
        <label>
          Class
          <select value={grade} onChange={(e) => handleGradeChange(e.target.value)}>
            {gradeOptions.map((gradeName) => (
              <option key={gradeName} value={gradeName}>
                {gradeName}
              </option>
            ))}
          </select>
        </label>

        <label>
          Mode
          <select value={mode} onChange={(e) => handleModeChange(e.target.value)}>
            {modeOptions.map((modeName) => (
              <option key={modeName} value={modeName}>
                {modeName}
              </option>
            ))}
          </select>
        </label>
      </section>

      <section className="premium-section admin-syllabus-subjects">
        <div className="premium-header">
          <h3>Visible Subjects</h3>
          <p>
            Remove subjects students should not see, or add a new subject before
            uploading its book content.
          </p>
        </div>

        <div className="admin-syllabus-subject-list">
          {subjectDraft.map((subjectName) => (
            <span key={subjectName} className="admin-syllabus-subject-chip">
              {subjectName}
              <button
                type="button"
                onClick={() => removeSubject(subjectName)}
                title={`Remove ${subjectName}`}
              >
                <Trash2 size={14} />
              </button>
            </span>
          ))}
        </div>

        <div className="admin-syllabus-subject-actions">
          <input
            value={newSubjectName}
            placeholder="Add subject, e.g. Marathi"
            onChange={(event) => setNewSubjectName(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                addSubject();
              }
            }}
          />
          <button type="button" className="secondary-btn" onClick={addSubject}>
            <Plus size={17} />
            Add Subject
          </button>
          <button
            type="button"
            className="primary-btn"
            onClick={saveSubjects}
            disabled={savingSubjects || subjectDraft.length === 0}
          >
            <Save size={17} />
            {savingSubjects ? "Saving..." : "Save Visible Subjects"}
          </button>
        </div>

        <span className={subjectsReviewed ? "review-status saved" : "review-status"}>
          {subjectsReviewed ? "Subjects reviewed" : "Subjects need review"}
        </span>
      </section>

      <section className="premium-section admin-syllabus-review-grid-section">
        <div className="premium-header">
          <h3>Student Dropdown Preview</h3>
          <p>
            These are validation dropdowns only. Use Review / Fix to adjust the
            list before students use the chapter selector.
          </p>
        </div>

        <div className="admin-syllabus-preview-grid">
          {subjectEntries.map(([subjectName, chapters]) => {
            const isReviewed = overrideKeys.has(optionKey(grade, mode, subjectName));
            const missingContentCount = chapters.filter((chapterName) => {
              const chapterStatus = getChapterStatus(subjectName, chapterName);

              return isReviewed && (!chapterStatus || !chapterStatus.has_content);
            }).length;

            return (
              <div key={subjectName} className="admin-syllabus-preview-panel">
                <div>
                  <strong>{subjectName}</strong>
                  <span>{chapters.length} option(s)</span>
                </div>

                <select aria-label={`${subjectName} chapter preview`}>
                  {chapters.map((chapterName) => (
                    <option key={chapterName} value={chapterName}>
                      {chapterName}
                    </option>
                  ))}
                </select>

                <div className="admin-syllabus-preview-actions">
                  <span className={isReviewed ? "review-status saved" : "review-status"}>
                    {isReviewed ? "Reviewed" : "Needs review"}
                  </span>
                  {isReviewed && (
                    <span
                      className={
                        missingContentCount > 0
                          ? "review-status missing"
                          : "review-status linked"
                      }
                    >
                      {missingContentCount > 0
                        ? `${missingContentCount} missing RAG`
                        : "RAG linked"}
                    </span>
                  )}
                  <button
                    type="button"
                    className="secondary-btn"
                    onClick={() => startReview(subjectName, chapters)}
                  >
                    Review / Fix
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {activeSubject && (
        <section className="premium-section admin-syllabus-editor">
          <div className="premium-header">
            <h3>{activeSubject}</h3>
            <p>
              Reorder, hide, or rename dropdown options. Renamed uploaded labels
              are also written back to RAG document metadata.
            </p>
          </div>

          <select
            className="admin-syllabus-live-select"
            defaultValue={draftItems[0]?.chapter || ""}
          >
            {draftItems.map((item) => (
              <option key={item.id} value={item.chapter}>
                {item.chapter}
              </option>
            ))}
          </select>

          <div className="admin-syllabus-draft-list">
            {draftItems.map((item, index) => (
              <div key={item.id} className="admin-syllabus-draft-row">
                <span>{index + 1}</span>
                <div className="admin-syllabus-draft-field">
                  <input
                    value={item.chapter}
                    onChange={(e) => updateDraftItem(item.id, e.target.value)}
                  />
                  {(() => {
                    const chapterStatus = getChapterStatus(activeSubject, item.chapter);

                    return (
                      <small
                        className={
                          chapterStatus?.has_content
                            ? "chapter-content-status linked"
                            : "chapter-content-status missing"
                        }
                      >
                        {chapterStatus?.has_content
                          ? `${chapterStatus.document_count} RAG document(s) linked`
                          : "No matching RAG document right now"}
                      </small>
                    );
                  })()}
                </div>
                <div>
                  <button
                    type="button"
                    onClick={() => moveDraftItem(index, -1)}
                    disabled={index === 0}
                    title="Move up"
                  >
                    <ArrowUp size={16} />
                  </button>
                  <button
                    type="button"
                    onClick={() => moveDraftItem(index, 1)}
                    disabled={index === draftItems.length - 1}
                    title="Move down"
                  >
                    <ArrowDown size={16} />
                  </button>
                  <button
                    type="button"
                    onClick={() => removeDraftItem(item.id)}
                    title="Hide from dropdown"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div className="admin-syllabus-editor-actions">
            <button type="button" className="secondary-btn" onClick={addDraftItem}>
              <Plus size={17} />
              Add Option
            </button>
            <button
              type="button"
              className="primary-btn"
              onClick={saveReview}
              disabled={saving || draftItems.length === 0}
            >
              <Save size={17} />
              {saving ? "Saving..." : "Save Reviewed Dropdown"}
            </button>
          </div>
        </section>
      )}
    </div>
  );
}

export default AdminSyllabusReviewPage;
