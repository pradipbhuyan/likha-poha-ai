import { useEffect, useState } from "react";
import {
  getAdminFamilies,
  createAdminParent,
  createAdminChild,
  createAdminStudent,
  createAdminTeacher,
  assignTeacherStudent,
  deleteTeacherAssignment,
  updateChildAccess,
  updateChildLimits,
  deleteUser,
  getAiSettings,
  updateAiSettings,
  listOfferCodes,
  createOfferCode,
  deactivateOfferCode,
} from "../api/adminControl";
import {
  SUBSCRIPTION_PLAN_ORDER,
  SUBSCRIPTION_PLANS,
} from "../config/subscriptionPlans";
import {
  COMMON_CBSE_SUBJECTS,
  normalizeSubjectName,
  parseSubjectList,
} from "../utils/subjectAccess";

const STUDENT_GRADE_OPTIONS = Array.from(
  { length: 10 },
  (_, index) => `Grade ${index + 1}`
);

const STUDENT_BOARD_OPTIONS = ["CBSE", "ICSE", "State Board"];

const AI_MODEL_OPTIONS = [
  {
    value: "default",
    label: "Default (gpt-4.1-nano — all plans)",
  },
  {
    value: "gpt-4.1-mini",
    label: "gpt-4.1-mini (faster, higher quality)",
  },
  {
    value: "gpt-4.1",
    label: "gpt-4.1 (full — highest quality)",
  },
];

const UNLIMITED_TOKEN_LIMIT = 0;

function normalizeTokenLimit(value) {
  /** Normalize form values so zero explicitly means unlimited token access. */
  const numericValue = Number(value);
  return Number.isFinite(numericValue) && numericValue > 0
    ? Math.floor(numericValue)
    : UNLIMITED_TOKEN_LIMIT;
}

function hasUnlimitedTokenAccess(child) {
  /** A student is unlimited only when both daily and monthly caps are disabled. */
  return (
    normalizeTokenLimit(child.daily_token_limit) === UNLIMITED_TOKEN_LIMIT &&
    normalizeTokenLimit(child.monthly_token_limit) === UNLIMITED_TOKEN_LIMIT
  );
}

function getFamilyDisplayName(family) {
  /** Prefer human-readable family labels over UUIDs in the admin roster. */
  const parents = family.parents || [];
  const children = family.children || [];
  const firstParent = parents[0]?.username?.trim();
  const firstChild = children[0]?.username?.trim();

  if (firstParent) return `${firstParent} Family`;
  if (firstChild) return `${firstChild}'s Family`;
  if (family.family_id === "no-family") return "Unassigned Accounts";

  return `Family ${String(family.family_id || "").slice(0, 8)}`;
}

function getChildCbseSubjects(child) {
  /** Return a normalized array for the child's custom CBSE subject access. */
  return Array.isArray(child.cbse_subjects)
    ? child.cbse_subjects
    : parseSubjectList(child.cbse_subjects || "");
}

function subjectListToText(subjects) {
  /** Render subject access arrays in a form-friendly comma list. */
  return Array.isArray(subjects) ? subjects.join(", ") : subjects || "";
}

