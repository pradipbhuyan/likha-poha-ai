import { useMemo, useState } from "react";
import {
  BarChart3,
  BookOpenCheck,
  CheckCircle2,
  ClipboardCheck,
  GraduationCap,
  HelpCircle,
  LineChart,
  LockKeyhole,
  MessageCircleQuestion,
  PlayCircle,
  ShieldCheck,
  Sparkles,
  Trophy,
  Users,
  Video,
} from "lucide-react";

import appLogo from "../assets/AITutorLogo1.png";

const STUDENT_SCREENS = [
  {
    key: "login",
    label: "Login",
    icon: LockKeyhole,
    title: "Student sign-in",
    subtitle: "A focused entry point with role-aware routing after login.",
    stats: ["Grade 9", "CBSE + SOF", "AI Ready"],
    layout: "login",
  },
  {
    key: "dashboard",
    label: "Dashboard",
    icon: BarChart3,
    title: "Student learning dashboard",
    subtitle: "Progress, weak areas, next actions, and usage in one view.",
    stats: ["78% weekly progress", "4 active chapters", "2 weak areas"],
    layout: "dashboard",
  },
  {
    key: "lessons",
    label: "Lessons",
    icon: BookOpenCheck,
    title: "Step-wise AI lessons",
    subtitle: "Chapter-aware lessons with narration, examples, diagrams, and practice.",
    stats: ["Step 3 of 5", "RAG linked", "Visual aid ready"],
    layout: "lesson",
  },
  {
    key: "doubt",
    label: "Ask Doubt",
    icon: MessageCircleQuestion,
    title: "Ask chapter-specific doubts",
    subtitle: "Students get simple, structured answers backed by uploaded books.",
    stats: ["Science", "Motion", "Saved history"],
    layout: "chat",
  },
  {
    key: "mock",
    label: "Mock Test",
    icon: ClipboardCheck,
    title: "Mock test practice",
    subtitle: "Fresh questions, review, explanations, and performance scoring.",
    stats: ["20 questions", "35 minutes", "RAG based"],
    layout: "test",
  },
  {
    key: "learn",
    label: "Learn More",
    icon: Video,
    title: "Curated learning resources",
    subtitle: "Videos and references aligned to the selected chapter.",
    stats: ["3 videos", "2 resources", "Chapter aligned"],
    layout: "resources",
  },
  {
    key: "analytics",
    label: "Analytics",
    icon: LineChart,
    title: "Performance analytics",
    subtitle: "Subject trends, test history, and recommended revision areas.",
    stats: ["Maths +12%", "Science 86%", "English 74%"],
    layout: "analytics",
  },
  {
    key: "leaderboard",
    label: "Leaderboard",
    icon: Trophy,
    title: "Healthy competition",
    subtitle: "Rankings motivate students while preserving progress context.",
    stats: ["Rank 3", "920 points", "4 badges"],
    layout: "leaderboard",
  },
];

const PARENT_SCREENS = [
  {
    key: "login",
    label: "Login",
    icon: LockKeyhole,
    title: "Parent sign-in",
    subtitle: "Parents enter a controlled family workspace.",
    stats: ["Family account", "Plan visible", "Secure access"],
    layout: "login",
  },
  {
    key: "dashboard",
    label: "Dashboard",
    icon: Users,
    title: "Family learning center",
    subtitle: "Children, parents, progress, and plan details in one dashboard.",
    stats: ["2 children", "Premium SOF", "₹1,499/month"],
    layout: "parentDashboard",
  },
  {
    key: "lessons",
    label: "Lessons",
    icon: BookOpenCheck,
    title: "Lesson progress visibility",
    subtitle: "Parents can see what the child studied and where help is needed.",
    stats: ["11 lessons", "83% completion", "2 follow-ups"],
    layout: "parentLessons",
  },
  {
    key: "doubt",
    label: "Ask Doubt",
    icon: HelpCircle,
    title: "Doubt history overview",
    subtitle: "Parents can review the kinds of questions their child is asking.",
    stats: ["18 doubts", "5 saved", "3 SOF"],
    layout: "parentDoubts",
  },
  {
    key: "mock",
    label: "Mock Test",
    icon: ClipboardCheck,
    title: "Test performance review",
    subtitle: "Scores, attempts, and weak areas help parents guide revision.",
    stats: ["76% average", "4 tests", "1 retake due"],
    layout: "parentTests",
  },
  {
    key: "learn",
    label: "Learn More",
    icon: Video,
    title: "Recommended resources",
    subtitle: "Parents see chapter resources that support current learning goals.",
    stats: ["6 resources", "2 watched", "4 pending"],
    layout: "resources",
  },
  {
    key: "analytics",
    label: "Analytics",
    icon: LineChart,
    title: "Family analytics",
    subtitle: "Usage, progress, and consistency across children.",
    stats: ["92% consistency", "₹ AI usage tracked", "3 strengths"],
    layout: "analytics",
  },
  {
    key: "leaderboard",
    label: "Leaderboard",
    icon: Trophy,
    title: "Motivation view",
    subtitle: "Parents can see achievement without turning learning into pressure.",
    stats: ["4 badges", "Top 10%", "Weekly streak"],
    layout: "leaderboard",
  },
];

