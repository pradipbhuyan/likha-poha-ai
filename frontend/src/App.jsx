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
    <div className="app-shell">
      <Sidebar
        activePage={activePage}
        setActivePage={handlePageChange}
        user={user}
        onLogout={handleLogout}
      />

      <main className="main-content">
        <h1>📚 Grade 9 CBSE + SOF Olympiad AI Tutor</h1>
        {renderPage()}
      </main>
    </div>
  );
}

export default App;