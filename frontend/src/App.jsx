import { useEffect, useRef, useState } from "react";
import LoginPage from "./pages/LoginPage";
import Sidebar from "./components/Sidebar";
import { ToastProvider } from "./context/ToastContext";
import { supabase } from "./api/supabaseClient";
import logo from "./assets/AITutorLogo1.png"; // eslint-disable-line no-unused-vars
import {
  STAGES, STATUS,
  clearOAuthSession,
  getOrCreateCorrelationId,
  getErrorMessage,
  getStages,
  inspectCallbackUrl,
  mapProviderError,
  recordStage,
  resetStages,
} from "./api/oauthDiagnostics";

import LessonsPage from "./pages/LessonsPage";
import DoubtPage from "./pages/DoubtPage";
import MockTestPage from "./pages/MockTestPage";
import ResourcesPage from "./pages/ResourcesPage";
import AnalyticsPage from "./pages/AnalyticsPage";
import LeaderboardPage from "./pages/LeaderboardPage";
import RagUploadPage from "./pages/RagUploadPage";
import AdminSyllabusReviewPage from "./pages/AdminSyllabusReviewPage";
import StudentDashboardPage from "./pages/StudentDashboardPage";
import FormulaSheetPage from "./pages/FormulaSheetPage";
import AdminQACenterPage from "./pages/AdminQACenterPage";
import AdminIssuesPage from "./pages/AdminIssuesPage";
import ReportIssueModal from "./components/ReportIssueModal";
import FeatureAuthAuditPage from "./pages/FeatureAuthAuditPage";
import { motion, AnimatePresence } from "framer-motion";
import { BookOpen, Users, GraduationCap, AlertTriangle, Atom, Microscope, FlaskConical, Briefcase, Landmark } from "lucide-react";
import { PAGE_ICONS } from "./utils/pageIcons";
import UsagePage from "./pages/UsagePage";
import ParentDashboardPage from "./pages/ParentDashboardPage";
import AdminControlPage from "./pages/AdminControlPage";
import SubscriptionPlansPage from "./pages/SubscriptionPlansPage";
import AdminSubscriptionSettingsPage from "./pages/AdminSubscriptionSettingsPage";
import AdminPricingCalculatorPage from "./pages/AdminPricingCalculatorPage";
import TeacherDashboardPage from "./pages/TeacherDashboardPage";
import TeacherTestPaperPage from "./pages/TeacherTestPaperPage";
import TeacherStudentAnalyticsPage from "./pages/TeacherStudentAnalyticsPage";
import ExemplarResearchPage from "./pages/ExemplarResearchPage";
import TeacherLessonPlanPage from "./pages/TeacherLessonPlanPage";
import ResetPasswordPage from "./pages/ResetPasswordPage";
import ChangePasswordPage from "./pages/ChangePasswordPage";
import SalesIncentivePage from "./pages/SalesIncentivePage";
import WalkthroughPage from "./pages/WalkthroughPage";
import SalesLeadPage from "./pages/SalesLeadPage";
import SalesDemoPage from "./pages/SalesDemoPage";
import SalesCollateralPage from "./pages/SalesCollateralPage";
import AdminPerformanceTestsPage from "./pages/AdminPerformanceTestsPage";
import AdminLearningSimulationPage from "./pages/AdminLearningSimulationPage";
import AdminGuideSettingsPage from "./pages/AdminGuideSettingsPage";
import AdminLessonCardPage from "./pages/AdminLessonCardPage";
import AdminCacheManagementPage from "./pages/AdminCacheManagementPage";
import AdminProductCataloguePage from "./pages/AdminProductCataloguePage";
import AdminPaymentsPage from "./pages/AdminPaymentsPage";
import AdminOperationsPage from "./pages/AdminOperationsPage";
import LandingPage from "./pages/LandingPage";
import ChatWidget from "./components/ChatWidget";
import FirstTimeGuide from "./components/FirstTimeGuide";
import AdminUnansweredQuestionsPage from "./pages/AdminUnansweredQuestionsPage";
import AdminLessonRepairPage from "./pages/AdminLessonRepairPage";
import AdminLessonExperiencePage from "./pages/AdminLessonExperiencePage";
import AdminAIStudioPage from "./pages/AdminAIStudioPage";
import ExamPrepPage from "./pages/ExamPrepPage";
import RefundPolicyPage from "./pages/RefundPolicyPage";
import PrivacyPolicyPage from "./pages/PrivacyPolicyPage";
import TermsOfServicePage from "./pages/TermsOfServicePage";
import SignupPage from "./pages/SignupPage";
import BlogPage from "./pages/BlogPage";
import BlogPostPage from "./pages/BlogPostPage";

import "./App.css";
import { resolveSubscription, ACCESS_SOURCE } from "./utils/resolveSubscription";

const PAGE_META = {
  dashboard: {
    title: "Dashboard",
    subtitle:
      "Your central AI learning hub for lessons, practice, progress, and recommendations.",
    icon: "🏠",
  },
  adminControl: {
    title: "Admin Control",
    subtitle: "Manage families, users, access, limits, and subscription readiness.",
    icon: "🛠️",
  },
  lessons: {
    title: "Lessons",
    subtitle:
      "Generate step-wise AI lessons with narration, progress, and RAG sources.",
    icon: "📖",
  },
  doubt: {
    title: "Ask Doubt",
    subtitle: "Ask chapter-specific doubts and get guided explanations.",
    icon: "❓",
  },
  mockTest: {
    title: "Mock Test",
    subtitle: "Take timed tests with scoring, review, and difficulty guidance.",
    icon: "🧪",
  },
  resources: {
    title: "Learn More",
    subtitle: "Explore free videos and learning resources for each chapter.",
    icon: "🎥",
  },
  featureAuthAudit: {
    title: "Feature Authorization Audit",
    subtitle: "Verify feature access across all plans, roles and scenarios. Catches Free Tier premium leakage.",
    icon: "🔐",
  },
  adminIssues: {
    title: "Product Bugs",
    icon: "🐛",
    roles: ["admin"],
  },
  adminQACenter: {
    title: "Platform QA Center",
    subtitle: "Automated quality audits for lesson content, formulas, and student flows.",
    icon: "🧪",
  },
  formulaSheet: {
    title: "Formula Sheet",
    subtitle: "Chapter-wise CBSE formula reference for your grade. Preview free, unlock all with Premium.",
    icon: "📐",
  },
  analytics: {
    title: "Analytics",
    subtitle: "Track progress, scores, history, and subject performance.",
    icon: "📊",
  },
  leaderboard: {
    title: "Leaderboard",
    subtitle: "Compare performance across users and test attempts.",
    icon: "🏆",
  },
  ragUpload: {
    title: "RAG Upload",
    subtitle:
      "Admin area for uploading textbook content into the AI knowledge base.",
    icon: "📤",
  },
  syllabusReview: {
    title: "Syllabus Review",
    subtitle:
      "Preview and approve student-facing class, subject, and chapter dropdowns.",
    icon: "✅",
  },
  subscriptionSettings: {
    title: "Subscription Settings",
    subtitle: "Manage subscription prices, discounts, and parent-facing plan details.",
    icon: "🏷️",
  },
  pricingCalculator: {
    title: "Pricing Calculator",
    subtitle:
      "Estimate per-student plan cost from tokens, hosting, database, and domain fees.",
    icon: "🧮",
  },
  performanceTests: {
    title: "Performance Tests",
    subtitle:
      "Run controlled backend checks and monitor latency, errors, and trend health.",
    icon: "⚡",
  },
  learningSimulation: {
    title: "Learning Simulation",
    subtitle:
      "Simulate Vijay (student) + Manish/Manisha (parents) over 7-day cycles. Detects anomalies and creates Product Bugs.",
    icon: "🔬",
  },
  guideThemes: {
    title: "Likha Poha AI Guide",
    subtitle:
      "Configure first-time walkthroughs, role themes, and periodic visual rotation.",
    icon: "✨",
  },
  productCatalogue: {
    label: "Product Catalogue",
    icon: "📦",
    roles: ["admin"],
  },
  cacheManagement: {
    title: "Cache & Question Bank",
    subtitle:
      "Pre-generate lessons and question banks grade by grade. Track progress and clear cache when needed.",
    icon: "🗄️",
  },
  salesLeads: {
    title: "Lead Claims",
    subtitle: "Submit student leads and track commissions. Payments auto-confirm on Razorpay checkout.",
    icon: "🤝",
  },
  salesIncentives: {
    title: "Sales Incentives",
    subtitle: "Track salespeople, student onboarding, packages, and commissions.",
    icon: "🤝",
  },
  salesDemo: {
    title: "Product Demo",
    subtitle:
      "Show safe prospect-facing demos for student, parent, and teacher flows.",
    icon: "🖥️",
  },
  salesCollaterals: {
    title: "Sales Collaterals",
    subtitle:
      "Download approved WhatsApp messages, Instagram reels, brochures, and demo scripts.",
    icon: "📣",
  },
  usage: {
    title: "AI Usage",
    subtitle: "Track token, image, and estimated AI costs by user and feature.",
    icon: "💰",
  },
  parentDashboard: {
    title: "Parent Dashboard",
    subtitle: "Track student progress, test performance, and AI usage.",
    icon: "👨‍👩‍👧",
  },
  teacherDashboard: {
    title: "Teacher Dashboard",
    subtitle: "Track assigned students, progress, AI usage, and teacher notes.",
    icon: "🎓",
  },
  platformWalkthrough: {
    title: "Platform Walkthrough",
    subtitle: "Watch the student platform walkthrough in English and Hindi.",
    icon: "🎬",
  },
  subscriptionPlans: {
    title: "Subscription",
    subtitle: "Compare plans, review inclusions, and choose payment options.",
    icon: "💳",
  },
  changePassword: {
    title: "Change Password",
    subtitle: "Update your account password securely.",
    icon: "🔐",
  },
  paymentLogs: {
    title: "Payment Logs",
    subtitle: "Revenue analytics, transaction history, and Excel export.",
    icon: "💳",
  },
  unansweredReview: {
    title: "AI Learning Review",
    subtitle: "Review unanswered questions and approve answers to grow platform intelligence.",
    icon: "🧠",
  },
  lessonRepair: {
    title: "Lesson Repair",
    subtitle: "Repair lessons that failed the 8-section quality audit. Admin-triggered LLM repair with draft-first safety.",
    icon: "🔧",
  },
  aiStudio: {
    title: "AI Studio",
    subtitle: "Configure AI providers, model routing, prompt templates, and monitor usage and quality.",
    icon: "🎛️",
  },
  teacherTestPaper: {
    title: "Create Test Paper",
    subtitle: "Generate AI-powered MCQ and subjective test papers for any grade. Download question paper + answer key.",
    icon: "📝",
  },
  teacherStudentAnalytics: {
    title: "Student Analytics",
    subtitle: "Track every assigned student's mock test scores, subject performance and progress trends.",
    icon: "📊",
  },
  exemplarResearch: {
    title: "Exemplar Research",
    subtitle: "Explore hard and tricky CBSE Science & Maths topics from NCERT Exemplar books. Instant AI explanations + practice links.",
    icon: "🔬",
  },
  teacherLessonPlan: {
    title: "Lesson Plans",
    subtitle: "Generate detailed CBSE-aligned lesson plans for any grade, subject and chapter. Download as PDF.",
    icon: "📋",
  },
  examPrep: {
    title: "Exam Prep Center",
    subtitle: "JEE Main · NEET UG · CUET UG — Practice questions, simulated tests, and AI explanations for Grade 11 & 12.",
    icon: "🎯",
  },
};