const TEACHER_SCREENS = [
  {
    key: "login",
    label: "Login",
    icon: LockKeyhole,
    title: "Teacher sign-in",
    subtitle: "Admin-created teacher accounts for schools and independent tutors.",
    stats: ["School view", "Assigned roster", "Secure"],
    layout: "login",
  },
  {
    key: "dashboard",
    label: "Dashboard",
    icon: GraduationCap,
    title: "Teacher classroom dashboard",
    subtitle: "Assigned students, progress, notes, and intervention signals.",
    stats: ["24 students", "5 need help", "8 notes"],
    layout: "teacherDashboard",
  },
  {
    key: "lessons",
    label: "Lessons",
    icon: BookOpenCheck,
    title: "Lesson coverage monitor",
    subtitle: "Teachers can see chapter coverage and student completion patterns.",
    stats: ["Motion", "68% complete", "4 lagging"],
    layout: "teacherLessons",
  },
  {
    key: "doubt",
    label: "Ask Doubt",
    icon: MessageCircleQuestion,
    title: "Common doubt patterns",
    subtitle: "Teachers identify recurring misconceptions across assigned students.",
    stats: ["12 doubts", "Force", "High priority"],
    layout: "teacherDoubts",
  },
  {
    key: "mock",
    label: "Mock Test",
    icon: ClipboardCheck,
    title: "Class test readiness",
    subtitle: "Mock scores and weak areas guide revision planning.",
    stats: ["71% class avg", "6 retakes", "2 topics weak"],
    layout: "teacherTests",
  },
  {
    key: "learn",
    label: "Learn More",
    icon: Video,
    title: "Resource planning",
    subtitle: "Teachers can recommend videos and resources for weak chapters.",
    stats: ["4 resources", "Motion", "Assigned"],
    layout: "resources",
  },
  {
    key: "analytics",
    label: "Analytics",
    icon: LineChart,
    title: "Class analytics",
    subtitle: "Student progress, usage, and weak-area trends for intervention.",
    stats: ["5 at risk", "9 improving", "3 top performers"],
    layout: "analytics",
  },
  {
    key: "leaderboard",
    label: "Leaderboard",
    icon: Trophy,
    title: "Class motivation",
    subtitle: "Leaderboard sample for schools that want gamified practice.",
    stats: ["Section A", "Top 5", "Weekly"],
    layout: "leaderboard",
  },
];

const DEMO_FLOWS = {
  student: {
    label: "Student",
    eyebrow: "Student Demo",
    title: "A guided study desk for every learner",
    subtitle:
      "Show the full journey from login to lessons, doubts, tests, resources, analytics, and leaderboard.",
    icon: BookOpenCheck,
    screens: STUDENT_SCREENS,
    highlights: [
      {
        icon: Sparkles,
        title: "Personalized lesson path",
        text: "Class, board, subject, chapter, narration style, and teacher persona adapt the lesson.",
      },
      {
        icon: MessageCircleQuestion,
        title: "Doubt history",
        text: "Students can ask contextual doubts and revisit answers later.",
      },
      {
        icon: ClipboardCheck,
        title: "Mock readiness",
        text: "Practice tests use uploaded content and explain every answer.",
      },
    ],
  },
  parent: {
    label: "Parent",
    eyebrow: "Parent Demo",
    title: "Clear visibility without classroom noise",
    subtitle:
      "Show how parents understand plan value, children, progress, tests, usage, and outcomes.",
    icon: Users,
    screens: PARENT_SCREENS,
    highlights: [
      {
        icon: BarChart3,
        title: "Family progress",
        text: "Parents see learning consistency, weak areas, and test performance.",
      },
      {
        icon: ShieldCheck,
        title: "Controlled access",
        text: "Subject and plan access can be configured per student.",
      },
      {
        icon: CheckCircle2,
        title: "Plan clarity",
        text: "Subscription value is visible before purchase or upgrade.",
      },
    ],
  },
  teacher: {
    label: "Teacher",
    eyebrow: "Teacher Demo",
    title: "A classroom view for schools and tutors",
    subtitle:
      "Show how schools and independent teachers monitor assigned students and plan interventions.",
    icon: GraduationCap,
    screens: TEACHER_SCREENS,
    highlights: [
      {
        icon: Users,
        title: "Assigned roster",
        text: "Teachers see only the students linked by admin.",
      },
      {
        icon: LineChart,
        title: "Intervention signals",
        text: "Progress and weak-area data help teachers support students early.",
      },
      {
        icon: ClipboardCheck,
        title: "Teacher notes",
        text: "Notes stay attached to students for structured follow-up.",
      },
    ],
  },
};

