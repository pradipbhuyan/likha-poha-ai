import { useEffect, useState } from "react";
import logoImg from "../assets/AITutorLogo1.png";
import { BookOpen, MessageCircle, ClipboardList, Users, TrendingUp } from "lucide-react";
import "./LandingPage.css";

export default function LandingPage({ onShowLogin, onShowSignup }) {
  function handleCta(planKey) {
    if (onShowSignup) {
      onShowSignup(planKey);
    } else {
      onShowLogin();
    }
  }
  const [openFaq, setOpenFaq] = useState(null);
  const [contactEmail, setContactEmail] = useState("likhapohaai@gmail.com");

  function toggleFaq(i) { setOpenFaq(p => p === i ? null : i); }

  useEffect(() => {
    fetch("/api/payments/contact")
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data?.email) setContactEmail(data.email); })
      .catch(() => {});
  }, []);

  const faqs = [
    {
      q: "Which classes and boards are supported?",
      a: "Likha Poha AI supports Class 5 to Class 10 for CBSE across all core subjects — Science, Maths, English, Social Science, and Hindi."
    },
    {
      q: "Does the AI use real textbooks or make things up?",
      a: "Every lesson and doubt answer is grounded in uploaded NCERT textbooks using RAG technology. The AI cannot hallucinate chapter content — it is strictly textbook-aligned."
    },
    {
      q: "How many practice questions are available?",
      a: "Likha Poha AI has 70,000+ practice questions covering all chapters from Class 5 to Class 10 across CBSE subjects, available instantly for mock tests and practice."
    },
    {
      q: "Is there a mobile app?",
      a: "Likha Poha AI is a mobile-first progressive web app. It works perfectly on any phone browser — no app download needed. Add it to your home screen for an app-like experience."
    },
    {
      q: "Can I manage multiple children on the Parent Dashboard?",
      a: "Yes — with a Family Premium plan, you can manage up to 2 children from a single Parent Dashboard. Each child gets their own profile, progress tracking, and weak area reports."
    },
    {
      q: "What does the Parent Dashboard show?",
      a: "The Parent Dashboard provides real-time tracking of daily learning progress, mock test scores and score trends, and automatic Weak Area Alerts when a chapter hasn't been revised in several days. The Things To Do Tonight card shows specific revision tasks updated daily."
    },
    {
      q: "How do I add a child to my account?",
      a: "Adding a child takes less than 2 minutes. Log in as a Parent at likhapoha.in, click Parent Dashboard in the left sidebar, scroll to the Family Hub section, and click '+ Add Child'. Fill in the child's name, class (Class 5–10), and a password. Your child can then log in at likhapoha.in using their credentials."
    },
    {
      q: "How does the AI identify a child's weak areas?",
      a: "Likha Poha AI continuously analyses the student's mock test history, average scores, and subject-specific performance. When a student scores below threshold on a chapter-wise test, the platform automatically flags it as a Weak Area and displays an alert on both the Student Dashboard and the Parent Dashboard."
    },
    {
      q: "How do students use the Analytics Dashboard for revision?",
      a: "The Analytics Dashboard turns past test results into a targeted revision plan. Score trend graphs show whether performance is improving over time. Automatic Weak Area Alerts show students exactly what to study next — removing the guesswork from daily revision."
    },
    {
      q: "Are the AI lessons based on specific NCERT chapters?",
      a: "Yes — every AI lesson is explicitly grounded in uploaded NCERT textbooks, not generic internet content. Students select their class, subject, and exact chapter, and the AI breaks it into a multi-step learning path (Concept Introduction, Core Explanation, Worked Examples, Exam-Style Problems, Revision) strictly following the CBSE textbook."
    },
    {
      q: "What types of tests can students create in Mock Test Studio?",
      a: "Students can create customisable CBSE practice tests. They can set the subject, chapter, difficulty, number of questions, and time limit — simulating real exam conditions. Completed tests provide instant scoring and a performance tier (Olympiad Ready, Strong Foundation, Good Progress, or Revision Needed)."
    },
    {
      q: "Is the AI safe for children? Can students ask anything they want?",
      a: "Likha Poha AI includes a built-in Academic Guardrail that keeps every conversation strictly focused on CBSE curriculum topics. The guardrail automatically detects and blocks questions about current politics, news, offensive content, and any topic outside the academic scope. Children cannot use the platform to have inappropriate or off-topic conversations."
    },
    {
      q: "Does it auto-renew?",
      a: "No. Plans expire at the end of the period. There are no automatic charges. You choose when to pay again. Full details at likhapoha.in/refund-policy."
    },
  ];

  return (
    <div className="lp">
      <nav className="lp-nav">
        <div className="lp-logo"><img src={logoImg} alt="Likha Poha AI" /><span>Likha Poha AI</span></div>
        <div className="lp-nav-r">
          <button className="lp-btn-ghost" onClick={onShowLogin}>Login</button>
          <button className="lp-btn-cta" onClick={() => handleCta("free")}>Try for Free</button>
        </div>
      </nav>

      {/* Hero */}
      <div className="lp-hero">
        <div className="lp-badge">&#127470;&#127475; Built for India &middot; Class 5&ndash;10 &middot; CBSE</div>
        <h1>Every Child Deserves a<br /><span className="lp-gr">Personal Tutor</span></h1>
        <p>AI-powered CBSE lessons from NCERT textbooks, instant doubt solving, mock tests with 70,000+ questions, and a real-time Parent Dashboard &mdash; on any phone, any night.</p>
        <div className="lp-hcta">
          <button className="lp-bc" onClick={() => handleCta("free")}>&#128640; Try for Free</button>
          <a href="#features" className="lp-bol">See Features &rarr;</a>
        </div>
        <div className="lp-stats">
          <div className="lp-stat"><div className="lp-sn">70,000+</div><div className="lp-sl">Practice Questions</div></div>
          <div className="lp-stat"><div className="lp-sn">6</div><div className="lp-sl">Core Subjects</div></div>
          <div className="lp-stat"><div className="lp-sn">Class 5&ndash;10</div><div className="lp-sl">CBSE Coverage</div></div>
          <div className="lp-stat"><div className="lp-sn">&#8377;0</div><div className="lp-sl">To Start</div></div>
        </div>
      </div>

      {/* Problem / Solution */}
      <div className="lp-sf"><div className="lp-si">
        <div className="lp-sh"><div className="lp-ey">The Real Problem</div><h2>Why Students Struggle at Home</h2></div>
        <div className="lp-pvs">
          <div className="lp-pcard prob"><div className="lp-ptitle bad">The Problem</div>
            <div className="lp-pitem"><span>&#10007;</span> Tuition costs &#8377;2,000&ndash;8,000/month per subject</div>
            <div className="lp-pitem"><span>&#10007;</span> Parents cannot track what the child actually studied</div>
            <div className="lp-pitem"><span>&#10007;</span> Generic YouTube videos do not follow the CBSE syllabus</div>
            <div className="lp-pitem"><span>&#10007;</span> No personalised feedback on weak areas</div>
            <div className="lp-pitem"><span>&#10007;</span> Practice questions often do not match exam patterns</div>
            <div className="lp-pitem"><span>&#10007;</span> 11pm doubt. No tutor available.</div>
          </div>
          <div className="lp-pcard sol"><div className="lp-ptitle good">Likha Poha AI Solution</div>
            <div className="lp-pitem"><span>&#10003;</span> AI lesson for every NCERT chapter &mdash; from your textbook</div>
            <div className="lp-pitem"><span>&#10003;</span> Parent Dashboard shows daily progress and Weak Area Alerts</div>
            <div className="lp-pitem"><span>&#10003;</span> Things To Do Tonight &mdash; specific revision tasks, updated daily</div>
            <div className="lp-pitem"><span>&#10003;</span> 70,000+ CBSE practice questions with instant scoring</div>
            <div className="lp-pitem"><span>&#10003;</span> Ask Doubt at 11pm &mdash; NCERT textbook answer in seconds</div>
            <div className="lp-pitem"><span>&#10003;</span> Available on any phone &mdash; no app download needed</div>
          </div>
        </div>
      </div></div>

      {/* Product screenshots */}
      <div className="lp-sw" id="features">
        <div className="lp-sh"><div className="lp-ey">See It In Action</div><h2>What Students and Parents Experience</h2><p>Everything works on any phone &mdash; no app download needed</p></div>
        <div className="lp-demo">
          <div className="lp-dc"><div className="lp-dh"><div className="lp-di" style={{background:"rgba(124,58,237,.2)"}}>&#128218;</div>AI LESSON</div><img src="/screenshots/lesson.png" alt="AI Lesson — step-wise NCERT chapter" style={{width:"100%",display:"block"}} loading="lazy" /><div className="lp-dcap">Step-wise lesson grounded in your NCERT textbook</div></div>
          <div className="lp-dc"><div className="lp-dh"><div className="lp-di" style={{background:"rgba(6,182,212,.2)"}}>&#129514;</div>MOCK TEST</div><img src="/screenshots/mocktest.png" alt="Mock Test Studio — 70,000 CBSE questions" style={{width:"100%",display:"block"}} loading="lazy" /><div className="lp-dcap">Mock Test Studio &mdash; 70,000+ CBSE questions, instant scoring</div></div>
          <div className="lp-dc"><div className="lp-dh"><div className="lp-di" style={{background:"rgba(34,197,94,.2)"}}>&#128202;</div>PARENT DASHBOARD</div><img src="/screenshots/parent-dashboard.png" alt="Parent Dashboard — chapter-level visibility" style={{width:"100%",display:"block"}} loading="lazy" /><div className="lp-dcap">Parent Dashboard &mdash; chapter-level daily visibility</div></div>
        </div>
      </div>

      {/* Features grid */}
      <div className="lp-sf" id="features-detail"><div className="lp-si">
        <div className="lp-sh"><div className="lp-ey">Features</div><h2>Everything Your Child Needs to Succeed</h2></div>
        <div className="lp-fg">
          <div className="lp-fc"><div className="lp-fi" style={{background:"rgba(124,58,237,.15)"}}><BookOpen size={22} strokeWidth={2} /></div><h3>AI Lessons</h3><p>NCERT-grounded, step-wise lessons. Concept Introduction, Core Explanation, Worked Examples, Exam-Style Questions, and Quick Revision &mdash; for every chapter.</p></div>
          <div className="lp-fc"><div className="lp-fi" style={{background:"rgba(6,182,212,.15)"}}><MessageCircle size={22} strokeWidth={2} /></div><h3>Ask Doubt</h3><p>Type any doubt. Get the NCERT textbook answer in seconds &mdash; 24 hours, any night, any subject.</p></div>
          <div className="lp-fc"><div className="lp-fi" style={{background:"rgba(245,158,11,.15)"}}><ClipboardList size={22} strokeWidth={2} /></div><h3>Mock Test Studio</h3><p>70,000+ CBSE practice questions. Every chapter. Instant scoring. Performance tier: Olympiad Ready, Strong Foundation, Good Progress, or Revision Needed.</p></div>
          <div className="lp-fc"><div className="lp-fi" style={{background:"rgba(34,197,94,.15)"}}><Users size={22} strokeWidth={2} /></div><h3>Parent Dashboard</h3><p>Real-time daily visibility. Which chapter was studied. Weak Area Alerts. Things To Do Tonight. Score trends week by week.</p></div>
          <div className="lp-fc"><div className="lp-fi" style={{background:"rgba(99,102,241,.15)"}}><TrendingUp size={22} strokeWidth={2} /></div><h3>Analytics</h3><p>Score trend graphs. Chapter-level performance. See exactly which subjects are improving and which need revision.</p></div>
          <div className="lp-fc"><div className="lp-fi" style={{background:"rgba(139,92,246,.15)"}}><span style={{fontSize:"1.2rem"}}>&#127942;</span></div><h3>Leaderboard</h3><p>Class Leaderboard. Study streak. XP points. Rank moves when you actually study &mdash; not when you say you will.</p></div>
        </div>
      </div></div>

      {/* Pricing */}
      <div className="lp-sw" id="pricing">
        <div className="lp-sh"><div className="lp-ey">Simple Pricing</div><h2>Choose Your Plan</h2><p>Start free &middot; No hidden charges &middot; Plans expire at end of period</p></div>
        <div className="lp-pg">
          {/* Free Tier */}
          <div className="lp-prc">
            <div className="lp-prname">Free Tier</div>
            <div className="lp-pramount">&#8377;0<span> forever</span></div>
            <div className="lp-prdesc">Get started. No credit card required.</div>
            <div className="lp-prf">Limited daily access</div>
            <div className="lp-prf">AI Lessons</div>
            <div className="lp-prf">Ask Doubt</div>
            <div className="lp-prf">Mock Tests</div>
            <button className="lp-bpro lp-bpout" onClick={() => handleCta("free_tier")}>Try for Free</button>
          </div>
          {/* Premium Nano */}
          <div className="lp-prc">
            <div className="lp-prname">Premium Nano</div>
            <div className="lp-pramount">&#8377;99<span>/8 days</span></div>
            <div className="lp-prdesc">Experience the complete platform before committing to a monthly plan.</div>
            <div className="lp-prf">All CBSE subjects &middot; Class 5&ndash;10</div>
            <div className="lp-prf">AI Lessons &mdash; every chapter</div>
            <div className="lp-prf">Ask Doubt &mdash; 24/7</div>
            <div className="lp-prf">Mock Test Studio &mdash; 70,000+ questions</div>
            <div className="lp-prf">Parent Dashboard + Weak Area Alerts</div>
            <div className="lp-prf">Analytics</div>
            <div className="lp-prf">No auto-renewal</div>
            <button className="lp-bpro lp-bpout" onClick={() => handleCta("free")}>Start 8-Day Access</button>
          </div>
          {/* Premium */}
          <div className="lp-prc pop">
            <div className="lp-popb">&#11088; Most Popular</div>
            <div className="lp-prname">Premium</div>
            <div className="lp-pramount">&#8377;299<span>/month</span></div>
            <div className="lp-prdesc">Ideal for students preparing consistently throughout the academic year.</div>
            <div className="lp-prf">All CBSE subjects &middot; Class 5&ndash;10</div>
            <div className="lp-prf">AI Lessons &mdash; every chapter</div>
            <div className="lp-prf">Ask Doubt &mdash; 24/7</div>
            <div className="lp-prf">Mock Test Studio &mdash; 70,000+ questions</div>
            <div className="lp-prf">Parent Dashboard + Weak Area Alerts</div>
            <div className="lp-prf">Analytics & Leaderboard</div>
            <div className="lp-prf">Formula Sheet</div>
            <button className="lp-bpro lp-bpfill" onClick={() => handleCta("starter")}>Choose Premium</button>
          </div>
          {/* Family Premium */}
          <div className="lp-prc">
            <div className="lp-prname">Family Premium</div>
            <div className="lp-pramount">&#8377;499<span>/month</span></div>
            <div className="lp-prdesc">One subscription for families with up to two children.</div>
            <div className="lp-prf">All CBSE subjects &middot; Class 5&ndash;10</div>
            <div className="lp-prf">Up to 2 children</div>
            <div className="lp-prf">Separate progress per child</div>
            <div className="lp-prf">All Premium features for both children</div>
            <div className="lp-prf">One Parent Dashboard</div>
            <button className="lp-bpro lp-bpout" onClick={() => handleCta("family_premium")}>Get Family Premium</button>
          </div>
        </div>
        <p className="lp-prnote">No hidden charges &middot; Plans expire at end of period &middot; No automatic charges</p>
      </div>

      {/* FAQ */}
      <div className="lp-sf"><div className="lp-si">
        <div className="lp-sh"><h2>Frequently Asked Questions</h2></div>
        {faqs.map((faq, i) => (
          <div key={i} className={"lp-faq-item" + (openFaq === i ? " open" : "")}>
            <button className="lp-faq-q" onClick={() => toggleFaq(i)}>{faq.q}<span className="lp-faq-icon">+</span></button>
            <div className="lp-faq-a">{faq.a}</div>
          </div>
        ))}
      </div></div>

      {/* CTA section */}
      <div className="lp-ctasec">
        <h2>Start Your Child&rsquo;s AI Learning Journey Today</h2>
        <p>Free to start &middot; Any phone &middot; No app download needed</p>
        <button className="lp-bc" onClick={() => handleCta("free")} style={{display:"inline-flex"}}>&#128640; Try for Free</button>
        <p style={{marginTop:"16px",fontSize:".8rem",color:"#cbd5e1"}}>Free Tier: &#8377;0 &middot; Try full platform: &#8377;99 for 8 days</p>
      </div>

      {/* Google Sign-In disclosure — required by Google API Services User Data Policy */}
      <div style={{background:"rgba(15,23,42,.95)",borderTop:"1px solid #1e293b",padding:"36px 24px"}}>
        <div style={{maxWidth:720,margin:"0 auto",display:"flex",gap:18,alignItems:"flex-start"}}>
          <div style={{flexShrink:0,width:36,height:36,borderRadius:8,background:"#fff",display:"flex",alignItems:"center",justifyContent:"center",marginTop:2}}>
            <svg width="20" height="20" viewBox="0 0 48 48"><path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9 3.2l6.7-6.7C35.8 2.5 30.3 0 24 0 14.6 0 6.6 5.4 2.6 13.3l7.8 6C12.3 13.2 17.7 9.5 24 9.5z"/><path fill="#4285F4" d="M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v8.5h12.7c-.6 3-2.3 5.5-4.8 7.2l7.5 5.8c4.4-4 7.1-10 7.1-17z"/><path fill="#FBBC05" d="M10.4 28.7A14.5 14.5 0 0 1 9.5 24c0-1.6.3-3.2.9-4.7l-7.8-6A24 24 0 0 0 0 24c0 3.8.9 7.4 2.6 10.7l7.8-6z"/><path fill="#34A853" d="M24 48c6.2 0 11.5-2.1 15.4-5.6l-7.5-5.8c-2.1 1.4-4.8 2.2-7.9 2.2-6.3 0-11.6-3.7-13.6-9l-7.8 6C6.6 42.6 14.6 48 24 48z"/></svg>
          </div>
          <div>
            <p style={{fontSize:".8rem",fontWeight:800,color:"#f8fafc",marginBottom:6,textTransform:"uppercase",letterSpacing:".06em"}}>Google Sign-In & Data Usage</p>
            <p style={{fontSize:".82rem",color:"#94a3b8",lineHeight:1.7,margin:0}}>
              Likha Poha AI uses Google Sign-In <strong style={{color:"#cbd5e1"}}>only to securely authenticate users</strong>. We collect only your name, email address, and profile picture.
            </p>
            <p style={{fontSize:".82rem",color:"#94a3b8",lineHeight:1.7,margin:"8px 0 0"}}>
              Likha Poha AI <strong style={{color:"#f87171"}}>does not access</strong> Gmail, Google Drive, Google Calendar, Google Contacts, or any other Google services.
              We <strong style={{color:"#f87171"}}>do not sell or share</strong> Google user data for advertising or marketing.
              See our <a href="/privacy-policy" style={{color:"#93c5fd"}}>Privacy Policy</a> for full details.
            </p>
          </div>
        </div>
      </div>

      <footer className="lp-footer">
        <p style={{fontSize:"1rem",fontWeight:700,marginBottom:"12px"}}>Likha Poha AI</p>
        <p>AI-Powered CBSE Tutor &middot; Class 5&ndash;10</p>
        <div style={{marginTop:"16px"}}>
          <a href="#">Home</a>
          <a href="#features">Features</a>
          <a href="#pricing">Pricing</a>
          <a href="/blog">Blog</a>
          <a href={`mailto:${contactEmail}`}>Contact</a>
          <a href="/refund-policy">Refund Policy</a>
          <a href="/privacy-policy">Privacy Policy</a>
          <a href="/terms-of-service">Terms of Service</a>
        </div>
        <p style={{marginTop:"20px"}}>&copy; 2026 Likha Poha AI &middot; Made with &#10084; in India</p>
      </footer>
    </div>
  );
}
