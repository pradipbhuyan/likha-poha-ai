import {
  BarChart3,
  BookOpen,
  Brain,
  ClipboardList,
  HelpCircle,
  Home,
  LogOut,
  Trophy,
  UploadCloud,
  Video,
} from "lucide-react";

import logo from "../assets/AITutorLogo.png";

function Sidebar({
  activePage,
  setActivePage,
  user,
  onLogout,
  mobileNavOpen,
  setMobileNavOpen,
}) {
  const isAdmin = ["admin", "pradip"].includes(user?.username);

  const pages = [
    { key: "dashboard", label: "Dashboard", icon: Home },
    { key: "lessons", label: "Lessons", icon: BookOpen },
    { key: "doubt", label: "Ask Doubt", icon: HelpCircle },
    { key: "quiz", label: "Quiz", icon: Brain },
    { key: "mockTest", label: "Mock Test", icon: ClipboardList },
    { key: "resources", label: "Learn More", icon: Video },
    { key: "analytics", label: "Analytics", icon: BarChart3 },
    { key: "leaderboard", label: "Leaderboard", icon: Trophy },
    { key: "ragUpload", label: "RAG Upload", icon: UploadCloud, adminOnly: true },
  ];

  const visiblePages = pages.filter((page) => !page.adminOnly || isAdmin);

  return (
    <aside
      className={
        mobileNavOpen
          ? "sidebar premium-sidebar mobile-open"
          : "sidebar premium-sidebar"
      }
    >
      <button
        className="mobile-close-btn"
        onClick={() => setMobileNavOpen(false)}
      >
        ✕
      </button>

      <div className="sidebar-brand">
        <img src={logo} alt="AI Tutor" className="brand-logo" />

        <div>
          <h2>AI Tutor</h2>
          <p>CBSE + SOF</p>
        </div>
      </div>

      <div className="user-card">
        <div className="avatar">
          {user?.username?.[0]?.toUpperCase() || "U"}
        </div>

        <div>
          <strong>{user.username}</strong>
          <span>{user.role}</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        {visiblePages.map((page) => {
          const Icon = page.icon;

          return (
            <button
              key={page.key}
              className={activePage === page.key ? "active" : ""}
              onClick={() => setActivePage(page.key)}
            >
              <span className="nav-icon">
                <Icon size={19} strokeWidth={2.4} />
              </span>

              <span>{page.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <button className="logout" onClick={onLogout}>
          <LogOut size={18} strokeWidth={2.4} />
          Logout
        </button>
      </div>
    </aside>
  );
}

export default Sidebar;