const ROLE_PROFILES = {
  student: { name: "Akshita", role: "student", initial: "A" },
  parent: { name: "Pradip", role: "parent", initial: "P" },
  teacher: { name: "Meera Teacher", role: "teacher", initial: "M" },
};

const NAV_LABELS = [
  "Dashboard",
  "Lessons",
  "Ask Doubt",
  "Mock Test",
  "Learn More",
  "Analytics",
  "Leaderboard",
];

function DemoMetric({ label, value }) {
  /** Render one compact metric used inside the sales demo mock screens. */
  return (
    <div className="sales-demo-mini-metric">
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function RealLoginPreview({ flowKey, screen, theme }) {
  /** Show a prospect-safe login screen that uses the real product logo. */
  const profile = ROLE_PROFILES[flowKey];

  return (
    <div className={`sales-real-login ${theme}`}>
      <section className="sales-real-login-panel">
        <img src={appLogo} alt="Likha Poha AI" />
        <p className="eyebrow">{screen.label}</p>
        <h4>{screen.title}</h4>
        <p>{screen.subtitle}</p>
        <label>
          Email or username
          <span>{profile.name.toLowerCase().replaceAll(" ", ".")}</span>
        </label>
        <label>
          Password
          <span>••••••••</span>
        </label>
        <button type="button">Sign in as {flowKey}</button>
      </section>
      <aside>
        <strong>AI Tutor</strong>
        <span>CBSE + SOF + Multi-board</span>
        <small>Demo data only</small>
      </aside>
    </div>
  );
}

function ScreenContent({ flowKey, screen }) {
  /** Render role/page-specific content inside a real app-style shell. */
  if (screen.layout === "lesson") {
    return (
      <div className="sales-real-two-column">
        <div className="sales-real-card">
          <p className="eyebrow">Learning Path</p>
          <h5>Select Lesson Setup</h5>
          <div className="sales-real-field">Grade 9</div>
          <div className="sales-real-field">SOF</div>
          <div className="sales-real-field">Maths Olympiad</div>
          <div className="sales-real-field">Number Systems</div>
          <div className="sales-real-progress"><span style={{ width: "64%" }} /></div>
        </div>
        <div className="sales-real-card feature">
          <p className="eyebrow">Step 3: Guided Example</p>
          <h5>Rational numbers as fractions</h5>
          <p>Convert 0.75 into p/q form, then practice two similar questions with AI checking.</p>
          <div className="sales-real-diagram">
            <span>Concept</span>
            <span>Example</span>
            <span>Practice</span>
          </div>
        </div>
      </div>
    );
  }

  if (screen.layout === "chat") {
    return (
      <div className="sales-real-card sales-real-chat-panel">
        <p className="eyebrow">Ask a follow-up</p>
        <div className="sales-real-chat user">Why is inertia higher for heavier objects?</div>
        <div className="sales-real-chat assistant">
          Inertia depends on mass. A heavier object resists change in motion more, so it needs more force to speed up, slow down, or change direction.
        </div>
        <div className="sales-real-actions">
          <span>Explain simply</span>
          <span>Give example</span>
          <span>Save to revision</span>
        </div>
      </div>
    );
  }

  if (screen.layout === "test") {
    return (
      <div className="sales-real-two-column">
        <div className="sales-real-card feature">
          <p className="eyebrow">Mock Test</p>
          <h5>Question 7 of 20</h5>
          <p>Which force keeps planets moving around the Sun?</p>
          <div className="sales-real-options">
            <span>Friction</span>
            <span className="correct">Gravity</span>
            <span>Magnetic force</span>
          </div>
        </div>
        <div className="sales-real-card">
          <h5>Review</h5>
          <DemoMetric label="Score preview" value="16/20" />
          <DemoMetric label="Weak area" value="Motion" />
        </div>
      </div>
    );
  }

  if (screen.layout === "resources") {
    return (
      <div className="sales-real-card">
        <p className="eyebrow">Learn More</p>
        <h5>Recommended resources</h5>
        {["Concept video: Osmosis", "NCERT reference notes", "SOF practice worksheet"].map((item) => (
          <div key={item} className="sales-real-resource">
            <PlayCircle size={18} />
            <span>{item}</span>
          </div>
        ))}
      </div>
    );
  }

  if (screen.layout === "analytics") {
    return (
      <div className="sales-real-card">
        <p className="eyebrow">Analytics</p>
        <h5>{screen.title}</h5>
        <div className="sales-real-bars">
          {[74, 88, 66, 92, 80, 71].map((height, index) => (
            <span key={`${height}-${index}`} style={{ height: `${height}%` }}>
              W{index + 1}
            </span>
          ))}
        </div>
        <div className="sales-real-actions">
          <span>Strong: Algebra</span>
          <span>Focus: Geometry</span>
        </div>
      </div>
    );
  }

  if (screen.layout === "leaderboard") {
    return (
      <div className="sales-real-card">
        <p className="eyebrow">Leaderboard</p>
        <h5>{screen.title}</h5>
        {["Akshita", "Rohan", "Shivam", "Maya"].map((name, index) => (
          <div key={name} className="sales-real-rank">
            <strong>#{index + 1}</strong>
            <span>{name}</span>
            <small>{980 - index * 45} pts</small>
          </div>
        ))}
      </div>
    );
  }

  const metrics = {
    student: [
      ["Weekly progress", "84%"],
      ["Lessons done", "12"],
      ["Doubts solved", "18"],
      ["Mock score", "76%"],
    ],
    parent: [
      ["Children", "2"],
      ["Avg score", "78%"],
      ["AI usage", "42%"],
      ["Plan", "Premium"],
    ],
    teacher: [
      ["Students", "24"],
      ["Avg score", "71%"],
      ["Need help", "5"],
      ["Notes", "8"],
    ],
  };

  return (
    <div className="sales-real-dashboard">
      <div className="sales-real-metrics">
        {metrics[flowKey].map(([label, value]) => (
          <DemoMetric key={label} label={label} value={value} />
        ))}
      </div>
      <div className="sales-real-card feature">
        <p className="eyebrow">Today</p>
        <h5>{screen.title}</h5>
        <p>{screen.subtitle}</p>
        <div className="sales-real-progress"><span style={{ width: "72%" }} /></div>
      </div>
    </div>
  );
}

function RealAppPreview({ flowKey, flow, screen, theme }) {
  /** Show the selected page inside a realistic app chrome based on product mockups. */
  const profile = ROLE_PROFILES[flowKey];

  if (screen.layout === "login") {
    return <RealLoginPreview flowKey={flowKey} screen={screen} theme={theme} />;
  }

  return (
    <div className={`sales-real-shell ${theme}`}>
      <aside className="sales-real-sidebar">
        <div className="sales-real-brand">
          <img src={appLogo} alt="Likha Poha AI" />
          <div>
            <strong>AI Tutor</strong>
            <span>CBSE + SOF</span>
          </div>
        </div>
        <div className="sales-real-profile">
          <b>{profile.initial}</b>
          <div>
            <strong>{profile.name}</strong>
            <span>{profile.role}</span>
          </div>
        </div>
        <nav>
          {NAV_LABELS.map((label) => (
            <span key={label} className={label === screen.label ? "active" : ""}>
              {label}
            </span>
          ))}
        </nav>
      </aside>
      <main className="sales-real-main">
        <header className="sales-real-header">
          <div>
            <p className="eyebrow">{flow.eyebrow}</p>
            <h4>{screen.title}</h4>
            <p>{screen.subtitle}</p>
          </div>
          <div className="sales-real-pills">
            <span>{theme === "dark" ? "Dark" : "Light"}</span>
            <span>AI Ready</span>
            <span>{flow.label}</span>
          </div>
        </header>
        <ScreenContent flowKey={flowKey} screen={screen} />
      </main>
    </div>
  );
}

function SalesDemoPage({ user }) {
  /** Presents safe, polished product demo screens for sales conversations. */
  const [activeFlow, setActiveFlow] = useState("student");
  const [activeScreenKey, setActiveScreenKey] = useState("login");
  const [previewTheme, setPreviewTheme] = useState("light");
  const flow = DEMO_FLOWS[activeFlow];
  const FlowIcon = flow.icon;
  const activeScreen = useMemo(
    () =>
      flow.screens.find((screen) => screen.key === activeScreenKey) ||
      flow.screens[0],
    [activeScreenKey, flow]
  );

  function chooseFlow(key) {
    /** Reset the screen path whenever the salesperson changes audience. */
    setActiveFlow(key);
    setActiveScreenKey("login");
  }

  return (
    <div className="premium-page sales-demo-page">
      <section className="premium-section sales-demo-hero">
        <div className="premium-header">
          <p className="eyebrow">Sales Demo Center</p>
          <h2>Prospect-ready product walkthrough</h2>
          <p>
            Use these rich demo screens for parent, school, and tutor
            conversations. They are presentation screens only, so no live
            student data is exposed while showing the product.
          </p>
        </div>

        <div className="sales-demo-presenter">
          <span>Presenter</span>
          <strong>{user?.username || "Sales Partner"}</strong>
        </div>
      </section>

      <section className="sales-demo-selector" aria-label="Demo audience">
        {Object.entries(DEMO_FLOWS).map(([key, item]) => {
          const ItemIcon = item.icon;

          return (
            <button
              key={key}
              type="button"
              className={activeFlow === key ? "active" : ""}
              onClick={() => chooseFlow(key)}
            >
              <ItemIcon size={20} />
              {item.label}
            </button>
          );
        })}
      </section>

      <section className="sales-demo-theme-switch" aria-label="Demo theme">
        {["light", "dark"].map((theme) => (
          <button
            key={theme}
            type="button"
            className={previewTheme === theme ? "active" : ""}
            onClick={() => setPreviewTheme(theme)}
          >
            {theme === "light" ? "Light preview" : "Dark preview"}
          </button>
        ))}
      </section>

      <section className="premium-section sales-demo-showcase">
        <div className="sales-demo-copy">
          <p className="eyebrow">{flow.eyebrow}</p>
          <h3>
            <FlowIcon size={30} />
            {flow.title}
          </h3>
          <p>{flow.subtitle}</p>

          <div className="sales-demo-stat-grid">
            {activeScreen.stats.map((text) => (
              <div key={text} className="sales-demo-stat">
                <strong>{text}</strong>
                <span>{activeScreen.label}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="sales-demo-device" aria-label={`${flow.label} demo preview`}>
          <div className="sales-demo-device-top">
            <span></span>
            <span></span>
            <span></span>
          </div>
          <div className="sales-demo-screen">
            <div className="sales-demo-screen-header">
              <div>
                <small>{activeScreen.label}</small>
                <h4>{activeScreen.title}</h4>
                <p>{activeScreen.subtitle}</p>
              </div>
              <span>{flow.label}</span>
            </div>
            <RealAppPreview
              flowKey={activeFlow}
              flow={flow}
              screen={activeScreen}
              theme={previewTheme}
            />
          </div>
        </div>
      </section>

      <section className="premium-section sales-demo-page-gallery">
        <div className="premium-header">
          <h3>Page-by-page demo path</h3>
          <p>
            Start from login, then open each page a prospect would naturally
            ask about during a walkthrough.
          </p>
        </div>

        <div className="sales-demo-screen-tabs">
          {flow.screens.map((screen) => {
            const ScreenIcon = screen.icon;

            return (
              <button
                key={screen.key}
                type="button"
                className={activeScreen.key === screen.key ? "active" : ""}
                onClick={() => setActiveScreenKey(screen.key)}
              >
                <ScreenIcon size={18} />
                {screen.label}
              </button>
            );
          })}
        </div>
      </section>

      <section className="sales-demo-highlight-grid">
        {flow.highlights.map((item) => {
          const HighlightIcon = item.icon;

          return (
            <article key={item.title} className="premium-card sales-demo-highlight">
              <div className="dashboard-stat-icon blue">
                <HighlightIcon size={22} />
              </div>
              <h4>{item.title}</h4>
              <p>{item.text}</p>
            </article>
          );
        })}
      </section>
    </div>
  );
}

export default SalesDemoPage;
