import { useEffect, useState } from "react";
import logoImg from "../assets/AITutorLogo1.png";
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
  const [contactEmail, setContactEmail] = useState("hello@likhapoha.in");

  function toggleFaq(i) { setOpenFaq(p => p === i ? null : i); }

  useEffect(() => {
    fetch("/api/payments/contact")
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data?.email) setContactEmail(data.email); })
      .catch(() => {});
  }, []);
  const faqs = [
    { q: "Which classes and boards are supported?", a: "LikhaPoha AI supports Class 5 to 10 for CBSE. State Board content can be uploaded by admins." },
    { q: "Does the AI use real textbooks or make things up?", a: "Every lesson and doubt answer is grounded in uploaded NCERT textbooks using RAG technology. The AI cannot hallucinate chapter content." },
    { q: "How many practice questions are available?", a: "LikhaPoha AI has 42,000+ practice questions covering all chapters from Grade 5 to Grade 10 across CBSE subjects available instantly for mock tests and practice." },
    { q: "How does the parent dashboard work?", a: "Parents see daily study time, mock test scores, trend charts, and automatic weak-area alerts when a child scores below 7/10 on any practice topic." },
    { q: "Is there a mobile app?", a: "LikhaPoha AI is a mobile-first progressive web app. It works perfectly on any phone browser. No app download needed. Add to home screen for app-like experience." },
  ];
  return (
    <div className="lp">
      <nav className="lp-nav">
        <div className="lp-logo"><img src={logoImg} alt="LikhaPoha AI" /><span>LikhaPoha AI</span></div>
        <div className="lp-nav-r">
          <button className="lp-btn-ghost" onClick={onShowLogin}>Login</button>
          <button className="lp-btn-cta" onClick={() => handleCta("free")}>Try for &#8377;100</button>
        </div>
      </nav>
      <div className="lp-hero">
        <div className="lp-badge">&#127470;&#127475; Built for India &middot; Class 5&ndash;10 &middot; CBSE</div>
        <h1>Your Child&#39;s Personal<br /><span className="lp-gr">AI Study Tutor</span></h1>
        <p>Step-wise textbook lessons, instant doubt answers, mock tests, and real-time parent insights &mdash; all in one place.</p>
        <div className="lp-hcta">
          <button className="lp-bc" onClick={() => handleCta("free")}>&#128640; Try for &#8377;100 &mdash; 14 Days</button>
          <a href="#features" className="lp-bol">See Features &rarr;</a>
        </div>
        <div className="lp-stats">
          <div className="lp-stat"><div className="lp-sn">700+</div><div className="lp-sl">Chapters (Gr 5&ndash;10)</div></div>
          <div className="lp-stat"><div className="lp-sn">6</div><div className="lp-sl">Classes (5&ndash;10)</div></div>
          <div className="lp-stat"><div className="lp-sn">6</div><div className="lp-sl">Core Subjects</div></div>
          <div className="lp-stat"><div className="lp-sn">42,000+</div><div className="lp-sl">Practice Questions</div></div>
        </div>
      </div>
      <div className="lp-sf"><div className="lp-si">
        <div className="lp-sh"><div className="lp-ey">The Real Problem</div><h2>Why Students Struggle at Home</h2></div>
        <div className="lp-pvs">
          <div className="lp-pcard prob"><div className="lp-ptitle bad">&#8855; The Problem</div>
            <div className="lp-pitem"><span>&#10007;</span> Tuition is expensive &mdash; &#8377;2,000&ndash;8,000/month per subject</div>
            <div className="lp-pitem"><span>&#10007;</span> Parents cannot track what the child actually studied</div>
            <div className="lp-pitem"><span>&#10007;</span> Generic YouTube videos do not follow CBSE syllabus</div>
            <div className="lp-pitem"><span>&#10007;</span> No personalised feedback on weak areas</div>
            <div className="lp-pitem"><span>&#10007;</span> Practice questions do not match actual exam patterns</div>
          </div>
          <div className="lp-pcard sol"><div className="lp-ptitle good">&#10003; LikhaPoha AI Solution</div>
            <div className="lp-pitem"><span>&#10003;</span> AI lesson for every chapter &mdash; instant, free of charge</div>
            <div className="lp-pitem"><span>&#10003;</span> Parent dashboard shows daily progress and weak areas</div>
            <div className="lp-pitem"><span>&#10003;</span> Lessons grounded in uploaded NCERT textbooks</div>
            <div className="lp-pitem"><span>&#10003;</span> Smart evaluation flags revision topics automatically</div>
            <div className="lp-pitem"><span>&#10003;</span> CBSE mock tests and 42,000+ practice questions included</div>
          </div>
        </div>
      </div></div>
      <div className="lp-sw">
        <div className="lp-sh"><div className="lp-ey">See It In Action</div><h2>A Glimpse of What Students Experience Daily</h2><p>Everything works on phone &mdash; no app download needed</p></div>
        <div className="lp-demo">
          <div className="lp-dc"><div className="lp-dh"><div className="lp-di" style={{background:"rgba(124,58,237,.2)"}}>&#128218;</div>AI LESSON</div><img src="/screenshots/lesson.png" alt="AI Lesson" style={{width:"100%",display:"block"}} loading="lazy" /><div className="lp-dcap">Step-wise chapter lesson grounded in your NCERT textbook</div></div>
          <div className="lp-dc"><div className="lp-dh"><div className="lp-di" style={{background:"rgba(6,182,212,.2)"}}>&#129514;</div>MOCK TEST</div><img src="/screenshots/mocktest.png" alt="Mock Test" style={{width:"100%",display:"block"}} loading="lazy" /><div className="lp-dcap">CBSE mock tests with instant scoring and explanations</div></div>
          <div className="lp-dc"><div className="lp-dh"><div className="lp-di" style={{background:"rgba(16,185,129,.2)"}}>&#128106;</div>PARENT DASHBOARD</div><img src="/screenshots/parent-dashboard.png" alt="Parent Dashboard" style={{width:"100%",display:"block"}} loading="lazy" /><div className="lp-dcap">Real-time progress, score trends and weak area alerts for parents</div></div>
        </div>
      </div>
      <div className="lp-sf" id="features"><div className="lp-si">
        <div className="lp-sh"><div className="lp-ey">Everything You Need</div><h2>Complete Study Toolkit for CBSE</h2><p>Powerful AI tools designed for Indian students</p></div>
        <div className="lp-fg">
          <div>
            <div className="lp-fc"><div className="lp-fi" style={{background:"rgba(124,58,237,.15)"}}>&#128218;</div><h3>Step-wise AI Lessons</h3><p>4&ndash;6 focused steps per chapter &mdash; Concept intro, Core explanation, Worked examples, Exam-style problems, Revision.</p></div>
            <div className="lp-fc"><div className="lp-fi" style={{background:"rgba(16,185,129,.15)"}}>&#10067;</div><h3>Instant Doubt Solving</h3><p>Ask any chapter question. AI answers from your actual NCERT textbook &mdash; not generic internet content.</p></div>
            <div className="lp-fc"><div className="lp-fi" style={{background:"rgba(245,158,11,.15)"}}>&#129514;</div><h3>Mock Tests and Question Bank</h3><p>CBSE class tests, mid-terms and full mock tests across all grades. 42,000+ practice questions covering every chapter.</p></div>
            <div className="lp-fc"><div className="lp-fi" style={{background:"rgba(239,68,68,.15)"}}>&#128106;</div><h3>Parent Dashboard</h3><p>Track daily study time, test scores, weak area alerts, and AI usage. Two children per family account.</p></div>
          </div>
          <div style={{display:"flex",flexDirection:"column",gap:"16px"}}>
            <div className="lp-dc"><div className="lp-dh"><div className="lp-di" style={{background:"rgba(16,185,129,.2)"}}>&#10067;</div>INSTANT DOUBT SOLVING</div><img src="/screenshots/doubt.png" alt="Doubt Solving" style={{width:"100%",display:"block"}} loading="lazy" /></div>
            <div className="lp-dc"><div className="lp-dh"><div className="lp-di" style={{background:"rgba(124,58,237,.2)"}}>&#128218;</div>LEARN MORE SECTION</div><img src="/screenshots/learn-more.png" alt="Learn More" style={{width:"100%",display:"block"}} loading="lazy" /></div>
          </div>
        </div>
      </div></div>
      <div className="lp-sf"><div className="lp-si">
        <div className="lp-sh"><div className="lp-ey">Kids Love It</div><h2>Gamified Learning Dashboard</h2><p>Badges, leaderboards and achievement streaks keep students motivated every day</p></div>
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"20px"}}>
          <div className="lp-dc"><div className="lp-dh"><div className="lp-di" style={{background:"rgba(245,158,11,.2)"}}>&#127942;</div>ACHIEVEMENTS AND BADGES</div><img src="/screenshots/gamified-dashboard.png" alt="Gamified Dashboard" style={{width:"100%",display:"block"}} loading="lazy" /></div>
          <div className="lp-dc"><div className="lp-dh"><div className="lp-di" style={{background:"rgba(99,102,241,.2)"}}>&#129351;</div>CLASS LEADERBOARD</div><img src="/screenshots/leaderboard.png" alt="Leaderboard" style={{width:"100%",display:"block"}} loading="lazy" /></div>
        </div>
      </div></div>
      <div className="lp-sw" id="pricing">
        <div className="lp-sh"><div className="lp-ey">Simple Pricing</div><h2>Choose Your Plan</h2><p>Start free, upgrade anytime &middot; Cancel anytime</p></div>
        <div className="lp-pg">
          <div className="lp-prc"><div className="lp-prname">Try It Out</div><div className="lp-pramount">&#8377;100<span>/14 days</span></div><div className="lp-prdesc">Explore before you commit</div><div className="lp-prf">CBSE Lessons (3 subjects)</div><div className="lp-prf">5 Doubt questions/day</div><div className="lp-prf">Basic mock tests</div><div className="lp-prf">Parent dashboard</div><button className="lp-bpro lp-bpout" onClick={() => handleCta("free")}>Get Started</button></div>
          <div className="lp-prc pop"><div className="lp-popb">Most Popular</div><div className="lp-prname">Standard</div><div className="lp-pramount">&#8377;299<span>/month</span></div><div className="lp-prdesc">For serious exam prep</div><div className="lp-prf">All CBSE subjects &middot; All grades</div><div className="lp-prf">Unlimited doubt solving</div><div className="lp-prf">Full question bank access</div><div className="lp-prf">Parent dashboard + alerts</div><div className="lp-prf">Priority support</div><button className="lp-bpro lp-bpfill" onClick={() => handleCta("starter")}>Start Now</button></div>
          <div className="lp-prc"><div className="lp-prname">Family</div><div className="lp-pramount">&#8377;499<span>/month</span></div><div className="lp-prdesc">Two children, one plan</div><div className="lp-prf">Everything in Standard</div><div className="lp-prf">Up to 2 children</div><div className="lp-prf">Multi-parent access</div><div className="lp-prf">Separate progress tracking</div><div className="lp-prf">Teacher dashboard access</div><button className="lp-bpro lp-bpout" onClick={() => handleCta("family_premium")}>Get Started</button></div>
        </div>
        <p className="lp-prnote">Save up to 40% with 12-month plan &middot; No hidden charges</p>
      </div>
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
      <div className="lp-sf"><div className="lp-si"><div className="lp-sh"><h2>Frequently Asked Questions</h2></div>
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
        <button className="lp-bc" onClick={() => handleCta("free")} style={{display:"inline-flex"}}>&#128640; Try for &#8377;100 &mdash; No Credit Card Needed</button>
        <p style={{marginTop:"16px",fontSize:".8rem",color:"#cbd5e1"}}>Try for 14 days at &#8377;100 &middot; Cancel anytime</p>
      </div>
      <footer className="lp-footer">
        <p style={{fontSize:"1rem",fontWeight:700,marginBottom:"12px"}}>LikhaPoha AI</p>
        <p>AI-Powered Tutor for CBSE &middot; Class 5&ndash;10</p>
        <div style={{marginTop:"16px"}}>
          <a href="#">Home</a>
          <a href="#features">Features</a>
          <a href="#pricing">Pricing</a>
          <a href={`mailto:${contactEmail}`}>Contact</a>
          <a href="/refund-policy">Refund Policy</a>
        </div>
        <p style={{marginTop:"20px"}}>&copy; 2026 LikhaPoha AI &middot; Made with &#10084; in India</p>
      </footer>
    </div>
  );
}
