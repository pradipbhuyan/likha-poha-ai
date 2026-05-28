import { useEffect, useState } from "react";
import LoginPage from "./pages/LoginPage";
import Sidebar from "./components/Sidebar";

import LessonsPage from "./pages/LessonsPage";
import DoubtPage from "./pages/DoubtPage";
import MockTestPage from "./pages/MockTestPage";
import ResourcesPage from "./pages/ResourcesPage";
import AnalyticsPage from "./pages/AnalyticsPage";
import LeaderboardPage from "./pages/LeaderboardPage";
import RagUploadPage from "./pages/RagUploadPage";
import DashboardPage from "./pages/DashboardPage";
import { motion, AnimatePresence } from "framer-motion";
import { PAGE_ICONS } from "./utils/pageIcons";
import UsagePage from "./pages/UsagePage";
import ParentDashboardPage from "./pages/ParentDashboardPage";


import "./App.css";

const PAGE_META = {
  dashboard: {
    title: "Dashboard",
    subtitle:
      "Your central AI learning hub for lessons, practice, progress, and recommendations.",
    icon: "🏠",
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
};

function App() {
  const [user, setUser] = useState(null);
  const [activePage, setActivePage] = useState("dashboard");
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [darkMode, setDarkMode] = useState(
    localStorage.getItem("tutor_dark_mode") === "true"
  );

  useEffect(() => {
    const savedUser = localStorage.getItem("tutor_user");
    const savedPage = localStorage.getItem("tutor_active_page");

    if (savedUser) {
      setUser(JSON.parse(savedUser));
    }

    if (savedUser) {
      const parsedUser = JSON.parse(savedUser);
    
      if (savedPage) {
        setActivePage(savedPage);
      } else if (parsedUser.role === "parent") {
        setActivePage("parentDashboard");
      } else {
        setActivePage("dashboard");
      }
    }

    document.body.classList.toggle("dark-mode", darkMode);
  }, []);

  useEffect(() => {
    document.body.classList.toggle("dark-mode", darkMode);

    localStorage.setItem("tutor_dark_mode", darkMode);
  }, [darkMode]);

  function handleLogin(userData) {
    setUser(userData);
    localStorage.setItem("tutor_user", JSON.stringify(userData));
  
    if (userData.role === "parent") {
      setActivePage("parentDashboard");
      localStorage.setItem("tutor_active_page", "parentDashboard");
    } else {
      setActivePage("dashboard");
      localStorage.setItem("tutor_active_page", "dashboard");
    }
  }

  function handleLogout() {
    setUser(null);
    localStorage.removeItem("tutor_user");
    localStorage.removeItem("tutor_active_page");
  }

  function handlePageChange(page) {
    setActivePage(page);
    setMobileNavOpen(false);
    localStorage.setItem("tutor_active_page", page);
  }

  if (!user) {
    return <LoginPage onLogin={handleLogin} />;
  }

  const pageMeta = PAGE_META[activePage] || PAGE_META.lessons;

  function renderPage() {
    switch (activePage) {
      case "dashboard":
        return <DashboardPage user={user} setActivePage={handlePageChange} />;
      case "lessons":
        return <LessonsPage user={user} />;
      case "doubt":
        return <DoubtPage user={user} />;
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
      case "usage":
        return <UsagePage user={user} />;
      case "parentDashboard":
        return <ParentDashboardPage user={user} />;
      default:
        return <LessonsPage user={user} />;
    }
  }

  return (
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
            <p className="eyebrow">Grade 9 CBSE + SOF Olympiad</p>
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
    </div>
  );
}

export default App;
