import { useEffect, useState } from "react";
import {
  LayoutDashboard, UserCircle, Users, Link2, Tag,
  Settings2, Monitor, Zap, BarChart2, LifeBuoy,
  KeyRound, PenLine, ClipboardList, Wrench, GraduationCap,
  Ticket, Image, UserPlus, Activity, Search, FlaskConical,
} from "lucide-react";
import AdminLessonExperienceLabPage from "./AdminLessonExperienceLabPage";
import "./AdminConsole.css";
import AdminQuickActions from "../components/AdminQuickActions";
import AdminRecentActivity from "../components/AdminRecentActivity";
import AdminGlobalSearch from "../components/AdminGlobalSearch";
import AdminFavorites, { usePinnedIds } from "../components/AdminFavorites";
import AdminNotificationCenter from "../components/AdminNotificationCenter";
import AdminBulkTools from "../components/AdminBulkTools";
import AdminSavedViews from "../components/AdminSavedViews";
import AdminAnalytics from "../components/AdminAnalytics";
import AdminViewAsUser from "../components/AdminViewAsUser";
import AdminSupportTools from "../components/AdminSupportTools";
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
  const [groqKeyPrefix, setGroqKeyPrefix] = useState("");
  const [groqModel, setGroqModel] = useState("llama-3.3-70b-versatile");
  const [newGroqKey, setNewGroqKey] = useState("");
  const [cerebrasKeyPrefix, setCerebrasKeyPrefix] = useState("");
  const [cerebrasModel, setCerebrasModel] = useState("gpt-oss-120b");
  const [newCerebrasKey, setNewCerebrasKey] = useState("");
  const [geminiKeyPrefix, setGeminiKeyPrefix] = useState("");
  const [geminiModel, setGeminiModel] = useState("gemini-2.5-flash");
  const [newGeminiKey, setNewGeminiKey] = useState("");
  const [sambanovaKeyPrefix, setSambanovaKeyPrefix] = useState("");
  const [sambanovaModel, setSambanovaModel] = useState("Meta-Llama-3.3-70B-Instruct");
  const [nvidiaKeyPrefix, setNvidiaKeyPrefix] = useState("");
  const [nvidiaModel, setNvidiaModel] = useState("meta/llama-4-scout-17b-16e-instruct");
  const [newNvidiaKey, setNewNvidiaKey] = useState("");
  const [ollamaCloudKeyPrefix, setOllamaCloudKeyPrefix] = useState("");
  const [ollamaCloudModel, setOllamaCloudModel] = useState("gemma3:4b");
  const [newOllamaCloudKey, setNewOllamaCloudKey] = useState("");
  const [newSambanovaKey, setNewSambanovaKey] = useState("");
  const [aiSettingsLoading, setAiSettingsLoading] = useState(true);
  const [aiSettingsSaving, setAiSettingsSaving] = useState(false);
  const [aiSettingsMessage, setAiSettingsMessage] = useState("");
  const [aiSettingsError, setAiSettingsError] = useState("");

  // Logging settings
  const [loggingEnabled, setLoggingEnabled] = useState(true);
  const [logLevel, setLogLevel] = useState("INFO");
  const [loggingLoading, setLoggingLoading] = useState(true);
  const [loggingMsg, setLoggingMsg] = useState("");

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
      setGroqKeyPrefix(data.groq_key_prefix || "");
      setGroqModel(data.groq_model || "llama-3.3-70b-versatile");
      setCerebrasKeyPrefix(data.cerebras_key_prefix || "");
      setCerebrasModel(data.cerebras_model || "gpt-oss-120b");
      setGeminiKeyPrefix(data.gemini_key_prefix || "");
      setGeminiModel(data.gemini_model || "gemini-2.0-flash-lite");
      setSambanovaKeyPrefix(data.sambanova_key_prefix || "");
      setSambanovaModel(data.sambanova_model || "Meta-Llama-3.3-70B-Instruct");
      setNvidiaKeyPrefix(data.nvidia_key_prefix || "");
      setNvidiaModel(data.nvidia_model || "meta/llama-4-scout-17b-16e-instruct");
      setOllamaCloudKeyPrefix(data.ollama_cloud_key_prefix || "");
      setOllamaCloudModel(data.ollama_cloud_model || "gemma3:4b");
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
        groq_model: groqModel,
        cerebras_model: cerebrasModel,
      };
      if (newApiKey.trim()) payload.openai_api_key = newApiKey.trim();
      if (newVeniceKey.trim()) payload.venice_api_key = newVeniceKey.trim();
      if (newGroqKey.trim()) payload.groq_api_key = newGroqKey.trim();
      if (newCerebrasKey.trim()) payload.cerebras_api_key = newCerebrasKey.trim();
      if (newGeminiKey.trim()) payload.gemini_api_key = newGeminiKey.trim();
      if (newSambanovaKey.trim()) payload.sambanova_api_key = newSambanovaKey.trim();
      if (newNvidiaKey.trim()) payload.nvidia_api_key = newNvidiaKey.trim();
      if (newOllamaCloudKey.trim()) payload.ollama_cloud_api_key = newOllamaCloudKey.trim();
      payload.gemini_model = geminiModel;
      payload.sambanova_model = sambanovaModel;
      payload.nvidia_model = nvidiaModel;
      payload.ollama_cloud_model = ollamaCloudModel;
      const data = await updateAiSettings(payload, user.accessToken);
      setAiEnabled(data.api_enabled ?? true);
      setAiKeyPrefix(data.api_key_prefix || "");
      setAiKeySource(data.key_source || "database");
      setAiProvider(data.provider || "openai");
      setVeniceKeyPrefix(data.venice_key_prefix || "");
      setVeniceModel(data.venice_model || "llama-3.3-70b");
      setGroqKeyPrefix(data.groq_key_prefix || "");
      setGroqModel(data.groq_model || "llama-3.3-70b-versatile");
      setCerebrasKeyPrefix(data.cerebras_key_prefix || "");
      setCerebrasModel(data.cerebras_model || "gpt-oss-120b");
      setNewApiKey("");
      setNewVeniceKey("");
      setNewGroqKey("");
      setNewCerebrasKey("");
      setNewSambanovaKey("");
      setNewNvidiaKey("");
      setNewOllamaCloudKey("");
      if (data.ollama_cloud_key_prefix !== undefined) setOllamaCloudKeyPrefix(data.ollama_cloud_key_prefix || "");
      if (data.ollama_cloud_model) setOllamaCloudModel(data.ollama_cloud_model);
      const providerLabel =
        data.provider === "venice" ? `Venice AI (${data.venice_model})` :
        data.provider === "groq" ? `Groq (${data.groq_model})` :
        data.provider === "cerebras" ? `Cerebras (${data.cerebras_model})` :
        data.provider === "gemini" ? `Gemini (${data.gemini_model})` :
        data.provider === "sambanova" ? `SambaNova (${data.sambanova_model})` :
        data.provider === "nvidia" ? `NVIDIA NIM (${data.nvidia_model})` :
        data.provider === "ollama_cloud" ? `Ollama Cloud (${data.ollama_cloud_model || ollamaCloudModel})` : "OpenAI";
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

  // ── Favorites / pinned actions shared between QuickActions + Favorites ─────
  const { pinnedIds, togglePin } = usePinnedIds();

  // ── Tab definitions (kept outside useState so it can validate URL params) ──
  const ADMIN_TABS = [
    { key: "overview",     label: "Overview",          Icon: LayoutDashboard },
    { key: "accounts",     label: "Accounts",          Icon: UserCircle },
    { key: "families",     label: "Families & Access", Icon: Users },
    { key: "associations", label: "Associations",      Icon: Link2 },
    { key: "offers",       label: "Offers",            Icon: Tag },
    { key: "ai",           label: "AI & Settings",     Icon: Settings2 },
    { key: "operations",   label: "Operations",        Icon: Monitor },
    { key: "bulk",         label: "Bulk Tools",        Icon: Zap },
    { key: "analytics",    label: "Analytics",         Icon: BarChart2 },
    { key: "support",      label: "Support",           Icon: LifeBuoy },
    { key: "lessonlab",    label: "Lesson Lab",        Icon: FlaskConical },
  ];
  const VALID_TAB_KEYS = new Set(ADMIN_TABS.map((t) => t.key));

  // ── Tab state (moved before early return to satisfy Rules of Hooks) ────────
  const [activeTab, setActiveTab] = useState(() => {
    try {
      const p = new URLSearchParams(window.location.search);
      const tabFromUrl = p.get("tab") || "overview";
      // Fall back to "overview" for any invalid/unknown tab value
      return VALID_TAB_KEYS.has(tabFromUrl) ? tabFromUrl : "overview";
    } catch { return "overview"; }
  });
  const handleTabChange = (tab) => {
    if (!VALID_TAB_KEYS.has(tab)) return;   // ignore invalid tab keys
    setActiveTab(tab);
    try {
      const u = new URL(window.location.href);
      u.searchParams.set("tab", tab);
      window.history.replaceState({}, "", u.toString());
    } catch { /* ignore */ }
  };

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

  const [collaborators, setCollaborators] = useState([]);
  const [collabLoading, setCollabLoading] = useState(false);
  const [collabUsername, setCollabUsername] = useState("");
  const [collabMsg, setCollabMsg] = useState("");
  const [collabErr, setCollabErr] = useState("");
  const [githubTokenMissing, setGithubTokenMissing] = useState(false);

  async function loadCollaborators() {
    setCollabLoading(true);
    try {
      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"}/api/admin-control/blog-collaborators`, {
        headers: { Authorization: `Bearer ${user?.accessToken}` },
      });
      const data = await res.json();
      if (!data.success && data.error?.includes("GITHUB_TOKEN")) {
        setGithubTokenMissing(true);
      } else {
        setGithubTokenMissing(false);
        setCollaborators(data.collaborators || []);
      }
    } catch { /* silently ignore */ }
    finally { setCollabLoading(false); }
  }

  async function inviteCollaborator(e) {
    e.preventDefault();
    setCollabMsg(""); setCollabErr("");
    if (!collabUsername.trim()) return;
    try {
      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"}/api/admin-control/blog-collaborators`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${user?.accessToken}` },
        body: JSON.stringify({ github_username: collabUsername.trim(), permission: "push" }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed");
      setCollabMsg(data.message || "Invitation sent!");
      setCollabUsername("");
      await loadCollaborators();
    } catch (err) { setCollabErr(err.message || "Failed to invite."); }
  }

  async function removeCollaborator(ghUsername) {
    if (!window.confirm(`Remove @${ghUsername} as blog collaborator?`)) return;
    try {
      await fetch(`${import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"}/api/admin-control/blog-collaborators/${ghUsername}`, {
        method: "DELETE", headers: { Authorization: `Bearer ${user?.accessToken}` },
      });
      setCollabMsg(`@${ghUsername} removed.`);
      await loadCollaborators();
    } catch (err) { setCollabErr(err.message || "Failed to remove."); }
  }

  async function loadLoggingSettings() {
    setLoggingLoading(true);
    try {
      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"}/api/admin-control/logging-settings`, {
        headers: { Authorization: `Bearer ${user?.accessToken}` },
      });
      const data = await res.json();
      setLoggingEnabled(data.logging_enabled ?? true);
      setLogLevel(data.log_level || "INFO");
    } catch { /* silently ignore */ }
    finally { setLoggingLoading(false); }
  }

  async function saveLoggingSettings(enabled, level) {
    setLoggingMsg("");
    try {
      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"}/api/admin-control/logging-settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${user?.accessToken}` },
        body: JSON.stringify({ logging_enabled: enabled, log_level: level }),
      });
      const data = await res.json();
      setLoggingEnabled(data.logging_enabled ?? enabled);
      setLogLevel(data.log_level || level);
      setLoggingMsg(data.message || (enabled ? "Logging enabled." : "Logging disabled."));
    } catch (err) { setLoggingMsg(err.message || "Failed to save."); }
  }

  // Load offer codes, influencer summary, and enrollments on mount
  useEffect(() => {
    if (user?.accessToken) { loadOfferCodes(); loadInfluencers(); loadEnrollments(); loadLoggingSettings(); loadCollaborators(); }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.accessToken]);

  if (loading) return <p>Loading admin control...</p>;

  // ---- AI Settings panel (rendered at top of page) ----
  const aiSettingsPanel = (
    <section className="premium-section">
      <div className="premium-header">
        <p className="eyebrow">Platform Configuration</p>
        <h3><KeyRound size={16} style={{display:"inline",verticalAlign:"middle",marginRight:6}} />AI API Settings</h3>
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

          {/* Provider selector — horizontal grid */}
          <div style={{ marginBottom: 20 }}>
            <strong>AI Provider</strong>
            <p style={{ fontSize: "0.82rem", color: "#888", margin: "4px 0 10px" }}>
              Groq, Cerebras, Gemini and SambaNova are <strong style={{color:"#22c55e"}}>100% free</strong> — no credit card needed.
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8 }}>
              {[
                ["openai",        "🤖 OpenAI",          "#6366f1"],
                ["venice",        "🎨 Venice AI",        "#8b5cf6"],
                ["groq",          "⚡ Groq",             "#10b981"],
                ["cerebras",      "🧠 Cerebras",         "#a855f7"],
                ["gemini",        "✨ Gemini",            "#f59e0b"],
                ["sambanova",     "🚀 SambaNova",        "#06b6d4"],
                ["nvidia",        "🟢 NVIDIA NIM",       "#76b900"],
                ["ollama_cloud",  "🦙 Ollama Cloud",     "#f97316"],
              ].map(([val, label, color]) => (
                <button key={val} onClick={() => setAiProvider(val)}
                  style={{
                    padding: "10px 8px", borderRadius: 10, border: `2px solid ${aiProvider === val ? color : "var(--border)"}`,
                    background: aiProvider === val ? `${color}18` : "var(--surface2,#111827)",
                    color: aiProvider === val ? color : "var(--muted)",
                    fontFamily: "inherit", fontSize: ".82rem", fontWeight: 700, cursor: "pointer",
                    transition: "all .18s", textAlign: "center",
                  }}>
                  {label}
                  {["groq","cerebras","gemini","sambanova","nvidia","ollama_cloud"].includes(val) && (
                    <span style={{ display:"block", fontSize:".68rem", color:"#22c55e", fontWeight:800, marginTop:2 }}>FREE</span>
                  )}
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

          {/* Groq settings */}
          {aiProvider === "groq" && (
            <div style={{ background: "rgba(16,185,129,.07)", border: "1px solid rgba(16,185,129,.25)", borderRadius: 10, padding: "14px 16px", marginBottom: 16 }}>
              <strong>Groq Settings</strong>
              <p style={{ fontSize: "0.82rem", color: "#888", margin: "4px 0 12px" }}>
                Groq has a <strong>free tier</strong> — 14,400 requests/day, no charge.
                Get your key at <a href="https://console.groq.com" target="_blank" rel="noreferrer" style={{ color: "var(--accent,#6366f1)" }}>console.groq.com</a>.
                Your OpenAI key is <strong>never used</strong> when Groq is active.
              </p>

              <label style={{ display: "block", marginBottom: 12 }}>
                <strong style={{ fontSize: ".85rem" }}>Groq API Key</strong>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4, marginBottom: 6 }}>
                  <code style={{ background: "var(--surface2,#111827)", padding: "4px 10px", borderRadius: 6, fontFamily: "monospace", fontSize: ".82rem", letterSpacing: 1 }}>
                    {groqKeyPrefix ? `${groqKeyPrefix}••••••••••` : "No key stored"}
                  </code>
                </div>
                <input type="password" value={newGroqKey} onChange={(e) => setNewGroqKey(e.target.value)}
                  placeholder="gsk_…" style={{ width: "100%", fontFamily: "monospace" }} autoComplete="new-password" />
              </label>

              <label style={{ display: "block" }}>
                <strong style={{ fontSize: ".85rem" }}>Groq Model</strong>
                <select value={groqModel} onChange={(e) => setGroqModel(e.target.value)} style={{ width: "100%", marginTop: 4 }}>
                  <option value="llama-3.3-70b-versatile">Llama 3.3 70B Versatile — Best quality (recommended)</option>
                  <option value="llama-3.1-8b-instant">Llama 3.1 8B Instant — Fastest, highest throughput (prewarm)</option>
                </select>
                <p style={{ fontSize: ".75rem", color: "#888", marginTop: 4 }}>
                  💡 Use <strong>8B Instant</strong> for prewarming (highest throughput). Use <strong>70B</strong> for live student responses.
                </p>
              </label>
            </div>
          )}

          {/* Cerebras settings */}
          {aiProvider === "cerebras" && (
            <div style={{ background: "rgba(139,92,246,.07)", border: "1px solid rgba(139,92,246,.25)", borderRadius: 10, padding: "14px 16px", marginBottom: 16 }}>
              <strong>Cerebras Settings</strong>
              <p style={{ fontSize: "0.82rem", color: "#888", margin: "4px 0 12px" }}>
                Cerebras runs Llama 3.3 70B with <strong>no daily token cap</strong> — ideal for prewarming all grades.
                Free, no credit card. Get your key at{" "}
                <a href="https://cloud.cerebras.ai" target="_blank" rel="noreferrer" style={{ color: "var(--accent,#6366f1)" }}>cloud.cerebras.ai</a>.
                Your OpenAI key is <strong>never used</strong> when Cerebras is active.
              </p>

              <label style={{ display: "block", marginBottom: 12 }}>
                <strong style={{ fontSize: ".85rem" }}>Cerebras API Key</strong>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4, marginBottom: 6 }}>
                  <code style={{ background: "var(--surface2,#111827)", padding: "4px 10px", borderRadius: 6, fontFamily: "monospace", fontSize: ".82rem", letterSpacing: 1 }}>
                    {cerebrasKeyPrefix ? `${cerebrasKeyPrefix}••••••••••` : "No key stored"}
                  </code>
                </div>
                <input type="password" value={newCerebrasKey} onChange={(e) => setNewCerebrasKey(e.target.value)}
                  placeholder="csk_…" style={{ width: "100%", fontFamily: "monospace" }} autoComplete="new-password" />
              </label>

              <label style={{ display: "block" }}>
                <strong style={{ fontSize: ".85rem" }}>Cerebras Model</strong>
                <select value={cerebrasModel} onChange={(e) => setCerebrasModel(e.target.value)} style={{ width: "100%", marginTop: 4 }}>
                  <option value="gpt-oss-120b">GPT-OSS 120B — Full quality, no token cap (recommended)</option>
                  <option value="zai-glm-4.7">ZAI GLM 4.7 — Lightweight, ultra-fast</option>
                </select>
                <p style={{ fontSize: ".75rem", color: "#888", marginTop: 4 }}>
                  💡 Use <strong>GPT-OSS 120B</strong> for all tasks — no token cap means you never get blocked during prewarming.
                </p>
              </label>
            </div>
          )}

          {/* Gemini settings */}
          {aiProvider === "gemini" && (
            <div style={{ background: "rgba(245,158,11,.07)", border: "1px solid rgba(245,158,11,.3)", borderRadius: 10, padding: "14px 16px", marginBottom: 16 }}>
              <strong>Google Gemini Settings</strong>
              <p style={{ fontSize: "0.82rem", color: "#888", margin: "4px 0 12px" }}>
                Gemini Flash has a <strong>1M token/day free tier</strong> — no credit card.
                Get your key at{" "}
                <a href="https://aistudio.google.com/apikey" target="_blank" rel="noreferrer" style={{ color: "var(--accent,#6366f1)" }}>aistudio.google.com/apikey</a>.
                Key starts with <code>AIza…</code>
              </p>
              <label style={{ display: "block", marginBottom: 12 }}>
                <strong style={{ fontSize: ".85rem" }}>Gemini API Key</strong>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4, marginBottom: 6 }}>
                  <code style={{ background: "var(--surface2,#111827)", padding: "4px 10px", borderRadius: 6, fontFamily: "monospace", fontSize: ".82rem", letterSpacing: 1 }}>
                    {geminiKeyPrefix ? `${geminiKeyPrefix}••••••••••` : "No key stored"}
                  </code>
                </div>
                <input type="password" value={newGeminiKey} onChange={(e) => setNewGeminiKey(e.target.value)}
                  placeholder="AIza…" style={{ width: "100%", fontFamily: "monospace" }} autoComplete="new-password" />
              </label>
              <label style={{ display: "block" }}>
                <strong style={{ fontSize: ".85rem" }}>Gemini Model</strong>
                <select value={geminiModel} onChange={(e) => setGeminiModel(e.target.value)} style={{ width: "100%", marginTop: 4 }}>
                  <option value="gemini-2.5-flash">Gemini 2.5 Flash — Fast, free, best quality (recommended ✅)</option>
                  <option value="gemini-2.5-pro">Gemini 2.5 Pro — Highest quality, more thoughtful</option>
                </select>
                <p style={{ fontSize: ".75rem", color: "#888", marginTop: 4 }}>
                  💡 Use <strong>Flash Lite</strong> for everything — 1M tokens/day free. Flash has 1M token context window — great for long lessons.
                </p>
              </label>
            </div>
          )}

          {/* SambaNova settings */}
          {aiProvider === "sambanova" && (
            <div style={{ background: "rgba(6,182,212,.07)", border: "1px solid rgba(6,182,212,.3)", borderRadius: 10, padding: "14px 16px", marginBottom: 16 }}>
              <strong>SambaNova Cloud Settings</strong>
              <p style={{ fontSize: "0.82rem", color: "#888", margin: "4px 0 12px" }}>
                SambaNova provides Llama 4 Scout with a <strong>generous free tier</strong> (~1M tokens/day).
                Get your key at{" "}
                <a href="https://cloud.sambanova.ai" target="_blank" rel="noreferrer" style={{ color: "var(--accent,#6366f1)" }}>cloud.sambanova.ai</a>.
                Key starts with <code>sn-</code>
              </p>
              <label style={{ display: "block", marginBottom: 12 }}>
                <strong style={{ fontSize: ".85rem" }}>SambaNova API Key</strong>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4, marginBottom: 6 }}>
                  <code style={{ background: "var(--surface2,#111827)", padding: "4px 10px", borderRadius: 6, fontFamily: "monospace", fontSize: ".82rem", letterSpacing: 1 }}>
                    {sambanovaKeyPrefix ? `${sambanovaKeyPrefix}••••••••••` : "No key stored"}
                  </code>
                </div>
                <input type="password" value={newSambanovaKey} onChange={(e) => setNewSambanovaKey(e.target.value)}
                  placeholder="sn-…" style={{ width: "100%", fontFamily: "monospace" }} autoComplete="new-password" />
              </label>
              <label style={{ display: "block" }}>
                <strong style={{ fontSize: ".85rem" }}>SambaNova Model</strong>
                <select value={sambanovaModel} onChange={(e) => setSambanovaModel(e.target.value)} style={{ width: "100%", marginTop: 4 }}>
                  <option value="Meta-Llama-3.3-70B-Instruct">✅ FREE — Meta-Llama-3.3-70B-Instruct (best quality, recommended)</option>
                  <option value="DeepSeek-V3.2">✅ FREE — DeepSeek-V3.2 (strong reasoning)</option>
                  <option value="DeepSeek-V3.1">✅ FREE — DeepSeek-V3.1 (strong reasoning, prev)</option>
                  <option value="gemma-4-31B-it">✅ FREE — gemma-4-31B-it (Google Gemma 4 31B)</option>
                  <option value="gpt-oss-120b">✅ FREE — gpt-oss-120b (large open-source)</option>
                  <option value="MiniMax-M2.7">💳 PAID — MiniMax-M2.7 (requires payment method)</option>
                </select>
                <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginTop: 6 }}>
                  💡 5 models are <strong>completely free</strong>. <strong>Meta-Llama-3.3-70B-Instruct</strong> gives best lesson quality. MiniMax-M2.7 requires a paid SambaNova account.
                </p>
              </label>
            </div>
          )}

          {/* NVIDIA NIM settings */}
          {aiProvider === "nvidia" && (
            <div style={{ background: "rgba(118,185,0,.07)", border: "1px solid rgba(118,185,0,.3)", borderRadius: 10, padding: "14px 16px", marginBottom: 16 }}>
              <strong>NVIDIA NIM Settings</strong>
              <p style={{ fontSize: "0.82rem", color: "#888", margin: "4px 0 12px" }}>
                NVIDIA NIM provides Llama 4 Scout and other models via an OpenAI-compatible API.
                Free tier available at{" "}
                <a href="https://build.nvidia.com/settings/api-keys" target="_blank" rel="noreferrer" style={{ color: "var(--accent,#6366f1)" }}>build.nvidia.com</a>.
                Key starts with <code>nvapi-</code>
              </p>
              <label style={{ display: "block", marginBottom: 12 }}>
                <strong style={{ fontSize: ".85rem" }}>NVIDIA API Key</strong>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4, marginBottom: 6 }}>
                  <code style={{ background: "var(--surface2,#111827)", padding: "4px 10px", borderRadius: 6, fontFamily: "monospace", fontSize: ".82rem", letterSpacing: 1 }}>
                    {nvidiaKeyPrefix ? `${nvidiaKeyPrefix}••••••••••` : "No key stored"}
                  </code>
                </div>
                <input type="password" value={newNvidiaKey} onChange={(e) => setNewNvidiaKey(e.target.value)}
                  placeholder="nvapi-…" style={{ width: "100%", fontFamily: "monospace" }} autoComplete="new-password" />
              </label>
              <label style={{ display: "block" }}>
                <strong style={{ fontSize: ".85rem" }}>NVIDIA Model</strong>
                <select value={nvidiaModel} onChange={(e) => setNvidiaModel(e.target.value)} style={{ width: "100%", marginTop: 4 }}>
                  <option value="meta/llama-3.1-8b-instruct">✅ FREE — meta/llama-3.1-8b-instruct (Llama 3.1 8B — fastest, recommended)</option>
                  <option value="meta/llama-3.1-70b-instruct">✅ FREE — meta/llama-3.1-70b-instruct (Llama 3.1 70B — best quality)</option>
                  <option value="meta/llama-3.2-3b-instruct">✅ FREE — meta/llama-3.2-3b-instruct (Llama 3.2 3B — ultra-fast)</option>
                  <option value="deepseek-ai/deepseek-v4-flash">✅ FREE — deepseek-ai/deepseek-v4-flash (DeepSeek V4 Flash)</option>
                  <option value="google/gemma-3-4b-it">✅ FREE — google/gemma-3-4b-it (Gemma 3 4B)</option>
                  <option value="google/gemma-3-12b-it">✅ FREE — google/gemma-3-12b-it (Gemma 3 12B)</option>
                  <option value="google/gemma-4-31b-it">✅ FREE — google/gemma-4-31b-it (Gemma 4 31B)</option>
                </select>
                <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginTop: 6 }}>
                  💡 <strong>meta/llama-3.1-8b-instruct</strong> is confirmed working on this account. Use <strong>llama-3.1-70b-instruct</strong> for best lesson quality. Get your free key at{" "}
                  <a href="https://build.nvidia.com/settings/api-keys" target="_blank" rel="noreferrer" style={{ color: "#76b900" }}>build.nvidia.com</a>.
                </p>
              </label>
            </div>
          )}

          {/* Ollama Cloud settings */}
          {aiProvider === "ollama_cloud" && (
            <div style={{ background: "rgba(249,115,22,.07)", border: "1px solid rgba(249,115,22,.3)", borderRadius: 10, padding: "14px 16px", marginBottom: 16 }}>
              <strong>Ollama Cloud Settings</strong>
              <p style={{ fontSize: "0.82rem", color: "#888", margin: "4px 0 12px" }}>
                Ollama Cloud has a <strong>free tier</strong> — gemma3:4b, gemma3:12b, gpt-oss:20b are free.
                Get your key at{" "}
                <a href="https://ollama.com" target="_blank" rel="noreferrer" style={{ color: "var(--accent,#6366f1)" }}>ollama.com</a>.
                Uses native Ollama API at <code>https://api.ollama.com</code>.
              </p>
              <label style={{ display: "block", marginBottom: 12 }}>
                <strong style={{ fontSize: ".85rem" }}>Ollama Cloud API Key</strong>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4, marginBottom: 6 }}>
                  <code style={{ background: "var(--surface2,#111827)", padding: "4px 10px", borderRadius: 6, fontFamily: "monospace", fontSize: ".82rem", letterSpacing: 1 }}>
                    {ollamaCloudKeyPrefix ? `${ollamaCloudKeyPrefix}••••••••••` : "No key stored"}
                  </code>
                </div>
                <input type="password" value={newOllamaCloudKey} onChange={(e) => setNewOllamaCloudKey(e.target.value)}
                  placeholder="Your Ollama Cloud key" style={{ width: "100%", fontFamily: "monospace" }} autoComplete="new-password" />
              </label>
              <label style={{ display: "block" }}>
                <strong style={{ fontSize: ".85rem" }}>Model</strong>
                <select value={ollamaCloudModel} onChange={(e) => setOllamaCloudModel(e.target.value)} style={{ width: "100%", marginTop: 4 }}>
                  <option value="gemma3:4b">gemma3:4b — Free tier, fast (recommended ✅)</option>
                  <option value="gemma3:12b">gemma3:12b — Free tier, higher quality</option>
                  <option value="gpt-oss:20b">gpt-oss:20b — Free tier, GPT-OSS</option>
                  <option value="glm-5.2">glm-5.2 — Premium (subscription required)</option>
                  <option value="minimax-m2.1">minimax-m2.1 — Premium (subscription required)</option>
                  <option value="kimi-k2.6">kimi-k2.6 — Premium (subscription required)</option>
                </select>
                <p style={{ fontSize: ".75rem", color: "#888", marginTop: 4 }}>
                  💡 Free models: <strong>gemma3:4b</strong>, <strong>gemma3:12b</strong>, <strong>gpt-oss:20b</strong> — confirmed working.
                  Premium models require a paid subscription at ollama.com/upgrade.
                </p>
              </label>
            </div>
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
      "Platform Access","Daily Token Limit","Monthly Token Limit","Created At",
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
    <div className="premium-page admin-control-page" data-testid="admin-control-page">

      {/* ── Tab Navigation + Search + Notifications ─────────────────────── */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 12px 0", flexWrap: "wrap" }}>
        <AdminGlobalSearch
          handleTabChange={handleTabChange}
          allStudents={allStudents}
          allParents={allParents}
          allTeachers={allTeachers}
          offerCodes={offerCodes}
        />
        <AdminNotificationCenter
          accessToken={user?.accessToken}
          onNavigate={handleTabChange}
        />
      </div>

      <nav className="admin-tab-nav" role="tablist" aria-label="Admin Console" data-testid="admin-tab-nav">
        {ADMIN_TABS.map((t) => (
          <button key={t.key} role="tab"
            aria-selected={activeTab === t.key}
            aria-controls={`admin-tab-panel-${t.key}`}
            id={`admin-tab-btn-${t.key}`}
            className={`admin-tab-btn${activeTab === t.key ? " active" : ""}`}
            onClick={() => handleTabChange(t.key)}
            data-testid={`admin-tab-${t.key}`}>
            <span className="admin-tab-icon" aria-hidden="true"><t.Icon size={15} strokeWidth={2} /></span>
            <span className="admin-tab-label">{t.label}</span>
          </button>
        ))}
      </nav>

      {/* ── Global message/error banners (always visible) ─────────────── */}
      {message && <div className="info-box" style={{ margin: "8px 16px 0" }}>{message}</div>}
      {error && <div className="error-box" style={{ margin: "8px 16px 0" }}>{error}</div>}

      {/* ── AI & Settings Tab ──────────────────────────────────────────── */}
      {activeTab === "ai" && (
      <div id="admin-tab-panel-ai" role="tabpanel" aria-labelledby="admin-tab-btn-ai" data-testid="tab-panel-ai">
      {aiSettingsPanel}

      {/* ── Blog Collaborators Panel ── */}
      <section className="premium-section">
        <div className="premium-header">
          <p className="eyebrow">Content Management</p>
          <h3><PenLine size={16} style={{display:"inline",verticalAlign:"middle",marginRight:6}} />Blog Collaborators</h3>
          <p>Invite GitHub users to edit blog posts directly on GitHub. They can create, edit, and delete <code>.md</code> files in <code>frontend/src/blog/posts/</code>.</p>
        </div>

        {githubTokenMissing ? (
          <div className="premium-card" style={{ maxWidth: 560 }}>
            <div className="error-box" style={{ marginBottom: 14 }}>
              ⚠️ <strong>GITHUB_TOKEN not configured</strong> — add it to your backend <code>.env</code> to enable collaborator management.
            </div>
            <p style={{ fontSize: ".85rem", color: "var(--muted)", marginBottom: 8 }}>Add this to <code>backend/.env</code>:</p>
            <pre style={{ background: "var(--surface2,#111827)", borderRadius: 8, padding: "10px 14px", fontSize: ".82rem", overflow: "auto" }}>
{`GITHUB_TOKEN=ghp_your_token_here
GITHUB_REPO=pradipbhuyan/likha-poha-ai`}
            </pre>
            <p style={{ fontSize: ".78rem", color: "var(--muted)", marginTop: 8 }}>
              Create a token at <a href="https://github.com/settings/tokens" target="_blank" rel="noreferrer" style={{ color: "#6366f1" }}>github.com/settings/tokens</a> with <strong>repo</strong> scope.
            </p>
          </div>
        ) : (
          <div className="premium-card" style={{ maxWidth: 620 }}>
            {/* Invite form */}
            <form onSubmit={inviteCollaborator} style={{ display: "flex", gap: 8, marginBottom: 20, flexWrap: "wrap" }}>
              <input
                type="text"
                value={collabUsername}
                onChange={e => setCollabUsername(e.target.value)}
                placeholder="GitHub username (e.g. blogwriter123)"
                style={{ flex: 1, minWidth: 200 }}
                required
              />
              <button className="primary-btn" type="submit" style={{ whiteSpace: "nowrap" }}>
                📨 Invite Collaborator
              </button>
            </form>

            {collabMsg && <div className="info-box" style={{ marginBottom: 12 }}>{collabMsg}</div>}
            {collabErr && <div className="error-box" style={{ marginBottom: 12 }}>{collabErr}</div>}

            {/* Current collaborators */}
            <h4 style={{ margin: "0 0 12px", fontSize: ".9rem" }}>Current Collaborators</h4>
            {collabLoading ? <p>Loading…</p> : collaborators.length === 0 ? (
              <p style={{ color: "var(--muted)", fontSize: ".85rem" }}>No collaborators yet. Invite someone above.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {collaborators.map(c => (
                  <div key={c.username} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 12px", background: "var(--surface2,#111827)", borderRadius: 8 }}>
                    {c.avatar && <img src={c.avatar} alt={c.username} style={{ width: 28, height: 28, borderRadius: "50%" }} />}
                    <div style={{ flex: 1 }}>
                      <strong>@{c.username}</strong>
                      <a href={c.profile_url} target="_blank" rel="noreferrer" style={{ marginLeft: 8, fontSize: ".75rem", color: "#6366f1" }}>View profile →</a>
                    </div>
                    <button onClick={() => removeCollaborator(c.username)} className="danger-btn" style={{ fontSize: ".78rem", padding: "4px 10px" }}>
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div style={{ marginTop: 16, padding: "10px 14px", background: "rgba(99,102,241,.06)", border: "1px solid rgba(99,102,241,.2)", borderRadius: 8, fontSize: ".8rem", color: "var(--muted)" }}>
              <strong style={{ color: "#a5b4fc" }}>How it works:</strong> The collaborator gets an email invitation. Once accepted, they can go to{" "}
              <a href="https://github.com/pradipbhuyan/likha-poha-ai/tree/main/frontend/src/blog/posts" target="_blank" rel="noreferrer" style={{ color: "#6366f1" }}>
                GitHub → blog/posts
              </a>{" "}
              and click ✏️ to edit any post, or create new <code>.md</code> files. Changes auto-deploy in ~3 minutes.
            </div>
          </div>
        )}
      </section>

      {/* ── Logging Settings Panel ── */}
      <section className="premium-section">
        <div className="premium-header">
          <p className="eyebrow">Platform Configuration</p>
          <h3><ClipboardList size={16} style={{display:"inline",verticalAlign:"middle",marginRight:6}} />Logging Settings</h3>
          <p>Control structured request/event logging for the backend. Disable to reduce log noise in production.</p>
        </div>
        {loggingLoading ? <p>Loading…</p> : (
          <div className="premium-card" style={{ maxWidth: 520 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 16 }}>
              <strong>Platform Logging</strong>
              <div
                onClick={() => {
                  const next = !loggingEnabled;
                  setLoggingEnabled(next);
                  saveLoggingSettings(next, logLevel);
                }}
                style={{
                  width: 52, height: 28, borderRadius: 14,
                  background: loggingEnabled ? "#10b981" : "#ccc",
                  position: "relative", cursor: "pointer", transition: "background 0.2s", flexShrink: 0,
                }}>
                <div style={{
                  position: "absolute", top: 3, left: loggingEnabled ? 27 : 3,
                  width: 22, height: 22, borderRadius: "50%", background: "#fff",
                  transition: "left 0.2s", boxShadow: "0 1px 4px rgba(0,0,0,.2)",
                }} />
              </div>
              <span style={{ fontWeight: 600, color: loggingEnabled ? "#10b981" : "#999" }}>
                {loggingEnabled ? "Logging ON" : "Logging OFF"}
              </span>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
              <label style={{ fontWeight: 600, minWidth: 80 }}>Log Level</label>
              <select value={logLevel} onChange={e => { setLogLevel(e.target.value); saveLoggingSettings(loggingEnabled, e.target.value); }}
                style={{ flex: 1, padding: "7px 10px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface2)", color: "var(--text)", fontFamily: "inherit" }}>
                <option value="DEBUG">DEBUG — everything (verbose)</option>
                <option value="INFO">INFO — requests + LLM calls (recommended)</option>
                <option value="WARNING">WARNING — only warnings + errors</option>
                <option value="ERROR">ERROR — errors only (minimal)</option>
              </select>
            </div>

            <div style={{ background: "rgba(16,185,129,.06)", border: "1px solid rgba(16,185,129,.2)", borderRadius: 8, padding: "10px 14px", fontSize: ".8rem", color: "var(--muted)" }}>
              <strong style={{ color: "#10b981" }}>What gets logged at INFO level:</strong>
              <ul style={{ margin: "6px 0 0", paddingLeft: 16 }}>
                <li>Every HTTP request: method, path, status, duration_ms, trace_id</li>
                <li>Every LLM call: provider, model, tokens, cost, duration_ms</li>
                <li>Lesson generation: grade, subject, source (cache/RAG/LLM)</li>
                <li>Payment events: order_id, plan_key, success/failure with LP error codes</li>
              </ul>
            </div>

            {loggingMsg && <div className="info-box" style={{ marginTop: 12 }}>{loggingMsg}</div>}
          </div>
        )}
      </section>
      </div>)}

      {/* ── Overview Tab ───────────────────────────────────────────────── */}
      {activeTab === "overview" && (
      <div id="admin-tab-panel-overview" role="tabpanel" aria-labelledby="admin-tab-btn-overview" data-testid="tab-panel-overview">
      <section className="premium-section admin-control-hero">
        <div className="premium-header">
          <p className="eyebrow">Admin Operations</p>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
            <h2 style={{ margin: 0 }}><Wrench size={18} style={{display:"inline",verticalAlign:"middle",marginRight:7}} />Admin Control Center</h2>
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

      {/* ── Quick Actions ── */}
      <section className="premium-section">
        <AdminQuickActions
          handleTabChange={handleTabChange}
          exportUsersCSV={exportUsersCSV}
          onPinToggle={togglePin}
          pinnedIds={pinnedIds}
        />
      </section>

      {/* ── Pinned Favorites ── */}
      <section className="premium-section">
        <AdminFavorites
          handleTabChange={handleTabChange}
          exportUsersCSV={exportUsersCSV}
        />
      </section>

      {/* ── Recent Activity ── */}
      <section className="premium-section">
        <AdminRecentActivity
          accessToken={user?.accessToken}
          onViewMore={() => handleTabChange("operations")}
        />
      </section>

      </div>)}

      {/* ── Account Creation Tab ───────────────────────────────────────── */}
      {activeTab === "accounts" && (
      <div id="admin-tab-panel-accounts" role="tabpanel" aria-labelledby="admin-tab-btn-accounts" data-testid="tab-panel-accounts">
      <section id="create-parent-form" className="premium-section admin-create-section">
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
              id="create-teacher-form"
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
            <h3><GraduationCap size={16} style={{display:"inline",verticalAlign:"middle",marginRight:6}} />Create Student</h3>
            <p>Create a standalone student account. Optionally link to a parent later.</p>
          </div>
          <div className="admin-create-grid">
            <div className="admin-create-card" style={{ gridColumn: "1 / -1" }}>
              <form id="create-student-form" onSubmit={handleCreateStudent} className="form-grid premium-rag-form-grid admin-compact-form">
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
      </div>)}

      {/* ── Offers & Influencers Tab ────────────────────────────────────── */}
      {activeTab === "offers" && (
      <div id="admin-tab-panel-offers" role="tabpanel" aria-labelledby="admin-tab-btn-offers" data-testid="tab-panel-offers">
      {/* ── Offer Codes Section ── */}
      <section id="create-offer-form" className="premium-section">
        <div className="premium-header">
          <p className="eyebrow">Access Management</p>
          <h3><Ticket size={16} style={{display:"inline",verticalAlign:"middle",marginRight:6}} />Offer Codes</h3>
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
                <h4 style={{margin:"0 0 8px",fontSize:".95rem"}}><Image size={14} style={{display:"inline",verticalAlign:"middle",marginRight:5}} />Refresh Promo Images</h4>
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
          <h3><UserPlus size={16} style={{display:"inline",verticalAlign:"middle",marginRight:6}} />Student Enrollments by Offer Code</h3>
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
          <h3><BarChart2 size={16} style={{display:"inline",verticalAlign:"middle",marginRight:6}} />Influencer Incentive Tracking</h3>
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
      </div>)}

      {/* ── Associations Tab ───────────────────────────────────────────── */}
      {activeTab === "associations" && (
      <div id="admin-tab-panel-associations" role="tabpanel" aria-labelledby="admin-tab-btn-associations" data-testid="tab-panel-associations">
      {/* ── Parent-Child Association Section ── */}
      <ParentChildAssociationSection accessToken={user?.accessToken} />

      {/* ── Teacher-Student Association Section ── */}
      <TeacherStudentAssociationSection accessToken={user?.accessToken} />
      </div>)}

      {/* ── Families & Access Tab ──────────────────────────────────────── */}
      {activeTab === "families" && (
      <div id="admin-tab-panel-families" role="tabpanel" aria-labelledby="admin-tab-btn-families" data-testid="tab-panel-families">
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
                  <h4><Activity size={14} style={{display:"inline",verticalAlign:"middle",marginRight:5}} />Student Activity</h4>

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
                  ["access_cbse", "Platform Access"],
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
      </div>)}

      {/* ── Operations Tab ─────────────────────────────────────────────── */}
      {activeTab === "operations" && (
      <div id="admin-tab-panel-operations" role="tabpanel" aria-labelledby="admin-tab-btn-operations" data-testid="tab-panel-operations">
        <AdminOperationsEmbed user={user} />
      </div>)}

      {/* ── Bulk Tools Tab ─────────────────────────────────────────────── */}
      {activeTab === "bulk" && (
      <div id="admin-tab-panel-bulk" role="tabpanel" aria-labelledby="admin-tab-btn-bulk" data-testid="tab-panel-bulk">
        <section className="premium-section">
          <div className="premium-header">
            <p className="eyebrow">Admin Tools</p>
            <h3><Zap size={16} style={{display:"inline",verticalAlign:"middle",marginRight:6}} />Bulk Operations</h3>
            <p>Assign teachers, reset passwords, grant access, export users, and import students at scale.</p>
          </div>
          <AdminBulkTools
            accessToken={user?.accessToken}
            allStudents={allStudents}
            allTeachers={allTeachers}
            allParents={allParents}
          />
        </section>
      </div>)}

      {/* ── Analytics Tab ──────────────────────────────────────────────── */}
      {activeTab === "analytics" && (
      <div id="admin-tab-panel-analytics" role="tabpanel" aria-labelledby="admin-tab-btn-analytics" data-testid="tab-panel-analytics">
        <section className="premium-section">
          <AdminAnalytics accessToken={user?.accessToken} />
        </section>
        <section className="premium-section" style={{ marginTop: 0 }}>
          <div className="premium-header">
            <p className="eyebrow">Admin Views</p>
            <h3><Search size={16} style={{display:"inline",verticalAlign:"middle",marginRight:6}} />Saved Views</h3>
            <p>Prebuilt filtered views for common operational queries — live data on each request.</p>
          </div>
          <AdminSavedViews accessToken={user?.accessToken} />
        </section>
      </div>)}

      {/* ── Support Tab ────────────────────────────────────────────────── */}
      {activeTab === "lessonlab" && (
      <div id="admin-tab-panel-lessonlab" role="tabpanel" aria-labelledby="admin-tab-btn-lessonlab" data-testid="tab-panel-lessonlab">
        <AdminLessonExperienceLabPage user={user} />
      </div>)}

      {activeTab === "support" && (
      <div id="admin-tab-panel-support" role="tabpanel" aria-labelledby="admin-tab-btn-support" data-testid="tab-panel-support">
        <section className="premium-section">
          <div className="premium-header">
            <p className="eyebrow">Support Tools</p>
            <h3>🛟 User Support</h3>
            <p>Look up users, view resolved subscription state, subscription history, audit events, and reset passwords.</p>
          </div>
          <AdminSupportTools accessToken={user?.accessToken} />
        </section>
        <section className="premium-section" style={{ marginTop: 0 }}>
          <div className="premium-header">
            <p className="eyebrow">Support Tools</p>
            <h3>👁 View as User</h3>
            <p>Read-only simulation of any user context. No JWT exchange. All admin actions remain restricted.</p>
          </div>
          <AdminViewAsUser accessToken={user?.accessToken} />
        </section>
      </div>)}

    </div>
  );
}

// ── Lightweight Operations embed (reuses AdminOperationsPage) ────────────────
function AdminOperationsEmbed({ user }) {
  // Lazy import AdminOperationsPage to avoid circular deps
  const [Page, setPage] = useState(null);
  useEffect(() => {
    import("./AdminOperationsPage").then((m) => setPage(() => m.default));
  }, []);
  if (!Page) return <div style={{padding:32,color:"#94a3b8"}}>Loading Operations Dashboard…</div>;
  return <Page user={user} />;
}

// ─────────────────────────────────────────────────────────────────────────────
// Parent-Child Association Component (used inside AdminControlPage)
// ─────────────────────────────────────────────────────────────────────────────

function ParentChildAssociationSection({ accessToken }) {
  /**
   * Admin-only section for linking parents to students.
   * Allows searching parents and students by name/email, then linking them.
   * Also shows all existing associations and allows unlinking.
   */
  const [parentQuery, setParentQuery] = useState("");
  const [studentQuery, setStudentQuery] = useState("");
  const [parentResults, setParentResults] = useState([]);
  const [studentResults, setStudentResults] = useState([]);
  const [selectedParent, setSelectedParent] = useState(null);
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [linking, setLinking] = useState(false);
  const [linkMsg, setLinkMsg] = useState("");
  const [linkErr, setLinkErr] = useState("");
  const [associations, setAssociations] = useState([]);
  const [assocLoading, setAssocLoading] = useState(false);
  const [assocQuery, setAssocQuery] = useState("");

  const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

  async function authGet(path) {
    const r = await fetch(`${API_BASE}${path}`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || "Request failed");
    return data;
  }

  async function authPost(path, body) {
    const r = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || "Request failed");
    return data;
  }

  async function authDelete(path) {
    const r = await fetch(`${API_BASE}${path}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || "Request failed");
    return data;
  }

  async function searchParents(q) {
    if (!q.trim()) { setParentResults([]); return; }
    try {
      const data = await authGet(`/api/admin-control/search-users?q=${encodeURIComponent(q)}&role=parent`);
      setParentResults(data.users || []);
    } catch { setParentResults([]); }
  }

  async function searchStudents(q) {
    if (!q.trim()) { setStudentResults([]); return; }
    try {
      const data = await authGet(`/api/admin-control/search-users?q=${encodeURIComponent(q)}&role=student`);
      setStudentResults(data.users || []);
    } catch { setStudentResults([]); }
  }

  async function loadAssociations() {
    setAssocLoading(true);
    try {
      const data = await authGet(`/api/admin-control/parent-child-associations?q=${encodeURIComponent(assocQuery)}`);
      setAssociations(data.associations || []);
    } catch { setAssociations([]); }
    finally { setAssocLoading(false); }
  }

  // Debounce search
  const { useState: _us, useEffect: _ue } = { useState, useEffect };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { const t = setTimeout(() => searchParents(parentQuery), 300); return () => clearTimeout(t); }, [parentQuery]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { const t = setTimeout(() => searchStudents(studentQuery), 300); return () => clearTimeout(t); }, [studentQuery]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { loadAssociations(); }, [assocQuery]);

  async function handleLink() {
    if (!selectedParent || !selectedStudent) { setLinkErr("Select both a parent and a student."); return; }
    setLinking(true); setLinkErr(""); setLinkMsg("");
    try {
      const result = await authPost("/api/admin-control/link-parent-child", {
        parent_id: selectedParent.id,
        child_id: selectedStudent.id,
      });
      setLinkMsg(result.message || "✅ Linked successfully.");
      setSelectedParent(null); setSelectedStudent(null);
      setParentQuery(""); setStudentQuery("");
      setParentResults([]); setStudentResults([]);
      loadAssociations();
    } catch (err) { setLinkErr(err.message || "Linking failed."); }
    finally { setLinking(false); }
  }

  async function handleUnlink(childId, childName) {
    if (!window.confirm(`Remove parent association from ${childName}?`)) return;
    try {
      await authDelete(`/api/admin-control/link-parent-child/${childId}`);
      setLinkMsg("✅ Association removed.");
      loadAssociations();
    } catch (err) { setLinkErr(err.message || "Failed to unlink."); }
  }

  const inputStyle = {
    width: "100%", background: "var(--surface2, #f8f9fa)", border: "1px solid var(--border, #e2e8f0)",
    borderRadius: 8, padding: "9px 12px", fontSize: ".88rem",
    fontFamily: "inherit", color: "inherit", outline: "none",
  };
  const resultItemStyle = (selected) => ({
    padding: "8px 12px", borderRadius: 8, cursor: "pointer", fontSize: ".85rem",
    background: selected ? "rgba(99,102,241,.15)" : "transparent",
    border: `1px solid ${selected ? "#6366f1" : "transparent"}`,
    marginBottom: 3,
  });

  return (
    <div className="premium-section" style={{ marginTop: 24 }}>
      <div className="premium-header">
        <h3>🔗 Parent-Child Association</h3>
        <p>Link an existing parent account to a student. Only admins can create or change these links.</p>
      </div>

      {linkMsg && <div className="info-box" style={{ marginBottom: 12 }}>{linkMsg}</div>}
      {linkErr && <div className="error-box" style={{ marginBottom: 12 }}>{linkErr}</div>}

      {/* Search + Link panel */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 24 }}>
        {/* Parent search */}
        <div className="premium-card">
          <h4 style={{ margin: "0 0 10px" }}>Search Parent</h4>
          <input
            style={inputStyle}
            placeholder="Search by name or email…"
            value={parentQuery}
            onChange={(e) => setParentQuery(e.target.value)}
          />
          {parentResults.length > 0 && (
            <div style={{ marginTop: 8, maxHeight: 200, overflowY: "auto" }}>
              {parentResults.map((u) => (
                <div key={u.id}
                  style={resultItemStyle(selectedParent?.id === u.id)}
                  onClick={() => setSelectedParent(u)}
                >
                  <strong>{u.username}</strong>
                  <small style={{ display: "block", color: "var(--muted, #64748b)" }}>{u.email}</small>
                </div>
              ))}
            </div>
          )}
          {selectedParent && (
            <div style={{ marginTop: 8, padding: "8px 12px", background: "rgba(99,102,241,.1)", borderRadius: 8, fontSize: ".85rem" }}>
              ✅ Selected: <strong>{selectedParent.username}</strong>
              <button onClick={() => setSelectedParent(null)}
                style={{ marginLeft: 8, background: "none", border: "none", cursor: "pointer", color: "#94a3b8", fontSize: ".9rem" }}>×</button>
            </div>
          )}
        </div>

        {/* Student search */}
        <div className="premium-card">
          <h4 style={{ margin: "0 0 10px" }}>Search Student</h4>
          <input
            style={inputStyle}
            placeholder="Search by name or email…"
            value={studentQuery}
            onChange={(e) => setStudentQuery(e.target.value)}
          />
          {studentResults.length > 0 && (
            <div style={{ marginTop: 8, maxHeight: 200, overflowY: "auto" }}>
              {studentResults.map((u) => (
                <div key={u.id}
                  style={resultItemStyle(selectedStudent?.id === u.id)}
                  onClick={() => setSelectedStudent(u)}
                >
                  <strong>{u.username}</strong>
                  <small style={{ display: "block", color: "var(--muted, #64748b)" }}>
                    {u.email} · {u.grade || "—"}
                    {u.parent_id ? " · (has parent)" : ""}
                  </small>
                </div>
              ))}
            </div>
          )}
          {selectedStudent && (
            <div style={{ marginTop: 8, padding: "8px 12px", background: "rgba(99,102,241,.1)", borderRadius: 8, fontSize: ".85rem" }}>
              ✅ Selected: <strong>{selectedStudent.username}</strong> ({selectedStudent.grade || "—"})
              <button onClick={() => setSelectedStudent(null)}
                style={{ marginLeft: 8, background: "none", border: "none", cursor: "pointer", color: "#94a3b8", fontSize: ".9rem" }}>×</button>
            </div>
          )}
        </div>
      </div>

      <button
        className="primary-btn"
        style={{ maxWidth: 280 }}
        disabled={linking || !selectedParent || !selectedStudent}
        onClick={handleLink}
      >
        {linking ? "Linking…" : "🔗 Link Parent to Student"}
      </button>

      {/* Existing associations */}
      <div style={{ marginTop: 28 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12, flexWrap: "wrap", gap: 10 }}>
          <h4 style={{ margin: 0 }}>Existing Associations ({associations.length})</h4>
          <input
            style={{ ...inputStyle, maxWidth: 260 }}
            placeholder="Filter by student name…"
            value={assocQuery}
            onChange={(e) => setAssocQuery(e.target.value)}
          />
        </div>

        {assocLoading ? (
          <p>Loading…</p>
        ) : associations.length === 0 ? (
          <div className="info-box">No parent-child associations found.</div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {associations.map((a, i) => (
              <div key={`${a.child.id}-${i}`} style={{
                display: "flex", alignItems: "center", justifyContent: "space-between",
                padding: "10px 14px", background: "var(--surface2, #f8f9fa)",
                borderRadius: 9, border: "1px solid var(--border, #e2e8f0)", flexWrap: "wrap", gap: 8,
              }}>
                <div style={{ fontSize: ".85rem" }}>
                  <strong>{a.child.username}</strong>
                  <span style={{ color: "var(--muted, #64748b)", marginLeft: 6 }}>({a.child.grade || "—"})</span>
                  <span style={{ margin: "0 8px", color: "var(--muted, #64748b)" }}>→</span>
                  <strong>{a.parent.username || "(unknown parent)"}</strong>
                  <span style={{ color: "var(--muted, #64748b)", marginLeft: 6, fontSize: ".78rem" }}>{a.parent.email || ""}</span>
                </div>
                <button
                  onClick={() => handleUnlink(a.child.id, a.child.username)}
                  style={{
                    background: "rgba(239,68,68,.1)", border: "1px solid rgba(239,68,68,.25)",
                    color: "#f87171", borderRadius: 7, padding: "4px 12px",
                    cursor: "pointer", fontSize: ".78rem", fontWeight: 600, fontFamily: "inherit",
                  }}
                >
                  Unlink
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Teacher-Student Association Component (used inside AdminControlPage)
// ─────────────────────────────────────────────────────────────────────────────

function TeacherStudentAssociationSection({ accessToken }) {
  const [teacherQuery, setTeacherQuery] = useState("");
  const [studentQuery, setStudentQuery] = useState("");
  const [teacherResults, setTeacherResults] = useState([]);
  const [studentResults, setStudentResults] = useState([]);
  const [selectedTeacher, setSelectedTeacher] = useState(null);
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [subject, setSubject] = useState("");
  const [grade, setGrade] = useState("Grade 9");
  const [linking, setLinking] = useState(false);
  const [linkMsg, setLinkMsg] = useState("");
  const [linkErr, setLinkErr] = useState("");
  const [associations, setAssociations] = useState([]);
  const [assocLoading, setAssocLoading] = useState(false);
  const [assocQuery, setAssocQuery] = useState("");

  const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

  async function authGet(path) {
    const r = await fetch(`${API_BASE}${path}`, { headers: { Authorization: `Bearer ${accessToken}` } });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || "Request failed");
    return data;
  }

  async function authPost(path, body) {
    const r = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || "Request failed");
    return data;
  }

  async function authDelete(path) {
    const r = await fetch(`${API_BASE}${path}`, { method: "DELETE", headers: { Authorization: `Bearer ${accessToken}` } });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || "Request failed");
    return data;
  }

  async function searchTeachers(q) {
    if (!q.trim()) { setTeacherResults([]); return; }
    try {
      const data = await authGet(`/api/admin-control/search-users?q=${encodeURIComponent(q)}&role=teacher`);
      setTeacherResults(data.users || []);
    } catch { setTeacherResults([]); }
  }

  async function searchStudents(q) {
    if (!q.trim()) { setStudentResults([]); return; }
    try {
      const data = await authGet(`/api/admin-control/search-users?q=${encodeURIComponent(q)}&role=student`);
      setStudentResults(data.users || []);
    } catch { setStudentResults([]); }
  }

  async function loadAssociations() {
    setAssocLoading(true);
    try {
      const data = await authGet(`/api/admin-control/teacher-student-associations?q=${encodeURIComponent(assocQuery)}`);
      setAssociations(data.associations || []);
    } catch { setAssociations([]); }
    finally { setAssocLoading(false); }
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { const t = setTimeout(() => searchTeachers(teacherQuery), 300); return () => clearTimeout(t); }, [teacherQuery]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { const t = setTimeout(() => searchStudents(studentQuery), 300); return () => clearTimeout(t); }, [studentQuery]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { loadAssociations(); }, [assocQuery]);

  async function handleLink() {
    if (!selectedTeacher || !selectedStudent) { setLinkErr("Select both a teacher and a student."); return; }
    setLinking(true); setLinkErr(""); setLinkMsg("");
    try {
      await authPost("/api/admin-control/teacher-assignments", {
        teacher_id: selectedTeacher.id,
        student_id: selectedStudent.id,
        grade: grade || selectedStudent.grade || "Grade 9",
        subject: subject || "General",
        section: "",
      });
      setLinkMsg(`✅ ${selectedStudent.username} assigned to teacher ${selectedTeacher.username}.`);
      setSelectedTeacher(null); setSelectedStudent(null);
      setTeacherQuery(""); setStudentQuery("");
      setTeacherResults([]); setStudentResults([]);
      setSubject(""); setGrade("Grade 9");
      loadAssociations();
    } catch (err) { setLinkErr(err.message || "Assignment failed."); }
    finally { setLinking(false); }
  }

  async function handleUnlink(assignmentId, studentName, teacherName) {
    if (!window.confirm(`Remove ${studentName} from teacher ${teacherName}?`)) return;
    try {
      await authDelete(`/api/admin-control/teacher-assignments/${assignmentId}`);
      setLinkMsg("✅ Assignment removed.");
      loadAssociations();
    } catch (err) { setLinkErr(err.message || "Failed to remove."); }
  }

  const inputStyle = {
    width: "100%", background: "var(--surface2, #f8f9fa)", border: "1px solid var(--border, #e2e8f0)",
    borderRadius: 8, padding: "9px 12px", fontSize: ".88rem", fontFamily: "inherit", color: "inherit", outline: "none",
  };
  const resultItemStyle = (selected) => ({
    padding: "8px 12px", borderRadius: 8, cursor: "pointer", fontSize: ".85rem",
    background: selected ? "rgba(16,185,129,.15)" : "transparent",
    border: `1px solid ${selected ? "#10b981" : "transparent"}`,
    marginBottom: 3,
  });

  return (
    <div className="premium-section" style={{ marginTop: 24 }}>
      <div className="premium-header">
        <h3>🎓 Teacher-Student Association</h3>
        <p>Assign an existing student to a teacher. Only admins can create or remove these assignments.</p>
      </div>

      {linkMsg && <div className="info-box" style={{ marginBottom: 12 }}>{linkMsg}</div>}
      {linkErr && <div className="error-box" style={{ marginBottom: 12 }}>{linkErr}</div>}

      {/* Search panel */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 16 }}>
        <div className="premium-card">
          <h4 style={{ margin: "0 0 10px" }}>Search Teacher</h4>
          <input style={inputStyle} placeholder="Search by name or email…" value={teacherQuery} onChange={(e) => setTeacherQuery(e.target.value)} />
          {teacherResults.length > 0 && (
            <div style={{ marginTop: 8, maxHeight: 200, overflowY: "auto" }}>
              {teacherResults.map((u) => (
                <div key={u.id} style={resultItemStyle(selectedTeacher?.id === u.id)} onClick={() => setSelectedTeacher(u)}>
                  <strong>{u.username}</strong>
                  <small style={{ display: "block", color: "var(--muted, #64748b)" }}>{u.email}</small>
                </div>
              ))}
            </div>
          )}
          {selectedTeacher && (
            <div style={{ marginTop: 8, padding: "8px 12px", background: "rgba(16,185,129,.1)", borderRadius: 8, fontSize: ".85rem" }}>
              ✅ Selected: <strong>{selectedTeacher.username}</strong>
              <button onClick={() => setSelectedTeacher(null)} style={{ marginLeft: 8, background: "none", border: "none", cursor: "pointer", color: "#94a3b8" }}>×</button>
            </div>
          )}
        </div>

        <div className="premium-card">
          <h4 style={{ margin: "0 0 10px" }}>Search Student</h4>
          <input style={inputStyle} placeholder="Search by name or email…" value={studentQuery} onChange={(e) => setStudentQuery(e.target.value)} />
          {studentResults.length > 0 && (
            <div style={{ marginTop: 8, maxHeight: 200, overflowY: "auto" }}>
              {studentResults.map((u) => (
                <div key={u.id} style={resultItemStyle(selectedStudent?.id === u.id)} onClick={() => setSelectedStudent(u)}>
                  <strong>{u.username}</strong>
                  <small style={{ display: "block", color: "var(--muted, #64748b)" }}>{u.email} · {u.grade || "—"}</small>
                </div>
              ))}
            </div>
          )}
          {selectedStudent && (
            <div style={{ marginTop: 8, padding: "8px 12px", background: "rgba(16,185,129,.1)", borderRadius: 8, fontSize: ".85rem" }}>
              ✅ Selected: <strong>{selectedStudent.username}</strong> ({selectedStudent.grade || "—"})
              <button onClick={() => setSelectedStudent(null)} style={{ marginLeft: 8, background: "none", border: "none", cursor: "pointer", color: "#94a3b8" }}>×</button>
            </div>
          )}
        </div>
      </div>

      {/* Subject + Grade for assignment */}
      <div style={{ display: "flex", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
        <label style={{ display: "flex", flexDirection: "column", gap: 4, flex: 1, minWidth: 160 }}>
          <span style={{ fontSize: ".85rem", fontWeight: 600 }}>Subject</span>
          <input style={{ ...inputStyle }} placeholder="e.g. Science" value={subject} onChange={(e) => setSubject(e.target.value)} />
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4, flex: 1, minWidth: 160 }}>
          <span style={{ fontSize: ".85rem", fontWeight: 600 }}>Grade</span>
          <select style={{ ...inputStyle }} value={grade} onChange={(e) => setGrade(e.target.value)}>
            {Array.from({ length: 12 }, (_, i) => `Grade ${i + 1}`).map(g => <option key={g} value={g}>{g}</option>)}
          </select>
        </label>
      </div>

      <button
        className="primary-btn"
        style={{ maxWidth: 320, background: "linear-gradient(135deg,#10b981,#059669)" }}
        disabled={linking || !selectedTeacher || !selectedStudent}
        onClick={handleLink}
      >
        {linking ? "Assigning…" : "🎓 Assign Student to Teacher"}
      </button>

      {/* Existing assignments */}
      <div style={{ marginTop: 28 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12, flexWrap: "wrap", gap: 10 }}>
          <h4 style={{ margin: 0 }}>Existing Assignments ({associations.length})</h4>
          <input style={{ ...inputStyle, maxWidth: 260 }} placeholder="Filter by teacher or student…" value={assocQuery} onChange={(e) => setAssocQuery(e.target.value)} />
        </div>
        {assocLoading ? <p>Loading…</p> : associations.length === 0 ? (
          <div className="info-box">No teacher-student assignments found.</div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {associations.map((a, i) => (
              <div key={`${a.id}-${i}`} style={{
                display: "flex", alignItems: "center", justifyContent: "space-between",
                padding: "10px 14px", background: "var(--surface2, #f8f9fa)",
                borderRadius: 9, border: "1px solid var(--border, #e2e8f0)", flexWrap: "wrap", gap: 8,
              }}>
                <div style={{ fontSize: ".85rem" }}>
                  <strong>{a.teacher.username || "(unknown teacher)"}</strong>
                  <span style={{ margin: "0 8px", color: "var(--muted, #64748b)" }}>→</span>
                  <strong>{a.student.username || "(unknown student)"}</strong>
                  <span style={{ color: "var(--muted, #64748b)", marginLeft: 6 }}>({a.student.grade || a.grade || "—"})</span>
                  {a.subject && <span style={{ marginLeft: 6, fontSize: ".78rem", color: "var(--muted, #64748b)" }}>· {a.subject}</span>}
                </div>
                <button
                  onClick={() => handleUnlink(a.id, a.student.username, a.teacher.username)}
                  style={{
                    background: "rgba(239,68,68,.1)", border: "1px solid rgba(239,68,68,.25)",
                    color: "#f87171", borderRadius: 7, padding: "4px 12px",
                    cursor: "pointer", fontSize: ".78rem", fontWeight: 600, fontFamily: "inherit",
                  }}
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default AdminControlPage;
