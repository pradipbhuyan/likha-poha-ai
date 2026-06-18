import { useEffect, useRef, useState } from "react";
import LoginPage from "./pages/LoginPage";
import Sidebar from "./components/Sidebar";
import { ToastProvider } from "./context/ToastContext";

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
import ResetPasswordPage from "./pages/ResetPasswordPage";
import ChangePasswordPage from "./pages/ChangePasswordPage";
import SalesIncentivePage from "./pages/SalesIncentivePage";
import SalesLeadPage from "./pages/SalesLeadPage";
import SalesDemoPage from "./pages/SalesDemoPage";
import SalesCollateralPage from "./pages/SalesCollateralPage";
import AdminPerformanceTestsPage from "./pages/AdminPerformanceTestsPage";
import AdminGuideSettingsPage from "./pages/AdminGuideSettingsPage";
import AdminCacheManagementPage from "./pages/AdminCacheManagementPage";
import AdminProductCataloguePage from "./pages/AdminProductCataloguePage";
import AdminPaymentsPage from "./pages/AdminPaymentsPage";
import FirstTimeGuide from "./components/FirstTimeGuide";
import LandingPage from "./pages/LandingPage";
import RefundPolicyPage from "./pages/RefundPolicyPage";
import SignupPage from "./pages/SignupPage";

import "./App.css";

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
};

function App() {
  /** Owns global session, navigation, and theme state for the single-page app shell. */
  const [user, setUser] = useState(null);
  const [showLanding, setShowLanding] = useState(
    () => !localStorage.getItem("tutor_user")
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

    const savedUser = localStorage.getItem("tutor_user");
    const savedPage = localStorage.getItem("tutor_active_page");

    if (savedUser) {
      setUser(JSON.parse(savedUser));
    }

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

  function handleLogin(userData) {
    /** Persist the authenticated user and send them to the right role-specific landing page. */
    setUser(userData);
    setRoutePath("/");
    localStorage.setItem("tutor_user", JSON.stringify(userData));
  
    if (userData.role === "admin") {
      setActivePage("adminControl");
      localStorage.setItem("tutor_active_page", "adminControl");
    } else if (userData.role === "parent") {
      setActivePage("parentDashboard");
      localStorage.setItem("tutor_active_page", "parentDashboard");
    } else if (userData.role === "teacher") {
      setActivePage("teacherDashboard");
      localStorage.setItem("tutor_active_page", "teacherDashboard");
    } else if (userData.role === "sales") {
      setActivePage("salesLeads");
      localStorage.setItem("tutor_active_page", "salesLeads");
    } else {
      setActivePage("dashboard");
      localStorage.setItem("tutor_active_page", "dashboard");
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
        onBackToLogin={() => {
          setShowSignup(false);
          setShowLanding(false);
          window.history.replaceState({}, "", "/");
          setRoutePath("/");
        }}
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
        return <MockTestPage user={user} />;
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
      case "subscriptionPlans":
        return <SubscriptionPlansPage user={user} />;
      case "changePassword":
        return <ChangePasswordPage user={user} />;
      case "paymentLogs":
        return <AdminPaymentsPage user={user} />;
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
            <p className="eyebrow">Class 5-10 CBSE</p>
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
    </div>
    </ToastProvider>
  );
}

export default App;
