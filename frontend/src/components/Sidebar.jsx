import {
  BarChart3,
  BookOpen,
  ClipboardList,
  HelpCircle,
  Home,
  LogOut,
  Trophy,
  UploadCloud,
  Video,
  DollarSign,
  Users,
  Settings,
} from "lucide-react";

import logo from "../assets/AITutorLogo1.png";

function Sidebar({
  activePage,
  setActivePage,
  user,
  onLogout,
  mobileNavOpen,
  setMobileNavOpen,
}) {
  const isAdmin = user?.role === "admin" || user?.username === "pradip";
  const isParent = user?.role === "parent";
  const isStudent = user?.role === "student";

  const pages = [
    {
      key: "dashboard",
      label: "Dashboard",
      icon: Home,
      roles: ["student", "admin"],
    },
    {
      key: "adminControl",
      label: "Admin Control",
      icon: Settings,
      roles: ["admin"],
    },
    {
      key: "ragUpload",
      label: "RAG Upload",
      icon: UploadCloud,
      roles: ["admin"],
    },
    {
      key: "usage",
      label: "AI Usage",
      icon: DollarSign,
      roles: ["admin"],
    },
    {
      key: "lessons",
      label: "Lessons",
      icon: BookOpen,
      roles: ["student", "admin"],
    },
    {
      key: "doubt",
      label: "Ask Doubt",
      icon: HelpCircle,
      roles: ["student", "admin"],
    },
    {
      key: "mockTest",
      label: "Mock Test",
      icon: ClipboardList,
      roles: ["student", "admin"],
    },
    {
      key: "resources",
      label: "Learn More",
      icon: Video,
      roles: ["student", "admin"],
    },
    {
      key: "analytics",
      label: "Analytics",
      icon: BarChart3,
      roles: ["student", "admin"],
    },
    {
      key: "leaderboard",
      label: "Leaderboard",
      icon: Trophy,
      roles: ["student", "admin"],
    },
    {
      key: "parentDashboard",
      label: "Parent Dashboard",
      icon: Users,
      roles: ["parent", "admin"],
    },
  ];

  const visiblePages = pages.filter((page) => {
    if (isAdmin) return true;
    return page.roles?.includes(user?.role);
  });

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
          <strong>{user?.username}</strong>
          <span>{user?.role}</span>
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
