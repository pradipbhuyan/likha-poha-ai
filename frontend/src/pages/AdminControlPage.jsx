import { useEffect, useState } from "react";
import { GRADE_11_12_STREAMS, getSubjectsForStream, isStreamGrade } from "../utils/streamSubjects";
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
  reactivateOfferCode,
  extendOfferCodeValidity,
  getInfluencerSummary,
  markInfluencerIncentivePaid,
  regeneratePromoImages,
  getOfferCodeEnrollments,
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
  { length: 12 },
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
  const [aiProvider, setAiProvider] = useState("openai");
  const [veniceKeyPrefix, setVeniceKeyPrefix] = useState("");
  const [veniceModel, setVeniceModel] = useState("llama-3.3-70b");
  const [newVeniceKey, setNewVeniceKey] = useState("");
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
  // Default valid_until = 30 days from now at 23:59 in local datetime-local format
  const defaultValidUntil = (() => {
    const d = new Date();
    d.setDate(d.getDate() + 30);
    d.setHours(23, 59, 0, 0);
    // Format as YYYY-MM-DDTHH:mm required by datetime-local input
    const pad = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  })();

  const [offerForm, setOfferForm] = useState({
    description: "",
    valid_until: defaultValidUntil,
    max_uses: 100,
    influencer_name: "",
    influencer_email: "",
    code_type: "free_trial",
    discount_percent: 0,
    incentive_inr: 0,
  });
  const [offerMsg, setOfferMsg] = useState("");
  const [offerErr, setOfferErr] = useState("");
  const [influencers, setInfluencers] = useState([]);
  const [influencerLoading, setInfluencerLoading] = useState(false);
  const [influencerMsg, setInfluencerMsg] = useState("");
  const [regenLoading, setRegenLoading] = useState(false);
  const [regenMsg, setRegenMsg] = useState("");
  const [enrollments, setEnrollments] = useState([]);
  const [enrollmentsLoading, setEnrollmentsLoading] = useState(false);
  const [expandedCode, setExpandedCode] = useState(null);

  const [childForms, setChildForms] = useState({});
  const [assignmentForms, setAssignmentForms] = useState({});
  // Stores { [parentId]: { email, password, username } } after child is created
  // so admin can show credentials to parent and next-step instructions.
  const [createdChildren, setCreatedChildren] = useState({});

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
      setAiProvider(data.provider || "openai");
      setVeniceKeyPrefix(data.venice_key_prefix || "");
      setVeniceModel(data.venice_model || "llama-3.3-70b");
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
      const payload = {
        api_enabled: enabledValue,
        provider: aiProvider,
        venice_model: veniceModel,
      };
      if (newApiKey.trim()) payload.openai_api_key = newApiKey.trim();
      if (newVeniceKey.trim()) payload.venice_api_key = newVeniceKey.trim();
      const data = await updateAiSettings(payload, user.accessToken);
      setAiEnabled(data.api_enabled ?? true);
      setAiKeyPrefix(data.api_key_prefix || "");
      setAiKeySource(data.key_source || "database");
      setAiProvider(data.provider || "openai");
      setVeniceKeyPrefix(data.venice_key_prefix || "");
      setVeniceModel(data.venice_model || "llama-3.3-70b");
      setNewApiKey("");
      setNewVeniceKey("");
      const providerLabel = data.provider === "venice" ? `Venice AI (${data.venice_model})` : "OpenAI";
      setAiSettingsMessage(
        data.api_enabled
          ? `AI API is ON — using ${providerLabel}.`
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
          skip_email_confirmation: true,
        },
        user.accessToken
      );

      // Save credentials so we can show next-step instructions to the parent
      setCreatedChildren((prev) => ({
        ...prev,
        [parentId]: {
          email: form.email,
          password: form.password,
          username: form.username,
          grade: form.grade || "Grade 9",
        },
      }));

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

  async function loadEnrollments() {
    setEnrollmentsLoading(true);
    try {
      const data = await getOfferCodeEnrollments(user.accessToken);
      setEnrollments(data.codes || []);
    } catch { /* silently ignore */ }
    finally { setEnrollmentsLoading(false); }
  }

  async function loadInfluencers() {
    setInfluencerLoading(true);
    try {
      const data = await getInfluencerSummary(user.accessToken);
      setInfluencers(data.influencers || []);
    } catch { /* table may not exist yet */ }
    finally { setInfluencerLoading(false); }
  }

  async function handleMarkPaid(codeId) {
    try {
      await markInfluencerIncentivePaid(codeId, user.accessToken);
      setInfluencerMsg("✅ Incentive marked as paid.");
      await loadInfluencers();
      await loadOfferCodes();
    } catch (err) { setInfluencerMsg(err.message || "Failed."); }
  }

  async function handleCreateOfferCode(e) {
    e.preventDefault();
    setOfferMsg("");
    setOfferErr("");
    if (!offerForm.valid_until) { setOfferErr("Valid Until date is required."); return; }
    try {
      const data = await createOfferCode({
        description: offerForm.description,
        valid_until: offerForm.valid_until,
        max_uses: Number(offerForm.max_uses) || 100,
        influencer_name: offerForm.influencer_name,
        influencer_email: offerForm.influencer_email,
        code_type: offerForm.code_type,
        discount_percent: Number(offerForm.discount_percent) || 0,
        incentive_inr: Number(offerForm.incentive_inr) || 0,
      }, user.accessToken);
      setOfferMsg(`✅ Code created: ${data.offer_code?.code || "—"}`);
      // Reset with a fresh default date (30 days from now)
      const freshDate = (() => {
        const d = new Date(); d.setDate(d.getDate() + 30); d.setHours(23, 59, 0, 0);
        const pad = (n) => String(n).padStart(2, "0");
        return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
      })();
      setOfferForm({ description: "", valid_until: freshDate, max_uses: 100, influencer_name: "", influencer_email: "", code_type: "free_trial", discount_percent: 0, incentive_inr: 0 });
      await loadOfferCodes();
      await loadInfluencers();
    } catch (err) {
      setOfferErr(err.message || "Unable to create offer code.");
    }
  }

  async function handleRegenPromoImages(offerCode, validUntil) {
    /** Regenerate all WhatsApp promo images with the offer code and re-upload to Supabase. */
    setRegenLoading(true);
    setRegenMsg("");
    try {
      const data = await regeneratePromoImages(
        { offer_code: offerCode, valid_until: validUntil },
        user.accessToken
      );
      setRegenMsg(`✅ ${data.uploaded} images regenerated and uploaded to Supabase (code: ${data.offer_code})`);
      await loadOfferCodes();
    } catch (err) {
      setRegenMsg(`❌ ${err.message}`);
    } finally {
      setRegenLoading(false);
    }
  }

  // Track which offer code has the extend-validity form open + the new date value
  const [extendingCodeId, setExtendingCodeId] = useState(null);
  const [extendDate, setExtendDate] = useState("");
  const [extendErr, setExtendErr] = useState("");

  async function handleExtendValidity(codeId) {
    if (!extendDate) { setExtendErr("Please pick a new expiry date."); return; }
    setExtendErr("");
    try {
      // Convert local datetime-local value to ISO string
      const isoDate = new Date(extendDate).toISOString();
      await extendOfferCodeValidity(codeId, isoDate, user.accessToken);
      setExtendingCodeId(null);
      setExtendDate("");
      // Refresh offer codes list — the updated valid_until is visible immediately
      const data = await listOfferCodes(user.accessToken);
      setOfferCodes(data.offer_codes || []);
      setOfferMsg("✅ Validity extended. All existing redemptions updated.");
    } catch (err) {
      setExtendErr(err.message || "Failed to extend validity.");
    }
  }

  async function handleDeactivateOfferCode(codeId) {
    if (!window.confirm("Deactivate this offer code? Users with existing redemptions keep their access.")) return;
    try {
      await deactivateOfferCode(codeId, user.accessToken);
      await loadOfferCodes();
      setOfferMsg("✅ Offer code deactivated.");
    } catch (err) {
      setOfferErr(err.message || "Unable to deactivate.");
    }
  }

  async function handleReactivateOfferCode(codeId) {
    if (!window.confirm("Reactivate this offer code? It will accept new redemptions again.")) return;
    try {
      await reactivateOfferCode(codeId, user.accessToken);
      await loadOfferCodes();
      setOfferMsg("✅ Offer code reactivated.");
    } catch (err) {
      setOfferErr(err.message || "Unable to reactivate.");
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

  // Load offer codes, influencer summary, and enrollments on mount
  useEffect(() => {
    if (user?.accessToken) { loadOfferCodes(); loadInfluencers(); loadEnrollments(); }
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

          {/* Provider selector */}
          <div style={{ marginBottom: 20 }}>
            <strong>AI Provider</strong>
            <p style={{ fontSize: "0.82rem", color: "#888", margin: "4px 0 8px" }}>
              Switch between OpenAI and Venice AI. Venice uses your Venice credits.
            </p>
            <div style={{ display: "flex", gap: 0, background: "var(--surface2,#111827)", border: "1px solid var(--border)", borderRadius: 9, padding: 3 }}>
              {[["openai", "🤖 OpenAI"], ["venice", "🎨 Venice AI"]].map(([val, label]) => (
                <button key={val} onClick={() => setAiProvider(val)}
                  style={{ flex: 1, padding: "8px 10px", borderRadius: 7, border: "none",
                    background: aiProvider === val ? "var(--accent, #6366f1)" : "transparent",
                    color: aiProvider === val ? "#fff" : "var(--muted)",
                    fontFamily: "inherit", fontSize: ".85rem", fontWeight: 600, cursor: "pointer" }}>
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Active key indicator */}
          {aiProvider === "openai" && (
            <div style={{ marginBottom: 20 }}>
              <strong>Active OpenAI Key</strong>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 6 }}>
                <code style={{ background: "var(--surface2, #f5f5f5)", padding: "6px 12px", borderRadius: 6, fontFamily: "monospace", fontSize: "0.95rem", letterSpacing: 2 }}>
                  {aiKeyPrefix ? `${aiKeyPrefix}••••••••••••••••` : "No key stored"}
                </code>
                <span style={{ fontSize: "0.8rem", color: "#888" }}>
                  ({aiKeySource === "database" ? "set via admin console" : "from environment variable"})
                </span>
              </div>
            </div>
          )}

          {/* New OpenAI key input */}
          {aiProvider === "openai" && (
            <label style={{ display: "block", marginBottom: 16 }}>
              <strong>Update OpenAI API Key</strong>
              <p style={{ fontSize: "0.82rem", color: "#888", margin: "4px 0 8px" }}>
                Paste a new OpenAI key to replace the current one. Leave blank to keep the existing key.
              </p>
              <input type="password" value={newApiKey} onChange={(e) => setNewApiKey(e.target.value)}
                placeholder="sk-proj-… or sk-…" style={{ width: "100%", fontFamily: "monospace" }} autoComplete="new-password" />
            </label>
          )}

          {/* Venice settings */}
          {aiProvider === "venice" && (
            <div style={{ background: "rgba(99,102,241,.07)", border: "1px solid rgba(99,102,241,.25)", borderRadius: 10, padding: "14px 16px", marginBottom: 16 }}>
              <strong>Venice AI Settings</strong>
              <p style={{ fontSize: "0.82rem", color: "#888", margin: "4px 0 12px" }}>
                Venice credits are used for all lessons, doubts, and pre-warm generation when Venice is active.
                Get your API key at <a href="https://venice.ai" target="_blank" rel="noreferrer" style={{ color: "var(--accent,#6366f1)" }}>venice.ai</a>.
              </p>

              <label style={{ display: "block", marginBottom: 12 }}>
                <strong style={{ fontSize: ".85rem" }}>Venice API Key</strong>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4, marginBottom: 6 }}>
                  <code style={{ background: "var(--surface2,#111827)", padding: "4px 10px", borderRadius: 6, fontFamily: "monospace", fontSize: ".82rem", letterSpacing: 1 }}>
                    {veniceKeyPrefix ? `${veniceKeyPrefix}••••••••••` : "No key stored"}
                  </code>
                </div>
                <input type="password" value={newVeniceKey} onChange={(e) => setNewVeniceKey(e.target.value)}
                  placeholder="your-venice-api-key" style={{ width: "100%", fontFamily: "monospace" }} autoComplete="new-password" />
              </label>

              <label style={{ display: "block" }}>
                <strong style={{ fontSize: ".85rem" }}>Venice Model</strong>
                <select value={veniceModel} onChange={(e) => setVeniceModel(e.target.value)} style={{ width: "100%", marginTop: 4 }}>
                  <option value="llama-3.3-70b">Llama 3.3 70B — Best quality (recommended)</option>
                  <option value="llama-3.2-3b">Llama 3.2 3B — Fastest + cheapest (prewarm)</option>
                  <option value="mistral-31-24b">Mistral 3.1 24B — Mid-size, fast</option>
                  <option value="qwen-2.5-72b">Qwen 2.5 72B — Strong STEM</option>
                  <option value="deepseek-r1-671b">DeepSeek R1 671B — Best reasoning</option>
                </select>
                <p style={{ fontSize: ".75rem", color: "#888", marginTop: 4 }}>
                  💡 Use Llama 3.2 3B for prewarm (cheap). Use Llama 3.3 70B for live student requests.
                </p>
              </label>
            </div>
          )}

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

  function exportUsersCSV() {
    /** Export all students, parents, teachers with subscription info to CSV. */
    const headers = [
      "Role","Name","Email","Grade","Board","Subscription Plan","Account Status",
      "CBSE Access","Daily Token Limit","Monthly Token Limit","Created At",
    ];

    const studentRows = allStudents.map(u => [
      "Student", u.username || "", u.email || "",
      u.grade || "", u.board || "CBSE",
      u.subscription_plan || "free", u.account_status || "active",
      u.access_cbse ? "Yes" : "No",
      u.daily_token_limit || 0, u.monthly_token_limit || 0,
      (u.created_at || "").slice(0, 10),
    ]);

    const parentRows = allParents.map(u => [
      "Parent", u.username || "", u.email || "",
      "", "",
      u.subscription_plan || "free", u.account_status || "active",
      u.access_cbse ? "Yes" : "No",
      u.daily_token_limit || 0, u.monthly_token_limit || 0,
      (u.created_at || "").slice(0, 10),
    ]);

    const teacherRows = allTeachers.map(u => [
      "Teacher", u.username || "", u.email || "",
      "", "",
      u.subscription_plan || "teacher", u.account_status || "active",
      "Yes",
      u.daily_token_limit || 0, u.monthly_token_limit || 0,
      (u.created_at || "").slice(0, 10),
    ]);

    const allRows = [...studentRows, ...parentRows, ...teacherRows];
    const csv = [headers, ...allRows]
      .map(row => row.map(v => `"${String(v).replace(/"/g, '""')}"`).join(","))
      .join("\r\n");

    const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `users_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="premium-page admin-control-page">
      {aiSettingsPanel}

      <section className="premium-section admin-control-hero">
        <div className="premium-header">
          <p className="eyebrow">Admin Operations</p>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
            <h2 style={{ margin: 0 }}>🛠️ Admin Control Center</h2>
            {(allStudents.length + allParents.length + allTeachers.length) > 0 && (
              <button onClick={exportUsersCSV}
                style={{ background: "var(--panel)", color: "var(--primary)", border: "1px solid var(--border)", borderRadius: 8, padding: "8px 16px", fontSize: ".85rem", fontWeight: 700, cursor: "pointer", fontFamily: "inherit", whiteSpace: "nowrap" }}>
                📥 Export Users to Excel
              </button>
            )}
          </div>
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
              <label>
                Influencer Name <small style={{color:"var(--muted)"}}>(optional)</small>
                <input type="text" value={offerForm.influencer_name}
                  onChange={e => setOfferForm(p => ({ ...p, influencer_name: e.target.value }))}
                  placeholder="e.g. Rohan Sharma" />
              </label>
              <label>
                Influencer Email <small style={{color:"var(--muted)"}}>(optional)</small>
                <input type="email" value={offerForm.influencer_email}
                  onChange={e => setOfferForm(p => ({ ...p, influencer_email: e.target.value }))}
                  placeholder="rohan@example.com" />
              </label>
              <label>
                Code Type
                <select value={offerForm.code_type} onChange={e => setOfferForm(p => ({ ...p, code_type: e.target.value }))}>
                  <option value="free_trial">Free Trial (free access)</option>
                  <option value="discount">Discount (% off paid plan)</option>
                </select>
              </label>
              {offerForm.code_type === "discount" && (
                <label>
                  Discount % (5–10)
                  <input type="number" min="5" max="10" value={offerForm.discount_percent}
                    onChange={e => setOfferForm(p => ({ ...p, discount_percent: e.target.value }))} />
                </label>
              )}
              <label>
                Incentive per Redemption (₹)
                <input type="number" min="0" value={offerForm.incentive_inr}
                  onChange={e => setOfferForm(p => ({ ...p, incentive_inr: e.target.value }))}
                  placeholder="e.g. 50" />
              </label>
              {offerMsg && <div className="info-box" style={{ gridColumn: "1 / -1" }}>{offerMsg}</div>}
              {offerErr && <div className="error-box" style={{ gridColumn: "1 / -1" }}>{offerErr}</div>}
              <button className="primary-btn" type="submit">Generate Offer Code</button>
            </form>

            {/* Refresh Promo Images — stamp all WhatsApp cards with active code */}
            {offerCodes.filter(oc => oc.is_active && new Date(oc.valid_until) > new Date()).length > 0 && (
              <div style={{marginTop:20, padding:"16px", background:"var(--surface2,#f8f9fa)", borderRadius:12, border:"1px solid var(--border)"}}>
                <h4 style={{margin:"0 0 8px",fontSize:".95rem"}}>🎨 Refresh Promo Images</h4>
                <p style={{fontSize:".82rem",color:"var(--muted)",marginBottom:12}}>
                  Stamp all 12 WhatsApp promo images with a new offer code and re-upload to Supabase automatically.
                  Salespeople see updated images on the Collaterals page immediately.
                </p>
                {offerCodes.filter(oc => oc.is_active && new Date(oc.valid_until) > new Date()).map(oc => (
                  <button key={oc.id}
                    className="secondary-btn"
                    style={{marginRight:8,marginBottom:8,fontSize:".82rem"}}
                    disabled={regenLoading}
                    onClick={() => handleRegenPromoImages(oc.code, oc.valid_until?.slice(0,10)?.split("-").reverse().join(" ").replace("-"," "))}>
                    {regenLoading ? "Regenerating…" : `🖼️ Stamp code ${oc.code}`}
                  </button>
                ))}
                {regenMsg && <div className={regenMsg.startsWith("✅") ? "info-box" : "error-box"} style={{marginTop:8}}>{regenMsg}</div>}
              </div>
            )}
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
                  const statusColor = isExpired ? "#ef4444" : oc.is_active ? "#22c55e" : "#f59e0b";
                  const statusLabel = isExpired ? "⛔ Expired" : oc.is_active ? "✅ Active" : "⏸️ Deactivated";
                  return (
                    <div key={oc.id} className="premium-rag-result-row success" style={{ flexWrap: "wrap", gap: 8 }}>
                      <div style={{ flex: 1, minWidth: 200 }}>
                        <strong style={{ fontFamily: "monospace", fontSize: "1.1rem", letterSpacing: 2 }}>{oc.code}</strong>
                        <p style={{ margin: "2px 0", fontSize: "0.82rem" }}>{oc.description || "No description"}</p>
                        <small style={{ color: statusColor, fontWeight: 600 }}>
                          {statusLabel} · Valid until {oc.valid_until?.slice(0, 10)}
                        </small>
                        <small style={{ display: "block", color: "var(--muted)" }}>
                          Used: {oc.uses_count}/{oc.max_uses}
                        </small>

                        {/* Signup link + share buttons */}
                        {(() => {
                          const signupLink = `https://likhapoha.in/signup?code=${oc.code}&role=student`;
                          const waText = encodeURIComponent(
                            `🎓 Join LikhaPoha AI — CBSE AI Tutor for Class 5–10!\n\nGet instant lessons, doubt answers & mock tests powered by AI.\n\n✅ Use this exclusive link to sign up:\n${signupLink}\n\n⏰ Valid until ${oc.valid_until?.slice(0,10)}`
                          );
                          const emailSubject = encodeURIComponent("LikhaPoha AI — CBSE AI Tutor Invitation");
                          const emailBody = encodeURIComponent(
                            `Hi,\n\nI'd like to invite you to try LikhaPoha AI — India's smartest CBSE AI Tutor for Class 5–10.\n\nUse this exclusive signup link:\n${signupLink}\n\nValid until: ${oc.valid_until?.slice(0,10)}\n\nFeatures:\n• Instant step-by-step CBSE lessons\n• AI doubt solving\n• Mock tests with 70,000+ questions\n\nBest regards`
                          );
                          return (
                            <div style={{ marginTop: 8 }}>
                              {/* Signup link display */}
                              <div style={{ display:"flex", alignItems:"center", gap:6, background:"rgba(99,102,241,.07)", borderRadius:7, padding:"5px 8px", marginBottom:6, flexWrap:"wrap" }}>
                                <code style={{ fontSize:".72rem", color:"#a5b4fc", fontFamily:"monospace", flex:1, wordBreak:"break-all" }}>
                                  {signupLink}
                                </code>
                                <button
                                  onClick={() => { navigator.clipboard.writeText(signupLink); }}
                                  style={{ background:"rgba(99,102,241,.2)", border:"none", borderRadius:5, padding:"3px 8px", color:"#a5b4fc", cursor:"pointer", fontSize:".72rem", fontWeight:700, fontFamily:"inherit", whiteSpace:"nowrap" }}
                                  title="Copy link">
                                  📋 Copy
                                </button>
                              </div>
                              {/* Share buttons */}
                              <div style={{ display:"flex", gap:6, flexWrap:"wrap" }}>
                                <a
                                  href={`https://wa.me/?text=${waText}`}
                                  target="_blank"
                                  rel="noreferrer"
                                  style={{ display:"inline-flex", alignItems:"center", gap:4, background:"#25d366", color:"#fff", borderRadius:6, padding:"4px 10px", fontSize:".78rem", fontWeight:700, textDecoration:"none", fontFamily:"inherit" }}>
                                  💬 Share on WhatsApp
                                </a>
                                <a
                                  href={`mailto:?subject=${emailSubject}&body=${emailBody}`}
                                  style={{ display:"inline-flex", alignItems:"center", gap:4, background:"rgba(59,130,246,.15)", color:"#60a5fa", border:"1px solid rgba(59,130,246,.3)", borderRadius:6, padding:"4px 10px", fontSize:".78rem", fontWeight:700, textDecoration:"none", fontFamily:"inherit" }}>
                                  📧 Send Email
                                </a>
                              </div>
                            </div>
                          );
                        })()}
                      </div>
                      <div style={{ display:"flex", flexDirection:"column", gap:6, alignSelf:"center" }}>
                        {/* Extend validity button */}
                        {extendingCodeId === oc.id ? (
                          <div style={{ display:"flex", flexDirection:"column", gap:4, minWidth:220 }}>
                            <input
                              type="datetime-local"
                              value={extendDate}
                              min={new Date().toISOString().slice(0,16)}
                              onChange={e => { setExtendDate(e.target.value); setExtendErr(""); }}
                              style={{ fontSize:".82rem", padding:"5px 8px", borderRadius:7,
                                       border:"1px solid #6366f1", background:"#1e293b", color:"#f8fafc" }}
                            />
                            {extendErr && <small style={{ color:"#ef4444" }}>{extendErr}</small>}
                            <div style={{ display:"flex", gap:6 }}>
                              <button className="primary-btn" style={{ padding:"5px 12px", fontSize:".8rem" }}
                                onClick={() => handleExtendValidity(oc.id)}>
                                ✅ Confirm
                              </button>
                              <button className="secondary-btn" style={{ padding:"5px 12px", fontSize:".8rem" }}
                                onClick={() => { setExtendingCodeId(null); setExtendDate(""); setExtendErr(""); }}>
                                Cancel
                              </button>
                            </div>
                          </div>
                        ) : (
                          <button className="secondary-btn" style={{ fontSize:".8rem", padding:"5px 12px", color:"#6366f1", borderColor:"#6366f1" }}
                            onClick={() => { setExtendingCodeId(oc.id); setExtendDate(oc.valid_until?.slice(0,16) || ""); setExtendErr(""); }}>
                            📅 Extend Validity
                          </button>
                        )}
                        {/* Deactivate / Reactivate */}
                        {!isExpired && (
                          oc.is_active ? (
                            <button className="danger-btn" style={{ fontSize:".8rem", padding:"5px 12px" }}
                              onClick={() => handleDeactivateOfferCode(oc.id)}>
                              Deactivate
                            </button>
                          ) : (
                            <button className="secondary-btn" style={{ fontSize:".8rem", padding:"5px 12px", color: "#22c55e", borderColor: "#22c55e" }}
                              onClick={() => handleReactivateOfferCode(oc.id)}>
                              ✅ Reactivate
                            </button>
                          )
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* ── Offer Code Enrollment Tracking ── */}
      <section className="premium-section">
        <div className="premium-header">
          <p className="eyebrow">Offer Code Programme</p>
          <h3>👥 Student Enrollments by Offer Code</h3>
          <p>See exactly which students enrolled using which code — with date, grade, and influencer attribution.</p>
        </div>
        {enrollmentsLoading ? <p>Loading…</p> : enrollments.length === 0 ? (
          <div className="info-box">No offer codes yet. Create one above.</div>
        ) : (
          <div style={{display:"flex",flexDirection:"column",gap:12}}>
            {enrollments.map(oc => {
              const isExpired = new Date(oc.valid_until) < new Date();
              const isExpanded = expandedCode === oc.id;
              return (
                <div key={oc.id} style={{border:"1px solid var(--border)",borderRadius:12,overflow:"hidden"}}>
                  {/* Code header row */}
                  <button
                    onClick={() => setExpandedCode(isExpanded ? null : oc.id)}
                    style={{width:"100%",background:"var(--surface2,#f8f9fa)",border:"none",padding:"12px 16px",cursor:"pointer",textAlign:"left",fontFamily:"inherit",display:"flex",alignItems:"center",gap:12,flexWrap:"wrap"}}>
                    <strong style={{fontFamily:"monospace",fontSize:"1rem",letterSpacing:2,minWidth:90}}>{oc.code}</strong>
                    <span style={{fontSize:".82rem",color:"var(--muted)",flex:1}}>{oc.description || (oc.influencer_name ? `Influencer: ${oc.influencer_name}` : "General")}</span>
                    <span style={{fontSize:".8rem",background: oc.enrollment_count > 0 ? "rgba(4,120,87,.12)" : "var(--border)", color: oc.enrollment_count > 0 ? "#047857" : "var(--muted)", padding:"2px 10px",borderRadius:20,fontWeight:700}}>
                      {oc.enrollment_count} enrolled
                    </span>
                    <span style={{fontSize:".8rem",color: isExpired ? "#ef4444" : "#22c55e"}}>
                      {isExpired ? "⛔ Expired" : "✅ Active"} till {oc.valid_until}
                    </span>
                    <span style={{fontSize:".8rem",color:"var(--muted)"}}>{isExpanded ? "▲ Hide" : "▼ Show students"}</span>
                  </button>

                  {/* Enrollment list */}
                  {isExpanded && (
                    <div style={{padding:"0 16px 12px"}}>
                      {oc.enrollment_count === 0 ? (
                        <p style={{fontSize:".85rem",color:"var(--muted)",padding:"12px 0"}}>No students have enrolled with this code yet.</p>
                      ) : (
                        <>
                          <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",padding:"8px 0",borderBottom:"1px solid var(--border)",marginBottom:8}}>
                            <span style={{fontSize:".82rem",fontWeight:700,color:"var(--muted)"}}>
                              {oc.enrollment_count} student{oc.enrollment_count !== 1 ? "s" : ""} enrolled
                              {oc.influencer_name ? ` via ${oc.influencer_name}` : ""}
                            </span>
                            <button
                              onClick={() => {
                                const csv = ["Name,Email,Grade,Board,Enrolled At,Access Until",
                                  ...oc.enrollments.map(e => `"${e.username}","${e.email}","${e.grade}","${e.board}","${e.enrolled_at}","${e.access_until}"`)
                                ].join("\r\n");
                                const blob = new Blob(["\uFEFF"+csv], {type:"text/csv;charset=utf-8;"});
                                const a = document.createElement("a");
                                a.href = URL.createObjectURL(blob);
                                a.download = `enrollments-${oc.code}-${new Date().toISOString().slice(0,10)}.csv`;
                                a.click();
                              }}
                              style={{background:"var(--panel)",border:"1px solid var(--border)",borderRadius:6,padding:"3px 10px",cursor:"pointer",fontFamily:"inherit",fontSize:".78rem",fontWeight:700}}>
                              📥 Export CSV
                            </button>
                          </div>
                          <div style={{overflowX:"auto"}}>
                            <table style={{width:"100%",borderCollapse:"collapse",fontSize:".82rem"}}>
                              <thead>
                                <tr style={{color:"var(--muted)",textAlign:"left"}}>
                                  {["Name","Email","Grade","Enrolled At","Access Until"].map(h => (
                                    <th key={h} style={{padding:"4px 8px",fontWeight:600}}>{h}</th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {oc.enrollments.map((e, i) => (
                                  <tr key={e.user_id} style={{borderTop:"1px solid var(--border)",background: i%2===0 ? "transparent" : "rgba(0,0,0,.02)"}}>
                                    <td style={{padding:"6px 8px",fontWeight:600}}>{e.username}</td>
                                    <td style={{padding:"6px 8px",color:"var(--muted)"}}>{e.email}</td>
                                    <td style={{padding:"6px 8px"}}>{e.grade}</td>
                                    <td style={{padding:"6px 8px",color:"var(--muted)"}}>{e.enrolled_at.replace("T"," ")}</td>
                                    <td style={{padding:"6px 8px",color: new Date(e.access_until) > new Date() ? "#22c55e" : "#ef4444",fontWeight:700}}>{e.access_until}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* ── Influencer Incentive Tracking ── */}
      <section className="premium-section">
        <div className="premium-header">
          <p className="eyebrow">Influencer Programme</p>
          <h3>📊 Influencer Incentive Tracking</h3>
          <p>Track incentive payables per influencer and mark payments as settled.</p>
        </div>
        {influencerMsg && <div className="info-box" style={{marginBottom:12}}>{influencerMsg}</div>}
        {influencerLoading ? <p>Loading…</p> : influencers.length === 0 ? (
          <div className="info-box">No influencer codes yet. Create an offer code with an Influencer Name above.</div>
        ) : (
          <div style={{overflowX:"auto"}}>
            <table style={{width:"100%",borderCollapse:"collapse",fontSize:".88rem"}}>
              <thead>
                <tr style={{borderBottom:"2px solid var(--border)",textAlign:"left"}}>
                  {["Influencer","Email","Codes","Total Redemptions","Incentive Payable","Status","Action"].map(h => (
                    <th key={h} style={{padding:"8px 12px",color:"var(--muted)",fontWeight:700}}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {influencers.map(inf => (
                  <tr key={inf.influencer_name} style={{borderBottom:"1px solid var(--border)"}}>
                    <td style={{padding:"10px 12px",fontWeight:700}}>{inf.influencer_name}</td>
                    <td style={{padding:"10px 12px",color:"var(--muted)",fontSize:".82rem"}}>{inf.influencer_email || "—"}</td>
                    <td style={{padding:"10px 12px",textAlign:"center"}}>{inf.codes?.length || 0}</td>
                    <td style={{padding:"10px 12px",textAlign:"center",fontWeight:700}}>{inf.total_redemptions}</td>
                    <td style={{padding:"10px 12px",fontWeight:800,color: inf.total_incentive_payable > 0 ? "#047857" : "var(--muted)"}}>
                      ₹{inf.total_incentive_payable}
                    </td>
                    <td style={{padding:"10px 12px"}}>
                      {inf.incentive_paid
                        ? <span style={{color:"#3b82f6",fontWeight:700}}>✅ All Paid</span>
                        : <span style={{color:"#f59e0b",fontWeight:700}}>⏳ Unpaid</span>}
                    </td>
                    <td style={{padding:"10px 12px"}}>
                      {!inf.incentive_paid && inf.codes?.filter(c => !c.incentive_paid).map(c => (
                        <button key={c.id}
                          onClick={() => handleMarkPaid(c.id)}
                          style={{background:"rgba(4,120,87,.1)",color:"var(--success)",border:"1px solid rgba(4,120,87,.3)",borderRadius:6,padding:"3px 10px",cursor:"pointer",fontFamily:"inherit",fontSize:".78rem",fontWeight:700,marginRight:4,marginBottom:4}}>
                          Pay {c.code}
                        </button>
                      ))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {families.map((family) => (
        <section key={family.family_id} className="premium-section admin-family-section">
          {/* ── Credentials card shown OUTSIDE <details> so it's always visible after creation ── */}
          {(family.parents || []).map((parent) => {
            const cred = createdChildren[parent.id];
            if (!cred) return null;
            const loginLink = `https://likhapoha.in/?u=${encodeURIComponent(cred.email)}`;
            return (
              <div key={`cred-${parent.id}`} style={{ background:"rgba(34,197,94,.07)", border:"1.5px solid rgba(34,197,94,.4)", borderRadius:12, padding:"16px 18px", marginBottom:16 }}>
                <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:10 }}>
                  <strong style={{ color:"#22c55e", fontSize:".95rem" }}>
                    ✅ Child account created for {cred.username}! (under {parent.username})
                  </strong>
                  <button onClick={() => setCreatedChildren(p => ({ ...p, [parent.id]: null }))}
                    style={{ background:"none", border:"none", cursor:"pointer", color:"var(--muted)", fontSize:"1rem" }}>✕</button>
                </div>
                {/* Login credentials */}
                <div style={{ background:"rgba(0,0,0,.2)", borderRadius:8, padding:"10px 12px", marginBottom:10, fontFamily:"monospace", fontSize:".82rem" }}>
                  <div style={{ marginBottom:4 }}>
                    <span style={{ color:"var(--muted)" }}>Username: </span>
                    <strong style={{ color:"#f8fafc" }}>{cred.username}</strong>
                    <button onClick={() => navigator.clipboard.writeText(cred.username)}
                      style={{ marginLeft:8, background:"none", border:"none", cursor:"pointer", color:"#a5b4fc", fontSize:".7rem", fontWeight:700 }}>📋</button>
                  </div>
                  <div style={{ marginBottom:4 }}>
                    <span style={{ color:"var(--muted)" }}>Login Email: </span>
                    <strong style={{ color:"#f8fafc" }}>{cred.email}</strong>
                    <button onClick={() => navigator.clipboard.writeText(cred.email)}
                      style={{ marginLeft:8, background:"none", border:"none", cursor:"pointer", color:"#a5b4fc", fontSize:".7rem", fontWeight:700 }}>📋</button>
                  </div>
                  <div>
                    <span style={{ color:"var(--muted)" }}>Password: </span>
                    <strong style={{ color:"#fbbf24" }}>{cred.password}</strong>
                    <button onClick={() => navigator.clipboard.writeText(cred.password)}
                      style={{ marginLeft:8, background:"none", border:"none", cursor:"pointer", color:"#a5b4fc", fontSize:".7rem", fontWeight:700 }}>📋</button>
                  </div>
                </div>
                {/* One-click login link */}
                <div style={{ marginBottom:10 }}>
                  <p style={{ fontSize:".75rem", color:"#a5b4fc", margin:"0 0 4px", fontWeight:600 }}>🔗 One-click login link (pre-fills email on login page)</p>
                  <div style={{ display:"flex", alignItems:"center", gap:6, background:"rgba(99,102,241,.1)", borderRadius:7, padding:"5px 8px", flexWrap:"wrap" }}>
                    <code style={{ fontSize:".7rem", color:"#c7d2fe", fontFamily:"monospace", flex:1, wordBreak:"break-all" }}>{loginLink}</code>
                    <button onClick={() => navigator.clipboard.writeText(loginLink)}
                      style={{ background:"rgba(99,102,241,.3)", border:"none", borderRadius:5, padding:"2px 8px", color:"#c7d2fe", cursor:"pointer", fontSize:".7rem", fontWeight:700, fontFamily:"inherit" }}>📋 Copy</button>
                  </div>
                  <p style={{ fontSize:".7rem", color:"var(--muted)", margin:"3px 0 0" }}>
                    Child can sign in with <strong>username</strong> OR <strong>email</strong> at likhapoha.in
                  </p>
                </div>
                {/* Next steps */}
                <div style={{ fontSize:".82rem", lineHeight:1.6 }}>
                  <p style={{ fontWeight:700, marginBottom:6, color:"#f8fafc" }}>📋 What to do next:</p>
                  <ol style={{ paddingLeft:18, margin:0, color:"var(--muted)" }}>
                    <li>Share the <strong>username or email + password</strong> with your child</li>
                    <li>Child logs in at <strong>likhapoha.in</strong> — can use username OR email</li>
                    <li>Child can <strong>change their password</strong> from profile settings anytime</li>
                    <li style={{ color:"#a5b4fc", fontWeight:600 }}>💡 Sit with your child for their first login and give a quick walkthrough</li>
                  </ol>
                </div>
                {/* Video walkthrough placeholder */}
                <div style={{ marginTop:10, background:"rgba(99,102,241,.08)", border:"1px dashed rgba(99,102,241,.35)", borderRadius:8, padding:"10px 14px", textAlign:"center" }}>
                  <div style={{ fontSize:"1.6rem", marginBottom:3 }}>▶️</div>
                  <p style={{ fontSize:".78rem", color:"#a5b4fc", margin:0, fontWeight:600 }}>Platform Walkthrough Video — Coming Soon</p>
                </div>
              </div>
            );
          })}
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
                  <h4>➕ Add Child for {parent.username}</h4>

                  {/* ── Credentials card shown AFTER child creation ── */}
                  {createdChildren[parent.id] && (
                    <div style={{ background:"rgba(34,197,94,.07)", border:"1.5px solid rgba(34,197,94,.3)", borderRadius:12, padding:"14px 16px", marginBottom:16 }}>
                      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:8 }}>
                        <strong style={{ color:"#22c55e", fontSize:".9rem" }}>
                          ✅ Child account created for {createdChildren[parent.id].username}!
                        </strong>
                        <button onClick={() => setCreatedChildren(p => ({ ...p, [parent.id]: null }))}
                          style={{ background:"none", border:"none", cursor:"pointer", color:"var(--muted)", fontSize:"1rem" }}>✕</button>
                      </div>

                      {/* Login credentials */}
                      <div style={{ background:"rgba(0,0,0,.15)", borderRadius:8, padding:"10px 12px", marginBottom:12, fontFamily:"monospace", fontSize:".82rem" }}>
                        <div style={{ marginBottom:4 }}>
                          <span style={{ color:"var(--muted)" }}>Username: </span>
                          <strong style={{ color:"#f8fafc" }}>{createdChildren[parent.id].username}</strong>
                          <button onClick={() => navigator.clipboard.writeText(createdChildren[parent.id].username)}
                            style={{ marginLeft:8, background:"none", border:"none", cursor:"pointer", color:"#a5b4fc", fontSize:".7rem", fontWeight:700 }}>📋</button>
                        </div>
                        <div style={{ marginBottom:4 }}>
                          <span style={{ color:"var(--muted)" }}>Login Email: </span>
                          <strong style={{ color:"#f8fafc" }}>{createdChildren[parent.id].email}</strong>
                          <button onClick={() => navigator.clipboard.writeText(createdChildren[parent.id].email)}
                            style={{ marginLeft:8, background:"none", border:"none", cursor:"pointer", color:"#a5b4fc", fontSize:".7rem", fontWeight:700 }}>📋</button>
                        </div>
                        <div>
                          <span style={{ color:"var(--muted)" }}>Password: </span>
                          <strong style={{ color:"#fbbf24" }}>{createdChildren[parent.id].password}</strong>
                          <button onClick={() => navigator.clipboard.writeText(createdChildren[parent.id].password)}
                            style={{ marginLeft:8, background:"none", border:"none", cursor:"pointer", color:"#a5b4fc", fontSize:".7rem", fontWeight:700 }}>📋</button>
                        </div>
                      </div>

                      {/* One-click login link */}
                      {(() => {
                        const loginLink = `https://likhapoha.in/?u=${encodeURIComponent(createdChildren[parent.id].email)}`;
                        return (
                          <div style={{ marginBottom:12 }}>
                            <p style={{ fontSize:".75rem", color:"#a5b4fc", margin:"0 0 4px", fontWeight:600 }}>🔗 One-click login link (pre-fills email)</p>
                            <div style={{ display:"flex", alignItems:"center", gap:6, background:"rgba(99,102,241,.1)", borderRadius:7, padding:"5px 8px", flexWrap:"wrap" }}>
                              <code style={{ fontSize:".7rem", color:"#c7d2fe", fontFamily:"monospace", flex:1, wordBreak:"break-all" }}>{loginLink}</code>
                              <button onClick={() => navigator.clipboard.writeText(loginLink)}
                                style={{ background:"rgba(99,102,241,.3)", border:"none", borderRadius:5, padding:"2px 8px", color:"#c7d2fe", cursor:"pointer", fontSize:".7rem", fontWeight:700, fontFamily:"inherit" }}>📋 Copy</button>
                            </div>
                            <p style={{ fontSize:".7rem", color:"var(--muted)", margin:"3px 0 0" }}>
                              Child can also sign in using their <strong>username</strong> OR <strong>email</strong> at likhapoha.in
                            </p>
                          </div>
                        );
                      })()}

                      {/* Next steps */}
                      <div style={{ fontSize:".82rem", lineHeight:1.6 }}>
                        <p style={{ fontWeight:700, marginBottom:6, color:"#f8fafc" }}>📋 What to do next:</p>
                        <ol style={{ paddingLeft:18, margin:0, color:"var(--muted)" }}>
                          <li>Share the <strong>username or email + password</strong> above with your child</li>
                          <li>Child logs in at <strong>likhapoha.in</strong> — can use <em>username</em> OR <em>email</em> to sign in</li>
                          <li>Child can <strong>change their password</strong> from their profile settings anytime</li>
                          <li style={{ color:"#a5b4fc", fontWeight:600 }}>💡 We recommend sitting with your child for their first login and giving them a quick walkthrough of the platform</li>
                        </ol>
                      </div>

                      {/* Video walkthrough placeholder */}
                      <div style={{ marginTop:12, background:"rgba(99,102,241,.1)", border:"1px dashed rgba(99,102,241,.4)", borderRadius:8, padding:"12px 14px", textAlign:"center" }}>
                        <div style={{ fontSize:"2rem", marginBottom:4 }}>▶️</div>
                        <p style={{ fontSize:".8rem", color:"#a5b4fc", margin:0, fontWeight:600 }}>Platform Walkthrough Video</p>
                        <p style={{ fontSize:".72rem", color:"var(--muted)", margin:"4px 0 0" }}>
                          Coming soon — a 3-minute video showing how to use LikhaPoha AI
                        </p>
                      </div>
                    </div>
                  )}

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
                        placeholder="Child's full name"
                        required
                      />
                    </label>

                    <label>
                      Child Login Email
                      <input
                        type="email"
                        value={childForm.email}
                        onChange={(e) =>
                          updateChildForm(parent.id, "email", e.target.value)
                        }
                        placeholder="child@example.com"
                        autoComplete="off"
                        required
                      />
                      <small style={{ color:"var(--muted)", fontSize:".75rem", marginTop:3, display:"block" }}>
                        This will be the child's login username
                      </small>
                    </label>

                    <label>
                      Set Password
                      <input
                        type="text"
                        value={childForm.password}
                        onChange={(e) =>
                          updateChildForm(parent.id, "password", e.target.value)
                        }
                        placeholder="Create a password for the child"
                        autoComplete="new-password"
                        required
                      />
                      <small style={{ color:"var(--muted)", fontSize:".75rem", marginTop:3, display:"block" }}>
                        👁️ Visible so you can confirm it — share this with your child
                      </small>
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
                      ✅ Create Child Account
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

                {/* Grade 11/12: stream shortcut auto-fills subject checkboxes */}
                {isStreamGrade(child.grade || "") && (
                  <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:10 }}>
                    <label style={{ fontSize:".85rem", fontWeight:600, minWidth:60 }}>Stream:</label>
                    <select
                      style={{ flex:1, fontSize:".85rem", padding:"6px 10px", borderRadius:8,
                               border:"1px solid var(--border)", background:"var(--surface2)", color:"var(--text)" }}
                      defaultValue=""
                      onChange={(e) => {
                        const subjects = getSubjectsForStream(e.target.value);
                        if (subjects.length > 0) {
                          updateLocalChild(family.family_id, child.id, "cbse_subjects", subjects);
                        }
                      }}
                    >
                      <option value="">— Apply stream shortcut —</option>
                      {GRADE_11_12_STREAMS.map(s => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                  </div>
                )}

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
