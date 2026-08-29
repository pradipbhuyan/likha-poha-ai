import { useState, useRef, useEffect } from "react";
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
  Layers,
  Bug,
  MessageSquare,
  FileText,
  Headphones,
  User,
  UserRound,
  CircleUser,
  CircleUserRound,
  School,
  Brain,
  Star,
  Rocket,
  Pencil,
  Camera,
  Trash2,
  Upload,
  Mail,
} from "lucide-react";

import logo from "../assets/AITutorLogo1.png";
import { isAllAccessTestUser } from "../utils/testAccounts";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// Icon choices for preset avatars — keys are preserved exactly from the old
// emoji set (boy1/boy2/boy3/girl1/girl2/girl3/star/rocket/book/brain) so
// avatars already saved to a student/parent's profile keep resolving to a
// picture instead of falling back to their initial.
const PRESET_AVATARS = [
  { key:"boy1", Icon: User }, { key:"boy2", Icon: UserRound }, { key:"boy3", Icon: GraduationCap },
  { key:"girl1", Icon: CircleUser }, { key:"girl2", Icon: CircleUserRound }, { key:"girl3", Icon: School },
  { key:"star", Icon: Star }, { key:"rocket", Icon: Rocket }, { key:"book", Icon: BookOpen },
  { key:"brain", Icon: Brain },
];

function AvatarDisplay({ avatar, initial, size = 40 }) {
  if (avatar && avatar.startsWith("data:")) {
    return <img src={avatar} alt="avatar" style={{ width: size, height: size, borderRadius: "50%", objectFit: "cover" }} />;
  }
  if (avatar) {
    const found = PRESET_AVATARS.find(a => a.key === avatar);
    if (found) {
      const Icon = found.Icon;
      return <Icon size={Math.round(size * 0.55)} strokeWidth={2} />;
    }
  }
  return <span style={{ fontSize: size * 0.5, fontWeight: 700 }}>{initial}</span>;
}

