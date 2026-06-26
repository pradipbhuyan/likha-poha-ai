import { useEffect, useRef, useState } from "react";
import LoginPage from "./pages/LoginPage";
import Sidebar from "./components/Sidebar";
import { ToastProvider } from "./context/ToastContext";
import { supabase } from "./api/supabaseClient";
import logo from "./assets/AITutorLogo1.png";

import LessonsPage from "./pages/LessonsPage";
import DoubtPage from "./pages/DoubtPage";
import MockTestPage from "./pages/MockTestPage";
import ResourcesPage from "./pages/ResourcesPage";
import AnalyticsPage from "./pages/AnalyticsPage";
import LeaderboardPage from "./pages/LeaderboardPage";
import RagUploadPage from "./pages/RagUploadPage";
import AdminSyllabusReviewPage from "./pages/AdminSyllabusReviewPage";
import DashboardPage from "./pages/DashboardPage";
import { motion, AnimatePresence } from "framer-motion";
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
import AdminGuideSettingsPage from "./pages/AdminGuideSettingsPage";
import AdminLessonCardPage from "./pages/AdminLessonCardPage";
import AdminCacheManagementPage from "./pages/AdminCacheManagementPage";
import AdminProductCataloguePage from "./pages/AdminProductCataloguePage";
import AdminPaymentsPage from "./pages/AdminPaymentsPage";
import AdminOperationsPage from "./pages/AdminOperationsPage";
import FirstTimeGuide from "./components/FirstTimeGuide";
import LandingPage from "./pages/LandingPage";
import ChatWidget from "./components/ChatWidget";
import AdminUnansweredQuestionsPage from "./pages/AdminUnansweredQuestionsPage";
import RefundPolicyPage from "./pages/RefundPolicyPage";
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
  guideThemes: {
    title: "LikhaPoha AI Guide",
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
  // Safety-net: if the OAuth spinner is somehow stuck, auto-clear after 8 s
  useEffect(() => {
    if (!oauthLoading) return;
    const t = setTimeout(() => setOauthLoading(false), 8000);
    return () => clearTimeout(t);
  }, [oauthLoading]);
  // When a student signs in via Google for the first time their grade is unknown.
  // We store their partial user object here and show a grade-picker before calling handleLogin.
  const [pendingOauthUser, setPendingOauthUser] = useState(null);
  const [oauthRole, setOauthRole] = useState("student");   // role chosen on setup screen
  const [oauthGrade, setOauthGrade] = useState("Grade 9");
  const [oauthStep, setOauthStep] = useState("role");      // "role" → "grade" → done
  const [oauthSaving, setOauthSaving] = useState(false);
  const OAUTH_GRADES = ["Grade 5","Grade 6","Grade 7","Grade 8","Grade 9","Grade 10"];
  // Prevent double-firing of onAuthStateChange on mobile (Supabase OAuth redirect behaviour)
  const oauthProcessed = useRef(false);

  // ── Google OAuth callback handler ──────────────────────────────────────────
  // Supabase redirects back to the app after Google auth with a session in the
  // URL fragment. onAuthStateChange fires with event=SIGNED_IN; we build the
  // normalized user object here and call handleLogin.
  useEffect(() => {
    const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        // Only handle OAuth sign-ins (not password-based logins, which are
        // handled directly in LoginPage / SignupPage).
        if (event !== "SIGNED_IN" || !session) return;
        const provider = session.user?.app_metadata?.provider;
        if (provider === "email") return;      // email/password — skip
        // Use localStorage directly (not the stale `user` closure) so returning
        // Google users with an active session are never re-processed on reload.
        if (localStorage.getItem("tutor_user")) {
          // Silently refresh the access token in the saved session without
          // showing the spinner — the user is already logged in.
          try {
            const saved = JSON.parse(localStorage.getItem("tutor_user"));
            const refreshed = { ...saved, accessToken: session.access_token };
            setUser(refreshed);
            localStorage.setItem("tutor_user", JSON.stringify(refreshed));
          } catch { /* non-critical */ }
          return;
        }
        if (oauthProcessed.current) return;    // prevent double-fire on mobile redirect
        oauthProcessed.current = true;

        setOauthLoading(true);
        try {
          // Fetch or wait for the profile row (the DB trigger creates it async)
          let profile = null;
          for (let attempt = 0; attempt < 6; attempt++) {
            const { data } = await supabase
              .from("profiles")
              .select("*")
              .eq("id", session.user.id)
              .maybeSingle();
            if (data) { profile = data; break; }
            await new Promise(r => setTimeout(r, 600));  // wait 600 ms then retry
          }

          if (!profile) {
            console.error("Google OAuth: profile row not found after 6 attempts");
            return;
          }

          // Fetch offer validity (best-effort)
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

          const normalizedUser = {
            id: session.user.id,
            email: session.user.email,
            username: profile.username || session.user.email,
            role: profile.role || "student",
            grade: profile.grade || "Grade 9",
            board: profile.board || "CBSE",
            parentId: profile.parent_id,
            familyId: profile.family_id,
            accessToken: session.access_token,
            accessCbse: !!profile.access_cbse,
            accessSofScience: !!profile.access_sof_science,
            accessSofMaths: !!profile.access_sof_maths,
            accessSofEnglish: !!profile.access_sof_english,
            cbseSubjects: Array.isArray(profile.cbse_subjects) ? profile.cbse_subjects : [],
            avatar: profile.avatar || session.user.user_metadata?.avatar_url || "",
            dailyTokenLimit: profile.daily_token_limit,
            monthlyTokenLimit: profile.monthly_token_limit,
            subscriptionPlan: profile.subscription_plan || "free",
            accountStatus: profile.account_status || "active",
            ...offerData,
          };

          // Detect first-time Google sign-in: check if the OAuth identity was
          // created within the last 3 minutes. This is more reliable than comparing
          // created_at vs last_sign_in_at (which can differ due to OAuth redirect time).
          const identityCreatedAt = session.user.identities?.[0]?.created_at;
          const identityAgeMs = identityCreatedAt
            ? Date.now() - new Date(identityCreatedAt).getTime()
            : Infinity;
          const isFirstLogin = identityAgeMs < 3 * 60 * 1000; // identity created < 3 min ago

          if (isFirstLogin) {
            setPendingOauthUser(normalizedUser);
            setOauthStep("role");
          } else {
            // Returning Google user — profile already has correct role/grade
            handleLogin(normalizedUser);
          }
        } finally {
          setOauthLoading(false);
        }
      }
    );
    return () => subscription.unsubscribe();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  // ──────────────────────────────────────────────────────────────────────────

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
    // Only restore activePage here (setUser is not needed).
    const savedUser = localStorage.getItem("tutor_user");
    const savedPage = localStorage.getItem("tutor_active_page");

    if (savedUser) {
      const parsedUser = JSON.parse(savedUser);

      if (savedPage && !(parsedUser.role === "admin" && savedPage === "dashboard")) {
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
  }, []);

  useEffect(() => {
    document.body.classList.toggle("dark-mode", darkMode);

    localStorage.setItem("tutor_dark_mode", darkMode);
  }, [darkMode]);

  async function handleLogin(userData) {
    /** Persist the authenticated user and send them to the right role-specific landing page. */
    const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

    // For students, fetch fresh profile to get subscription_expires_at and check expiry
    let enrichedUser = userData;
    if (userData.role === "student" && userData.accessToken) {
      try {
        const r = await fetch(`${API_BASE}/api/auth/profile`, {
          headers: { Authorization: `Bearer ${userData.accessToken}` },
        });
        if (r.ok) {
          const p = await r.json();
          enrichedUser = {
            ...userData,
            accessCbse: p.access_cbse ?? userData.accessCbse,
            subscriptionPlan: p.subscription_plan ?? userData.subscriptionPlan,
            subscriptionExpiresAt: p.subscription_expires_at || null,
            subscriptionDaysRemaining: p.subscription_days_remaining ?? null,
            subscriptionExpiringSoon: !!p.subscription_expiring_soon,
          };
        }
      } catch { /* non-critical */ }
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
              How are you using LikhaPoha AI?
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 8 }}>
              {[
                { r: "student", icon: "🎓", label: "Student", desc: "I want to learn and take practice tests" },
                { r: "parent",  icon: "👨‍👩‍👧", label: "Parent",  desc: "I want to track my child's learning" },
                { r: "teacher", icon: "📋", label: "Teacher", desc: "I monitor my students' progress" },
              ].map(({ r, icon, label, desc }) => (
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
                  <span style={{ fontSize: "1.4rem", flexShrink: 0 }}>{icon}</span>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: "0.9rem" }}>{label}</div>
                    <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>{desc}</div>
                  </div>
                </div>
              ))}
            </div>
            <button
              style={{ ...btnBase, background: "linear-gradient(135deg,#6366f1,#8b5cf6)", color: "#fff", marginTop: 16 }}
              onClick={() => {
                if (oauthRole === "student") {
                  setOauthStep("grade"); // students need to pick grade next
                } else {
                  // Parents and teachers — save role then send to Subscription page
                  setOauthSaving(true);
                  supabase.from("profiles").update({ role: oauthRole }).eq("id", pendingOauthUser.id).then(() => {
                    handleLogin({ ...pendingOauthUser, role: oauthRole });
                    setPendingOauthUser(null);
                    setOauthSaving(false);
                    // Give React one tick to mount the app shell, then navigate
                    setTimeout(() => setActivePage("subscriptionPlans"), 100);
                  });
                }
              }}
              disabled={oauthSaving}
            >
              {oauthSaving ? "Setting up…" : "Continue →"}
            </button>
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
          <select value={oauthGrade} onChange={e => setOauthGrade(e.target.value)} style={selectStyle}>
            {OAUTH_GRADES.map(g => <option key={g}>{g}</option>)}
          </select>
          <button
            disabled={oauthSaving}
            onClick={async () => {
              setOauthSaving(true);
              try {
                await supabase.from("profiles")
                  .update({ grade: oauthGrade, role: "student" })
                  .eq("id", pendingOauthUser.id);
              } catch { /* non-critical */ }
              handleLogin({ ...pendingOauthUser, role: "student", grade: oauthGrade });
              setPendingOauthUser(null);
              setOauthSaving(false);
              // Send new Google students to Subscription page to choose plan / offer code
              setTimeout(() => setActivePage("subscriptionPlans"), 100);
            }}
            style={{ ...btnBase, background: "linear-gradient(135deg,#6366f1,#8b5cf6)", color: "#fff" }}
          >
            {oauthSaving ? "Saving…" : `Continue as ${oauthGrade} student →`}
          </button>
          <button
            style={{ ...btnBase, background: "transparent", color: "#94a3b8", marginTop: 8, fontSize: "0.82rem" }}
            onClick={() => setOauthStep("role")}
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
        return <DashboardPage user={user} setActivePage={handlePageChange} />;
      case "adminControl":
        return <AdminControlPage user={user} />;
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

            <div className="status-pill">
              <span className="status-dot"></span>
              AI Ready
            </div>

            <div className="profile-pill">{user.username}</div>
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

      <FirstTimeGuide user={user} activePage={activePage} />
      <ChatWidget />
    </div>
    </ToastProvider>
  );
}

export default App;