function App() {
  /** Owns global session, navigation, and theme state for the single-page app shell. */
  const [user, setUser] = useState(() => {
    // If ?u= is in URL, the link is a "sign in as child" link.
    // Force the session clear so the login page renders with the pre-filled username.
    const params = new URLSearchParams(window.location.search);
    if (params.get("u") || params.get("p")) {
      localStorage.removeItem("tutor_user");
      localStorage.removeItem("tutor_active_page");
      return null;
    }
    // ── KEY FIX: initialize user from localStorage immediately ────────────
    // Without this, user=null is captured in the onAuthStateChange closure,
    // causing a returning Google-auth user to see the "Signing you in with
    // Google…" spinner on every new page load (even though they never logged out).
    const saved = localStorage.getItem("tutor_user");
    return saved ? JSON.parse(saved) : null;
  });
  const [showLanding, setShowLanding] = useState(
    () => {
      // Skip landing page if ?u= (pre-filled login link) or ?code= (offer signup) is in URL
      const params = new URLSearchParams(window.location.search);
      if (params.get("u") || params.get("p") || params.get("code")) return false;
      return !localStorage.getItem("tutor_user");
    }
  );
  const [showSignup, setShowSignup] = useState(false);
  const [signupInitialPlan, setSignupInitialPlan] = useState("free");
  const [activePage, setActivePage] = useState("dashboard");
  const [reportBugOpen, setReportBugOpen] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  // Detect Supabase recovery/invite hash fragments on first load
  const _initialHash = window.location.hash;
  const _isRecovery = Boolean(_initialHash && (
    _initialHash.includes("type=recovery") || _initialHash.includes("type=invite")
  ));
  const isRecoveryFlow = useRef(_isRecovery);
  const [routePath, setRoutePath] = useState(_isRecovery ? "/reset-password" : window.location.pathname);
  const [darkMode, setDarkMode] = useState(
    localStorage.getItem("tutor_dark_mode") === "true"
  );
  const [oauthLoading, setOauthLoading] = useState(false);
  const [oauthError, setOauthError] = useState(null);    // visible error with retry
  // Welcome transition — shown for 2.5s after every fresh login/signup
  const [showWelcome, setShowWelcome] = useState(false);
  const [welcomeUser, setWelcomeUser] = useState(null);
  // Safety-net: if the OAuth spinner is somehow stuck, auto-clear after 15 s
  useEffect(() => {
    if (!oauthLoading) return;
    const t = setTimeout(() => {
      setOauthLoading(false);
      setOauthError("Google sign-in timed out. Please try again.");
    }, 15000);
    return () => clearTimeout(t);
  }, [oauthLoading]);
  // pendingOauthUser: set when /auth/me returns needs_role_selection=true
  const [pendingOauthUser, setPendingOauthUser] = useState(null);
  const [oauthRole, setOauthRole] = useState("student");
  const [oauthGrade, setOauthGrade] = useState("Grade 9");
  const [oauthStream, setOauthStream] = useState("");
  const [oauthStep, setOauthStep] = useState("role");      // "role" → "grade" → done
  const [oauthSaving, setOauthSaving] = useState(false);
  const [oauthSaveError, setOauthSaveError] = useState(null);
  const [_oauthDiagnostics, setOauthDiagnostics] = useState([]);  // safe stages for display — eslint-disable-line no-unused-vars
  const OAUTH_GRADES = ["Grade 5","Grade 6","Grade 7","Grade 8","Grade 9","Grade 10","Grade 11","Grade 12"];
  const OAUTH_NEEDS_STREAM = ["Grade 11","Grade 12"];
  const OAUTH_STREAM_OPTIONS = [
    { key: "PCM",        label: "Science — PCM",    desc: "Physics, Chemistry, Mathematics",     Icon: Atom },
    { key: "PCB",        label: "Science — PCB",    desc: "Physics, Chemistry, Biology",         Icon: Microscope },
    { key: "PCMB",       label: "Science — PCMB",   desc: "Physics, Chemistry, Maths & Biology", Icon: FlaskConical },
    { key: "Commerce",   label: "Commerce",         desc: "Accountancy, Business, Economics",    Icon: Briefcase },
    { key: "Humanities", label: "Humanities",       desc: "History, Pol. Science, Geography",    Icon: Landmark },
  ];
  // Prevent double-firing — module-level (not React ref) so it survives re-renders
  // and is keyed to the URL so each unique callback is processed exactly once.
  const oauthProcessed = useRef(false);
  const _oauthCallbackUrl = useRef(null);

  /**
   * Build normalized user object from /auth/me response and call handleLogin.
   * Defined BEFORE the OAuth useEffect so it is in scope when the callback runs.
   * Called for State A (existing profile) and State B/C (after complete-profile).
   */
  async function _finishOAuthLogin(meData, session) {
    const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
    const accessToken = session.access_token;

    let offerData = { offerAccess: false };
    try {
      const r = await fetch(`${API_BASE}/api/offer/my-access`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (r.ok) {
        const d = await r.json();
        offerData = {
          offerAccess: !!d.has_offer_access,
          offerValidUntil: d.valid_until || null,
          offerDaysRemaining: d.days_remaining ?? null,
          offerExpiringSoon: !!d.expiring_soon,
          offerExpiredOn: d.expired_on || null,
        };
      }
    } catch { /* non-critical */ }

    const normalizedUser = {
      id: meData.id,
      email: meData.email,
      username: meData.username || meData.email,
      role: meData.role,
      grade: meData.grade || "Grade 9",
      board: meData.board || "CBSE",
      parentId: meData.parent_id,
      familyId: meData.family_id,
      accessToken,
      accessCbse: !!meData.access_cbse,
      accessSofScience: !!meData.access_sof_science,
      accessSofMaths: !!meData.access_sof_maths,
      accessSofEnglish: !!meData.access_sof_english,
      cbseSubjects: Array.isArray(meData.cbse_subjects) ? meData.cbse_subjects : [],
      stream: meData.stream || null,
      avatar: meData.avatar || session.user?.user_metadata?.avatar_url || "",
      dailyTokenLimit: meData.daily_token_limit,
      monthlyTokenLimit: meData.monthly_token_limit,
      subscriptionPlan: meData.subscription_plan || "free",
      accountStatus: meData.account_status || "active",
      canReportIssues: !!meData.can_report_issues,
      ...offerData,
    };

    handleLogin(normalizedUser);
  }

  // ── Google OAuth Reliability Layer ─────────────────────────────────────────
  //
  // Root cause of cross-device failure:
  //   • Supabase PKCE auto-exchanges `code=` and clears URL BEFORE our handler
  //     runs, so URL-param detection fails on second devices / mobile.
  //   • Identity age heuristic (< 5 min) only passes on first-ever login.
  //   • When tutor_user absent and no URL params, flow returned early silently.
  //
  // Fix: if SIGNED_IN fires for a Google user AND no app profile exists
  // in localStorage, always treat it as a fresh login — call /auth/me to
  // determine role and route accordingly. No reliance on URL params or identity age.
  //
  // Cross-device scenario that now works:
  //   Device A: login → profile in localStorage, tutor_user set
  //   Device B: login same Google account → no tutor_user → fresh login processed
  //
  // Additional improvements:
  //   • Explicit PKCE session exchange before onAuthStateChange fallback
  //   • Bounded retry with backoff for session establishment
  //   • Correlation ID in /auth/me request header for backend tracing
  //   • Stage recording for visible diagnostics on error
  //   • Double-invocation guard keyed to callback URL (not just a boolean)
  // ──────────────────────────────────────────────────────────────────────────
  useEffect(() => {
    const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

    // ── Phase 1: Explicit PKCE callback handling (mobile-safe) ──────────────
    // Supabase PKCE redirects deliver a `code=` query param.  The SDK usually
    // auto-exchanges it, but on some mobile browsers the auto-exchange races
    // with our listener.  We explicitly call exchangeCodeForSession so the
    // session exists before onAuthStateChange fires.
    const _handleExplicitCallback = async () => {
      const cbInfo = inspectCallbackUrl();

      // Provider error (e.g. user clicked "Cancel" on Google consent)
      if (cbInfo.hasError) {
        const errCode = mapProviderError(cbInfo.errorParam, cbInfo.errorDescription || "");
        recordStage(STAGES.CALLBACK_PARAMS_DETECTED, STATUS.FAILED,
          cbInfo.errorDescription || cbInfo.errorParam || "OAuth provider error",
          errCode,
        );
        setOauthDiagnostics(getStages());
        setOauthError(getErrorMessage(errCode));
        setOauthLoading(false);
        // Clean error params from URL
        try { window.history.replaceState({}, "", window.location.pathname); } catch { /* */ }
        return;
      }

      if (cbInfo.hasCode) {
        recordStage(STAGES.CALLBACK_PARAMS_DETECTED, STATUS.SUCCESS,
          "OAuth code detected in URL");

        // Attempt explicit PKCE exchange (Supabase v2 PKCE flow)
        // If SDK already exchanged it, this is a no-op / returns existing session.
        if (typeof supabase.auth.exchangeCodeForSession === "function") {
          try {
            recordStage(STAGES.SESSION_EXCHANGE_STARTED, STATUS.PENDING,
              "Exchanging OAuth code for session");
            await supabase.auth.exchangeCodeForSession(window.location.href);
            recordStage(STAGES.SESSION_EXCHANGE_COMPLETED, STATUS.SUCCESS,
              "Session exchange complete");
          } catch (exchErr) {
            // Non-fatal — SDK may have already exchanged; continue to getSession()
            recordStage(STAGES.SESSION_EXCHANGE_COMPLETED, STATUS.SKIPPED,
              `Exchange attempted: ${exchErr?.message || "already done"}`);
          }
          // Clean code from URL immediately after exchange
          try {
            window.history.replaceState(
              {},
              "",
              window.location.pathname + window.location.hash.replace(/[#?].*/, ""),
            );
          } catch { /* */ }
        }
      }
    };

    // ── Phase 2: Wait for Supabase session with bounded retries ─────────────
    const _waitForSession = async (maxWaitMs = 8000) => {
      const start = Date.now();
      const backoff = [100, 200, 400, 600, 800, 1000, 1200, 1500];

      for (let attempt = 0; attempt < backoff.length; attempt++) {
        try {
          const { data } = await supabase.auth.getSession();
          if (data?.session?.access_token) return data.session;
        } catch { /* retry */ }

        if (Date.now() - start >= maxWaitMs) break;
        await new Promise(r => setTimeout(r, backoff[attempt]));
      }

      // Final fallback: wait once for SIGNED_IN auth state event (1.5s budget)
      return new Promise((resolve) => {
        const timeout = setTimeout(() => resolve(null), 1500);
        const { data: { subscription: sub } } = supabase.auth.onAuthStateChange(
          (event, sess) => {
            if ((event === "SIGNED_IN" || event === "TOKEN_REFRESHED") && sess?.access_token) {
              clearTimeout(timeout);
              sub.unsubscribe();
              resolve(sess);
            }
          },
        );
      });
    };

    // ── Phase 3: Call /auth/me with correlation ID ───────────────────────────
    const _callAuthMe = async (accessToken, correlationId) => {
      recordStage(STAGES.AUTH_ME_STARTED, STATUS.PENDING, "Calling /api/auth/me");

      let meData = null;
      let meError = null;
      const backoff = [0, 800, 1200, 1600];

      for (let attempt = 0; attempt < backoff.length; attempt++) {
        if (backoff[attempt] > 0) await new Promise(r => setTimeout(r, backoff[attempt]));
        try {
          const r = await fetch(`${API_BASE}/api/auth/me`, {
            headers: {
              Authorization: `Bearer ${accessToken}`,
              "X-OAuth-Correlation-ID": correlationId,
            },
          });
          if (r.ok) {
            meData = await r.json();
            recordStage(STAGES.AUTH_ME_COMPLETED, STATUS.SUCCESS,
              `Profile loaded: ${meData.needs_role_selection ? "needs role" : "complete"}`);
            break;
          }
          if (r.status === 401) {
            // Token not yet valid on this attempt — retry with backoff
            meError = "auth_me_unauthorized";
            if (attempt < backoff.length - 1) continue;
          } else {
            meError = `auth_me_failed_${r.status}`;
            break;
          }
        } catch (netErr) {
          meError = "auth_me_network";
          if (attempt < backoff.length - 1) continue;
        }
      }

      if (!meData) {
        recordStage(STAGES.AUTH_ME_COMPLETED, STATUS.FAILED,
          "Could not load profile", meError || "auth_me_failed");
      }
      return { meData, meError };
    };

    // ── Main OAuth handler — processes one callback at a time ────────────────
    const _processFreshLogin = async (session) => {
      const correlationId = getOrCreateCorrelationId();
      recordStage(STAGES.SESSION_DETECTED, STATUS.SUCCESS,
        "Supabase session established");

      if (!session.access_token) {
        recordStage(STAGES.ACCESS_TOKEN_DETECTED, STATUS.FAILED,
          "Session exists but no access token", "oauth_access_token_missing");
        setOauthDiagnostics(getStages());
        setOauthError(getErrorMessage("oauth_access_token_missing"));
        setOauthLoading(false);
        return;
      }
      recordStage(STAGES.ACCESS_TOKEN_DETECTED, STATUS.SUCCESS,
        "Access token present");

      const { meData, meError } = await _callAuthMe(session.access_token, correlationId);

      if (!meData) {
        setOauthDiagnostics(getStages());
        setOauthError(getErrorMessage(meError || "auth_me_failed"));
        setOauthLoading(false);
        return;
      }

      recordStage(STAGES.PROFILE_COMPLETE_CHECKED, STATUS.SUCCESS,
        meData.needs_role_selection ? "Role selection required" : "Profile complete");

      if (meData.needs_role_selection) {
        // State B/C: new Google user — show role picker
        const partialUser = {
          id: meData.id || session.user?.id,
          email: meData.email || session.user?.email,
          username: meData.username || session.user?.user_metadata?.full_name || session.user?.email,
          avatar: meData.avatar || session.user?.user_metadata?.avatar_url || "",
          accessToken: session.access_token,
        };
        recordStage(STAGES.ROUTE_RESOLVED, STATUS.SUCCESS, "Showing role picker");
        setPendingOauthUser(partialUser);
        setOauthStep("role");
        setOauthLoading(false);
        clearOAuthSession();
        return;
      }

      // State A: profile complete — build user and route
      recordStage(STAGES.ROUTE_RESOLVED, STATUS.SUCCESS,
        `Routing to ${meData.role || "dashboard"}`);
      recordStage(STAGES.NAVIGATION_STARTED, STATUS.PENDING, "Completing login");
      await _finishOAuthLogin(meData, session);
      recordStage(STAGES.NAVIGATION_COMPLETED, STATUS.SUCCESS, "Login complete");
      clearOAuthSession();
      setOauthLoading(false);
    };

    // ── onAuthStateChange listener ───────────────────────────────────────────
    // Handles both: fresh OAuth callback AND page reload with existing session.
    //
    // CRITICAL FIX for cross-device failure:
    //   Old code relied on URL params (cleared by PKCE) OR identity age < 5 min.
    //   Both fail on second device. New logic: if SIGNED_IN fires for a Google
    //   user AND there is no tutor_user in localStorage, treat as fresh login.
    //   This correctly handles all cross-device scenarios.
    //
    // SECURITY: no action taken unless Supabase session is valid with access_token.
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        if (event !== "SIGNED_IN" || !session) return;

        const provider = session.user?.app_metadata?.provider;
        if (provider === "email") return; // email/password handled by LoginPage

        const hasAppProfile = !!localStorage.getItem("tutor_user");

        if (hasAppProfile) {
          // Page reload or tab open with existing session — just refresh token silently
          try {
            const saved = JSON.parse(localStorage.getItem("tutor_user"));
            const refreshed = { ...saved, accessToken: session.access_token };
            setUser(refreshed);
            localStorage.setItem("tutor_user", JSON.stringify(refreshed));
          } catch { /* non-critical */ }
          return;
        }

        // No app profile in localStorage → fresh login (works cross-device)
        // Guard: deduplicate by callback URL so mobile double-invocation is safe
        const currentUrl = window.location.href;
        if (oauthProcessed.current && _oauthCallbackUrl.current === currentUrl) return;
        if (oauthProcessed.current && _oauthCallbackUrl.current !== currentUrl) {
          // Different URL — new callback, reset guard
          oauthProcessed.current = false;
        }
        oauthProcessed.current = true;
        _oauthCallbackUrl.current = currentUrl;

        // Only clear app-specific keys — NEVER touch Supabase auth storage (sb-* keys)
        localStorage.removeItem("tutor_user");
        localStorage.removeItem("tutor_active_page");

        resetStages();
        recordStage(STAGES.CALLBACK_RECEIVED, STATUS.SUCCESS,
          `SIGNED_IN for provider=${provider}`);

        setOauthLoading(true);
        setOauthError(null);

        try {
          await _processFreshLogin(session);
        } catch (err) {
          console.error("[oauth] Unexpected error in callback handler:", err?.message);
          recordStage(STAGES.FAILED, STATUS.FAILED,
            "Unexpected error in OAuth flow", "unknown");
          setOauthDiagnostics(getStages());
          setOauthError("We couldn't complete Google sign-in. Please try again.");
          setOauthLoading(false);
        }
      }
    );

    // ── Explicit PKCE handling on page load (mobile-safe) ───────────────────
    // Run this ONCE on mount. If the URL has a `code=` param, we exchange it
    // explicitly so the session exists before onAuthStateChange fires.
    // This handles mobile browsers that may not fire the event reliably.
    (async () => {
      const cbInfo = inspectCallbackUrl();
      if (cbInfo.isOAuthCallback) {
        resetStages();
        getOrCreateCorrelationId(); // initialize correlation ID
        recordStage(STAGES.CALLBACK_RECEIVED, STATUS.SUCCESS,
          "OAuth callback URL detected on page load");
        await _handleExplicitCallback();
      }
    })();

    return () => subscription.unsubscribe();
  // _finishOAuthLogin is a stable inner function; intentionally not in deps.
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    function handlePopState() {
      /** Keep the app shell in sync when browser navigation changes the URL.
       * While isRecoveryFlow is true, block any popstate from navigating away
       * — Supabase SDK pushes history entries while processing the token.
       */
      if (isRecoveryFlow.current) return;
      setRoutePath(window.location.pathname);
    }

    window.addEventListener("popstate", handlePopState);

    // user is already initialized from localStorage in useState() above.
    // Verify session and refresh profile to prevent stale data on app restart.
    const savedUser = localStorage.getItem("tutor_user");
    const savedPage = localStorage.getItem("tutor_active_page");

    // Session recovery: silently refresh access token + profile on app load
    // Skip if this is a fresh OAuth redirect — OAuth handler will take over
    const _urlParams = new URLSearchParams(window.location.search);
    const _urlHash = window.location.hash || "";
    const _isOAuthReturn = _urlHash.includes("access_token") || _urlHash.includes("code=") ||
                           _urlParams.has("code") || _urlParams.has("access_token");
    if (savedUser && !_isOAuthReturn) {
      const API_BASE_RESTORE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
      (async () => {
        try {
          const { data: { session }, error } = await supabase.auth.getSession();
          if (error || !session) {
            // Session genuinely expired — clear stale local state
            console.info("[auth] Session expired on app load, clearing cache.");
            localStorage.removeItem("tutor_user");
            localStorage.removeItem("tutor_active_page");
            setUser(null);
            return;
          }
          // Session is valid — refresh access token and fetch fresh profile
          const { data: refreshed } = await supabase.auth.refreshSession();
          const freshToken = refreshed?.session?.access_token || session.access_token;
          const r = await fetch(`${API_BASE_RESTORE}/api/auth/profile`, {
            headers: { Authorization: `Bearer ${freshToken}` },
          });
          if (r.ok) {
            const p = await r.json();
            const parsed = JSON.parse(savedUser);
            const freshUser = {
              ...parsed,
              accessToken: freshToken,
              accessCbse: !!p.access_cbse,
              accessSofScience: !!p.access_sof_science,
              accessSofMaths: !!p.access_sof_maths,
              accessSofEnglish: !!p.access_sof_english,
              subscriptionPlan: p.subscription_plan || parsed.subscriptionPlan,
              subscriptionExpiresAt: p.subscription_expires_at || null,
              subscriptionDaysRemaining: p.subscription_days_remaining ?? null,
              subscriptionExpiringSoon: !!p.subscription_expiring_soon,
              cbseSubjects: Array.isArray(p.cbse_subjects) ? p.cbse_subjects : parsed.cbseSubjects,
              stream: p.stream || parsed.stream || null,
              accountStatus: p.account_status || parsed.accountStatus,
              grade: p.grade || parsed.grade,
              avatar: p.avatar || parsed.avatar,
              canReportIssues: !!p.can_report_issues,
            };
            setUser(freshUser);
            localStorage.setItem("tutor_user", JSON.stringify(freshUser));
          }
        } catch (e) {
          console.error("[auth] Session recovery failed:", e.message);
          // Non-critical: don't log out user on network failure, just keep stale data
        }
      })();
    }

    if (savedUser) {
      const parsedUser = JSON.parse(savedUser);

      // Restore saved page, but guard against role-incompatible pages:
      // - admin must not land on student "dashboard"
      // - parent must not land on student "dashboard"
      const isBadPageForRole =
        (parsedUser.role === "admin" && savedPage === "dashboard") ||
        (parsedUser.role === "parent" && savedPage === "dashboard");
      if (savedPage && !isBadPageForRole) {
        setActivePage(savedPage);
      } else if (parsedUser.role === "admin") {
        setActivePage("adminControl");
      } else if (parsedUser.role === "parent") {
        setActivePage("parentDashboard");
      } else if (parsedUser.role === "teacher") {
        setActivePage("teacherDashboard");
      } else if (parsedUser.role === "sales") {
        setActivePage("salesLeads");
      } else {
        setActivePage("dashboard");
      }
    }

    document.body.classList.toggle("dark-mode", darkMode);

    return () => window.removeEventListener("popstate", handlePopState);
  // darkMode is intentionally excluded — this effect runs once on mount only.
  // The next effect handles darkMode changes reactively.
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    document.body.classList.toggle("dark-mode", darkMode);
    localStorage.setItem("tutor_dark_mode", darkMode);
  }, [darkMode]);

  // ── oauthError screen — shown when Google OAuth fails ──────────────────
  // Must be placed AFTER all useEffect/hook calls to comply with React's
  // rules of hooks (no conditional hook calls).
  if (oauthError) {
    return (
      <div style={{
        minHeight: "100vh", display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center",
        background: "#0f172a", color: "#f8fafc", gap: 16,
        fontFamily: "-apple-system, sans-serif", padding: 24,
      }}>
        <AlertTriangle size={44} style={{ color: "#fca5a5", marginBottom: 4 }} strokeWidth={1.8} />
        <p style={{ fontSize: "1rem", color: "#fca5a5", textAlign: "center", maxWidth: 360 }}>
          {oauthError}
        </p>
        <button
          onClick={() => {
            setOauthError(null);
            oauthProcessed.current = false;
            window.location.replace("/");
          }}
          style={{
            padding: "11px 28px", borderRadius: 10, border: "none",
            background: "#6366f1", color: "#fff", fontFamily: "inherit",
            fontSize: "0.9rem", fontWeight: 700, cursor: "pointer",
          }}
        >
          Try Again
        </button>
        <button
          onClick={() => { setOauthError(null); setShowLanding(false); }}
          style={{
            padding: "8px 20px", borderRadius: 10,
            border: "1px solid #334155", background: "transparent",
            color: "#94a3b8", fontFamily: "inherit",
            fontSize: "0.82rem", fontWeight: 600, cursor: "pointer",
          }}
        >
          Back to Login
        </button>
      </div>
    );
  }

  async function handleLogin(userData) {
    /** Persist the authenticated user and send them to the right role-specific landing page. */
    const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

    // Always fetch fresh profile for ALL roles to prevent stale data after login.
    // This ensures subscription/access/role data is current immediately after login
    // without requiring a hard refresh.
    let enrichedUser = userData;
    if (userData.accessToken) {
      try {
        const r = await fetch(`${API_BASE}/api/auth/profile`, {
          headers: { Authorization: `Bearer ${userData.accessToken}` },
        });
        if (r.ok) {
          const p = await r.json();
          enrichedUser = {
            ...userData,
            accessCbse: !!p.access_cbse,
            accessSofScience: !!p.access_sof_science,
            accessSofMaths: !!p.access_sof_maths,
            accessSofEnglish: !!p.access_sof_english,
            subscriptionPlan: p.subscription_plan ?? userData.subscriptionPlan,
            subscriptionExpiresAt: p.subscription_expires_at || null,
            subscriptionDaysRemaining: p.subscription_days_remaining ?? null,
            subscriptionExpiringSoon: !!p.subscription_expiring_soon,
            cbseSubjects: Array.isArray(p.cbse_subjects) ? p.cbse_subjects : userData.cbseSubjects,
            stream: p.stream || userData.stream || null,
            dailyTokenLimit: p.daily_token_limit ?? userData.dailyTokenLimit,
            monthlyTokenLimit: p.monthly_token_limit ?? userData.monthlyTokenLimit,
            accountStatus: p.account_status || userData.accountStatus,
            grade: p.grade || userData.grade,
            avatar: p.avatar || userData.avatar,
            canReportIssues: !!p.can_report_issues,
          };
        }
      } catch (e) {
        // Non-critical: log but continue with login
        console.error("[handleLogin] Profile fetch failed:", e.message);
      }
    }

    setUser(enrichedUser);
    setRoutePath("/");
    localStorage.setItem("tutor_user", JSON.stringify(enrichedUser));
  
    if (enrichedUser.role === "admin") {
      setActivePage("adminControl");
      localStorage.setItem("tutor_active_page", "adminControl");
    } else if (enrichedUser.role === "parent") {
      setActivePage("parentDashboard");
      localStorage.setItem("tutor_active_page", "parentDashboard");
    } else if (enrichedUser.role === "teacher") {
      setActivePage("teacherDashboard");
      localStorage.setItem("tutor_active_page", "teacherDashboard");
    } else if (enrichedUser.role === "sales") {
      setActivePage("salesLeads");
      localStorage.setItem("tutor_active_page", "salesLeads");
    } else {
      // Students: will be gated to subscriptionPlans if unpaid
      setActivePage("dashboard");
      localStorage.setItem("tutor_active_page", "dashboard");
    }

    // Show welcome transition screen for 2.5s (skip for admin/sales roles)
    if (!["admin", "sales"].includes(enrichedUser.role)) {
      setWelcomeUser(enrichedUser);
      setShowWelcome(true);
      setTimeout(() => setShowWelcome(false), 2500);
    }
  }

  /** Refresh user profile from DB after a successful payment or promo-code redemption.
   *  Called by SubscriptionPlansPage via the onSubscriptionComplete prop.
   */
  async function handleSubscriptionComplete() {
    try {
      const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;

      const { data: profile } = await supabase
        .from("profiles")
        .select("*")
        .eq("id", user.id)
        .maybeSingle();
      if (!profile) return;

      let offerData = { offerAccess: false };
      try {
        const r = await fetch(`${API_BASE}/api/offer/my-access`, {
          headers: { Authorization: `Bearer ${session.access_token}` },
        });
        if (r.ok) {
          const d = await r.json();
          offerData = {
            offerAccess: !!d.has_offer_access,
            offerValidUntil: d.valid_until || null,
            offerDaysRemaining: d.days_remaining ?? null,
            offerExpiringSoon: !!d.expiring_soon,
            offerExpiredOn: d.expired_on || null,
          };
        }
      } catch { /* non-critical */ }

      const updatedUser = {
        ...user,
        accessToken: session.access_token,
        subscriptionPlan: profile.subscription_plan || "free",
        accessCbse: !!profile.access_cbse,
        accessSofScience: !!profile.access_sof_science,
        accessSofMaths: !!profile.access_sof_maths,
        accessSofEnglish: !!profile.access_sof_english,
        cbseSubjects: Array.isArray(profile.cbse_subjects) ? profile.cbse_subjects : [],
        stream: profile.stream || null,
        dailyTokenLimit: profile.daily_token_limit,
        monthlyTokenLimit: profile.monthly_token_limit,
        accountStatus: profile.account_status || "active",
        ...offerData,
      };
      setUser(updatedUser);
      localStorage.setItem("tutor_user", JSON.stringify(updatedUser));

      // Route to the correct role-specific landing page after subscription unlock
      const role = updatedUser.role;
      const targetPage =
        role === "admin" ? "adminControl" :
        role === "parent" ? "parentDashboard" :
        role === "teacher" ? "teacherDashboard" :
        role === "sales" ? "salesLeads" :
        "dashboard"; // students go to their dashboard
      setActivePage(targetPage);
      localStorage.setItem("tutor_active_page", targetPage);
    } catch (err) {
      console.error("handleSubscriptionComplete:", err);
    }
  }

  /** Refresh user profile from backend and update state. Call after:
   *  - child added/removed
   *  - subscription changed
   *  - role changed
   *  - any data mutation that affects user session
   */
  // eslint-disable-next-line no-unused-vars
  async function handleRefreshUser() {
    try {
      const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
      const { data: { session }, error } = await supabase.auth.getSession();
      if (error || !session) {
        console.error("[handleRefreshUser] No session:", error?.message);
        return;
      }
      const r = await fetch(`${API_BASE}/api/auth/profile`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (!r.ok) return;
      const p = await r.json();
      const updatedUser = {
        ...user,
        accessToken: session.access_token,
        accessCbse: !!p.access_cbse,
        accessSofScience: !!p.access_sof_science,
        accessSofMaths: !!p.access_sof_maths,
        accessSofEnglish: !!p.access_sof_english,
        subscriptionPlan: p.subscription_plan || user?.subscriptionPlan,
        subscriptionExpiresAt: p.subscription_expires_at || null,
        subscriptionDaysRemaining: p.subscription_days_remaining ?? null,
        subscriptionExpiringSoon: !!p.subscription_expiring_soon,
        cbseSubjects: Array.isArray(p.cbse_subjects) ? p.cbse_subjects : user?.cbseSubjects,
        stream: p.stream || user?.stream || null,
        dailyTokenLimit: p.daily_token_limit ?? user?.dailyTokenLimit,
        monthlyTokenLimit: p.monthly_token_limit ?? user?.monthlyTokenLimit,
        accountStatus: p.account_status || user?.accountStatus,
        grade: p.grade || user?.grade,
        avatar: p.avatar || user?.avatar,
      };
      setUser(updatedUser);
      localStorage.setItem("tutor_user", JSON.stringify(updatedUser));
    } catch (e) {
      console.error("[handleRefreshUser] failed:", e.message);
    }
  }

  function handleLogout() {
    /** Clear the local session and force the app back to the login page. */
    setUser(null);
    setRoutePath("/");
    localStorage.removeItem("tutor_user");
    localStorage.removeItem("tutor_active_page");
  }

  function handleBackToLogin() {
    /** Leave the recovery route and go directly to the login page — bypass the landing page. */
    isRecoveryFlow.current = false;
    window.history.replaceState({}, "", "/");
    setRoutePath("/");
    setUser(null);
    setShowLanding(false);  // skip landing page → go straight to login form
  }

  function handlePageChange(page) {
    /** Switch pages, close mobile navigation, and remember the last selected page. */
    setActivePage(page);
    setMobileNavOpen(false);
    localStorage.setItem("tutor_active_page", page);
  }

  if (routePath === "/reset-password") {
    return (
      <ResetPasswordPage
        onBackToLogin={handleBackToLogin}
      />
    );
  }

  if (routePath === "/signup" || showSignup) {
    const planFromUrl = new URLSearchParams(window.location.search).get("plan") || signupInitialPlan;
    return (
      <SignupPage
        initialPlan={planFromUrl}
        onLogin={handleLogin}
        onBackToLogin={() => {
          setShowSignup(false);
          setShowLanding(false);
          window.history.replaceState({}, "", "/");
          setRoutePath("/");
        }}
      />
    );
  }

  if (routePath === "/blog" || routePath.startsWith("/blog/")) {
    const slug = routePath.startsWith("/blog/") ? routePath.replace("/blog/", "") : null;
    if (slug) {
      return (
        <BlogPostPage
          slug={slug}
          onShowLogin={() => { window.history.replaceState({}, "", "/"); setRoutePath("/"); setShowLanding(false); }}
          onShowSignup={(plan) => { setSignupInitialPlan(plan || "free"); setShowSignup(true); window.history.replaceState({}, "", "/"); setRoutePath("/signup"); }}
          onBack={() => { window.history.replaceState({}, "", "/blog"); setRoutePath("/blog"); }}
        />
      );
    }
    return (
      <BlogPage
        onShowLogin={() => { window.history.replaceState({}, "", "/"); setRoutePath("/"); setShowLanding(false); }}
        onShowSignup={(plan) => { setSignupInitialPlan(plan || "free"); setShowSignup(true); window.history.replaceState({}, "", "/"); setRoutePath("/signup"); }}
        onViewPost={(postSlug) => { window.history.pushState({}, "", `/blog/${postSlug}`); setRoutePath(`/blog/${postSlug}`); }}
      />
    );
  }

  if (routePath === "/refund-policy") {
    return (
      <RefundPolicyPage
        onBackToHome={() => {
          window.history.replaceState({}, "", "/");
          setRoutePath("/");
        }}
      />
    );
  }

  if (routePath === "/privacy-policy") {
    return (
      <PrivacyPolicyPage
        onBackToHome={() => {
          window.history.replaceState({}, "", "/");
          setRoutePath("/");
        }}
      />
    );
  }

  if (routePath === "/terms-of-service") {
    return (
      <TermsOfServicePage
        onBackToHome={() => {
          window.history.replaceState({}, "", "/");
          setRoutePath("/");
        }}
      />
    );
  }

  // Profile setup overlay for new Google-authenticated users
  if (pendingOauthUser) {
    const cardStyle = {
      minHeight: "100vh",
      display: "flex", alignItems: "center", justifyContent: "center",
      background: "#0f172a", padding: "24px",
      fontFamily: "-apple-system, sans-serif",
    };
    const boxStyle = {
      width: "100%", maxWidth: 420,
      background: "#1e293b", borderRadius: 16,
      padding: "36px 32px", color: "#f8fafc",
      boxShadow: "0 20px 60px rgba(0,0,0,.5)",
    };
    const btnBase = {
      width: "100%", padding: "13px", borderRadius: 10,
      border: "none", fontSize: "0.95rem", fontWeight: 700,
      cursor: "pointer", fontFamily: "inherit",
    };
    const selectStyle = {
      width: "100%", background: "#111827",
      border: "2px solid #334155", borderRadius: 10,
      padding: "12px 14px", color: "#f8fafc",
      fontSize: "1rem", fontFamily: "inherit",
      marginBottom: 20, cursor: "pointer",
    };
    const avatar = pendingOauthUser.avatar;
    const firstName = pendingOauthUser.username.split(" ")[0];

    // Step 1: Role selection
    if (oauthStep === "role") {
      return (
        <div style={cardStyle}>
          <div style={boxStyle}>
            {avatar && (
              <div style={{ textAlign: "center", marginBottom: 16 }}>
                <img src={avatar} alt="Profile"
                  style={{ width: 60, height: 60, borderRadius: "50%", border: "3px solid #6366f1" }} />
              </div>
            )}
            <h2 style={{ margin: "0 0 6px", fontSize: "1.3rem", fontWeight: 800, textAlign: "center" }}>
              Welcome, {firstName}! 👋
            </h2>
            <p style={{ margin: "0 0 24px", fontSize: "0.88rem", color: "#94a3b8", textAlign: "center" }}>
              How are you using Likha Poha AI?
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 8 }}>
              {[
              { r: "student", Icon: GraduationCap, label: "Student", desc: "I want to learn and take practice tests" },
              { r: "parent",  Icon: Users,          label: "Parent",  desc: "I want to track my child's learning" },
              ].map(({ r, Icon: RoleIcon, label, desc }) => (
                <div key={r}
                  onClick={() => setOauthRole(r)}
                  style={{
                    display: "flex", alignItems: "center", gap: 14,
                    padding: "14px 16px", borderRadius: 10, cursor: "pointer",
                    background: oauthRole === r ? "rgba(99,102,241,.15)" : "#111827",
                    border: `2px solid ${oauthRole === r ? "#6366f1" : "#1e293b"}`,
                    transition: "all .15s",
                  }}
                >
                  <RoleIcon size={22} strokeWidth={1.8} style={{ flexShrink: 0, color: oauthRole === r ? "#a5b4fc" : "#64748b" }} />
                  <div>
                    <div style={{ fontWeight: 700, fontSize: "0.9rem" }}>{label}</div>
                    <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>{desc}</div>
                  </div>
                </div>
              ))}
            </div>
            <button
              style={{ ...btnBase, background: "linear-gradient(135deg,#6366f1,#8b5cf6)", color: "#fff", marginTop: 16 }}
              onClick={async () => {
                setOauthSaveError(null);
                if (oauthRole === "student") {
                  setOauthStep("grade");
                  return;
                }
                // Parents and teachers — call backend to set role securely
                setOauthSaving(true);
                try {
                  const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
                  // Refresh token before calling backend
                  let freshToken = pendingOauthUser.accessToken;
                  try {
                    const { data: refreshed } = await supabase.auth.refreshSession();
                    if (refreshed?.session?.access_token) freshToken = refreshed.session.access_token;
                  } catch { /* use original token */ }

                  const resp = await fetch(`${API_BASE}/api/auth/oauth/complete-profile`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json", Authorization: `Bearer ${freshToken}` },
                    body: JSON.stringify({ role: oauthRole, full_name: pendingOauthUser.username }),
                  });
                  const result = await resp.json();

                  if (!resp.ok) {
                    // 409 = role conflict — show friendly message, do not proceed
                    setOauthSaveError(result.detail || "Could not complete sign-in. Please try again.");
                    return;
                  }

                  // Get fresh session after profile update
                  const { data: freshSession } = await supabase.auth.getSession();
                  const finalToken = freshSession?.session?.access_token || freshToken;
                  await _finishOAuthLogin(result, { ...freshSession?.session, access_token: finalToken, user: freshSession?.session?.user });
                  setPendingOauthUser(null);
                } catch (err) {
                  setOauthSaveError("We couldn't save your role. Please try again.");
                  console.error("[oauth] complete-profile error:", err);
                } finally {
                  setOauthSaving(false);
                }
              }}
              disabled={oauthSaving}
            >
              {oauthSaving ? "Setting up…" : "Continue →"}
            </button>
            {oauthSaveError && (
              <div style={{ marginTop: 12, padding: "10px 14px", borderRadius: 8,
                background: "rgba(239,68,68,.12)", border: "1px solid rgba(239,68,68,.3)",
                fontSize: "0.82rem", color: "#fca5a5", textAlign: "center" }}>
                {oauthSaveError}
              </div>
            )}
          </div>
        </div>
      );
    }

    // Step 2: Grade selection (students only)
    return (
      <div style={cardStyle}>
        <div style={boxStyle}>
          {avatar && (
            <div style={{ textAlign: "center", marginBottom: 16 }}>
              <img src={avatar} alt="Profile"
                style={{ width: 60, height: 60, borderRadius: "50%", border: "3px solid #6366f1" }} />
            </div>
          )}
          <h2 style={{ margin: "0 0 6px", fontSize: "1.3rem", fontWeight: 800, textAlign: "center" }}>
            Which class are you in? 📚
          </h2>
          <p style={{ margin: "0 0 20px", fontSize: "0.88rem", color: "#94a3b8", textAlign: "center" }}>
            We'll personalise your lessons and practice tests.
          </p>
          <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "#cbd5e1", marginBottom: 8 }}>
            Select your class
          </label>
          <select
            value={oauthGrade}
            onChange={e => { setOauthGrade(e.target.value); setOauthStream(""); }}
            style={selectStyle}
          >
            {OAUTH_GRADES.map(g => <option key={g}>{g}</option>)}
          </select>

          {/* Stream picker — shown for Grade 11 and Grade 12 */}
          {OAUTH_NEEDS_STREAM.includes(oauthGrade) && (
            <div style={{ marginBottom: 20 }}>
              <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "#cbd5e1", marginBottom: 10 }}>
                Choose your academic stream for {oauthGrade}
              </label>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {OAUTH_STREAM_OPTIONS.map(s => (
                  <div
                    key={s.key}
                    onClick={() => setOauthStream(s.key)}
                    style={{
                      display: "flex", alignItems: "center", gap: 12,
                      padding: "11px 14px", borderRadius: 10, cursor: "pointer",
                      background: oauthStream === s.key ? "rgba(99,102,241,.15)" : "#111827",
                      border: `2px solid ${oauthStream === s.key ? "#6366f1" : "#1e293b"}`,
                      transition: "all .15s",
                    }}
                  >
                    <s.Icon size={18} strokeWidth={1.8} style={{ flexShrink: 0, color: oauthStream === s.key ? "#a5b4fc" : "#64748b" }} />
                    <div>
                      <div style={{ fontWeight: 700, fontSize: ".85rem", color: oauthStream === s.key ? "#a5b4fc" : "#f8fafc" }}>{s.label}</div>
                      <div style={{ fontSize: ".72rem", color: "#64748b", marginTop: 1 }}>{s.desc}</div>
                    </div>
                    {oauthStream === s.key && (
                      <span style={{ marginLeft: "auto", color: "#6366f1", fontWeight: 800, fontSize: ".8rem" }}>✓</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          <button
            disabled={oauthSaving || (OAUTH_NEEDS_STREAM.includes(oauthGrade) && !oauthStream)}
            onClick={async () => {
              setOauthSaveError(null);
              // Validate stream for Grade 11/12
              if (OAUTH_NEEDS_STREAM.includes(oauthGrade) && !oauthStream) {
                setOauthSaveError("Please choose your academic stream to continue.");
                return;
              }
              setOauthSaving(true);
              try {
                const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
                let freshToken = pendingOauthUser.accessToken;
                try {
                  const { data: refreshed } = await supabase.auth.refreshSession();
                  if (refreshed?.session?.access_token) freshToken = refreshed.session.access_token;
                } catch { /* use original token */ }

                const body = { role: "student", grade: oauthGrade, full_name: pendingOauthUser.username };
                if (OAUTH_NEEDS_STREAM.includes(oauthGrade) && oauthStream) {
                  body.stream = oauthStream;
                }

                const resp = await fetch(`${API_BASE}/api/auth/oauth/complete-profile`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json", Authorization: `Bearer ${freshToken}` },
                  body: JSON.stringify(body),
                });
                const result = await resp.json();

                if (!resp.ok) {
                  setOauthSaveError(result.detail || "Could not save your grade. Please try again.");
                  return;
                }

                const { data: freshSession } = await supabase.auth.getSession();
                const finalToken = freshSession?.session?.access_token || freshToken;
                await _finishOAuthLogin(result, { ...freshSession?.session, access_token: finalToken, user: freshSession?.session?.user });
                setPendingOauthUser(null);
              } catch (err) {
                setOauthSaveError("We couldn't save your grade. Please try again.");
                console.error("[oauth] complete-profile (student) error:", err);
              } finally {
                setOauthSaving(false);
              }
            }}
            style={{
              ...btnBase,
              background: (OAUTH_NEEDS_STREAM.includes(oauthGrade) && !oauthStream)
                ? "#334155"
                : "linear-gradient(135deg,#6366f1,#8b5cf6)",
              color: "#fff",
              cursor: (OAUTH_NEEDS_STREAM.includes(oauthGrade) && !oauthStream) ? "not-allowed" : "pointer",
              opacity: (OAUTH_NEEDS_STREAM.includes(oauthGrade) && !oauthStream) ? 0.6 : 1,
            }}
          >
            {oauthSaving ? "Saving…" : OAUTH_NEEDS_STREAM.includes(oauthGrade) && !oauthStream
              ? "Select a stream to continue"
              : `Continue as ${oauthGrade} student →`}
          </button>
          {oauthSaveError && (
            <div style={{ marginTop: 12, padding: "10px 14px", borderRadius: 8,
              background: "rgba(239,68,68,.12)", border: "1px solid rgba(239,68,68,.3)",
              fontSize: "0.82rem", color: "#fca5a5", textAlign: "center" }}>
              {oauthSaveError}
            </div>
          )}
          <button
            style={{ ...btnBase, background: "transparent", color: "#94a3b8", marginTop: 8, fontSize: "0.82rem" }}
            onClick={() => { setOauthStep("role"); setOauthSaveError(null); }}
          >
            ← Back
          </button>
        </div>
      </div>
    );
  }

  // Show a full-screen spinner while the OAuth callback is being processed
  if (oauthLoading) {
    return (
      <div style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        background: "#0f172a",
        color: "#f8fafc",
        gap: 16,
        fontFamily: "-apple-system, sans-serif",
      }}>
        <div style={{
          width: 48, height: 48, border: "4px solid #334155",
          borderTopColor: "#6366f1", borderRadius: "50%",
          animation: "spin 0.8s linear infinite",
        }} />
        <p style={{ fontSize: "1rem", color: "#94a3b8" }}>Signing you in with Google…</p>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (!user) {
    if (showLanding) {
      return (
        <LandingPage
          onShowLogin={() => setShowLanding(false)}
          onShowSignup={(plan) => {
            setSignupInitialPlan(plan || "free");
            setShowSignup(true);
          }}
        />
      );
    }
    return (
      <LoginPage
        onLogin={handleLogin}
        onShowSignup={() => {
          setShowSignup(true);
          setSignupInitialPlan("free");
        }}
      />
    );
  }

  // ── Welcome transition screen — shown for 2.5s after fresh login ──────────
  if (showWelcome && welcomeUser) {
    const wu = welcomeUser;
    const firstName = (wu.username || "").split(" ")[0] || "there";
    const role = wu.role;
    const grade = wu.grade || "";

    const roleConfig = {
      student: {
        Icon: BookOpen,
        headline: `Hello ${firstName}${grade ? `, ${grade}` : ""}!`,
        line1: "Your AI tutor is ready.",
        line2: "Lessons, mock tests and doubts — all set for you.",
        color: "#6366f1",
      },
      parent: {
        Icon: Users,
        headline: `Welcome, ${firstName}!`,
        line1: "Your child's learning dashboard is set up.",
        line2: "Track progress, tests, and activity — all in one place.",
        color: "#10b981",
      },
      teacher: {
        Icon: GraduationCap,
        headline: `Welcome, ${firstName}!`,
        line1: "Your classroom and student roster are ready.",
        line2: "Start assigning lessons and tracking progress today.",
        color: "#f59e0b",
      },
    };
    const cfg = roleConfig[role] || roleConfig.student;

    return (
      <div style={{
        position: "fixed", inset: 0, zIndex: 9999,
        display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center",
        background: "#0f172a",
        animation: "wfadeIn .3s ease",
        fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
      }}>
        <style>{`
          @keyframes wfadeIn{from{opacity:0;transform:scale(.97)}to{opacity:1;transform:scale(1)}}
          @keyframes wdots{0%,80%,100%{opacity:.25}40%{opacity:1}}
          @keyframes wbar{0%{width:0%}100%{width:100%}}
        `}</style>

        {/* Logo */}
        <img src="/loading-logo.gif" alt="Likha Poha AI" height="80"
          style={{ width: "auto", marginBottom: 32, opacity: .9 }} />

        {/* Icon + headline */}
        <cfg.Icon size={56} strokeWidth={1.4} style={{ color: cfg.color, marginBottom: 12 }} />
        <h2 style={{ fontSize: "1.5rem", fontWeight: 900, color: "#f1f5f9", margin: "0 0 10px", textAlign: "center", padding: "0 24px" }}>
          {cfg.headline}
        </h2>
        <p style={{ fontSize: ".9rem", color: "#94a3b8", margin: "0 0 4px", textAlign: "center" }}>{cfg.line1}</p>
        <p style={{ fontSize: ".82rem", color: "#64748b", margin: "0 0 32px", textAlign: "center" }}>{cfg.line2}</p>

        {/* Animated dots progress */}
        <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
          {[0,1,2,3,4].map(i => (
            <div key={i} style={{
              width: 8, height: 8, borderRadius: "50%",
              background: cfg.color,
              animation: `wdots 1.2s ease-in-out ${i * 0.18}s infinite`,
            }} />
          ))}
        </div>

        {/* Progress bar */}
        <div style={{ width: 220, height: 3, background: "#1e293b", borderRadius: 4, overflow: "hidden" }}>
          <div style={{
            height: "100%",
            background: `linear-gradient(90deg, ${cfg.color}, ${cfg.color}88)`,
            borderRadius: 4,
            animation: "wbar 2.5s ease-out forwards",
          }} />
        </div>
        <p style={{ fontSize: ".72rem", color: "#475569", marginTop: 12 }}>
          Taking you to your dashboard…
        </p>
      </div>
    );
  }

  // ── Free Tier access ──────────────────────────────────────────────────────
  // All registered users automatically access the platform on the Free Tier.
  // There is no subscription gate — users see the dashboard immediately and
  // can upgrade to a paid plan (Nano / Premium / Family) at any time.
  //
  // Free Tier limitations (limited lessons, 5/day mock tests & doubts) are
  // enforced by the backend route handlers (lesson.py, doubt.py, mock_test.py)
  // via is_free_tier_user(), not by blocking UI access here.
  // ──────────────────────────────────────────────────────────────────────────

  const pageMeta = PAGE_META[activePage] || PAGE_META.lessons;

  function renderPage() {
    /** Render the active page component while keeping all routing state inside the app shell. */
    switch (activePage) {
      case "dashboard":
        return <StudentDashboardPage user={user} setActivePage={handlePageChange} />;
      case "formulaSheet":
        return <FormulaSheetPage user={user} setActivePage={handlePageChange} />;
      case "adminControl":
        return <AdminControlPage user={user} />;
      case "adminQACenter":
        return <AdminQACenterPage user={user} setActivePage={handlePageChange} />;
      case "adminIssues":
        return <AdminIssuesPage user={user} setActivePage={handlePageChange} />;
      case "featureAuthAudit":
        return <FeatureAuthAuditPage user={user} />;
      case "lessons":
        return <LessonsPage user={user} setActivePage={handlePageChange} />;
      case "doubt":
        return <DoubtPage user={user} setActivePage={handlePageChange} />;
      case "mockTest":
        return <MockTestPage user={user} setActivePage={handlePageChange} />;
      case "resources":
        return <ResourcesPage user={user} />;
      case "analytics":
        return <AnalyticsPage user={user} />;
      case "leaderboard":
        return <LeaderboardPage user={user} />;
      case "ragUpload":
        return <RagUploadPage user={user} />;
      case "syllabusReview":
        return <AdminSyllabusReviewPage user={user} />;
      case "subscriptionSettings":
        return <AdminSubscriptionSettingsPage user={user} />;
      case "pricingCalculator":
        return <AdminPricingCalculatorPage user={user} />;
      case "performanceTests":
        return <AdminPerformanceTestsPage user={user} />;
      case "learningSimulation":
        return <AdminLearningSimulationPage user={user} />;
      case "guideThemes":
        return <AdminGuideSettingsPage user={user} />;
      case "lessonCardStyle":
        return <AdminLessonCardPage user={user} />;
      case "productCatalogue":
        return <AdminProductCataloguePage user={user} />;
      case "cacheManagement":
        return <AdminCacheManagementPage user={user} />;
      case "salesIncentives":
        return <SalesIncentivePage user={user} />;
      case "salesLeads":
        return <SalesLeadPage user={user} />;
      case "salesDemo":
        return <SalesDemoPage user={user} />;
      case "salesCollaterals":
        return <SalesCollateralPage user={user} />;
      case "usage":
        return <UsagePage user={user} />;
      case "parentDashboard":
        return <ParentDashboardPage user={user} />;
      case "teacherDashboard":
        return <TeacherDashboardPage user={user} />;
      case "teacherLessonPlan":
        return <TeacherLessonPlanPage user={user} />;
      case "teacherTestPaper":
        return <TeacherTestPaperPage user={user} />;
      case "teacherStudentAnalytics":
        return <TeacherStudentAnalyticsPage user={user} />;
      case "exemplarResearch":
        return <ExemplarResearchPage user={user} setActivePage={handlePageChange} />;
      case "subscriptionPlans":
        return <SubscriptionPlansPage user={user} onSubscriptionComplete={handleSubscriptionComplete} />;
      case "platformWalkthrough":
        return <WalkthroughPage user={user} />;
      case "changePassword":
        return <ChangePasswordPage user={user} />;
      case "paymentLogs":
        return <AdminPaymentsPage user={user} />;
      case "adminOperations":
        return <AdminOperationsPage user={user} />;
      case "unansweredReview":
        return <AdminUnansweredQuestionsPage user={user} />;
      case "lessonRepair":
        return <AdminLessonRepairPage user={user} />;
      case "lessonExperience":
        if (user?.role !== "admin") return null;
        return <AdminLessonExperiencePage user={user} />;
      case "aiStudio":
        return <AdminAIStudioPage user={user} />;
      case "examPrep":
        return <ExamPrepPage user={user} setActivePage={handlePageChange} />;
      default:
        return <LessonsPage user={user} />;
    }
  }

  return (
    <ToastProvider>
    <div className="app-shell premium-app-shell">
      <Sidebar
        activePage={activePage}
        setActivePage={handlePageChange}
        user={user}
        onLogout={handleLogout}
        mobileNavOpen={mobileNavOpen}
        setMobileNavOpen={setMobileNavOpen}
      />

      <main className="main-content premium-main">
        <header className="topbar">
          <button
            className="mobile-menu-btn"
            onClick={() => setMobileNavOpen(true)}
          >
            ☰
          </button>
          <div>
            <p className="eyebrow">Your Personal Tutor - AI Powered</p>
            <h1>
              {(() => {
                const PageIcon = PAGE_ICONS[activePage];

                return (
                  <>
                    {PageIcon && (
                      <PageIcon
                        size={38}
                        strokeWidth={2.4}
                        className="page-title-icon"
                      />
                    )}

                    {pageMeta.title}
                  </>
                );
              })()}
            </h1>
            <p className="page-subtitle">{pageMeta.subtitle}</p>
          </div>

          <div className="topbar-actions">
            <button
              className="theme-toggle-btn"
              onClick={() => setDarkMode((prev) => !prev)}
            >
              {darkMode ? "☀️ Light" : "🌙 Dark"}
            </button>

            <div className="profile-pill">{user.username}</div>

            {/* Likha Poha AI Guide — inline in header, no longer floating */}
            {["student", "parent"].includes(user.role) && (
              <FirstTimeGuide user={user} activePage={activePage} />
            )}
          </div>
        </header>

        {/* Paid subscription expiry banner — driven by the canonical resolver.
            Only shown for PAID users with a validUntil date.
            Offer-code users are never shown this banner (they see offer status
            on the Subscription page instead). */}
        {user?.role === "student" && (() => {
          // Resolve using the same canonical function as SubscriptionPlansPage
          // so App.jsx and the subscription page can never show conflicting states.
          const resolved = resolveSubscription(user,
            user?.offerAccess && user?.offerValidUntil
              ? { has_offer_access: user.offerAccess, valid_until: user.offerValidUntil,
                  days_remaining: user.offerDaysRemaining, expiring_soon: !!user.offerExpiringSoon }
              : null
          );
          if (resolved.accessSource !== ACCESS_SOURCE.PAID || !resolved.validUntil) return null;
          return (
            <div style={{
              padding: "10px 20px",
              background: resolved.expiringSoon
                ? "linear-gradient(135deg, rgba(245,158,11,.15), rgba(239,68,68,.1))"
                : "linear-gradient(135deg, rgba(99,102,241,.12), rgba(139,92,246,.1))",
              borderBottom: `1px solid ${resolved.expiringSoon ? "rgba(245,158,11,.4)" : "rgba(99,102,241,.3)"}`,
              display: "flex", alignItems: "center", justifyContent: "space-between",
              flexWrap: "wrap", gap: 8,
            }}>
              <span style={{ fontSize: ".85rem", fontWeight: 600, color: resolved.expiringSoon ? "#fbbf24" : "#a5b4fc" }}>
                {resolved.expiringSoon ? "⚠️" : "✨"}{" "}
                <strong>{resolved.planName} active</strong>
                {" — "}
                {resolved.daysRemaining != null
                  ? resolved.daysRemaining === 0
                    ? "expires today"
                    : `${resolved.daysRemaining} day${resolved.daysRemaining !== 1 ? "s" : ""} remaining`
                  : `until ${new Date(resolved.validUntil).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}`}
                {resolved.expiringSoon && " — upgrade to keep your access"}
              </span>
              <button
                onClick={() => handlePageChange("subscriptionPlans")}
                style={{
                  background: resolved.expiringSoon ? "rgba(245,158,11,.2)" : "rgba(99,102,241,.2)",
                  border: `1px solid ${resolved.expiringSoon ? "rgba(245,158,11,.5)" : "rgba(99,102,241,.5)"}`,
                  borderRadius: 6, padding: "4px 12px", cursor: "pointer",
                  fontSize: ".78rem", fontWeight: 700, fontFamily: "inherit",
                  color: resolved.expiringSoon ? "#fbbf24" : "#a5b4fc",
                  whiteSpace: "nowrap",
                }}
              >
                {resolved.expiringSoon ? "Upgrade now →" : "View plans →"}
              </button>
            </div>
          );
        })()}

        <AnimatePresence mode="wait">
          <motion.section
            key={activePage}
            className="page-surface"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.22, ease: "easeOut" }}
          >
            {renderPage()}
          </motion.section>
        </AnimatePresence>
      </main>

      <ChatWidget />

      {/* Global floating Report Issue button — visible to student/parent/teacher */}
      {user && user.canReportIssues === true && (
        <>
          <button
            data-testid="global-report-issue-btn"
            onClick={() => setReportBugOpen(true)}
            title="Report an issue"
            style={{ position:"fixed", bottom:88, right:20, zIndex:900,
              background:"#6366f1", color:"#fff", border:"none", borderRadius:28,
              padding:"10px 18px", fontFamily:"inherit", fontWeight:700, fontSize:".82rem",
              cursor:"pointer", boxShadow:"0 4px 16px rgba(99,102,241,0.4)",
              display:"flex", alignItems:"center", gap:6 }}>
            🐛 Report Issue
          </button>
          <ReportIssueModal
            open={reportBugOpen}
            onClose={() => setReportBugOpen(false)}
            context={{ route: activePage, grade: user?.grade }}
            user={user}
          />
        </>
      )}
    </div>
    </ToastProvider>
  );
}

export default App;