function Sidebar({
  activePage,
  setActivePage,
  user,
  onLogout,
  mobileNavOpen,
  setMobileNavOpen,
}) {
  /** Builds the role-aware navigation menu and renders the persistent app sidebar. */
  // Admin is a role, never a username. Usernames come from a user-supplied
  // field at signup with no uniqueness check, so granting on a literal name
  // means anyone who registers it inherits the grant.
  const isAdmin = user?.role === "admin";
  const [avatar, setAvatar] = useState(user?.avatar || "");
  const [showAvatarPicker, setShowAvatarPicker] = useState(false);
  const fileRef = useRef(null);
  const cameraRef = useRef(null);

  // Mobile nav drawer: block page scroll behind it and let Escape close it.
  useEffect(() => {
    if (!mobileNavOpen) return undefined;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    function handleKeyDown(e) {
      if (e.key === "Escape") setMobileNavOpen(false);
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [mobileNavOpen, setMobileNavOpen]);

  async function saveAvatar(newAvatar) {
    setAvatar(newAvatar);
    setShowAvatarPicker(false);
    try {
      await fetch(`${API_BASE}/api/profile/update-avatar`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${user?.accessToken}` },
        body: JSON.stringify({ avatar: newAvatar }),
      });
      // Update localStorage so avatar persists on refresh
      const saved = JSON.parse(localStorage.getItem("tutor_user") || "{}");
      saved.avatar = newAvatar;
      localStorage.setItem("tutor_user", JSON.stringify(saved));
    } catch { /* non-critical */ }
  }

  const pages = [
    {
      key: "dashboard",
      label: "Dashboard",
      icon: Home,
      roles: ["student", "admin"],
      hideForAdmin: true,
      group: "Home",
    },
        {
      key: "adminControl",
      label: "Admin Control",
      icon: Settings,
      roles: ["admin"],
      group: "Overview",
    },
    {
      key: "adminIssues",
      label: "Product Bugs",
      icon: Bug,
      roles: ["admin"],
      group: "Overview",
    },
    {
      key: "adminFeedback",
      label: "User Feedback",
      icon: MessageSquare,
      roles: ["admin"],
      group: "Overview",
    },
    {
      key: "adminTechDebt",
      label: "Tech Debt Backlog",
      icon: ListChecks,
      roles: ["admin"],
      group: "Overview",
    },
    {
      key: "cacheManagement",
      label: "Cache & Question Bank",
      icon: Database,
      roles: ["admin"],
      group: "Content Pipeline",
    },
    {
      key: "ragUpload",
      label: "RAG Upload",
      icon: UploadCloud,
      roles: ["admin"],
      group: "Content Pipeline",
    },
    {
      key: "syllabusReview",
      label: "Syllabus Review",
      icon: ListChecks,
      roles: ["admin"],
      group: "Content Pipeline",
    },
    {
      key: "lessonRepair",
      label: "Lesson Repair",
      icon: Layers,
      roles: ["admin"],
      group: "Content Pipeline",
    },
    {
      key: "lessonExperience",
      label: "Lesson Experience",
      icon: Sparkles,
      roles: ["admin"],
      group: "Content Pipeline",
    },
    {
      key: "lessonCardStyle",
      label: "Lesson Card Style",
      icon: Layers,
      roles: ["admin"],
      group: "Content Pipeline",
    },
    {
      key: "unansweredReview",
      label: "AI Learning Review",
      icon: BrainCircuit,
      roles: ["admin"],
      group: "Content Pipeline",
    },
    {
      key: "adminQACenter",
      label: "Platform QA Center",
      icon: Layers,
      roles: ["admin"],
      group: "Quality & Testing",
    },
    {
      key: "learningSimulation",
      label: "Learning Simulation",
      icon: Activity,
      roles: ["admin"],
      group: "Quality & Testing",
    },
    {
      key: "performanceTests",
      label: "Performance Tests",
      icon: Activity,
      roles: ["admin"],
      group: "Quality & Testing",
    },
    {
      key: "aiStudio",
      label: "AI Studio",
      icon: Sparkles,
      roles: ["admin"],
      group: "AI Configuration",
    },
    {
      key: "guideThemes",
      label: "Likha Poha AI Guide",
      icon: Sparkles,
      roles: ["admin"],
      group: "AI Configuration",
    },
    {
      key: "subscriptionSettings",
      label: "Subscription Settings",
      icon: Tags,
      roles: ["admin"],
      group: "Commercial",
    },
    {
      key: "pricingCalculator",
      label: "Pricing Calculator",
      icon: Calculator,
      roles: ["admin"],
      group: "Commercial",
    },
    {
      key: "productCatalogue",
      label: "Product Catalogue",
      icon: Package,
      roles: ["admin"],
      group: "Commercial",
    },
    {
      key: "paymentLogs",
      label: "Payment Logs",
      icon: CreditCard,
      roles: ["admin"],
      group: "Commercial",
    },
    {
      key: "usage",
      label: "AI Usage",
      icon: DollarSign,
      roles: ["admin"],
      group: "Commercial",
    },
    {
      key: "salesLeads",
      label: isAdmin ? "Lead Claims" : "My Lead Claims",
      icon: Users,
      roles: ["admin", "sales"],
      group: "Sales",
    },
    {
      key: "salesIncentives",
      label: "Sales Incentives",
      icon: Handshake,
      roles: ["admin"],  // admin-only: old attribution system
      group: "Sales",
    },
    {
      key: "adminSchoolOutreach",
      label: "School Outreach",
      icon: Mail,
      roles: ["admin"],
      group: "Sales",
    },
    {
      key: "salesDemo",
      label: "Product Demo",
      icon: MonitorPlay,
      roles: ["admin", "sales"],
      group: "Sales",
    },
    {
      key: "salesCollaterals",
      label: "Sales Collaterals",
      icon: Megaphone,
      roles: ["admin", "sales"],
      group: "Sales",
    },
    {
      key: "adminChat",
      label: "Platform Chat",
      icon: MessageSquare,
      roles: ["admin"],
      group: "Communication",
    },
    {
      key: "teacherDashboard",
      label: "Teacher Dashboard",
      icon: GraduationCap,
      roles: ["teacher"],
      hideForAdmin: true,
    },
    {
      key: "principalDashboard",
      label: "Principal Command Center",
      icon: School,
      roles: ["principal"],
      hideForAdmin: true,
    },
    {
      key: "teacherLessonPlan",
      label: "Create Lesson Plans",
      icon: BookOpen,
      roles: ["teacher"],
      hideForAdmin: true,
    },
    {
      key: "teacherTestPaper",
      label: "Create Test Paper",
      icon: ClipboardList,
      roles: ["teacher"],
      hideForAdmin: true,
    },
    {
      key: "teacherLectureAudio",
      label: "Listen to Lecture",
      icon: Headphones,
      roles: ["teacher"],
      hideForAdmin: true,
    },
    {
      key: "lessons",
      label: "Lessons",
      icon: BookOpen,
      roles: ["teacher"],
      hideForAdmin: true,
    },
    {
      key: "teacherStudentAnalytics",
      label: "Student Analytics",
      icon: BarChart3,
      roles: ["teacher"],
      hideForAdmin: true,
    },
    {
      key: "lessons",
      label: "Lessons",
      icon: BookOpen,
      roles: ["student", "admin"],
      hideForAdmin: true,
      group: "Learn",
    },
    {
      key: "doubt",
      label: "Ask Doubt",
      icon: HelpCircle,
      roles: ["student", "admin"],
      hideForAdmin: true,
      group: "Learn",
    },
    {
      key: "mockTest",
      label: "Mock Test",
      icon: ClipboardList,
      roles: ["student", "admin"],
      hideForAdmin: true,
      group: "Practise & Prepare",
    },
    {
      key: "examPrep",
      label: "Exam Prep Center",
      icon: GraduationCap,
      roles: ["admin", "student"],
      gradeFilter: ["Grade 11", "Grade 12"],
      // All-access QA accounts see this regardless of grade, so the team can
      // check the Grade 11/12 experience from one login.
      bypassGradeFilterForTestAccounts: true,
      group: "Practise & Prepare",
    },
    {
      key: "boardPapers",
      label: "Board Papers",
      icon: FileText,
      roles: ["student", "admin"],
      gradeFilter: ["Grade 9", "Grade 10", "Grade 11", "Grade 12"],
      hideForAdmin: true,
      group: "Practise & Prepare",
    },
    {
      key: "formulaSheet",
      label: "Formulas & Concepts",
      icon: Calculator,
      roles: ["student"],
      hideForAdmin: true,
      group: "Revision Tools",
    },
    {
      key: "exemplarResearch",
      label: "Exemplar Research",
      icon: Sparkles,
      roles: ["student"],
      gradeFilter: ["Grade 8", "Grade 9", "Grade 10", "Grade 11", "Grade 12"],
      hideForAdmin: true,
      group: "Revision Tools",
    },
    {
      key: "resources",
      label: "Learn More",
      icon: Video,
      roles: ["student", "admin"],
      hideForAdmin: true,
      group: "Revision Tools",
    },
    {
      key: "analytics",
      label: "Analytics",
      icon: BarChart3,
      roles: ["student", "admin"],
      hideForAdmin: true,
      group: "Progress",
    },
    {
      key: "leaderboard",
      label: "Leaderboard",
      icon: Trophy,
      roles: ["student", "admin"],
      group: "Progress",
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
      hideForAdmin: true,
      group: "Help & Account",
    },
    {
      key: "subscriptionPlans",
      label: "Subscription",
      icon: CreditCard,
      roles: ["student", "parent", "teacher"],
      hideForAdmin: true,
      group: "Help & Account",
    },
    {
      key: "changePassword",
      label: "Change Password",
      icon: KeyRound,
      roles: ["student", "parent", "teacher", "admin", "sales"],
      group: "Help & Account",
    },
  ];

  const visiblePages = pages.filter((page) => {
    /** Hide student/parent-only destinations from admin while keeping admin tools visible. */
    if (isAdmin) return !page.parentOnly && !page.hideForAdmin;
    // All-access QA accounts. Keyed on profiles.is_test_account rather than a
    // username, which signup takes from a user-supplied field and never
    // checks for uniqueness — a name here would be a grant anyone could claim.
    if (page.bypassGradeFilterForTestAccounts && isAllAccessTestUser(user)) return true;
    if (!page.roles?.includes(user?.role)) return false;
    // Grade-gated pages: students must be in one of the allowed grades
    if (page.gradeFilter && user?.role === "student") {
      return page.gradeFilter.includes(user?.grade);
    }
    return true;
  });

  return (
    <>
    {mobileNavOpen && (
      <div
        className="mobile-nav-backdrop"
        aria-hidden="true"
        onClick={() => setMobileNavOpen(false)}
      />
    )}
    <aside
      className={
        mobileNavOpen
          ? "sidebar premium-sidebar mobile-open"
          : "sidebar premium-sidebar"
      }
    >
      <button
        className="mobile-close-btn"
        aria-label="Close navigation menu"
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

      <div className="user-card" style={{ position: "relative" }}>
        {/* Avatar — clickable for student/parent to change */}
        <div
          className="avatar"
          style={{
            cursor: ["student", "parent", "teacher"].includes(user?.role) ? "pointer" : "default",
            overflow: avatar && avatar.startsWith("data:") ? "hidden" : "visible",
            display: "flex", alignItems: "center", justifyContent: "center",
            position: "relative",
          }}
          title={["student", "parent", "teacher"].includes(user?.role) ? "Click to change avatar" : ""}
          onClick={() => ["student", "parent", "teacher"].includes(user?.role) && setShowAvatarPicker(p => !p)}
        >
          <AvatarDisplay avatar={avatar} initial={user?.username?.[0]?.toUpperCase() || "U"} size={40} />
          {["student", "parent", "teacher"].includes(user?.role) && (
            <span style={{ position: "absolute", bottom: -2, right: -2, background: "#6366f1", borderRadius: "50%", width: 14, height: 14, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Pencil size={8} strokeWidth={2.5} color="#fff" />
            </span>
          )}
        </div>

        <div className="user-card-info">
          <strong>{user?.username}</strong>
          <span>{user?.role}</span>
        </div>
      </div>

      {/* Avatar picker dropdown */}
      {showAvatarPicker && (
        <div style={{ position: "absolute", left: 12, top: 180, zIndex: 200, background: "var(--panel, #1e293b)", border: "1px solid var(--border)", borderRadius: 12, padding: 14, width: 256, boxShadow: "0 8px 32px rgba(0,0,0,.4)" }}>
          <p style={{ fontSize: ".72rem", fontWeight: 700, color: "var(--muted)", marginBottom: 8 }}>Choose Avatar</p>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 10 }}>
            {PRESET_AVATARS.map(av => {
              const Icon = av.Icon;
              return (
                <button key={av.key} onClick={() => saveAvatar(av.key)}
                  style={{
                    width: 40, height: 40, borderRadius: "50%",
                    border: `2px solid ${avatar === av.key ? "#6366f1" : "rgba(99,102,241,.2)"}`,
                    background: avatar === av.key ? "rgba(99,102,241,.2)" : "rgba(255,255,255,.04)",
                    cursor: "pointer", overflow: "hidden",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    padding: 0, color: avatar === av.key ? "#a5b4fc" : "var(--text, #e2e8f0)",
                    boxShadow: avatar === av.key ? "0 0 0 3px rgba(99,102,241,.35)" : "none",
                  }}>
                  <Icon size={20} strokeWidth={2} />
                </button>
              );
            })}
          </div>
          {/* Upload + Camera row */}
          <div style={{ display: "flex", gap: 6, marginBottom: 6 }}>
            <label style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: 4, background: "rgba(99,102,241,.1)", border: "1px solid rgba(99,102,241,.2)", borderRadius: 7, padding: "6px 8px", cursor: "pointer", fontSize: ".72rem", color: "#a5b4fc", fontWeight: 600 }}>
              <Upload size={14} strokeWidth={2} /> Upload
              <input ref={fileRef} type="file" accept="image/*" style={{ display: "none" }}
                onChange={e => { const f = e.target.files?.[0]; if (!f) return; const r = new FileReader(); r.onload = ev => saveAvatar(ev.target.result); r.readAsDataURL(f); }} />
            </label>
            {/* Take Photo: mobile → file capture, desktop → getUserMedia */}
            {/Mobi|Android|iPhone|iPad/i.test(navigator.userAgent) ? (
              <>
                <input
                  ref={cameraRef}
                  type="file"
                  accept="image/*"
                  capture="environment"
                  style={{ display: "none" }}
                  onChange={e => { const f = e.target.files?.[0]; if (!f) return; const r = new FileReader(); r.onload = ev => saveAvatar(ev.target.result); r.readAsDataURL(f); }}
                />
                <button
                  type="button"
                  onClick={() => cameraRef.current?.click()}
                  style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: 4, background: "rgba(16,185,129,.1)", border: "1px solid rgba(16,185,129,.2)", borderRadius: 7, padding: "6px 8px", cursor: "pointer", fontSize: ".72rem", color: "#6ee7b7", fontWeight: 600 }}>
                  <Camera size={14} strokeWidth={2} /> Camera
                </button>
              </>
            ) : (
              <button
                onClick={() => {
                  setShowAvatarPicker(false);
                  // Open webcam using getUserMedia inline
                  const modal = document.createElement("div");
                  modal.style.cssText = "position:fixed;inset:0;background:rgba(0,0,0,.85);z-index:2147483647;display:flex;align-items:center;justify-content:center;";
                  // Lucide's "camera" icon (svg path), inlined since this
                  // modal is raw DOM (innerHTML), outside React's render tree.
                  const cameraIconSvg = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-3px;margin-right:6px"><path d="M13.997 4a2 2 0 0 1 1.76 1.05l.486.9A2 2 0 0 0 18.003 7H20a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h1.997a2 2 0 0 0 1.759-1.048l.489-.904A2 2 0 0 1 10.004 4z"/><circle cx="12" cy="13" r="3"/></svg>';
                  modal.innerHTML = `<div style="background:#1e293b;border-radius:16px;padding:20px;max-width:420px;width:90%;text-align:center">
                    <p style="color:#f1f5f9;font-weight:700;margin-bottom:12px;display:flex;align-items:center;justify-content:center">${cameraIconSvg}Take a Photo</p>
                    <video id="avatarCamVideo" autoplay playsinline muted style="width:100%;border-radius:10px;background:#000;max-height:300px"></video>
                    <canvas id="avatarCamCanvas" style="display:none"></canvas>
                    <div style="display:flex;gap:8px;margin-top:12px">
                      <button id="avatarCamCapture" style="flex:2;padding:10px;border:none;border-radius:8px;background:#6366f1;color:#fff;font-weight:700;cursor:pointer;display:flex;align-items:center;justify-content:center">${cameraIconSvg}Capture</button>
                      <button id="avatarCamClose" style="flex:1;padding:10px;border:none;border-radius:8px;background:rgba(239,68,68,.2);color:#f87171;font-weight:700;cursor:pointer">Cancel</button>
                    </div>
                  </div>`;
                  document.body.appendChild(modal);
                  let camStream = null;
                  navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" }, audio: false })
                    .then(s => { camStream = s; const v = document.getElementById("avatarCamVideo"); if (v) v.srcObject = s; })
                    .catch(() => { alert("Camera not available."); document.body.removeChild(modal); });
                  document.getElementById("avatarCamCapture").onclick = () => {
                    const v = document.getElementById("avatarCamVideo");
                    const c = document.getElementById("avatarCamCanvas");
                    c.width = v.videoWidth; c.height = v.videoHeight;
                    c.getContext("2d").drawImage(v, 0, 0);
                    const dataUrl = c.toDataURL("image/jpeg", 0.85);
                    camStream?.getTracks().forEach(t => t.stop());
                    document.body.removeChild(modal);
                    saveAvatar(dataUrl);
                  };
                  document.getElementById("avatarCamClose").onclick = () => {
                    camStream?.getTracks().forEach(t => t.stop());
                    document.body.removeChild(modal);
                  };
                }}
                style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: 4, background: "rgba(16,185,129,.1)", border: "1px solid rgba(16,185,129,.2)", borderRadius: 7, padding: "6px 8px", cursor: "pointer", fontSize: ".72rem", color: "#6ee7b7", fontWeight: 600 }}>
                <Camera size={14} strokeWidth={2} /> Camera
              </button>
            )}
          </div>
          <button onClick={() => saveAvatar("")}
            style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "center", gap: 4, background: "rgba(239,68,68,.08)", border: "1px solid rgba(239,68,68,.2)", borderRadius: 7, padding: "6px 8px", cursor: "pointer", fontSize: ".72rem", color: "#f87171", fontWeight: 600, marginBottom: 6 }}>
            <Trash2 size={14} strokeWidth={2} /> Remove Avatar
          </button>
          <button onClick={() => setShowAvatarPicker(false)}
            style={{ width: "100%", background: "none", border: "none", cursor: "pointer", fontSize: ".72rem", color: "var(--muted)" }}>
            Cancel
          </button>
        </div>
      )}

      <nav className="sidebar-nav" aria-label="Main navigation">
        {(() => {
          // Group labels help both students and admin, who each have long
          // enough lists to benefit — teacher, sales, and parent still keep
          // the flat list they already rely on.
          const showGroups = user?.role === "student" || isAdmin;
          let lastGroup = null;

          return visiblePages.map((page) => {
            const Icon = page.icon;
            const showGroupLabel = showGroups && page.group && page.group !== lastGroup;
            lastGroup = page.group;

            return (
              <div key={page.key} className="sidebar-nav-item">
                {showGroupLabel && (
                  <p className="sidebar-group-label">{page.group}</p>
                )}
                <button
                  className={activePage === page.key ? "active" : ""}
                  aria-current={activePage === page.key ? "page" : undefined}
                  onClick={() => {
                    setActivePage(page.key);
                    setMobileNavOpen(false);
                  }}
                >
                  <span className="nav-icon">
                    <Icon size={19} strokeWidth={2.4} />
                  </span>

                  <span>{page.label}</span>
                </button>
              </div>
            );
          });
        })()}
      </nav>

      <div className="sidebar-footer">
        <button className="logout" onClick={onLogout}>
          <LogOut size={18} strokeWidth={2.4} />
          Logout
        </button>
      </div>
    </aside>
    </>
  );
}

export default Sidebar;
