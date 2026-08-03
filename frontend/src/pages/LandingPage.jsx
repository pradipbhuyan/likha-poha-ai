import { useEffect, useState } from "react";
import logoImg from "../assets/AITutorLogo1.png";
import { BookOpen, MessageCircle, ClipboardList, Users, TrendingUp, Zap, Leaf, ShieldCheck, Globe, GraduationCap, HelpCircle, BarChart2, Trophy, Award, Target, Monitor, FlaskConical, Landmark, Star, Heart, Calculator, Languages, Headphones } from "lucide-react";
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
    { q: "Which classes and boards are supported?", a: "LikhaPoha AI supports Grade 5 to Grade 12 for CBSE. Grade 5–10 covers Science, Maths, English, Social Science, and Hindi. Grade 11–12 adds Physics, Chemistry, Mathematics, Biology, Accountancy, Economics, and Business Studies — plus an Exam Prep Center for JEE Main, NEET UG, CUET UG, SAT, IELTS, and TOEFL iBT." },
    { q: "What is the Exam Prep Center for Grade 11 & 12?", a: "The Exam Prep Center covers six exams: JEE Main, NEET UG, and CUET UG with an NTA-style simulator, curated MCQ question bank, subject-wise topic priorities, and simulated full-length tests with a floating countdown timer and question palette — exactly like the real exam interface. It also covers SAT, IELTS, and TOEFL iBT for students planning to study abroad, with exam-authentic practice for each format. It is included in the Premium plan at no extra cost." },
    { q: "Does the AI use real textbooks or make things up?", a: "Every lesson and doubt answer is grounded in uploaded NCERT textbooks using RAG technology. The AI cannot hallucinate chapter content — it is strictly textbook-aligned." },
    { q: "How many practice questions are available?", a: "LikhaPoha AI has 140,000+ practice questions covering all chapters from Grade 5 to Grade 12 across CBSE subjects — including question banks for JEE Main, NEET UG, CUET UG, SAT, IELTS, and TOEFL iBT for Grade 11 & 12." },
    { q: "Is there a mobile app?", a: "LikhaPoha AI is a mobile-first progressive web app. It works perfectly on any phone browser — no app download needed. Add it to your home screen for an app-like experience." },
    { q: "Can I manage multiple children on the Parent Dashboard?", a: "Yes — the Parent Dashboard includes a Family Learning Center where you can manage multiple children from one unified dashboard. Simply click the '+ Add Child' button to add another child and track their progress, test performance, and weak areas separately." },
    { q: "What does the Parent Dashboard show?", a: "The Parent Dashboard acts as a central Family Learning Center. It provides real-time tracking of daily learning progress, mock test scores and score trends, AI usage, and automatic weak-area alerts when a child is struggling. It also lets parents add children and manage subscription plans." },
    {
      q: "How do I add a child to my account?",
      a: "Adding a child takes less than 2 minutes. Step 1 — Log in as a Parent at likhapoha.in. Step 2 — Click Parent Dashboard in the left sidebar. Step 3 — In the Your Children section, click '+ Add Child'. Step 4 — Fill in the details: child's name (required), email (optional — leave blank if they have no email), child's class (Grade 5–10), and a password you will share with them. Step 5 — Click 'Add Child' to create the account. A confirmation screen will show the username and password you can share directly with your child. Your child can then log in at likhapoha.in using their username or email + password. You can add up to 2 children under one Family Premium plan."
    },
    { q: "How do I manage multiple children on one account?", a: "With the Family Premium plan, you can manage up to 2 children from a single Parent Dashboard. Add each child by clicking '+ Add Child' in your dashboard. Each child gets their own profile, progress tracking, and weak area reports visible to you." },
    { q: "How does the AI identify a child's weak areas?", a: "After each mock test, LikhaPoha AI evaluates the student's performance chapter by chapter. Chapters where a student is struggling are flagged as weak areas and shown as alerts on both the Student Dashboard and the Parent Dashboard, so revision time goes to the topics that need it most." },
    { q: "How do students use the Analytics Dashboard for revision?", a: "The Analytics Dashboard turns past test results into a targeted revision plan. Score trend graphs show whether performance is improving over time. Subject performance heatmaps highlight which subjects need more focus. Automatic weak area alerts are combined to show students exactly what to study next — removing the guesswork from daily revision." },
    { q: "How do score trend graphs help with revision?", a: "Score trend graphs show a visual timeline of your mock test performance over time, making it easy to see at a glance whether your average scores are improving with practice. This helps you gauge if your current revision is working or if you need to shift focus to different subjects." },
    { q: "Are the AI lessons based on specific NCERT chapters?", a: "Yes — every AI lesson is explicitly grounded in uploaded NCERT textbooks, not generic internet content. Students select their grade, subject, and exact chapter, and the AI breaks it into a multi-step learning path (concept introduction, core explanation, worked examples, exam problems, revision) strictly following the CBSE textbook." },
    { q: "What types of tests can students create with Mock Tests?", a: "Students can create highly customizable CBSE practice tests including class tests, mid-terms, and full mock tests. They can set the subject, chapter, difficulty, number of questions, time limit, and toggle negative marking — simulating real exam conditions. Completed tests provide instant scoring and a guided revision plan." },
    { q: "What resources are in the Learn More library?", a: "The Learn More library offers curated free resources hand-picked for each specific chapter — including NCERT articles, topic-specific YouTube video links, and open references. Students select their grade, subject, and chapter to discover materials tailored exactly to what they are studying." },
    { q: "Is the AI safe for children? Can students ask anything they want?", a: "LikhaPoha AI includes a built-in Academic Guardrail that keeps conversations focused on CBSE curriculum topics. It automatically detects and blocks questions about current politics, news, election results, live sports scores, and stock or market prices — instantly redirecting the student back to their studies. Parents can be confident that doubt-solving and lessons stay focused on academics, not current-affairs or off-topic chatter." },
  ];
  const missionCards = [
    { icon: <BookOpen size={20} strokeWidth={2}/>, t: "Strictly NCERT-grounded", d: "No hallucinations — only textbook facts" },
    { icon: <ShieldCheck size={20} strokeWidth={2}/>, t: "Safe for children", d: "Academic guardrail blocks off-topic content" },
    { icon: <Globe size={20} strokeWidth={2}/>, t: "Free to start", d: "Core platform is free. Upgrade to Premium anytime for full access." },
    { icon: <GraduationCap size={20} strokeWidth={2}/>, t: "All grades covered", d: "Grade 5 through 12 + JEE, NEET, CUET, SAT, IELTS, TOEFL" },
  ];
  const examPrepCards = [
    { icon: <Monitor size={24} strokeWidth={2}/>, color: "#6366f1", title: "JEE Main Simulator", desc: "NTA-style interface — one question at a time, floating countdown timer, question palette, Mark & Next, basic calculator. Physics, Chemistry, Mathematics." },
    { icon: <FlaskConical size={24} strokeWidth={2}/>, color: "#10b981", title: "NEET UG Prep", desc: "Physics, Chemistry, Biology with NCERT-exact terminology. Subject-wise topic priority cards showing weightage and key subtopics." },
    { icon: <Landmark size={24} strokeWidth={2}/>, color: "#f59e0b", title: "CUET UG Prep", desc: "All streams — Science, Commerce, Humanities. English, General Test, and domain subjects with curated practice questions." },
    { icon: <Calculator size={24} strokeWidth={2}/>, color: "#3b82f6", title: "Digital SAT Prep", desc: "Adaptive-format practice for Reading & Writing and Math. Accepted by 1,900+ US universities. No negative marking." },
    { icon: <Languages size={24} strokeWidth={2}/>, color: "#8b5cf6", title: "IELTS Academic Prep", desc: "Listening, Reading, Writing & Speaking practice with band-score guidance for university admissions worldwide." },
    { icon: <Headphones size={24} strokeWidth={2}/>, color: "#06b6d4", title: "TOEFL iBT Prep", desc: "Authentic academic passages and lecture-style listening practice for US and global university admissions." },
  ];
  return (
    <div className="lp">
      {/* Non-sticky anchor target for the footer "Home" link — putting id="home"
          directly on the sticky nav breaks native anchor-scroll, since a
          stuck element's getBoundingClientRect().top is already 0. */}
      <div id="home" style={{ position: "absolute" }} aria-hidden="true" />
      <nav className="lp-nav">
        <div className="lp-logo"><img src={logoImg} alt="LikhaPoha AI" /><span>LikhaPoha AI</span></div>
        <div className="lp-nav-links">
          <a href="#features">Features</a>
          <a href="#pricing">Pricing</a>
          <a href="#faq">FAQ</a>
        </div>
        <div className="lp-nav-r">
          <button className="lp-btn-ghost" onClick={onShowLogin}>Login</button>
          <button className="lp-btn-cta" onClick={() => handleCta("free")}>Try for Free</button>
        </div>
      </nav>
      <div className="lp-hero">
        <div className="lp-badge">&#127470;&#127475; Built for India &middot; Grade 5&ndash;12 &middot; CBSE &middot; JEE &middot; NEET &middot; CUET &middot; SAT &middot; IELTS &middot; TOEFL</div>
        <h1>Every Child Deserves a<br /><span className="lp-gr">Personal AI Tutor</span></h1>
        <p>NCERT-grounded lessons, instant doubt solving, Grade 11&ndash;12 competitive exam prep, and real-time parent insights &mdash; Grade 5 to Grade 12, anytime, anywhere.</p>
        <div className="lp-hcta">
          <button className="lp-bc" onClick={() => handleCta("free")} style={{display:"inline-flex",alignItems:"center",gap:8}}><Zap size={18} strokeWidth={2.5} /> Try for Free</button>
          <a href="#features" className="lp-bol">See Features &rarr;</a>
        </div>
        <div className="lp-stats">
          <div className="lp-stat"><div className="lp-sn">900+</div><div className="lp-sl">Chapters (Gr 5&ndash;12)</div></div>
          <div className="lp-stat"><div className="lp-sn">8</div><div className="lp-sl">Grades (5&ndash;12)</div></div>
          <div className="lp-stat"><div className="lp-sn">12+</div><div className="lp-sl">Subjects</div></div>
          <div className="lp-stat"><div className="lp-sn">140,000+</div><div className="lp-sl">Practice Questions</div></div>
        </div>
      </div>
      {/* AI for Good */}
      <div style={{background:"linear-gradient(135deg,rgba(16,185,129,.08),rgba(99,102,241,.05))",borderTop:"1px solid rgba(16,185,129,.2)",borderBottom:"1px solid rgba(16,185,129,.15)",padding:"28px 20px",textAlign:"center"}}>
        <div style={{maxWidth:860,margin:"0 auto"}}>
          <div style={{fontSize:".68rem",fontWeight:800,textTransform:"uppercase",letterSpacing:".1em",color:"#10b981",marginBottom:8}}>Our Mission</div>
          <h2 style={{fontSize:"1.3rem",fontWeight:900,margin:"0 0 10px",display:"flex",alignItems:"center",justifyContent:"center",gap:8}}><Leaf size={20} color="#10b981" strokeWidth={2} /> AI for Good &mdash; Bridging India&rsquo;s Education Gap</h2>
          <p style={{fontSize:".9rem",color:"var(--muted,#94a3b8)",maxWidth:660,margin:"0 auto 18px",lineHeight:1.7}}>Quality education should not depend on how much a family can afford. LikhaPoha AI uses <strong>responsible AI</strong> to give every Indian student &mdash; from Class 5 to Class 12 &mdash; personalised, textbook-grounded learning previously available only to students who could afford private tutors.</p>
          <div style={{display:"flex",gap:14,flexWrap:"wrap",justifyContent:"center"}}>
            {missionCards.map(f=>(
              <div key={f.t} style={{background:"rgba(16,185,129,.06)",border:"1px solid rgba(16,185,129,.15)",borderRadius:10,padding:"12px 16px",flex:"1 1 160px",maxWidth:210}}>
                <div style={{display:"flex",justifyContent:"center",marginBottom:6,color:"#10b981"}}>{f.icon}</div>
                <div style={{fontWeight:700,fontSize:".8rem",marginBottom:2}}>{f.t}</div>
                <div style={{fontSize:".7rem",color:"var(--muted,#94a3b8)"}}>{f.d}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="lp-sf"><div className="lp-si">
        <div className="lp-sh"><div className="lp-ey">The Real Problem</div><h2>Why Students Struggle at Home</h2></div>
        <div className="lp-pvs">
          {/* Problem column */}
          <div className="lp-pcard prob"><div className="lp-ptitle bad">The Problem</div>
            <div className="lp-pitem"><span>&#10007;</span> Tuition is expensive &mdash; &#8377;2,000&ndash;8,000/month per subject</div>
            <div className="lp-pitem"><span>&#10007;</span> Parents cannot track what the child actually studied</div>
            <div className="lp-pitem"><span>&#10007;</span> Generic YouTube videos do not follow the CBSE syllabus</div>
            <div className="lp-pitem"><span>&#10007;</span> No personalised feedback on weak areas</div>
            <div className="lp-pitem"><span>&#10007;</span> Practice questions often do not match actual exam patterns</div>
            <div className="lp-pitem"><span>&#10007;</span> Students lose motivation when they don&rsquo;t understand concepts immediately</div>
            <div className="lp-pitem"><span>&#10007;</span> Teachers cannot provide one-on-one attention to every child</div>
          </div>
          {/* Solution column */}
          <div className="lp-pcard sol"><div className="lp-ptitle good">LikhaPoha AI Solution</div>
            <div className="lp-pitem"><span>&#10003;</span> AI lesson for every chapter &mdash; instant and accessible</div>
            <div className="lp-pitem"><span>&#10003;</span> Parent dashboard shows daily progress and weak areas</div>
            <div className="lp-pitem"><span>&#10003;</span> Lessons grounded in uploaded NCERT textbooks</div>
            <div className="lp-pitem"><span>&#10003;</span> Smart evaluation automatically identifies revision topics</div>
            <div className="lp-pitem"><span>&#10003;</span> Personalised learning path based on each student&rsquo;s performance</div>
            <div className="lp-pitem"><span>&#10003;</span> CBSE-aligned practice questions and mock tests</div>
            <div className="lp-pitem"><span>&#10003;</span> Available 24&times;7 &mdash; learn anytime, anywhere</div>
            <div className="lp-pitem"><span>&#10003;</span> Instant doubt-solving with AI tutor support</div>
          </div>
        </div>

        {/* Results grid */}
        <div style={{marginTop:"28px",marginBottom:"28px"}}>
          <div className="lp-ey" style={{marginBottom:"14px"}}>Results for Students & Parents</div>
          <div className="lp-results">
            <div className="lp-rcard"><span className="lp-ri"><TrendingUp size={16} strokeWidth={2.5} /></span> Better exam preparation through <strong>targeted revision</strong></div>
            <div className="lp-rcard"><span className="lp-ri"><TrendingUp size={16} strokeWidth={2.5} /></span> Faster improvement in <strong>weak subjects</strong></div>
            <div className="lp-rcard"><span className="lp-ri"><TrendingUp size={16} strokeWidth={2.5} /></span> Increased learning <strong>confidence and engagement</strong></div>
            <div className="lp-rcard"><span className="lp-ri"><TrendingUp size={16} strokeWidth={2.5} /></span> Reduced dependence on <strong>costly tuition classes</strong></div>
            <div className="lp-rcard"><span className="lp-ri"><TrendingUp size={16} strokeWidth={2.5} /></span> Complete visibility for parents on <strong>learning progress</strong></div>
            <div className="lp-rcard"><span className="lp-ri"><TrendingUp size={16} strokeWidth={2.5} /></span> <strong>Personalised</strong> learning experience for every child</div>
          </div>
        </div>

        {/* Closing statement */}
        <div className="lp-closing">
          <p>&ldquo;Every child deserves a personal tutor. <strong>LikhaPoha AI makes high-quality,
          syllabus-aligned learning accessible to every student</strong> &mdash; anytime, anywhere,
          at minimal cost.&rdquo;</p>
        </div>

      </div></div>
      <div className="lp-sw">
        <div className="lp-sh"><div className="lp-ey">See It In Action</div><h2>A Glimpse of What Students Experience Daily</h2><p>Everything works on phone &mdash; no app download needed</p></div>
        <div className="lp-demo">
          <div className="lp-dc"><div className="lp-dh"><span className="lp-dh-dots"><span></span><span></span><span></span></span><div className="lp-di" style={{background:"rgba(124,58,237,.2)"}}><BookOpen size={16} strokeWidth={2}/></div>AI LESSON</div><img src="/screenshots/S05-lesson-content.png" alt="AI Lesson" style={{width:"100%",display:"block"}} loading="lazy" /><div className="lp-dcap">Step-wise chapter lesson grounded in your NCERT textbook</div></div>
          <div className="lp-dc"><div className="lp-dh"><span className="lp-dh-dots"><span></span><span></span><span></span></span><div className="lp-di" style={{background:"rgba(6,182,212,.2)"}}><ClipboardList size={16} strokeWidth={2}/></div>MOCK TEST</div><img src="/screenshots/S07-mock-test-question.png" alt="Mock Test" style={{width:"100%",display:"block"}} loading="lazy" /><div className="lp-dcap">CBSE mock tests with instant scoring and AI explanations</div></div>
          <div className="lp-dc"><div className="lp-dh"><span className="lp-dh-dots"><span></span><span></span><span></span></span><div className="lp-di" style={{background:"rgba(16,185,129,.2)"}}><Users size={16} strokeWidth={2}/></div>PARENT DASHBOARD</div><img src="/screenshots/S13-parent-dashboard-top.png" alt="Parent Dashboard" style={{width:"100%",display:"block"}} loading="lazy" /><div className="lp-dcap">Real-time progress, score trends and weak area alerts for parents</div></div>
        </div>
      </div>
      <div className="lp-sf" id="features"><div className="lp-si">
        <div className="lp-sh"><div className="lp-ey">Everything You Need</div><h2>Complete Study Toolkit for CBSE</h2><p>Powerful AI tools designed for Indian students</p></div>
        <div className="lp-fg">
          <div>
            <div className="lp-fc" style={{background:"linear-gradient(180deg,rgba(124,58,237,.05),transparent 60%),#0f172a",borderColor:"rgba(124,58,237,.25)"}}><div className="lp-fi" style={{background:"rgba(124,58,237,.15)"}}><BookOpen size={22} strokeWidth={2} /></div><h3>Step-wise AI Lessons</h3><p>4&ndash;6 focused steps per chapter &mdash; Concept intro, Core explanation, Worked examples, Exam-style problems, Revision.</p></div>
            <div className="lp-fc" style={{background:"linear-gradient(180deg,rgba(16,185,129,.05),transparent 60%),#0f172a",borderColor:"rgba(16,185,129,.25)"}}><div className="lp-fi" style={{background:"rgba(16,185,129,.15)"}}><MessageCircle size={22} strokeWidth={2} /></div><h3>Instant Doubt Solving</h3><p>Ask any chapter question. AI answers from your actual NCERT textbook &mdash; not generic internet content.</p></div>
            <div className="lp-fc" style={{background:"linear-gradient(180deg,rgba(245,158,11,.05),transparent 60%),#0f172a",borderColor:"rgba(245,158,11,.25)"}}><div className="lp-fi" style={{background:"rgba(245,158,11,.15)"}}><ClipboardList size={22} strokeWidth={2} /></div><h3>Mock Tests and Question Bank</h3><p>CBSE class tests, mid-terms and full mock tests across all grades. 140,000+ practice questions — Grade 5 to Grade 12.</p></div>
            <div className="lp-fc" style={{background:"linear-gradient(180deg,rgba(239,68,68,.05),transparent 60%),#0f172a",borderColor:"rgba(239,68,68,.25)"}}><div className="lp-fi" style={{background:"rgba(239,68,68,.15)"}}><Users size={22} strokeWidth={2} /></div><h3>Parent Dashboard</h3><p>Track daily study time, test scores, weak area alerts, and AI usage. Two children per family account.</p></div>
          </div>
          <div style={{display:"flex",flexDirection:"column",gap:"16px"}}>
            <div className="lp-dc"><div className="lp-dh"><span className="lp-dh-dots"><span></span><span></span><span></span></span><div className="lp-di" style={{background:"rgba(16,185,129,.2)"}}><HelpCircle size={16} strokeWidth={2}/></div>INSTANT DOUBT SOLVING</div><img src="/screenshots/S06-ask-doubt-answer.png" alt="Doubt Solving" style={{width:"100%",display:"block"}} loading="lazy" /></div>
            <div className="lp-dc"><div className="lp-dh"><span className="lp-dh-dots"><span></span><span></span><span></span></span><div className="lp-di" style={{background:"rgba(99,102,241,.2)"}}><BarChart2 size={16} strokeWidth={2}/></div>STUDENT ANALYTICS</div><img src="/screenshots/S11-analytics-top.png" alt="Student Analytics" style={{width:"100%",display:"block"}} loading="lazy" /></div>
          </div>
        </div>
      </div></div>
      <div className="lp-sf lp-gamified"><div className="lp-si">
        <div className="lp-sh"><div className="lp-ey">Kids Love It</div><h2>Gamified Learning Dashboard</h2><p>Badges, leaderboards and achievement streaks keep students motivated every day</p></div>
        <div className="lp-2col">
          <div className="lp-dc"><div className="lp-dh"><span className="lp-dh-dots"><span></span><span></span><span></span></span><div className="lp-di" style={{background:"rgba(245,158,11,.2)"}}><Trophy size={16} strokeWidth={2}/></div>ACHIEVEMENTS AND BADGES</div><img src="/screenshots/S04-dash-xp-streak.png" alt="Gamified Dashboard" style={{width:"100%",display:"block"}} loading="lazy" /></div>
          <div className="lp-dc"><div className="lp-dh"><span className="lp-dh-dots"><span></span><span></span><span></span></span><div className="lp-di" style={{background:"rgba(99,102,241,.2)"}}><Award size={16} strokeWidth={2}/></div>CLASS LEADERBOARD</div><img src="/screenshots/S12-leaderboard.png" alt="Leaderboard" style={{width:"100%",display:"block"}} loading="lazy" /></div>
        </div>
      </div></div>
      {/* Exam Prep Center — Grade 11 & 12 */}
      <div className="lp-sw" style={{background:"linear-gradient(135deg,rgba(99,102,241,.06),rgba(139,92,246,.04))"}}>
        <div className="lp-sh"><div className="lp-ey" style={{color:"#8b5cf6"}}>Grade 11 & 12 &mdash; New!</div><h2 style={{display:"flex",alignItems:"center",justifyContent:"center",gap:8}}><Target size={22} strokeWidth={2}/> Exam Prep Center</h2><p>JEE Main, NEET UG, CUET UG, SAT, IELTS & TOEFL iBT — curated question banks and exam-authentic simulators for Indian competitive exams and global study-abroad tests, all in one place.</p></div>
        <div className="lp-examgrid" style={{maxWidth:900,margin:"0 auto 8px"}}>
          {examPrepCards.map(f=>(
            <div key={f.title} style={{background:"#1e293b",border:"1px solid "+f.color+"44",borderRadius:12,padding:"18px 16px"}}>
              <div style={{marginBottom:10,color:f.color}}>{f.icon}</div>
              <div style={{fontWeight:800,fontSize:".9rem",color:f.color,marginBottom:6}}>{f.title}</div>
              <div style={{fontSize:".78rem",color:"#94a3b8",lineHeight:1.6}}>{f.desc}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="lp-sw" id="pricing">
        <div className="lp-sh"><div className="lp-ey">Simple Pricing</div><h2>Choose Your Plan</h2><p>Start free &middot; No hidden charges</p></div>
        <div className="lp-pg">
          <div className="lp-prc pop"><div className="lp-popb" style={{display:"flex",alignItems:"center",justifyContent:"center",gap:5}}><Star size={13} strokeWidth={2} fill="currentColor"/> Most Popular</div><div className="lp-prname">Premium</div><div className="lp-pramount">&#8377;299<span>/month</span></div><div className="lp-prdesc">Everything you need for serious CBSE exam prep — unlimited AI access every month.</div><div className="lp-prf">All CBSE subjects &middot; All grades</div><div className="lp-prf">Unlimited AI lessons, doubts & mock tests</div><div className="lp-prf">Exemplar Research & Lessons</div><div className="lp-prf">Formula & Concepts library</div><div className="lp-prf">10 Years of Board Papers with answers</div><div className="lp-prf">Learn More curated video library</div><div className="lp-prf">Parent dashboard + alerts</div><div className="lp-prf">Priority support</div><button className="lp-bpro lp-bpfill" onClick={() => handleCta("starter")}>Choose Premium</button></div>
          <div className="lp-prc"><div className="lp-prname">Family Premium</div><div className="lp-pramount">&#8377;499<span>/month</span></div><div className="lp-prsave">Save &#8377;99/month vs. 2 separate Premium plans</div><div className="lp-prdesc">Everything in Premium for up to 2 children — one shared family plan.</div><div className="lp-prf">Everything in Premium</div><div className="lp-prf">Up to 2 children with separate progress</div><div className="lp-prf">Exemplar Research & Lessons</div><div className="lp-prf">Formula & Concepts library</div><div className="lp-prf">10 Years of Board Papers with answers</div><div className="lp-prf">Learn More curated video library</div><div className="lp-prf">Parent dashboard + analytics</div><div className="lp-prf">Family learning management</div><button className="lp-bpro lp-bpout" onClick={() => handleCta("family_premium")}>Get Family Premium</button></div>
        </div>
        <p className="lp-prnote">No hidden charges &middot; Plans expire at end of period</p>
      </div>
      {/* Testimonials + score improvements hidden until we have real customer feedback
      <div className="lp-sf"><div className="lp-si">
        <div className="lp-sh"><div className="lp-ey">What Families Say</div><h2>Loved by Students and Parents Across India</h2><p>Join hundreds of families already learning smarter</p></div>
        <div className="lp-tgrid">
          <div className="lp-tc"><div className="lp-ttop"><div className="lp-tav">&#128103;</div><div><div className="lp-tname">Priya Kapoor</div><div className="lp-trole">Class 9 Student</div><div className="lp-tsch">DPS, New Delhi</div></div></div><div className="lp-tquote">The step-wise lessons are amazing. I used to spend 2 hours per chapter &mdash; now it takes 30 minutes and I actually understand it.</div><div className="lp-stars">&#9733;&#9733;&#9733;&#9733;&#9733;</div></div>
          <div className="lp-tc"><div className="lp-ttop"><div className="lp-tav">&#128104;</div><div><div className="lp-tname">Rajesh Menon</div><div className="lp-trole">Parent</div><div className="lp-tsch">Kendriya Vidyalaya, Kochi</div></div></div><div className="lp-tquote">I finally know exactly what my son is studying. The weak area alerts helped us focus revision before his half-yearly exams.</div><div className="lp-stars">&#9733;&#9733;&#9733;&#9733;&#9733;</div></div>
          <div className="lp-tc"><div className="lp-ttop"><div className="lp-tav">&#128102;</div><div><div className="lp-tname">Aryan Singh</div><div className="lp-trole">Class 9 Student</div><div className="lp-tsch">Ryan International, Mumbai</div></div></div><div className="lp-tquote">The mock test question bank is incredible. I scored 89% in my CBSE finals after 3 weeks of practice on LikhaPoha.</div><div className="lp-stars">&#9733;&#9733;&#9733;&#9733;&#9733;</div></div>
          <div className="lp-tc"><div className="lp-ttop"><div className="lp-tav">&#128105;</div><div><div className="lp-tname">Dr. Sunita Sharma</div><div className="lp-trole">Parent</div><div className="lp-tsch">Chinmaya Vidyalaya, Delhi</div></div></div><div className="lp-tquote">Better than tuition at 1/10th the cost. My daughter's science grade jumped from 68% to 87% in one term.</div><div className="lp-stars">&#9733;&#9733;&#9733;&#9733;&#9733;</div></div>
        </div>
      </div></div>
      <div className="lp-sw">
        <div className="lp-sh"><div className="lp-ey">Real Results</div><h2>Real Score Improvements</h2><p>From struggling to succeeding</p></div>
        <div className="lp-skg">
          <div className="lp-skcard"><div className="lp-sktop"><div className="lp-skarrow"><div><div className="lp-skbef">54%</div><div style={{fontSize:".65rem",color:"#cbd5e1"}}>BEFORE</div></div><div className="lp-skarr">&#8599;</div><div><div className="lp-skaft">82%</div><div style={{fontSize:".65rem",color:"#cbd5e1"}}>AFTER</div></div></div><div className="lp-skbadge">+28%</div></div><div className="lp-skname">Ananya Patel</div><div className="lp-skschool">Zydus School, Ahmedabad</div><div className="lp-skq" style={{fontSize:".78rem",marginTop:"6px",color:"#93c5fd"}}>Science</div><div className="lp-skq">The doubt-solving feature helped me understand reactions I had been confused about for months.</div></div>
          <div className="lp-skcard"><div className="lp-sktop"><div className="lp-skarrow"><div><div className="lp-skbef">48%</div><div style={{fontSize:".65rem",color:"#cbd5e1"}}>BEFORE</div></div><div className="lp-skarr">&#8599;</div><div><div className="lp-skaft">79%</div><div style={{fontSize:".65rem",color:"#cbd5e1"}}>AFTER</div></div></div><div className="lp-skbadge">+31%</div></div><div className="lp-skname">Karan Mehta</div><div className="lp-skschool">Modern School, Noida</div><div className="lp-skq" style={{fontSize:".78rem",marginTop:"6px",color:"#93c5fd"}}>Mathematics</div><div className="lp-skq">The worked examples in each lesson made algebra click for me finally.</div></div>
        </div>
      </div>
      */}
      <div className="lp-sf" id="faq"><div className="lp-si"><div className="lp-sh"><h2>Frequently Asked Questions</h2></div>
        {faqs.map((faq, i) => (
          <div key={i} className={"lp-faq-item" + (openFaq === i ? " open" : "")}>
            <button className="lp-faq-q" onClick={() => toggleFaq(i)}>{faq.q}<span className="lp-faq-icon">+</span></button>
            <div className="lp-faq-a">{faq.a}</div>
          </div>
        ))}
      </div></div>
      <div className="lp-ctasec">
        <h2>Start Your Child's AI Learning Journey Today</h2>
        <p>Join hundreds of families already studying smarter with LikhaPoha AI</p>
        <button className="lp-bc" onClick={() => handleCta("free")} style={{display:"inline-flex",alignItems:"center",gap:8}}><Zap size={18} strokeWidth={2.5}/> Try for Free</button>
        <p style={{marginTop:"16px",fontSize:".8rem",color:"#cbd5e1"}}>Free to start &middot; Upgrade anytime</p>
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
              LikhaPoha AI uses Google Sign-In <strong style={{color:"#cbd5e1"}}>only to securely authenticate users</strong>. When you sign in with Google, we request basic profile information such as your name, email address, and profile picture.
            </p>
            <p style={{fontSize:".82rem",color:"#94a3b8",lineHeight:1.7,margin:"8px 0 0"}}>
              We use this information <strong style={{color:"#cbd5e1"}}>only to</strong> create your account, keep you logged in securely, personalize your learning experience, and save your study progress.
            </p>
            <p style={{fontSize:".82rem",color:"#94a3b8",lineHeight:1.7,margin:"8px 0 0"}}>
              LikhaPoha AI <strong style={{color:"#f87171"}}>does not access</strong> Gmail, Google Drive, Google Calendar, Google Contacts, or any other Google services.
              We <strong style={{color:"#f87171"}}>do not sell or share</strong> Google user data for advertising or marketing.
              See our <a href="/privacy-policy" style={{color:"#93c5fd"}}>Privacy Policy</a> for full details.
            </p>
          </div>
        </div>
      </div>

      <footer className="lp-footer">
        <p style={{fontSize:"1rem",fontWeight:700,marginBottom:"12px"}}>LikhaPoha AI</p>
        <p>AI-Powered Tutor for CBSE &middot; Grade 5&ndash;12 &middot; JEE &middot; NEET &middot; CUET &middot; SAT &middot; IELTS &middot; TOEFL</p>
        <div style={{marginTop:"16px"}}>
          <a href="#home">Home</a>
          <a href="#features">Features</a>
          <a href="#pricing">Pricing</a>
          <a href="/blog">Blog</a>
          <a href={`mailto:${contactEmail}`}>Contact</a>
          <a href="/refund-policy">Refund Policy</a>
          <a href="/privacy-policy">Privacy Policy</a>
          <a href="/terms-of-service">Terms of Service</a>
        </div>
        <p style={{marginTop:"20px"}}>&copy; {new Date().getFullYear()} LikhaPoha AI &middot; Made with <Heart size={13} color="#ef4444" fill="#ef4444" style={{display:"inline",verticalAlign:"middle"}}/> in India</p>
      </footer>
    </div>
  );
}