function AdminControlPage({ user }) {
  /** Admin operations page for managing families, access, subscriptions, and AI limits. */
  const [families, setFamilies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  // ---- AI Settings state ----
  const [aiEnabled, setAiEnabled] = useState(true);
  const [aiKeyPrefix, setAiKeyPrefix] = useState("");
  const [aiKeySource, setAiKeySource] = useState("environment");
  const [newApiKey, setNewApiKey] = useState("");
  const [aiSettingsLoading, setAiSettingsLoading] = useState(true);
  const [aiSettingsSaving, setAiSettingsSaving] = useState(false);
  const [aiSettingsMessage, setAiSettingsMessage] = useState("");
  const [aiSettingsError, setAiSettingsError] = useState("");

  const [parentForm, setParentForm] = useState({
    email: "",
    password: "",
    username: "",
    skip_email_confirmation: false,
  });

  const [teacherForm, setTeacherForm] = useState({
    email: "",
    password: "",
    username: "",
    teacher_type: "independent",
    school_name: "",
    subjectsCsv: "Science, Maths, English",
    gradesCsv: "Grade 9",
    status: "active",
  });

  const [studentForm, setStudentForm] = useState({
    email: "",
    password: "",
    username: "",
    grade: "Grade 9",
    board: "CBSE",
    skip_email_confirmation: true,
  });
  const [studentMsg, setStudentMsg] = useState("");
  const [studentErr, setStudentErr] = useState("");

  const [offerCodes, setOfferCodes] = useState([]);
  const [offerCodesLoading, setOfferCodesLoading] = useState(false);
  const [offerForm, setOfferForm] = useState({
    description: "",
    valid_until: "",
    max_uses: 100,
  });
  const [offerMsg, setOfferMsg] = useState("");
  const [offerErr, setOfferErr] = useState("");

  const [childForms, setChildForms] = useState({});
  const [assignmentForms, setAssignmentForms] = useState({});

  async function loadFamilies() {
    /** Fetch all families with their parents and children for admin editing. */
    try {
      const data = await getAdminFamilies(user.accessToken);
      setFamilies(data.families || []);
    } catch (err) {
      console.error(err);
      setError("Unable to load admin control data.");
    } finally {
      setLoading(false);
    }
  }

  async function loadAiSettings() {
    /** Fetch current AI master switch state and key prefix from the backend. */
    setAiSettingsLoading(true);
    try {
      const data = await getAiSettings(user.accessToken);
      setAiEnabled(data.api_enabled ?? true);
      setAiKeyPrefix(data.api_key_prefix || "");
      setAiKeySource(data.key_source || "environment");
    } catch (err) {
      console.error(err);
    } finally {
      setAiSettingsLoading(false);
    }
  }

  async function saveAiSettings(overrideEnabled) {
    /** Persist the master switch and optional new key, then refresh the displayed prefix. */
    const enabledValue = overrideEnabled !== undefined ? overrideEnabled : aiEnabled;
    setAiSettingsSaving(true);
    setAiSettingsMessage("");
    setAiSettingsError("");
    try {
      const payload = { api_enabled: enabledValue };
      if (newApiKey.trim()) {
        payload.openai_api_key = newApiKey.trim();
      }
      const data = await updateAiSettings(payload, user.accessToken);
      setAiEnabled(data.api_enabled ?? true);
      setAiKeyPrefix(data.api_key_prefix || "");
      setAiKeySource(data.key_source || "database");
      setNewApiKey("");
      setAiSettingsMessage(
        data.api_enabled
          ? "AI API is ON — lessons and doubts work normally."
          : "AI API is OFF — all AI features are disabled for all users."
      );
    } catch (err) {
      setAiSettingsError(err.message || "Unable to save AI settings.");
    } finally {
      setAiSettingsSaving(false);
    }
  }

  useEffect(() => {
    if (user?.accessToken) {
      loadFamilies();
      loadAiSettings();
    }
  }, [user?.accessToken]);

  async function handleCreateParent(e) {
    /** Create a parent account and refresh the family list. */
    e.preventDefault();
    setMessage("");
    setError("");

    try {
      const payload = {
        email: parentForm.email,
        username: parentForm.username,
        skip_email_confirmation: parentForm.skip_email_confirmation,
      };

      // Only send password when admin explicitly bypasses email confirmation
      if (parentForm.skip_email_confirmation && parentForm.password) {
        payload.password = parentForm.password;
      }

      await createAdminParent(payload, user.accessToken);

      setParentForm({
        email: "",
        password: "",
        username: "",
        skip_email_confirmation: false,
      });

      await loadFamilies();
      setMessage("Parent created successfully.");
    } catch (err) {
      console.error(err);
      setError(err.message || "Unable to create parent.");
    }
  }

  async function handleCreateChild(e, familyId, parentId) {
    /** Create a child account under an existing family and parent. */
    e.preventDefault();
    setMessage("");
    setError("");

    const form = childForms[parentId] || {
      email: "",
      password: "",
      username: "",
      grade: "Grade 9",
      board: "CBSE",
    };

    try {
      await createAdminChild(
        {
          ...form,
          parent_id: parentId,
          family_id: familyId,
        },
        user.accessToken
      );

      setChildForms((prev) => ({
        ...prev,
        [parentId]: {
          email: "",
          password: "",
          username: "",
          grade: "Grade 9",
          board: "CBSE",
        },
      }));

      await loadFamilies();
      setMessage("Child created successfully.");
    } catch (err) {
      console.error(err);
      setError(err.message || "Unable to create child.");
    }
  }

  function parseCsvList(value) {
    /** Convert admin comma-separated inputs into clean API arrays. */
    return String(value || "")
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }

  async function handleCreateStudent(e) {
    /** Create a standalone student from the admin panel (no parent required). */
    e.preventDefault();
    setStudentMsg("");
    setStudentErr("");
    try {
      await createAdminStudent(
        {
          email: studentForm.email,
          username: studentForm.username,
          password: studentForm.skip_email_confirmation ? studentForm.password : undefined,
          grade: studentForm.grade,
          board: studentForm.board,
          skip_email_confirmation: studentForm.skip_email_confirmation,
        },
        user.accessToken
      );
      setStudentForm({ email: "", password: "", username: "", grade: "Grade 9", board: "CBSE", skip_email_confirmation: true });
      setStudentMsg("✅ Student created successfully!");
      await loadFamilies();
    } catch (err) {
      setStudentErr(err.message || "Unable to create student.");
    }
  }

  async function loadOfferCodes() {
    setOfferCodesLoading(true);
    try {
      const data = await listOfferCodes(user.accessToken);
      setOfferCodes(data.offer_codes || []);
    } catch {
      // offer_codes table may not exist yet — silently ignore
    } finally {
      setOfferCodesLoading(false);
    }
  }

  async function handleCreateOfferCode(e) {
    e.preventDefault();
    setOfferMsg("");
    setOfferErr("");
    if (!offerForm.valid_until) { setOfferErr("Valid Until date is required."); return; }
    try {
      const data = await createOfferCode(
        { description: offerForm.description, valid_until: offerForm.valid_until, max_uses: Number(offerForm.max_uses) || 100 },
        user.accessToken
      );
      setOfferMsg(`✅ Code created: ${data.offer_code?.code || "—"}`);
      setOfferForm({ description: "", valid_until: "", max_uses: 100 });
      await loadOfferCodes();
    } catch (err) {
      setOfferErr(err.message || "Unable to create offer code.");
    }
  }

  async function handleDeactivateOfferCode(codeId) {
    if (!window.confirm("Deactivate this offer code? Users with existing redemptions keep their access.")) return;
    try {
      await deactivateOfferCode(codeId, user.accessToken);
      await loadOfferCodes();
    } catch (err) {
      setOfferErr(err.message || "Unable to deactivate.");
    }
  }

  async function handleCreateTeacher(e) {
    /** Create a teacher account that can later be assigned students. */
    e.preventDefault();
    setMessage("");
    setError("");

    try {
      await createAdminTeacher(
        {
          email: teacherForm.email,
          password: teacherForm.password,
          username: teacherForm.username,
          teacher_type: teacherForm.teacher_type,
          school_name: teacherForm.school_name,
          subjects: parseCsvList(teacherForm.subjectsCsv),
          grades: parseCsvList(teacherForm.gradesCsv),
          status: teacherForm.status,
        },
        user.accessToken
      );

      setTeacherForm({
        email: "",
        password: "",
        username: "",
        teacher_type: "independent",
        school_name: "",
        subjectsCsv: "Science, Maths, English",
        gradesCsv: "Grade 9",
        status: "active",
      });

      await loadFamilies();
      setMessage("Teacher created successfully.");
    } catch (err) {
      console.error(err);
      setError(err.message || "Unable to create teacher.");
    }
  }

  async function handleAssignTeacherStudent(e, teacher, allStudents) {
    /** Link one existing student to a teacher with optional class context. */
    e.preventDefault();
    setMessage("");
    setError("");

    const form = assignmentForms[teacher.id] || {};
    const studentId = form.student_id || allStudents[0]?.id;
    const student = allStudents.find((item) => item.id === studentId);

    if (!studentId) {
      setError("Create a student before assigning them to a teacher.");
      return;
    }

    try {
      await assignTeacherStudent(
        {
          teacher_id: teacher.id,
          student_id: studentId,
          grade: form.grade || student?.grade || "Grade 9",
          subject: form.subject || "",
          section: form.section || "",
        },
        user.accessToken
      );

      setAssignmentForms((prev) => ({
        ...prev,
        [teacher.id]: {
          student_id: "",
          subject: "",
          section: "",
        },
      }));

      await loadFamilies();
      setMessage(`Student assigned to ${teacher.username}.`);
    } catch (err) {
      console.error(err);
      setError(err.message || "Unable to assign student.");
    }
  }

  async function removeTeacherAssignment(assignmentId) {
    /** Remove one teacher-student link and refresh the admin page. */
    setMessage("");
    setError("");

    try {
      await deleteTeacherAssignment(assignmentId, user.accessToken);
      await loadFamilies();
      setMessage("Teacher assignment removed.");
    } catch (err) {
      console.error(err);
      setError(err.message || "Unable to remove teacher assignment.");
    }
  }

  async function suspendChild(child) {
    /** Mark a child account as suspended using the same plan-saving path. */
    const updatedChild = {
      ...child,
      account_status: "suspended",
    };
  
    await savePlan(updatedChild);
  }
  
  async function reactivateChild(child) {
    /** Restore a suspended child account to active status. */
    const updatedChild = {
      ...child,
      account_status: "active",
    };
  
    await savePlan(updatedChild);
  }

  async function savePlan(child) {
    /** Save both subscription access and token limits so plan changes stay consistent. */
    setMessage("");
    setError("");
  
    try {
      await updateChildAccess(
        child.id,
        {
          access_cbse: !!child.access_cbse,
          access_sof_science: !!child.access_sof_science,
          access_sof_maths: !!child.access_sof_maths,
          access_sof_english: !!child.access_sof_english,
          subscription_plan: child.subscription_plan || "free",
          account_status: child.account_status || "active",
          grade: child.grade || "Grade 9",
          ai_model_preference: child.ai_model_preference || "default",
          cbse_subjects: getChildCbseSubjects(child),
        },
        user.accessToken
      );
  
      await updateChildLimits(
        child.id,
        {
          daily_token_limit: normalizeTokenLimit(child.daily_token_limit),
          monthly_token_limit: normalizeTokenLimit(child.monthly_token_limit),
        },
        user.accessToken
      );
  
      await loadFamilies();
      setMessage(`Plan saved for ${child.username}.`);
    } catch (err) {
      console.error(err);
      setError("Unable to save plan.");
    }
  }

  async function saveAll(child) {
    /**
     * Save all child settings in one click: plan, access flags, AI model,
     * board, grade, status, token limits, and CBSE subject access.
     * Replaces the three separate Save Plan / Save Access / Save Limits buttons.
     */
    setMessage("");
    setError("");

    try {
      await updateChildAccess(
        child.id,
        {
          access_cbse: !!child.access_cbse,
          access_sof_science: !!child.access_sof_science,
          access_sof_maths: !!child.access_sof_maths,
          access_sof_english: !!child.access_sof_english,
          subscription_plan: child.subscription_plan || "free",
          account_status: child.account_status || "active",
          grade: child.grade || "Grade 9",
          board: child.board || "CBSE",
          ai_model_preference: child.ai_model_preference || "default",
          cbse_subjects: getChildCbseSubjects(child),
        },
        user.accessToken
      );

      await updateChildLimits(
        child.id,
        {
          daily_token_limit: normalizeTokenLimit(child.daily_token_limit),
          monthly_token_limit: normalizeTokenLimit(child.monthly_token_limit),
        },
        user.accessToken
      );

      await loadFamilies();
      setMessage(`✅ All changes saved for ${child.username}.`);
    } catch (err) {
      console.error(err);
      setError(`Unable to save changes for ${child.username}.`);
    }
  }

  async function removeUser(userId) {
    /** Delete a user after confirmation and reload the admin roster. */
    setMessage("");
    setError("");

    if (!window.confirm("Delete this user? This cannot be undone.")) return;

    try {
      await deleteUser(userId, user.accessToken);
      await loadFamilies();
      setMessage("User deleted successfully.");
    } catch (err) {
      console.error(err);
      setError("Unable to delete user.");
    }
  }

  function applyPlanPreset(familyId, childId, planName) {
    /** Apply a configured subscription preset to local child state before saving it. */
    const preset = SUBSCRIPTION_PLANS[planName];
  
    if (!preset) return;
  
    setFamilies((prev) =>
      prev.map((family) => {
        if (family.family_id !== familyId) return family;
  
        return {
          ...family,
          children: family.children.map((child) =>
            child.id === childId
              ? {
                  ...child,
                  subscription_plan: planName,
                  access_cbse: preset.access_cbse,
                  access_sof_science: preset.access_sof_science,
                  access_sof_maths: preset.access_sof_maths,
                  access_sof_english: preset.access_sof_english,
                  daily_token_limit: preset.daily_token_limit,
                  monthly_token_limit: preset.monthly_token_limit,
                  cbse_subjects: [],
                }
              : child
          ),
        };
      })
    );
  }

  function updateTokenAccessMode(familyId, childId, mode) {
    /** Switch between unlimited access and the selected plan's normal token caps. */
    setFamilies((prev) =>
      prev.map((family) => {
        if (family.family_id !== familyId) return family;

        return {
          ...family,
          children: family.children.map((child) => {
            if (child.id !== childId) return child;

            if (mode === "unlimited") {
              return {
                ...child,
                daily_token_limit: UNLIMITED_TOKEN_LIMIT,
                monthly_token_limit: UNLIMITED_TOKEN_LIMIT,
              };
            }

            const preset = SUBSCRIPTION_PLANS[child.subscription_plan || "free"];

            return {
              ...child,
              daily_token_limit: preset?.daily_token_limit || 50000,
              monthly_token_limit: preset?.monthly_token_limit || 1000000,
            };
          }),
        };
      })
    );
  }


  function updateLocalChild(familyId, childId, field, value) {
    /** Update a child field locally inside the nested family list. */
    setFamilies((prev) =>
      prev.map((family) => {
        if (family.family_id !== familyId) return family;

        return {
          ...family,
          children: family.children.map((child) =>
            child.id === childId ? { ...child, [field]: value } : child
          ),
        };
      })
    );
  }

  function updateChildCbseSubjects(familyId, childId, value) {
    /** Store the custom CBSE subject list locally while the admin edits it. */
    updateLocalChild(familyId, childId, "cbse_subjects", parseSubjectList(value));
  }

  function toggleChildCbseSubject(familyId, childId, child, subjectName, checked) {
    /** Toggle one common CBSE subject inside the child's custom subject list. */
    const currentSubjects = getChildCbseSubjects(child);
    const subjectKey = normalizeSubjectName(subjectName);
    const withoutSubject = currentSubjects.filter(
      (item) => normalizeSubjectName(item) !== subjectKey
    );
    const nextSubjects = checked
      ? [...withoutSubject, subjectName]
      : withoutSubject;

    updateLocalChild(familyId, childId, "cbse_subjects", nextSubjects);
  }

  function updateChildForm(parentId, field, value) {
    /** Track per-parent child creation forms without mixing family rows. */
    setChildForms((prev) => ({
      ...prev,
      [parentId]: {
        email: "",
        password: "",
        username: "",
        ...(prev[parentId] || {}),
        [field]: value,
      },
    }));
  }

  function updateAssignmentForm(teacherId, field, value) {
    /** Track per-teacher student assignment forms independently. */
    setAssignmentForms((prev) => ({
      ...prev,
      [teacherId]: {
        ...(prev[teacherId] || {}),
        [field]: value,
      },
    }));
  }

  // Load offer codes when the AI settings panel loads
  useEffect(() => {
    if (user?.accessToken) loadOfferCodes();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.accessToken]);

  if (loading) return <p>Loading admin control...</p>;

  // ---- AI Settings panel (rendered at top of page) ----
  const aiSettingsPanel = (
    <section className="premium-section">
      <div className="premium-header">
        <p className="eyebrow">Platform Configuration</p>
        <h3>🔑 AI API Settings</h3>
        <p>Control the OpenAI master switch and set the API key used across the entire platform.</p>
      </div>

      {aiSettingsLoading ? (
        <p>Loading AI settings…</p>
      ) : (
        <div className="premium-card" style={{ maxWidth: 620 }}>
          {/* Master switch */}
          <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 20 }}>
            <strong style={{ fontSize: "1rem" }}>Master AI Switch</strong>
            <label style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }}>
              <div
                onClick={() => {
                  const next = !aiEnabled;
                  setAiEnabled(next);
                  saveAiSettings(next);
                }}
                style={{
                  width: 52,
                  height: 28,
                  borderRadius: 14,
                  background: aiEnabled ? "var(--accent, #6c63ff)" : "#ccc",
                  position: "relative",
                  cursor: "pointer",
                  transition: "background 0.2s",
                  flexShrink: 0,
                }}
              >
                <div
                  style={{
                    position: "absolute",
                    top: 3,
                    left: aiEnabled ? 27 : 3,
                    width: 22,
                    height: 22,
                    borderRadius: "50%",
                    background: "#fff",
                    transition: "left 0.2s",
                    boxShadow: "0 1px 4px rgba(0,0,0,0.2)",
                  }}
                />
              </div>
              <span style={{ fontWeight: 600, color: aiEnabled ? "var(--accent, #6c63ff)" : "#999" }}>
                {aiEnabled ? "API ON" : "API OFF"}
              </span>
            </label>
            {!aiEnabled && (
              <span className="error-box" style={{ padding: "4px 10px", fontSize: "0.8rem", margin: 0 }}>
                All AI features are disabled for all users
              </span>
            )}
          </div>

          {/* Active key indicator */}
          <div style={{ marginBottom: 20 }}>
            <strong>Active Key</strong>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 6 }}>
              <code
                style={{
                  background: "var(--surface2, #f5f5f5)",
                  padding: "6px 12px",
                  borderRadius: 6,
                  fontFamily: "monospace",
                  fontSize: "0.95rem",
                  letterSpacing: 2,
                }}
              >
                {aiKeyPrefix ? `${aiKeyPrefix}••••••••••••••••` : "No key stored"}
              </code>
              <span style={{ fontSize: "0.8rem", color: "#888" }}>
                ({aiKeySource === "database" ? "set via admin console" : "from environment variable"})
              </span>
            </div>
          </div>

          {/* New key input */}
          <label style={{ display: "block", marginBottom: 16 }}>
            <strong>Update API Key</strong>
            <p style={{ fontSize: "0.82rem", color: "#888", margin: "4px 0 8px" }}>
              Paste a new OpenAI key to replace the current one. Leave blank to keep the existing key.
            </p>
            <input
              type="password"
              value={newApiKey}
              onChange={(e) => setNewApiKey(e.target.value)}
              placeholder="sk-proj-… or sk-…"
              style={{ width: "100%", fontFamily: "monospace" }}
              autoComplete="new-password"
            />
          </label>

          <button
            className="primary-btn"
            onClick={() => saveAiSettings()}
            disabled={aiSettingsSaving}
          >
            {aiSettingsSaving ? "Saving…" : "💾 Save AI Settings"}
          </button>

          {aiSettingsMessage && (
            <div className="info-box" style={{ marginTop: 12 }}>{aiSettingsMessage}</div>
          )}
          {aiSettingsError && (
            <div className="error-box" style={{ marginTop: 12 }}>{aiSettingsError}</div>
          )}
        </div>
      )}
    </section>
  );

  const allTeachers = families.flatMap((family) => family.teachers || []);
  const allStudents = families.flatMap((family) => family.children || []);
  const allParents = families.flatMap((family) => family.parents || []);
  const activeStudents = allStudents.filter(
    (student) => (student.account_status || "active") === "active"
  );
  const studentById = Object.fromEntries(
    allStudents.map((student) => [student.id, student])
  );

  return (
    <div className="premium-page admin-control-page">
      {aiSettingsPanel}

      <section className="premium-section admin-control-hero">
        <div className="premium-header">
          <p className="eyebrow">Admin Operations</p>
          <h2>🛠️ Admin Control Center</h2>
          <p>Manage accounts, teacher access, subscriptions, and AI limits from one workspace.</p>
        </div>

        <div className="admin-overview-grid">
          <div className="admin-overview-card">
            <span>Families</span>
            <strong>{families.length}</strong>
          </div>

          <div className="admin-overview-card">
            <span>Parents</span>
            <strong>{allParents.length}</strong>
          </div>

          <div className="admin-overview-card">
            <span>Students</span>
            <strong>{allStudents.length}</strong>
            <small>{activeStudents.length} active</small>
          </div>

          <div className="admin-overview-card">
            <span>Teachers</span>
            <strong>{allTeachers.length}</strong>
          </div>
        </div>
      </section>

      {message && <div className="info-box">{message}</div>}
      {error && <div className="error-box">{error}</div>}

      <section className="premium-section admin-create-section">
        <div className="premium-header">
          <p className="eyebrow">Quick Create</p>
          <h3>Accounts</h3>
          <p>Create parent families and teacher logins without leaving the admin console.</p>
        </div>

        <div className="admin-create-grid">
          <div className="admin-create-card">
            <div className="admin-card-heading">
              <span>👨‍👩‍👧</span>
              <div>
                <h3>Create New Parent</h3>
                <p>Create a new family with one parent account.</p>
              </div>
            </div>

            <form
              onSubmit={handleCreateParent}
              className="form-grid premium-rag-form-grid admin-compact-form"
            >
              <label>
                Parent Name
                <input
                  type="text"
                  value={parentForm.username}
                  onChange={(e) =>
                    setParentForm((prev) => ({
                      ...prev,
                      username: e.target.value,
                    }))
                  }
                  required
                />
              </label>

              <label>
                Parent Email
                <input
                  type="email"
                  value={parentForm.email}
                  onChange={(e) =>
                    setParentForm((prev) => ({
                      ...prev,
                      email: e.target.value,
                    }))
                  }
                  required
                />
              </label>

              {!parentForm.skip_email_confirmation && (
                <div className="info-box" style={{ gridColumn: "1 / -1", fontSize: "0.85rem" }}>
                  📧 An invitation email will be sent to the parent. They must click the link to verify their email and set their own password before they can log in.
                </div>
              )}

              <label style={{ gridColumn: "1 / -1" }}>
                <input
                  type="checkbox"
                  checked={parentForm.skip_email_confirmation}
                  onChange={(e) =>
                    setParentForm((prev) => ({
                      ...prev,
                      skip_email_confirmation: e.target.checked,
                      password: "",
                    }))
                  }
                />{" "}
                In-person onboarding — skip email confirmation and set password directly
              </label>

              {parentForm.skip_email_confirmation && (
                <label>
                  Temporary Password
                  <input
                    type="password"
                    value={parentForm.password}
                    onChange={(e) =>
                      setParentForm((prev) => ({
                        ...prev,
                        password: e.target.value,
                      }))
                    }
                    required={parentForm.skip_email_confirmation}
                    placeholder="Required for in-person onboarding"
                  />
                </label>
              )}

              <button className="primary-btn" type="submit">
                {parentForm.skip_email_confirmation ? "Create Parent (Immediate Access)" : "Send Invite Email"}
              </button>
            </form>
          </div>

          <div className="admin-create-card">
            <div className="admin-card-heading">
              <span>🎓</span>
              <div>
                <h3>Teacher Accounts</h3>
                <p>Create teacher logins for schools or independent teachers.</p>
              </div>
            </div>

            <form
              onSubmit={handleCreateTeacher}
              className="form-grid premium-rag-form-grid admin-compact-form"
            >
              <label>
                Teacher Name
                <input
                  type="text"
                  value={teacherForm.username}
                  onChange={(e) =>
                    setTeacherForm((prev) => ({
                      ...prev,
                      username: e.target.value,
                    }))
                  }
                  required
                />
              </label>

              <label>
                Teacher Email
                <input
                  type="email"
                  value={teacherForm.email}
                  onChange={(e) =>
                    setTeacherForm((prev) => ({
                      ...prev,
                      email: e.target.value,
                    }))
                  }
                  required
                />
              </label>

              <label>
                Temporary Password
                <input
                  type="password"
                  value={teacherForm.password}
                  onChange={(e) =>
                    setTeacherForm((prev) => ({
                      ...prev,
                      password: e.target.value,
                    }))
                  }
                  required
                />
              </label>

              <label>
                Teacher Type
                <select
                  value={teacherForm.teacher_type}
                  onChange={(e) =>
                    setTeacherForm((prev) => ({
                      ...prev,
                      teacher_type: e.target.value,
                    }))
                  }
                >
                  <option value="independent">Independent Teacher</option>
                  <option value="school">School Teacher</option>
                </select>
              </label>

              <label>
                School / Organization
                <input
                  type="text"
                  value={teacherForm.school_name}
                  onChange={(e) =>
                    setTeacherForm((prev) => ({
                      ...prev,
                      school_name: e.target.value,
                    }))
                  }
                  placeholder="Optional for independent teachers"
                />
              </label>

              <label>
                Status
                <select
                  value={teacherForm.status}
                  onChange={(e) =>
                    setTeacherForm((prev) => ({
                      ...prev,
                      status: e.target.value,
                    }))
                  }
                >
                  <option value="active">Active</option>
                  <option value="suspended">Suspended</option>
                </select>
              </label>

              <label>
                Subjects
                <input
                  type="text"
                  value={teacherForm.subjectsCsv}
                  onChange={(e) =>
                    setTeacherForm((prev) => ({
                      ...prev,
                      subjectsCsv: e.target.value,
                    }))
                  }
                  placeholder="Science, Maths, English"
                />
              </label>

              <label>
                Grades
                <input
                  type="text"
                  value={teacherForm.gradesCsv}
                  onChange={(e) =>
                    setTeacherForm((prev) => ({
                      ...prev,
                      gradesCsv: e.target.value,
                    }))
                  }
                  placeholder="Grade 6, Grade 7, Grade 9"
                />
              </label>

              <button className="primary-btn admin-teacher-create-btn" type="submit">
                Create Teacher
              </button>
            </form>
          </div>
        </div>

        {/* ── Create Student Card ── */}
        <div style={{ marginTop: 32 }}>
          <div className="premium-header" style={{ marginBottom: 16 }}>
            <p className="eyebrow">Quick Create</p>
            <h3>🎓 Create Student</h3>
            <p>Create a standalone student account. Optionally link to a parent later.</p>
          </div>
          <div className="admin-create-grid">
            <div className="admin-create-card" style={{ gridColumn: "1 / -1" }}>
              <form onSubmit={handleCreateStudent} className="form-grid premium-rag-form-grid admin-compact-form">
                <label>
                  Student Name
                  <input type="text" value={studentForm.username} onChange={e => setStudentForm(p => ({ ...p, username: e.target.value }))} required />
                </label>
                <label>
                  Student Email
                  <input type="email" value={studentForm.email} onChange={e => setStudentForm(p => ({ ...p, email: e.target.value }))} required />
                </label>
                <label>
                  Grade
                  <select value={studentForm.grade} onChange={e => setStudentForm(p => ({ ...p, grade: e.target.value }))}>
                    {STUDENT_GRADE_OPTIONS.map(g => <option key={g} value={g}>{g}</option>)}
                  </select>
                </label>
                <label>
                  Board
                  <select value={studentForm.board} onChange={e => setStudentForm(p => ({ ...p, board: e.target.value }))}>
                    {STUDENT_BOARD_OPTIONS.map(b => <option key={b} value={b}>{b}</option>)}
                  </select>
                </label>
                <label style={{ gridColumn: "1 / -1" }}>
                  <input type="checkbox" checked={studentForm.skip_email_confirmation}
                    onChange={e => setStudentForm(p => ({ ...p, skip_email_confirmation: e.target.checked, password: "" }))} />{" "}
                  In-person onboarding — skip email confirmation and set password directly
                </label>
                {studentForm.skip_email_confirmation && (
                  <label>
                    Password
                    <input type="password" value={studentForm.password}
                      onChange={e => setStudentForm(p => ({ ...p, password: e.target.value }))}
                      required placeholder="Set password for immediate access" />
                  </label>
                )}
                {!studentForm.skip_email_confirmation && (
                  <div className="info-box" style={{ gridColumn: "1 / -1", fontSize: "0.85rem" }}>
                    📧 An invitation email will be sent. The student must click the link to verify and set their password.
                  </div>
                )}
                {studentMsg && <div className="info-box" style={{ gridColumn: "1 / -1" }}>{studentMsg}</div>}
                {studentErr && <div className="error-box" style={{ gridColumn: "1 / -1" }}>{studentErr}</div>}
                <button className="primary-btn" type="submit">
                  {studentForm.skip_email_confirmation ? "Create Student (Immediate Access)" : "Send Invite Email"}
                </button>
              </form>
            </div>
          </div>
        </div>

        <details className="admin-roster-panel">
          <summary>
            <span>Current Teachers</span>
            <strong>{allTeachers.length}</strong>
          </summary>

          {allTeachers.length === 0 ? (
            <div className="info-box">
              No teacher accounts yet. Create one above, then assign students.
            </div>
          ) : (
            allTeachers.map((teacher) => {
              const metadata = teacher.teacher_profile || {};
              const form = assignmentForms[teacher.id] || {};

              return (
                <div
                  key={teacher.id}
                  className="premium-card"
                  style={{ marginBottom: 18 }}
                >
                  <div className="premium-rag-result-row success">
                    <div>
                      <strong>{teacher.username}</strong>
                      <p>{teacher.email}</p>
                      <small>
                        {metadata.teacher_type || "independent"}
                        {metadata.school_name ? ` • ${metadata.school_name}` : ""}
                      </small>
                    </div>

                    <button
                      className="danger-btn"
                      onClick={() => removeUser(teacher.id)}
                    >
                      Delete Teacher
                    </button>
                  </div>

                  <div className="family-summary-row" style={{ marginTop: 14 }}>
                    <span>
                      Subjects: {(metadata.subjects || []).join(", ") || "Any"}
                    </span>
                    <span>
                      Grades: {(metadata.grades || []).join(", ") || "Any"}
                    </span>
                  </div>

                  <form
                    onSubmit={(e) =>
                      handleAssignTeacherStudent(e, teacher, allStudents)
                    }
                    className="form-grid premium-rag-form-grid"
                    style={{ marginTop: 18 }}
                  >
                    <label>
                      Assign Student
                      <select
                        value={form.student_id || ""}
                        onChange={(e) => {
                          const selected = studentById[e.target.value];
                          updateAssignmentForm(
                            teacher.id,
                            "student_id",
                            e.target.value
                          );
                          updateAssignmentForm(
                            teacher.id,
                            "grade",
                            selected?.grade || "Grade 9"
                          );
                        }}
                      >
                        <option value="">Select student</option>
                        {allStudents.map((student) => (
                          <option key={student.id} value={student.id}>
                            {student.username} ({student.grade || "Grade 9"})
                          </option>
                        ))}
                      </select>
                    </label>

                    <label>
                      Subject
                      <input
                        value={form.subject || ""}
                        onChange={(e) =>
                          updateAssignmentForm(
                            teacher.id,
                            "subject",
                            e.target.value
                          )
                        }
                        placeholder="Science"
                      />
                    </label>

                    <label>
                      Section / Group
                      <input
                        value={form.section || ""}
                        onChange={(e) =>
                          updateAssignmentForm(
                            teacher.id,
                            "section",
                            e.target.value
                          )
                        }
                        placeholder="9A or Pradip batch"
                      />
                    </label>

                    <button className="secondary-btn" type="submit">
                      Assign Student
                    </button>
                  </form>

                  {(teacher.assignments || []).length > 0 && (
                    <div style={{ marginTop: 18 }}>
                      <h4>Assigned Students</h4>
                      {(teacher.assignments || []).map((assignment) => {
                        const assignedStudent =
                          studentById[assignment.student_id] || {};

                        return (
                          <div
                            key={
                              assignment.id ||
                              `${assignment.student_id}-${assignment.subject}`
                            }
                            className="premium-rag-result-row success"
                            style={{ marginBottom: 10 }}
                          >
                            <div>
                              <strong>
                                {assignedStudent.username ||
                                  assignment.student_id}
                              </strong>
                              <p>
                                {assignment.grade || "Grade 9"} •{" "}
                                {assignment.subject || "General"}
                                {assignment.section
                                  ? ` • ${assignment.section}`
                                  : ""}
                              </p>
                            </div>

                            {assignment.id && (
                              <button
                                className="secondary-btn"
                                onClick={() =>
                                  removeTeacherAssignment(assignment.id)
                                }
                              >
                                Remove
                              </button>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </details>
      </section>

      {/* ── Offer Codes Section ── */}
      <section className="premium-section">
        <div className="premium-header">
          <p className="eyebrow">Access Management</p>
          <h3>🎟️ Offer Codes</h3>
          <p>Create 8-character alphanumeric codes that grant platform access for a defined period.</p>
        </div>

        <div className="admin-create-grid">
          <div className="admin-create-card">
            <div className="admin-card-heading">
              <span>➕</span>
              <div><h3>Create Offer Code</h3><p>Auto-generates an 8-character code on creation.</p></div>
            </div>
            <form onSubmit={handleCreateOfferCode} className="form-grid premium-rag-form-grid admin-compact-form">
              <label>
                Description
                <input type="text" value={offerForm.description}
                  onChange={e => setOfferForm(p => ({ ...p, description: e.target.value }))}
                  placeholder="e.g. Trial batch June 2026" />
              </label>
              <label>
                Valid Until
                <input type="datetime-local" value={offerForm.valid_until}
                  onChange={e => setOfferForm(p => ({ ...p, valid_until: e.target.value }))} required />
              </label>
              <label>
                Max Redemptions
                <input type="number" min="1" max="10000" value={offerForm.max_uses}
                  onChange={e => setOfferForm(p => ({ ...p, max_uses: e.target.value }))} />
              </label>
              {offerMsg && <div className="info-box" style={{ gridColumn: "1 / -1" }}>{offerMsg}</div>}
              {offerErr && <div className="error-box" style={{ gridColumn: "1 / -1" }}>{offerErr}</div>}
              <button className="primary-btn" type="submit">Generate Offer Code</button>
            </form>
          </div>

          <div className="admin-create-card">
            <div className="admin-card-heading">
              <span>📋</span>
              <div><h3>Active Offer Codes</h3><p>Click Deactivate to prevent new redemptions.</p></div>
            </div>
            {offerCodesLoading ? (
              <p>Loading…</p>
            ) : offerCodes.length === 0 ? (
              <div className="info-box">No offer codes yet. Create one on the left.</div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {offerCodes.map(oc => {
                  const isExpired = new Date(oc.valid_until) < new Date();
                  return (
                    <div key={oc.id} className="premium-rag-result-row success" style={{ flexWrap: "wrap", gap: 8 }}>
                      <div style={{ flex: 1, minWidth: 200 }}>
                        <strong style={{ fontFamily: "monospace", fontSize: "1.1rem", letterSpacing: 2 }}>{oc.code}</strong>
                        <p style={{ margin: "2px 0", fontSize: "0.82rem" }}>{oc.description || "No description"}</p>
                        <small style={{ color: isExpired ? "#ef4444" : "#22c55e" }}>
                          {isExpired ? "⛔ Expired" : "✅ Active"} · Valid until {oc.valid_until?.slice(0, 10)}
                        </small>
                        <small style={{ display: "block" }}>
                          Used: {oc.uses_count}/{oc.max_uses}
                        </small>
                      </div>
                      {oc.is_active && !isExpired && (
                        <button className="danger-btn" style={{ alignSelf: "center" }}
                          onClick={() => handleDeactivateOfferCode(oc.id)}>
                          Deactivate
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </section>

      {families.map((family) => (
        <section key={family.family_id} className="premium-section admin-family-section">
          <details className="admin-family-details">
            <summary className="admin-family-summary">
              <div>
                <p className="eyebrow">Family</p>
                <h3>{getFamilyDisplayName(family)}</h3>
                <small className="admin-family-id">
                  ID: {family.family_id}
                </small>
              </div>

              <div className="admin-family-summary-metrics">
                <span>{(family.parents || []).length} parent(s)</span>
                <span>{(family.children || []).length} child(ren)</span>
                <span>{(family.teachers || []).length} teacher(s)</span>
              </div>
            </summary>

          <h4>Parents</h4>

          {(family.parents || []).map((parent) => {
            const childForm = childForms[parent.id] || {
              email: "",
              password: "",
              username: "",
              grade: "Grade 9",
              board: "CBSE",
            };

            return (
              <div
                key={parent.id}
                className="premium-card"
                style={{ marginBottom: 18 }}
              >
                <div className="premium-rag-result-row success">
                  <div>
                    <strong>{parent.username}</strong>
                    <p>{parent.email}</p>
                    <small>{parent.role}</small>
                  </div>

                  <button
                    className="danger-btn"
                    onClick={() => removeUser(parent.id)}
                  >
                    Delete Parent
                  </button>
                </div>

                <div style={{ marginTop: 18 }}>
                  <h4>Create Child Under {parent.username}</h4>

                  <form
                    onSubmit={(e) =>
                      handleCreateChild(e, family.family_id, parent.id)
                    }
                    className="form-grid premium-rag-form-grid"
                  >
                    <label>
                      Child Name
                      <input
                        type="text"
                        value={childForm.username}
                        onChange={(e) =>
                          updateChildForm(parent.id, "username", e.target.value)
                        }
                        required
                      />
                    </label>

                    <label>
                      Child Email
                      <input
                        type="email"
                        value={childForm.email}
                        onChange={(e) =>
                          updateChildForm(parent.id, "email", e.target.value)
                        }
                        required
                      />
                    </label>

                    <label>
                      Temporary Password
                      <input
                        type="password"
                        value={childForm.password}
                        onChange={(e) =>
                          updateChildForm(parent.id, "password", e.target.value)
                        }
                        required
                      />
                    </label>

                    <label>
                      Class
                      <select
                        value={childForm.grade || "Grade 9"}
                        onChange={(e) =>
                          updateChildForm(parent.id, "grade", e.target.value)
                        }
                      >
                        {STUDENT_GRADE_OPTIONS.map((gradeOption) => (
                          <option key={gradeOption} value={gradeOption}>
                            {gradeOption}
                          </option>
                        ))}
                      </select>
                    </label>

                    <label>
                      Board
                      <select
                        value={childForm.board || "CBSE"}
                        onChange={(e) =>
                          updateChildForm(parent.id, "board", e.target.value)
                        }
                      >
                        {STUDENT_BOARD_OPTIONS.map((boardOption) => (
                          <option key={boardOption} value={boardOption}>
                            {boardOption}
                          </option>
                        ))}
                      </select>
                    </label>

                    <button className="secondary-btn" type="submit">
                      Create Child
                    </button>
                  </form>
                </div>
              </div>
            );
          })}

          <h4 style={{ marginTop: 24 }}>Children</h4>

          {(family.children || []).map((child) => {
            const schoolBoardLabel = child.board || "CBSE";
            const unlimitedTokens = hasUnlimitedTokenAccess(child);

            return (
            <div
              key={child.id}
              className="premium-card"
              style={{ marginBottom: 18 }}
            >
              <h3>{child.username}</h3>
              <p>
                {child.email} • {child.board || "CBSE"} • {child.grade || "Grade 9"}
              </p>

              {child.activity && (
                <div
                  className="premium-card"
                  style={{
                    marginTop: 14,
                    marginBottom: 18,
                    padding: 16,
                  }}
                >
                  <h4>📊 Student Activity</h4>

                  <div className="form-grid premium-rag-form-grid">
                    <div>
                      <strong>{child.activity.lessons_generated || 0}</strong>
                      <p>Lessons</p>
                    </div>

                    <div>
                      <strong>{child.activity.doubts_asked || 0}</strong>
                      <p>Doubts</p>
                    </div>

                    <div>
                      <strong>
                        {child.activity.mock_tests_generated || 0}
                      </strong>
                      <p>Mock Tests</p>
                    </div>

                    <div>
                      <strong>{child.activity.requests_total || 0}</strong>
                      <p>Total AI Requests</p>
                    </div>

                    <div>
                      <strong>{child.activity.tokens_today || 0}</strong>
                      <p>Tokens Today</p>
                    </div>

                    <div>
                      <strong>{child.activity.tokens_this_month || 0}</strong>
                      <p>Tokens This Month</p>
                    </div>

                    <div>
                      <strong>{child.activity.tokens_total || 0}</strong>
                      <p>Total Tokens</p>
                    </div>

                    <div>
                      <strong>
                        ${Number(child.activity.cost_total || 0).toFixed(6)}
                      </strong>
                      <p>Total Cost</p>
                    </div>
                  </div>

                  <small>
                    Last Activity:{" "}
                    {child.activity.last_activity
                      ? child.activity.last_activity.slice(0, 19)
                      : "No activity yet"}
                  </small>
                </div>
              )}

              <div className="form-grid premium-rag-form-grid">
                <label>
                  Class
                  <select
                    value={child.grade || "Grade 9"}
                    onChange={(e) =>
                      updateLocalChild(
                        family.family_id,
                        child.id,
                        "grade",
                        e.target.value
                      )
                    }
                  >
                    {STUDENT_GRADE_OPTIONS.map((gradeOption) => (
                      <option key={gradeOption} value={gradeOption}>
                        {gradeOption}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  Board
                  <select
                    value={child.board || "CBSE"}
                    onChange={(e) =>
                      updateLocalChild(
                        family.family_id,
                        child.id,
                        "board",
                        e.target.value
                      )
                    }
                  >
                    {STUDENT_BOARD_OPTIONS.map((boardOption) => (
                      <option key={boardOption} value={boardOption}>
                        {boardOption}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  Plan
                  <select
                    value={child.subscription_plan || "free"}
                    onChange={(e) =>
                      applyPlanPreset(
                        family.family_id,
                        child.id,
                        e.target.value
                      )
                    }
                  >
                    {SUBSCRIPTION_PLAN_ORDER.map((planKey) => (
                      <option key={planKey} value={planKey}>
                        {SUBSCRIPTION_PLANS[planKey].label}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  Status
                  <select
                    value={child.account_status || "active"}
                    onChange={(e) =>
                      updateLocalChild(
                        family.family_id,
                        child.id,
                        "account_status",
                        e.target.value
                      )
                    }
                  >
                    <option value="active">Active</option>
                    <option value="trial">Trial</option>
                    <option value="suspended">Suspended</option>
                    <option value="expired">Expired</option>
                  </select>
                </label>

                <label>
                  AI Token Access
                  <select
                    value={unlimitedTokens ? "unlimited" : "limited"}
                    onChange={(e) =>
                      updateTokenAccessMode(
                        family.family_id,
                        child.id,
                        e.target.value
                      )
                    }
                  >
                    <option value="limited">Limited / Custom</option>
                    <option value="unlimited">Unlimited</option>
                  </select>
                </label>

                <label>
                  Daily Tokens
                  <input
                    type={unlimitedTokens ? "text" : "number"}
                    value={
                      unlimitedTokens
                        ? "Unlimited"
                        : normalizeTokenLimit(child.daily_token_limit)
                    }
                    disabled={unlimitedTokens}
                    onChange={(e) =>
                      updateLocalChild(
                        family.family_id,
                        child.id,
                        "daily_token_limit",
                        e.target.value
                      )
                    }
                  />
                </label>

                <label>
                  Monthly Tokens
                  <input
                    type={unlimitedTokens ? "text" : "number"}
                    value={
                      unlimitedTokens
                        ? "Unlimited"
                        : normalizeTokenLimit(child.monthly_token_limit)
                    }
                    disabled={unlimitedTokens}
                    onChange={(e) =>
                      updateLocalChild(
                        family.family_id,
                        child.id,
                        "monthly_token_limit",
                        e.target.value
                      )
                    }
                  />
                </label>

                <label>
                  AI Model for SOF Mock & Doubts
                  <select
                    value={child.ai_model_preference || "default"}
                    onChange={(e) =>
                      updateLocalChild(
                        family.family_id,
                        child.id,
                        "ai_model_preference",
                        e.target.value
                      )
                    }
                  >
                    {AI_MODEL_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <div style={{ marginTop: 16 }}>
                {[
                  ["access_cbse", schoolBoardLabel],
                  ["access_sof_science", "SOF Science"],
                  ["access_sof_maths", "SOF Maths"],
                  ["access_sof_english", "SOF English"],
                ].map(([field, label]) => (
                  <label
                    key={field}
                    style={{ display: "block", marginBottom: 8 }}
                  >
                    <input
                      type="checkbox"
                      checked={!!child[field]}
                      onChange={(e) =>
                        updateLocalChild(
                          family.family_id,
                          child.id,
                          field,
                          e.target.checked
                        )
                      }
                    />{" "}
                    {label}
                  </label>
                ))}
              </div>

              <div className="admin-cbse-subject-access">
                <div>
                  <h4>{schoolBoardLabel} Subject Access</h4>
                  <p>
                    Leave blank for all {schoolBoardLabel} subjects, or select only the
                    subjects included in a custom lower-cost plan.
                  </p>
                </div>

                <div className="admin-cbse-subject-chip-grid">
                  {COMMON_CBSE_SUBJECTS.map((subjectName) => {
                    const selectedSubjects = getChildCbseSubjects(child);
                    const isChecked = selectedSubjects.some(
                      (item) =>
                        normalizeSubjectName(item) ===
                        normalizeSubjectName(subjectName)
                    );

                    return (
                      <label key={subjectName}>
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={(e) =>
                            toggleChildCbseSubject(
                              family.family_id,
                              child.id,
                              child,
                              subjectName,
                              e.target.checked
                            )
                          }
                        />
                        {subjectName}
                      </label>
                    );
                  })}
                </div>

                <label>
                  Custom / Extra Subjects
                  <input
                    type="text"
                    value={subjectListToText(child.cbse_subjects)}
                    onChange={(e) =>
                      updateChildCbseSubjects(
                        family.family_id,
                        child.id,
                        e.target.value
                      )
                    }
                    placeholder={`Blank = all ${schoolBoardLabel} subjects, or Science, Maths`}
                  />
                </label>

                <button
                  className="secondary-btn"
                  type="button"
                  onClick={() =>
                    updateLocalChild(
                      family.family_id,
                      child.id,
                      "cbse_subjects",
                      []
                    )
                  }
                >
                  Allow All {schoolBoardLabel} Subjects
                </button>
              </div>

              <div style={{ display: "flex", gap: 12, marginTop: 20, flexWrap: "wrap", alignItems: "center" }}>
                <button
                  className="primary-btn"
                  onClick={() => saveAll(child)}
                  style={{ minWidth: 180 }}
                >
                  💾 Save All Changes
                </button>

                {child.account_status === "suspended" ? (
                  <button
                    className="secondary-btn"
                    onClick={() => reactivateChild(child)}
                  >
                    🔓 Reactivate
                  </button>
                ) : (
                  <button
                    className="secondary-btn"
                    onClick={() => suspendChild(child)}
                  >
                    🔒 Suspend
                  </button>
                )}

                <button
                  className="danger-btn"
                  style={{ marginLeft: "auto" }}
                  onClick={() => removeUser(child.id)}
                >
                  🗑 Delete Child
                </button>
              </div>
            </div>
            );
          })}
          </details>
        </section>
      ))}
    </div>
  );
}

export default AdminControlPage;
