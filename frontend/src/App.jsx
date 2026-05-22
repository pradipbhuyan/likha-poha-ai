import { useEffect, useState } from "react";
import LoginPage from "./pages/LoginPage";
import Sidebar from "./components/Sidebar";

import LessonsPage from "./pages/LessonsPage";
import DoubtPage from "./pages/DoubtPage";
import QuizPage from "./pages/QuizPage";
import MockTestPage from "./pages/MockTestPage";
import ResourcesPage from "./pages/ResourcesPage";
import AnalyticsPage from "./pages/AnalyticsPage";
import LeaderboardPage from "./pages/LeaderboardPage";
import RagUploadPage from "./pages/RagUploadPage";

import "./App.css";

const PAGE_META = {
  lessons: {
    title: "Lessons",
    subtitle: "Generate step-wise AI lessons with narration, progress, and RAG sources.",
    icon: "📖",
  },
  doubt: {
    title: "Ask Doubt",
    subtitle: "Ask chapter-specific doubts and get guided explanations.",
    icon: "❓",
  },
  quiz: {
    title: "Quiz",
    subtitle: "Practice instantly with question-by-question feedback.",
    icon: "📝",
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
    subtitle: "Admin area for uploading textbook content into the AI knowledge base.",
    icon: "📤",
  },
};

function App() {
  const [user, setUser] = useState(null);
  const [activePage, setActivePage] = useState("lessons");

  useEffect(() => {
    const savedUser = localStorage.getItem("tutor_user");
    const savedPage = localStorage.getItem("tutor_active_page");

    if (savedUser) {
      setUser(JSON.parse(savedUser));
    }

    if (savedPage) {
      setActivePage(savedPage);
    }
  }, []);

  function handleLogin(userData) {
    setUser(userData);
    localStorage.setItem("tutor_user", JSON.stringify(userData));
  }

  function handleLogout() {
    setUser(null);
    localStorage.removeItem("tutor_user");
    localStorage.removeItem("tutor_active_page");
  }

  function handlePageChange(page) {
    setActivePage(page);
    localStorage.setItem("tutor_active_page", page);
  }

  if (!user) {
    return <LoginPage onLogin={handleLogin} />;
  }

  const pageMeta = PAGE_META[activePage] || PAGE_META.lessons;

  function renderPage() {
    switch (activePage) {
      case "lessons":
        return <LessonsPage user={user} />;
      case "doubt":
        return <DoubtPage user={user} />;
      case "quiz":
        return <QuizPage user={user} />;
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
      />

      <main className="main-content premium-main">
        <header className="topbar">
          <div>
            <p className="eyebrow">Grade 9 CBSE + SOF Olympiad</p>
            <h1>
              <span>{pageMeta.icon}</span> {pageMeta.title}
            </h1>
            <p className="page-subtitle">{pageMeta.subtitle}</p>
          </div>

          <div className="topbar-actions">
            <div className="status-pill">
              <span className="status-dot"></span>
              AI Ready
            </div>

            <div className="profile-pill">
              {user.username}
            </div>
          </div>
        </header>

        <section className="page-surface">
          {renderPage()}
        </section>
      </main>
    </div>
  );
}

export default App;