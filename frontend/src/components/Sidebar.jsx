function Sidebar({ activePage, setActivePage, user, onLogout }) {
  const isAdmin = ["admin", "pradip"].includes(user?.username);

  const pages = [
    { key: "lessons", label: "📖 Lessons" },
    { key: "doubt", label: "❓ Ask Doubt" },
    { key: "quiz", label: "📝 Quiz" },
    { key: "mockTest", label: "🧪 Mock Test" },
    { key: "resources", label: "🎥 Learn More" },
    { key: "analytics", label: "📊 Analytics" },
    { key: "leaderboard", label: "🏆 Leaderboard" },
    { key: "ragUpload", label: "📤 RAG Upload", adminOnly: true },
  ];

  const visiblePages = pages.filter(
    (page) => !page.adminOnly || isAdmin
  );

  return (
    <aside className="sidebar">
      <h2>AI Tutor</h2>

      <p className="user-info">
        👤 {user.username}
        <br />
        <small>{user.role}</small>
      </p>

      <nav>
        {visiblePages.map((page) => (
          <button
            key={page.key}
            className={activePage === page.key ? "active" : ""}
            onClick={() => setActivePage(page.key)}
          >
            {page.label}
          </button>
        ))}
      </nav>

      <button className="logout" onClick={onLogout}>
        Logout
      </button>
    </aside>
  );
}

export default Sidebar;