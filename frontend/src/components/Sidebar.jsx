import {
  BarChart3,
  BookOpen,
  ClipboardList,
  CreditCard,
  HelpCircle,
  Home,
  LogOut,
  Trophy,
  UploadCloud,
  Video,
  DollarSign,
  Tags,
  Users,
  Settings,
  GraduationCap,
  ListChecks,
  Calculator,
  KeyRound,
  Handshake,
  MonitorPlay,
  Megaphone,
  Activity,
  Sparkles,
  Database,
  Package,
  BrainCircuit,
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
  /** Builds the role-aware navigation menu and renders the persistent app sidebar. */
  const isAdmin = user?.role === "admin" || user?.username === "pradip";

  const pages = [
    {
      key: "dashboard",
      label: "Dashboard",
      icon: Home,
      roles: ["student", "admin"],
      hideForAdmin: true,
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
      key: "syllabusReview",
      label: "Syllabus Review",
      icon: ListChecks,
      roles: ["admin"],
    },
    {
      key: "teacherDashboard",
      label: "Teacher Dashboard",
      icon: GraduationCap,
      roles: ["teacher"],
      hideForAdmin: true,
    },
    {
      key: "subscriptionSettings",
      label: "Subscription Settings",
      icon: Tags,
      roles: ["admin"],
    },
    {
      key: "pricingCalculator",
      label: "Pricing Calculator",
      icon: Calculator,
      roles: ["admin"],
    },
    {
      key: "paymentLogs",
      label: "Payment Logs",
      icon: CreditCard,
      roles: ["admin"],
    },
    {
      key: "performanceTests",
      label: "Performance Tests",
      icon: Activity,
      roles: ["admin"],
    },
    {
      key: "guideThemes",
      label: "LikhaPoha AI Guide",
      icon: Sparkles,
      roles: ["admin"],
    },
    {
      key: "cacheManagement",
      label: "Cache & Question Bank",
      icon: Database,
      roles: ["admin"],
    },
    {
      key: "productCatalogue",
      label: "Product Catalogue",
      icon: Package,
      roles: ["admin"],
    },
    {
      key: "unansweredReview",
      label: "AI Learning Review",
      icon: BrainCircuit,
      roles: ["admin"],
    },
    {
      key: "salesLeads",
      label: isAdmin ? "Lead Claims" : "My Lead Claims",
      icon: Users,
      roles: ["admin", "sales"],
    },
    {
      key: "salesIncentives",
      label: "Sales Incentives",
      icon: Handshake,
      roles: ["admin"],  // admin-only: old attribution system
    },
    {
      key: "salesDemo",
      label: "Product Demo",
      icon: MonitorPlay,
      roles: ["admin", "sales"],
    },
    {
      key: "salesCollaterals",
      label: "Sales Collaterals",
      icon: Megaphone,
      roles: ["admin", "sales"],
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
      hideForAdmin: true,
    },
    {
      key: "doubt",
      label: "Ask Doubt",
      icon: HelpCircle,
      roles: ["student", "admin"],
      hideForAdmin: true,
    },
    {
      key: "mockTest",
      label: "Mock Test",
      icon: ClipboardList,
      roles: ["student", "admin"],
      hideForAdmin: true,
    },
    {
      key: "resources",
      label: "Learn More",
      icon: Video,
      roles: ["student", "admin"],
      hideForAdmin: true,
    },
    {
      key: "analytics",
      label: "Analytics",
      icon: BarChart3,
      roles: ["student", "admin"],
      hideForAdmin: true,
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
      hideForAdmin: true,
    },
    {
      key: "platformWalkthrough",
      label: "Platform Walkthrough",
      icon: Video,
      roles: ["student", "parent", "teacher", "sales"],
    },
    {
      key: "subscriptionPlans",
      label: "Subscription",
      icon: CreditCard,
      roles: ["student", "parent"],
    },
    {
      key: "changePassword",
      label: "Change Password",
      icon: KeyRound,
      roles: ["student", "parent", "teacher", "admin", "sales"],
    },
  ];

  const visiblePages = pages.filter((page) => {
    /** Hide student/parent-only destinations from admin while keeping admin tools visible. */
    if (isAdmin) return !page.parentOnly && !page.hideForAdmin;
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
          <p style={{ fontSize: "1.05rem", fontWeight: 700, lineHeight: 1.25, color: "#f1f5f9" }}>Your Personal Tutor</p>
          <p style={{ fontSize: "0.82rem", fontWeight: 600, marginTop: 3, background: "linear-gradient(135deg,#6366f1,#10b981)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>AI Powered ✦</p>
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
