import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import logoImg from "../assets/AITutorLogo1.png";
import { BookOpen, MessageCircle, MessagesSquare, ClipboardList, Users, TrendingUp, Zap, Leaf, ShieldCheck, Globe, GraduationCap, HelpCircle, BarChart2, Trophy, Award, Target, Monitor, FlaskConical, Landmark, Heart, Calculator, Languages, Headphones, Check, X, FileText } from "lucide-react";
import NoticeboardPricingTable from "../components/NoticeboardPricingTable";
import "./LandingPage.css";

const MISSION_ICONS = [BookOpen, ShieldCheck, Globe, GraduationCap];
const EXAM_PREP_ICONS = [Monitor, FlaskConical, Landmark, Calculator, Languages, Headphones];
const EXAM_PREP_COLORS = ["#6366f1", "#10b981", "#f59e0b", "#3b82f6", "#8b5cf6", "#06b6d4"];

export default function LandingPage({ onShowLogin, onShowSignup }) {
  const { t, i18n } = useTranslation("landing");

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

  const stats = t("hero.stats", { returnObjects: true });
  const missionCards = t("mission.cards", { returnObjects: true });
  const problemItems = t("problem.items", { returnObjects: true });
  const solutionItems = t("solution.items", { returnObjects: true });
  const resultItems = t("results.items", { returnObjects: true });
  const featureCards = t("features.cards", { returnObjects: true });
  const examPrepCards = t("examPrep.cards", { returnObjects: true });
  const faqs = t("faq.items", { returnObjects: true });

  return (
    <div className="lp">
      {/* Non-sticky anchor target for the footer "Home" link — putting id="home"
          directly on the sticky nav breaks native anchor-scroll, since a
          stuck element's getBoundingClientRect().top is already 0. */}
      <div id="home" style={{ position: "absolute" }} aria-hidden="true" />
      <nav className="lp-nav">
        <div className="lp-logo"><img src={logoImg} alt="LikhaPoha AI" /><span>LikhaPoha AI</span></div>
        <div className="lp-nav-links">
          <a href="#features">{t("nav.features")}</a>
          <a href="#pricing">{t("nav.pricing")}</a>
          <a href="#faq">{t("nav.faq")}</a>
        </div>
        <div className="lp-nav-r">
          <div className="lp-langswitch" role="group" aria-label="Language">
            <button type="button" className={i18n.resolvedLanguage === "en" ? "active" : ""} onClick={() => i18n.changeLanguage("en")}>EN</button>
            <button type="button" className={i18n.resolvedLanguage === "hi" ? "active" : ""} onClick={() => i18n.changeLanguage("hi")}>हिं</button>
          </div>
          <button className="lp-btn-ghost" onClick={onShowLogin}>{t("nav.login")}</button>
          <button className="lp-btn-cta" onClick={() => handleCta("free")}>{t("nav.cta")}</button>
        </div>
      </nav>
      <div className="lp-hero">
        <div className="lp-badge">{t("hero.badge")}</div>
        <h1>{t("hero.titleLine1")}<br /><span className="lp-gr">{t("hero.titleAccent")}</span></h1>
        <p>{t("hero.subtitle")}</p>
        <div className="lp-hcta">
          <button className="lp-bc" onClick={() => handleCta("free")} style={{display:"inline-flex",alignItems:"center",gap:8}}><Zap size={18} strokeWidth={2.5} /> {t("hero.ctaPrimary")}</button>
          <a href="#features" className="lp-bol">{t("hero.ctaSecondary")}</a>
        </div>
        <div className="lp-stats">
          {stats.map((s, i) => (
            <div className="lp-stat" key={i}><div className="lp-sn">{s.n}</div><div className="lp-sl">{s.l}</div></div>
          ))}
        </div>
      </div>
      {/* AI for Good */}
      <div style={{background:"linear-gradient(135deg,rgba(16,185,129,.08),rgba(99,102,241,.05))",borderTop:"1px solid rgba(16,185,129,.2)",borderBottom:"1px solid rgba(16,185,129,.15)",padding:"28px 20px",textAlign:"center"}}>
        <div style={{maxWidth:860,margin:"0 auto"}}>
          <div style={{fontSize:".68rem",fontWeight:800,textTransform:"uppercase",letterSpacing:".1em",color:"#10b981",marginBottom:8}}>{t("mission.eyebrow")}</div>
          <h2 style={{fontSize:"1.3rem",fontWeight:900,margin:"0 0 10px",display:"flex",alignItems:"center",justifyContent:"center",gap:8}}><Leaf size={20} color="#10b981" strokeWidth={2} /> {t("mission.title")}</h2>
          <p style={{fontSize:".9rem",color:"var(--muted,#94a3b8)",maxWidth:660,margin:"0 auto 18px",lineHeight:1.7}}>{t("mission.descPre")}<strong>{t("mission.descStrong")}</strong>{t("mission.descPost")}</p>
          <div style={{display:"flex",gap:14,flexWrap:"wrap",justifyContent:"center"}}>
            {missionCards.map((f, i) => {
              const Icon = MISSION_ICONS[i];
              return (
                <div key={f.t} style={{background:"rgba(16,185,129,.06)",border:"1px solid rgba(16,185,129,.15)",borderRadius:10,padding:"12px 16px",flex:"1 1 160px",maxWidth:210}}>
                  <div style={{display:"flex",justifyContent:"center",marginBottom:6,color:"#10b981"}}><Icon size={20} strokeWidth={2}/></div>
                  <div style={{fontWeight:700,fontSize:".8rem",marginBottom:2}}>{f.t}</div>
                  <div style={{fontSize:".7rem",color:"var(--muted,#94a3b8)"}}>{f.d}</div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div className="lp-sf"><div className="lp-si">
        <div className="lp-sh"><div className="lp-ey">{t("problem.eyebrow")}</div><h2>{t("problem.title")}</h2></div>
        <div className="lp-pvs">
          {/* Problem column */}
          <div className="lp-pcard prob"><div className="lp-ptitle bad">{t("problem.label")}</div>
            {problemItems.map((p, i) => (
              <div className="lp-pitem" key={i}><X size={16} strokeWidth={2.5} color="#ef4444" style={{flexShrink:0,marginTop:2}} /> {p}</div>
            ))}
          </div>
          {/* Solution column */}
          <div className="lp-pcard sol"><div className="lp-ptitle good">{t("solution.label")}</div>
            {solutionItems.map((s, i) => (
              <div className="lp-pitem" key={i}><Check size={16} strokeWidth={2.5} color="#10b981" style={{flexShrink:0,marginTop:2}} /> {s}</div>
            ))}
          </div>
        </div>

        {/* Results grid */}
        <div style={{marginTop:"28px",marginBottom:"28px"}}>
          <div className="lp-ey" style={{marginBottom:"14px"}}>{t("results.eyebrow")}</div>
          <div className="lp-results">
            {resultItems.map((r, i) => (
              <div className="lp-rcard" key={i}><span className="lp-ri"><TrendingUp size={16} strokeWidth={2.5} /></span> {r.pre}<strong>{r.strong}</strong>{r.post}</div>
            ))}
          </div>
        </div>

        {/* Closing statement */}
        <div className="lp-closing">
          <p>{t("closing.pre")}<strong>{t("closing.strong")}</strong>{t("closing.post")}</p>
        </div>

      </div></div>
      <div className="lp-sw">
        <div className="lp-sh"><div className="lp-ey">{t("demo.eyebrow")}</div><h2>{t("demo.title")}</h2><p>{t("demo.subtitle")}</p></div>
        <div className="lp-demo">
          <div className="lp-dc"><div className="lp-dh"><span className="lp-dh-dots"><span></span><span></span><span></span></span><div className="lp-di" style={{background:"rgba(124,58,237,.2)"}}><BookOpen size={16} strokeWidth={2}/></div>{t("demo.lesson.label")}</div><img src="/screenshots/2026-08-lessons.png" alt="AI Lesson" style={{width:"100%",display:"block"}} loading="lazy" /><div className="lp-dcap">{t("demo.lesson.caption")}</div></div>
          <div className="lp-dc"><div className="lp-dh"><span className="lp-dh-dots"><span></span><span></span><span></span></span><div className="lp-di" style={{background:"rgba(6,182,212,.2)"}}><ClipboardList size={16} strokeWidth={2}/></div>{t("demo.mocktest.label")}</div><img src="/screenshots/2026-08-mocktest.png" alt="Mock Test" style={{width:"100%",display:"block"}} loading="lazy" /><div className="lp-dcap">{t("demo.mocktest.caption")}</div></div>
          <div className="lp-dc"><div className="lp-dh"><span className="lp-dh-dots"><span></span><span></span><span></span></span><div className="lp-di" style={{background:"rgba(16,185,129,.2)"}}><Users size={16} strokeWidth={2}/></div>{t("demo.parent.label")}</div><img src="/screenshots/2026-08-parentdashboard.png" alt="Parent Dashboard" style={{width:"100%",display:"block"}} loading="lazy" /><div className="lp-dcap">{t("demo.parent.caption")}</div></div>
        </div>
      </div>
      <div className="lp-sf" id="features"><div className="lp-si">
        <div className="lp-sh"><div className="lp-ey">{t("features.eyebrow")}</div><h2>{t("features.title")}</h2><p>{t("features.subtitle")}</p></div>
        <div className="lp-fg">
          <div>
            <div className="lp-fc" style={{background:"linear-gradient(180deg,rgba(124,58,237,.05),transparent 60%),#0f172a",borderColor:"rgba(124,58,237,.25)"}}><div className="lp-fi" style={{background:"rgba(124,58,237,.15)"}}><BookOpen size={22} strokeWidth={2} /></div><h3>{featureCards[0].title}</h3><p>{featureCards[0].desc}</p></div>
            <div className="lp-fc" style={{background:"linear-gradient(180deg,rgba(16,185,129,.05),transparent 60%),#0f172a",borderColor:"rgba(16,185,129,.25)"}}><div className="lp-fi" style={{background:"rgba(16,185,129,.15)"}}><MessageCircle size={22} strokeWidth={2} /></div><h3>{featureCards[1].title}</h3><p>{featureCards[1].desc}</p></div>
            <div className="lp-fc" style={{background:"linear-gradient(180deg,rgba(245,158,11,.05),transparent 60%),#0f172a",borderColor:"rgba(245,158,11,.25)"}}><div className="lp-fi" style={{background:"rgba(245,158,11,.15)"}}><ClipboardList size={22} strokeWidth={2} /></div><h3>{featureCards[2].title}</h3><p>{featureCards[2].desc}</p></div>
            <div className="lp-fc" style={{background:"linear-gradient(180deg,rgba(239,68,68,.05),transparent 60%),#0f172a",borderColor:"rgba(239,68,68,.25)"}}><div className="lp-fi" style={{background:"rgba(239,68,68,.15)"}}><Users size={22} strokeWidth={2} /></div><h3>{featureCards[3].title}</h3><p>{featureCards[3].desc}</p></div>
            <div className="lp-fc" style={{background:"linear-gradient(180deg,rgba(59,130,246,.05),transparent 60%),#0f172a",borderColor:"rgba(59,130,246,.25)"}}><div className="lp-fi" style={{background:"rgba(59,130,246,.15)"}}><MessagesSquare size={22} strokeWidth={2} /></div><h3>{featureCards[4].title}</h3><p>{featureCards[4].desc}</p></div>
          </div>
          <div style={{display:"flex",flexDirection:"column",gap:"16px"}}>
            <div className="lp-dc"><div className="lp-dh"><span className="lp-dh-dots"><span></span><span></span><span></span></span><div className="lp-di" style={{background:"rgba(16,185,129,.2)"}}><HelpCircle size={16} strokeWidth={2}/></div>{t("features.doubtLabel")}</div><img src="/screenshots/2026-08-askdoubt.png" alt="Doubt Solving" style={{width:"100%",display:"block"}} loading="lazy" /></div>
            <div className="lp-dc"><div className="lp-dh"><span className="lp-dh-dots"><span></span><span></span><span></span></span><div className="lp-di" style={{background:"rgba(99,102,241,.2)"}}><BarChart2 size={16} strokeWidth={2}/></div>{t("features.analyticsLabel")}</div><img src="/screenshots/2026-08-analytics.png" alt="Student Analytics" style={{width:"100%",display:"block"}} loading="lazy" /></div>
          </div>
        </div>
      </div></div>
      <div className="lp-sf lp-gamified"><div className="lp-si">
        <div className="lp-sh"><div className="lp-ey">{t("gamified.eyebrow")}</div><h2>{t("gamified.title")}</h2><p>{t("gamified.subtitle")}</p></div>
        <div className="lp-2col">
          <div className="lp-dc"><div className="lp-dh"><span className="lp-dh-dots"><span></span><span></span><span></span></span><div className="lp-di" style={{background:"rgba(245,158,11,.2)"}}><Trophy size={16} strokeWidth={2}/></div>{t("gamified.achievementsLabel")}</div><img src="/screenshots/2026-08-dashboard.png" alt="Gamified Dashboard" style={{width:"100%",display:"block"}} loading="lazy" /></div>
          <div className="lp-dc"><div className="lp-dh"><span className="lp-dh-dots"><span></span><span></span><span></span></span><div className="lp-di" style={{background:"rgba(99,102,241,.2)"}}><Award size={16} strokeWidth={2}/></div>{t("gamified.leaderboardLabel")}</div><img src="/screenshots/2026-08-leaderboard.png" alt="Leaderboard" style={{width:"100%",display:"block"}} loading="lazy" /></div>
        </div>
      </div></div>
      {/* Exam Prep Center — Grade 11 & 12 */}
      <div className="lp-sw" style={{background:"linear-gradient(135deg,rgba(99,102,241,.06),rgba(139,92,246,.04))"}}>
        <div className="lp-sh"><div className="lp-ey" style={{color:"#8b5cf6"}}>{t("examPrep.eyebrow")}</div><h2 style={{display:"flex",alignItems:"center",justifyContent:"center",gap:8}}><Target size={22} strokeWidth={2}/> {t("examPrep.title")}</h2><p>{t("examPrep.subtitle")}</p></div>
        <div className="lp-examgrid" style={{maxWidth:900,margin:"0 auto 8px"}}>
          {examPrepCards.map((f, i) => {
            const Icon = EXAM_PREP_ICONS[i];
            const color = EXAM_PREP_COLORS[i];
            return (
              <div key={f.title} style={{background:"#1e293b",border:"1px solid "+color+"44",borderRadius:12,padding:"18px 16px"}}>
                <div style={{marginBottom:10,color:color}}><Icon size={24} strokeWidth={2}/></div>
                <div style={{fontWeight:800,fontSize:".9rem",color:color,marginBottom:6}}>{f.title}</div>
                <div style={{fontSize:".78rem",color:"#94a3b8",lineHeight:1.6}}>{f.desc}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Board Papers + JEE Main Simulator — proof screenshots */}
      <div className="lp-sf"><div className="lp-si">
        <div className="lp-sh"><div className="lp-ey">{t("realExam.eyebrow")}</div><h2>{t("realExam.title")}</h2><p>{t("realExam.subtitle")}</p></div>
        <div className="lp-2col">
          <div className="lp-dc"><div className="lp-dh"><span className="lp-dh-dots"><span></span><span></span><span></span></span><div className="lp-di" style={{background:"rgba(59,130,246,.2)"}}><FileText size={16} strokeWidth={2}/></div>{t("realExam.boardPapersLabel")}</div><img src="/screenshots/2026-08-boardpapers.png" alt="Board Papers" style={{width:"100%",display:"block"}} loading="lazy" /><div className="lp-dcap">{t("realExam.boardPapersCaption")}</div></div>
          <div className="lp-dc"><div className="lp-dh"><span className="lp-dh-dots"><span></span><span></span><span></span></span><div className="lp-di" style={{background:"rgba(99,102,241,.2)"}}><Monitor size={16} strokeWidth={2}/></div>{t("realExam.jeeLabel")}</div><img src="/screenshots/2026-08-jee-simulator.png" alt="JEE Main Simulator" style={{width:"100%",display:"block"}} loading="lazy" /><div className="lp-dcap">{t("realExam.jeeCaption")}</div></div>
        </div>
      </div></div>

      <div className="lp-sw" id="pricing">
        <div className="lp-sh"><div className="lp-ey">{t("pricingSection.eyebrow")}</div><h2>{t("pricingSection.title")}</h2><p>{t("pricingSection.subtitle")}</p></div>
        <NoticeboardPricingTable theme="dark" showCta={false} />
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
      <div className="lp-sf" id="faq"><div className="lp-si"><div className="lp-sh"><h2>{t("faq.title")}</h2></div>
        {faqs.map((faq, i) => (
          <div key={i} className={"lp-faq-item" + (openFaq === i ? " open" : "")}>
            <button className="lp-faq-q" onClick={() => toggleFaq(i)}>{faq.q}<span className="lp-faq-icon">+</span></button>
            <div className="lp-faq-a">{faq.a}</div>
          </div>
        ))}
      </div></div>
      <div className="lp-ctasec">
        <h2>{t("cta.title")}</h2>
        <p>{t("cta.subtitle")}</p>
        <button className="lp-bc" onClick={() => handleCta("free")} style={{display:"inline-flex",alignItems:"center",gap:8}}><Zap size={18} strokeWidth={2.5}/> {t("cta.button")}</button>
        <p style={{marginTop:"16px",fontSize:".8rem",color:"#cbd5e1"}}>{t("cta.footnote")}</p>
      </div>
      {/* Google Sign-In disclosure — required by Google API Services User Data Policy.
          Left in English deliberately: this is compliance-mandated boilerplate, not
          marketing copy, and a translated version should go through legal review
          before shipping rather than being machine-translated here. */}
      <div style={{background:"rgba(15,23,42,.95)",borderTop:"1px solid #1e293b",padding:"36px 24px"}}>
        <div style={{maxWidth:720,margin:"0 auto",display:"flex",gap:18,alignItems:"flex-start"}}>
          <div style={{flexShrink:0,width:36,height:36,borderRadius:8,background:"#fff",display:"flex",alignItems:"center",justifyContent:"center",marginTop:2}}>
            <svg width="20" height="20" viewBox="0 0 48 48"><path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9 3.2l6.7-6.7C35.8 2.5 30.3 0 24 0 14.6 0 6.6 5.4 2.6 13.3l7.8 6C12.3 13.2 17.7 9.5 24 9.5z"/><path fill="#4285F4" d="M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v8.5h12.7c-.6 3-2.3 5.5-4.8 7.2l7.5 5.8c4.4-4 7.1-10 7.1-17z"/><path fill="#FBBC05" d="M10.4 28.7A14.5 14.5 0 0 1 9.5 24c0-1.6.3-3.2.9-4.7l-7.8-6A24 24 0 0 0 0 24c0 3.8.9 7.4 2.6 10.7l7.8-6z"/><path fill="#34A853" d="M24 48c6.2 0 11.5-2.1 15.4-5.6l-7.5-5.8c-2.1 1.4-4.8 2.2-7.9 2.2-6.3 0-11.6-3.7-13.6-9l-7.8 6C6.6 42.6 14.6 48 24 48z"/></svg>
          </div>
          <div>
            <p style={{fontSize:".8rem",fontWeight:800,color:"#f8fafc",marginBottom:6,textTransform:"uppercase",letterSpacing:".06em"}}>Google Sign-In &amp; Data Usage</p>
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
        <p>{t("footer.tagline")}</p>
        <div style={{marginTop:"16px"}}>
          <a href="#home">{t("footer.home")}</a>
          <a href="#features">{t("footer.features")}</a>
          <a href="#pricing">{t("footer.pricing")}</a>
          <a href="/blog">{t("footer.blog")}</a>
          <a href={`mailto:${contactEmail}`}>{t("footer.contact")}</a>
          <a href="/refund-policy">{t("footer.refund")}</a>
          <a href="/privacy-policy">{t("footer.privacy")}</a>
          <a href="/terms-of-service">{t("footer.terms")}</a>
        </div>
        <p style={{marginTop:"20px"}}>&copy; {new Date().getFullYear()} LikhaPoha AI &middot; {t("footer.madeInPre")} <Heart size={13} color="#ef4444" fill="#ef4444" style={{display:"inline",verticalAlign:"middle"}}/> {t("footer.madeInPost")}</p>
      </footer>
    </div>
  );
}
