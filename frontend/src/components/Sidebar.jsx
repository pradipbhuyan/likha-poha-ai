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
    { key: "dashboard", label: "Dashboard", icon: "🏠" },
    { key: "lessons", label: "Lessons", icon: "📖" },
    { key: "doubt", label: "Ask Doubt", icon: "❓" },
    { key: "quiz", label: "Quiz", icon: "📝" },
    { key: "mockTest", label: "Mock Test", icon: "🧪" },
    { key: "resources", label: "Learn More", icon: "🎥" },
    { key: "analytics", label: "Analytics", icon: "📊" },
    { key: "leaderboard", label: "Leaderboard", icon: "🏆" },
    { key: "ragUpload", label: "RAG Upload", icon: "📤", adminOnly: true },
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
        <div className="brand-icon">📚</div>

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
        {visiblePages.map((page) => (
          <button
            key={page.key}
            className={activePage === page.key ? "active" : ""}
            onClick={() => setActivePage(page.key)}
          >
            <span className="nav-icon">{page.icon}</span>
            <span>{page.label}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="mini-status">
          <span className="status-dot"></span>
          AI Tutor Online
        </div>

        <button className="logout" onClick={onLogout}>
          Logout
        </button>
      </div>
    </aside>
  );
}

export default Sidebar;
