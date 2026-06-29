/**
 * StudentDashboardPage.jsx — Redesigned Student Dashboard (Option 1)
 * Uses /api/student/dashboard/summary for all data.
 * Falls back to existing getAnalytics/getStudentProfile if new endpoint unavailable.
 * Safety: feature auth, score normalization, no premium feature leakage.
 */
import { useCallback, useEffect, useState } from "react";
import { getStudentDashboardSummary, getStudentExams, addStudentExam, deleteStudentExam } from "../api/analytics";
import { getAnalytics } from "../api/analytics";
import { getStudentProfile } from "../api/profile";
import { getRecommendations } from "../api/recommendations";
import { getWeakChapters } from "../api/analytics";
import "./StudentDashboardPage.css";
import ReportIssueModal from "../components/ReportIssueModal";

// ── Design tokens / helpers ───────────────────────────────────────────────────
function greet(){var h=new Date().getHours();return h<12?"Good morning":h<17?"Good afternoon":"Good evening";}
var SUBJ_COLORS={"Mathematics":"#6366f1","Science":"#22c55e","English":"#f59e0b","Hindi":"#ef4444","Social Science":"#0ea5e9","Maths":"#6366f1"};
function subjCol(s){return SUBJ_COLORS[s]||"#6366f1";}
function safePct(v){if(v==null)return null;var n=parseFloat(v);return(isNaN(n)||n<0||n>100)?null:Math.round(n);}

function ProgBar({pct=0,color="#6366f1",height=6}){
  return(
    <div style={{height,background:"var(--surface2,#f1f5f9)",borderRadius:4,overflow:"hidden",margin:"5px 0"}}>
      <div style={{height:"100%",width:Math.min(pct,100)+"%",background:color,borderRadius:4,transition:"width .5s"}}/>
    </div>
  );
}
function SdCard({children,testid,style}){
  return <div data-testid={testid} className="sd-card" style={style}>{children}</div>;
}
function SdBtn({children,onClick,small,color="#6366f1",outline}){
  return(
    <button onClick={onClick} style={{
      padding:small?"4px 10px":"8px 14px",borderRadius:8,cursor:"pointer",fontFamily:"inherit",
      fontWeight:700,fontSize:small?".72rem":".8rem",whiteSpace:"nowrap",
      background:outline?"transparent":color,color:outline?color:"#fff",
      border:outline?`1px solid ${color}`:"none",
    }}>{children}</button>
  );
}

// ── Skeleton ──────────────────────────────────────────────────────────────────
function Skel(){
  return(
    <div className="sd-page" style={{padding:"20px 0"}}>
      <div style={{height:24,background:"var(--border,#e5e7eb)",borderRadius:6,width:"40%",marginBottom:8}}/>
      <div style={{height:14,background:"var(--border,#e5e7eb)",borderRadius:4,width:"60%",marginBottom:20}}/>
      <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:12}}>
        {[1,2,3,4].map(i=><div key={i} style={{height:80,background:"var(--border,#e5e7eb)",borderRadius:12}}/>)}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main component
// ─────────────────────────────────────────────────────────────────────────────
export default function StudentDashboardPage({ user, setActivePage }) {
  var [reportOpen, setReportOpen] = useState(false);
  const [data, setData]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [exams, setExams]     = useState([]);
  const [showAddExam, setShowAddExam] = useState(false);
  const [examForm, setExamForm] = useState({title:"",subject:"",exam_date:"",exam_type:""});
  const [examLoading, setExamLoading] = useState(false);
  const [examMsg, setExamMsg] = useState(null);

  const load = useCallback(async function(){
    setLoading(true);
    try {
      // Try new summary endpoint first
      var summary = await getStudentDashboardSummary().catch(()=>null);
      if (summary?.success) {
        setData(summary);
        setLoading(false);
        return;
      }
      // Fallback: assemble from existing APIs
      const [analytics, profileRes, recRes, weakRes] = await Promise.allSettled([
        getAnalytics(user.username),
        getStudentProfile(user.username),
        getRecommendations(user.username),
        getWeakChapters(user.username),
      ]);
      var hist = analytics.value?.history || analytics.value?.test_history || [];
      var profile = profileRes.value?.profile || {};
      var recs = recRes.value?.recommendations || [];
      var weakTopics = weakRes.value?.weak_chapters?.slice(0,5).map(w=>({subject:w.subject,chapter:w.chapter,score:w.best_score})) || [];
      var scores = hist.map(r=>safePct(r.percentage)).filter(v=>v!=null);
      var avg = scores.length?Math.round(scores.reduce((a,b)=>a+b,0)/scores.length):null;
      var subjMap={};
      hist.forEach(function(r){var s=r.subject||"Unknown";var p=safePct(r.percentage);if(p!=null){if(!subjMap[s])subjMap[s]=[];subjMap[s].push(p);}});
      var subjAvgs={};
      Object.entries(subjMap).forEach(function([s,v]){subjAvgs[s]=Math.round(v.reduce((a,b)=>a+b,0)/v.length);});
      setData({
        success:true,
        student:{username:profile.username||user.username,grade:profile.grade||user.grade||"Grade 9",study_streak_days:profile.study_streak_days||0,lessons_completed:profile.lessons_completed||0},
        subscription:{canonical_plan_key:user.accessCbse?"PREMIUM":"FREE_TIER",has_full_access:!!user.accessCbse},
        features:{has_full_access:!!user.accessCbse,exemplar_locked:!user.accessCbse,mock_test_limited:!user.accessCbse},
        mock_tests:{available:hist.length>0,total:hist.length,average_score:avg,best_score:scores.length?Math.max(...scores):null,subject_averages:subjAvgs,recent:hist.slice(0,5).map(r=>({subject:r.subject,chapter:r.chapter||"",score:safePct(r.percentage),date:(r.created_at||"").substring(0,10)})),score_trend:[]},
        progress:{available:false,overall_pct:0,completed_chapters:0,in_progress_chapters:0,subject_progress:{},last_chapter:null},
        weak_topics:weakTopics,
        activity:{last_active:null,feature_counts:{doubt:0},total_90d:0},
        achievements:[],
        recommendations:recs.slice(0,3).map(r=>({type:"rec",title:r.title||r.recommendation||"",body:r.body||r.description||"",priority:r.priority||"medium",action:"lessons"})),
        plan:{tasks:[{task:"Start a new lesson",done:false,type:"lesson"}],estimated_minutes:15},
      });
    } catch(e) {
      console.error("[StudentDashboard] load failed:", e.message);
      setData({success:false});
    } finally {
      setLoading(false);
    }
  },[user.username]);

  useEffect(function(){load();},[load]);

  useEffect(function(){
    getStudentExams().then(function(r){if(r?.success)setExams(r.exams||[]);}).catch(function(){});
  },[]);

  async function handleAddExam(e) {
    e.preventDefault();
    if(!examForm.title||!examForm.subject||!examForm.exam_date){setExamMsg("Title, subject and date are required.");return;}
    setExamLoading(true); setExamMsg(null);
    var res=await addStudentExam(examForm).catch(function(e2){return{success:false,error:e2.message};});
    setExamLoading(false);
    if(res?.success){
      setExams(function(prev){return[...prev,res.exam].sort(function(a,b){return a.exam_date>b.exam_date?1:-1;});});
      setShowAddExam(false);
      setExamForm({title:"",subject:"",exam_date:"",exam_type:""});
    } else { setExamMsg(res?.error||res?.detail||"Could not add exam."); }
  }

  async function handleCancelExam(examId) {
    await deleteStudentExam(examId).catch(function(){});
    setExams(function(prev){return prev.filter(function(e){return e.id!==examId;});});
  }

  function nav(page){if(setActivePage)setActivePage(page);}

  if(loading) return <Skel/>;
  if(!data||!data.success) return(
    <div className="sd-page" style={{padding:"24px 0"}}>
      <div style={{color:"var(--text-muted,#94a3b8)",padding:20}}>Dashboard is loading. Please try again. <button onClick={load} style={{color:"#6366f1",background:"none",border:"none",cursor:"pointer",fontFamily:"inherit",fontWeight:600}}>Retry</button></div>
    </div>
  );

  var s=data.student||{};
  var sub=data.subscription||{};
  var feat=data.features||{};
  var mt=data.mock_tests||{};
  var prog=data.progress||{};
  var weak=data.weak_topics||[];
  var act=data.activity||{};
  var ach=data.achievements||[];
  var recs=data.recommendations||[];
  var plan=data.plan||{};
  var name=(s.username||"Student").split(" ")[0];
  var isFree=sub.canonical_plan_key==="FREE_TIER"||!sub.has_full_access;

  // 50 daily motivation quotes — one unique quote per day of year (day % 50)
  var QUOTES=[
    {q:"Education is the most powerful weapon you can use to change the world.",a:"Nelson Mandela"},
    {q:"The expert in anything was once a beginner.",a:"Helen Hayes"},
    {q:"Success is the sum of small efforts, repeated day in and day out.",a:"Robert Collier"},
    {q:"Imagination is more important than knowledge.",a:"Albert Einstein"},
    {q:"In mathematics you don't understand things. You just get used to them.",a:"John von Neumann"},
    {q:"Pure mathematics is, in its way, the poetry of logical ideas.",a:"Albert Einstein"},
    {q:"The important thing is not to stop questioning.",a:"Albert Einstein"},
    {q:"Science is not only a disciple of reason but also one of romance and passion.",a:"Stephen Hawking"},
    {q:"The more I learn, the more I realize how much I don't know.",a:"Albert Einstein"},
    {q:"Mathematics is the language in which God has written the universe.",a:"Galileo Galilei"},
    {q:"An investment in knowledge pays the best interest.",a:"Benjamin Franklin"},
    {q:"It always seems impossible until it's done.",a:"Nelson Mandela"},
    {q:"Tell me and I forget. Teach me and I remember. Involve me and I learn.",a:"Benjamin Franklin"},
    {q:"Learning never exhausts the mind.",a:"Leonardo da Vinci"},
    {q:"Not all those who wander are lost, but some are lost in equations.",a:"Ada Lovelace"},
    {q:"The beautiful thing about learning is that no one can take it away from you.",a:"B.B. King"},
    {q:"Science is the father of knowledge, but opinion breeds ignorance.",a:"Hippocrates"},
    {q:"Research is formalized curiosity. It is poking and prying with a purpose.",a:"Zora Neale Hurston"},
    {q:"To raise new questions, new possibilities, to regard old problems from a new angle — this is what marks real advance in science.",a:"Albert Einstein"},
    {q:"The roots of education are bitter, but the fruit is sweet.",a:"Aristotle"},
    {q:"The more you know, the more you realize you know nothing.",a:"Socrates"},
    {q:"An ounce of practice is worth more than tons of preaching.",a:"Mahatma Gandhi"},
    {q:"Darkness cannot drive out darkness: only light can do that. Ignorance cannot drive out ignorance: only knowledge can do that.",a:"Inspired by Martin Luther King Jr."},
    {q:"First, solve the problem. Then, write the code.",a:"John Johnson"},
    {q:"The measure of intelligence is the ability to change.",a:"Albert Einstein"},
    {q:"You don't have to be great to start, but you have to start to be great.",a:"Zig Ziglar"},
    {q:"Equipped with his five senses, man explores the universe and calls the adventure Science.",a:"Edwin Hubble"},
    {q:"The whole of science is nothing more than a refinement of everyday thinking.",a:"Albert Einstein"},
    {q:"The greatest enemy of knowledge is not ignorance, it is the illusion of knowledge.",a:"Stephen Hawking"},
    {q:"Mathematics is not about numbers, equations, computations, or algorithms: it is about understanding.",a:"William Paul Thurston"},
    {q:"Without mathematics, there's nothing you can do. Everything around you is mathematics.",a:"Shakuntala Devi"},
    {q:"Even if you're on the right track, you'll get run over if you just sit there.",a:"Will Rogers"},
    {q:"Develop a passion for learning. If you do, you will never cease to grow.",a:"Anthony J. D'Angelo"},
    {q:"The function of education is to teach one to think intensively and to think critically.",a:"Martin Luther King Jr."},
    {q:"The only way to do great work is to love what you do.",a:"Steve Jobs"},
    {q:"In learning you will teach, and in teaching you will learn.",a:"Phil Collins"},
    {q:"Education is not the filling of a pail, but the lighting of a fire.",a:"W.B. Yeats"},
    {q:"The capacity to learn is a gift; the ability to learn is a skill; the willingness to learn is a choice.",a:"Brian Herbert"},
    {q:"Try to learn something about everything and everything about something.",a:"T.H. Huxley"},
    {q:"Creativity is intelligence having fun.",a:"Albert Einstein"},
    {q:"The secret of getting ahead is getting started.",a:"Mark Twain"},
    {q:"Science knows no country, because knowledge belongs to humanity.",a:"Louis Pasteur"},
    {q:"Do not be embarrassed by your failures, learn from them and start again.",a:"Richard Branson"},
    {q:"Perseverance is not a long race; it is many short races one after another.",a:"Walter Elliott"},
    {q:"Somewhere, something incredible is waiting to be known.",a:"Sharon Begley"},
    {q:"The science of today is the technology of tomorrow.",a:"Edward Teller"},
    {q:"Doubt is the origin of wisdom.",a:"René Descartes"},
    {q:"Study without desire spoils the memory, and it retains nothing that it takes in.",a:"Leonardo da Vinci"},
    {q:"Success is walking from failure to failure with no loss of enthusiasm.",a:"Winston Churchill"},
    {q:"Intelligence plus character — that is the goal of true education.",a:"Martin Luther King Jr."},
  ];
  // Day of year (0-364) % 50 — unique quote each day, cycling through all 50
  var _now=new Date();
  var _start=new Date(_now.getFullYear(),0,0);
  var _dayOfYear=Math.floor((_now-_start)/(1000*60*60*24));
  var qItem=QUOTES[_dayOfYear%QUOTES.length];

  return(
    <div className="sd-page" data-testid="student-dashboard-page">
      {/* Floating Report Issue button */}
      <button data-testid="report-issue-btn" onClick={() => setReportOpen(true)}
        style={{ position:"fixed", bottom:24, right:24, zIndex:500,
          background:"#6366f1", color:"#fff", border:"none", borderRadius:28,
          padding:"10px 18px", fontFamily:"inherit", fontWeight:700, fontSize:".82rem",
          cursor:"pointer", boxShadow:"0 4px 16px rgba(99,102,241,0.4)",
          display:"flex", alignItems:"center", gap:6 }}>
        🐛 Report Issue
      </button>
      <ReportIssueModal open={reportOpen} onClose={() => setReportOpen(false)}
        context={{ route: "dashboard", grade: user?.grade }}
        user={user} />

      {/* ── HERO ── */}
      <div className="sd-hero" data-testid="student-hero">
        <div>
          <div style={{fontSize:"1.3rem",fontWeight:800,color:"var(--text,#1e293b)",lineHeight:1.2}}>
            {greet()}, {name}! 👋
          </div>
          <div style={{fontSize:".85rem",color:"var(--text-muted,#64748b)",marginTop:3}}>
            Let's make today a productive learning day.
          </div>
        </div>
        <div style={{display:"flex",gap:10,flexShrink:0,flexWrap:"wrap"}}>
          <div className="sd-card" style={{padding:"10px 16px",textAlign:"center",minWidth:80}}>
            <div style={{fontSize:".65rem",color:"var(--text-muted,#64748b)"}}>Day Streak</div>
            <div style={{fontWeight:800,fontSize:"1.3rem",color:"#f59e0b"}}>{s.study_streak_days||0}</div>
            <div style={{fontSize:".6rem"}}>🔥</div>
          </div>
          <div className="sd-card" style={{padding:"10px 16px",textAlign:"center",minWidth:80}}>
            <div style={{fontSize:".65rem",color:"var(--text-muted,#64748b)"}}>Progress</div>
            <div style={{fontWeight:800,fontSize:"1.3rem",color:"#6366f1"}}>{prog.overall_pct||0}%</div>
            <div style={{fontSize:".6rem"}}>📈</div>
          </div>
        </div>
      </div>

      {/* ── QUICK STATS ── */}
      <div className="sd-quick-row" data-testid="student-quick-stats">
        {[
          {icon:"🎯",val:"45 min",label:"Today's Goal",sub:"Daily learning time",col:"#22c55e"},
          {icon:"📖",val:prog.in_progress_chapters||0,label:"Lessons Left",sub:"Complete today",col:"#6366f1"},
          {icon:"📅",val:"—",label:"Next Exam",sub:"Not scheduled",col:"#94a3b8"},
          {icon:"⭐",val:(act.total_90d||0),label:"XP Points",sub:"Keep learning!",col:"#f59e0b"},
        ].map(function(it){return(
          <SdCard key={it.label} style={{display:"flex",alignItems:"center",gap:10}}>
            <span style={{fontSize:"1.5rem",flexShrink:0}}>{it.icon}</span>
            <div>
              <div style={{fontWeight:800,fontSize:"1rem",color:it.col}}>{it.val}</div>
              <div style={{fontWeight:700,fontSize:".75rem",color:"var(--text,#1e293b)"}}>{it.label}</div>
              <div style={{fontSize:".65rem",color:"var(--text-muted,#94a3b8)"}}>{it.sub}</div>
            </div>
          </SdCard>
        );})}
      </div>

      {/* ── MAIN ROW: Continue Learning / Today's Plan / AI Coach ── */}
      <div className="sd-main-row">
        {/* Continue Learning */}
        <SdCard testid="continue-learning-card">
          <div style={{display:"flex",justifyContent:"space-between",marginBottom:8}}>
            <span style={{fontWeight:700,fontSize:".88rem"}}>Continue Learning</span>
            <button onClick={function(){nav("lessons");}} style={{background:"none",border:"none",color:"#6366f1",fontSize:".73rem",fontWeight:600,cursor:"pointer"}}>View all</button>
          </div>
          {prog.last_chapter?(
            <>
              <div style={{fontSize:".7rem",color:"var(--text-muted,#94a3b8)"}}>{prog.last_chapter.subject}</div>
              <div style={{fontWeight:700,fontSize:".9rem",margin:"4px 0 8px"}}>{prog.last_chapter.chapter}</div>
              <ProgBar pct={prog.last_chapter.progress_pct}/>
              <div style={{fontSize:".68rem",color:"var(--text-muted,#94a3b8)",marginBottom:10}}>{prog.last_chapter.progress_pct}% Complete</div>
              <SdBtn onClick={function(){nav("lessons");}}>Continue Learning →</SdBtn>
            </>
          ):(
            <>
              <div style={{color:"var(--text-muted,#94a3b8)",fontSize:".82rem",marginBottom:12}}>
                {prog.available?"Start a new lesson to continue here.":"Begin your first AI lesson today!"}
              </div>
              <SdBtn onClick={function(){nav("lessons");}}>Start Learning →</SdBtn>
            </>
          )}
        </SdCard>

        {/* Today's Plan */}
        <SdCard testid="todays-plan-card">
          <div style={{display:"flex",justifyContent:"space-between",marginBottom:8}}>
            <span style={{fontWeight:700,fontSize:".88rem"}}>Today's Plan</span>
            {plan.estimated_minutes&&<span style={{fontSize:".68rem",color:"var(--text-muted,#94a3b8)"}}>~{plan.estimated_minutes}min</span>}
          </div>
          {(plan.tasks||[]).length===0?(
            <div style={{color:"var(--text-muted,#94a3b8)",fontSize:".82rem"}}>No plan yet.</div>
          ):(
            <>
              {(plan.tasks||[]).map(function(t,i){return(
                <div key={i} style={{display:"flex",alignItems:"center",gap:7,marginBottom:7}}>
                  <span style={{fontSize:".9rem"}}>{t.done?"✅":"⭕"}</span>
                  <span style={{fontSize:".8rem",color:"var(--text,#1e293b)"}}>{t.task}</span>
                </div>
              );})}
            </>
          )}
        </SdCard>

        {/* AI Learning Coach */}
        <SdCard testid="ai-coach-card">
          <div style={{fontWeight:700,fontSize:".88rem",marginBottom:8}}>AI Learning Coach</div>
          {recs.length>0?(
            <>
              <div style={{fontSize:".82rem",marginBottom:6}}>{recs[0].body||"Keep up the great work!"}</div>
              <span style={{fontSize:".7rem",fontWeight:700,padding:"2px 8px",borderRadius:10,background:"#6366f118",color:"#6366f1"}}>{recs[0].title}</span>
              <div style={{marginTop:8}}>
                <button onClick={function(){nav(recs[0].action||"lessons");}} style={{background:"none",border:"none",color:"#6366f1",fontWeight:700,fontSize:".78rem",cursor:"pointer",fontFamily:"inherit"}}>
                  → {recs[0].action==="mock_test"?"Take Mock Test":recs[0].action==="subscription"?"Upgrade Plan":"Continue Lesson"}
                </button>
              </div>
            </>
          ):(
            <div style={{fontSize:".82rem",color:"var(--text-muted,#94a3b8)"}}>Keep practicing daily for best results.</div>
          )}
        </SdCard>
      </div>

      {/* ── MIDDLE ROW: Subject Progress / Mock Tests / Weak Topics / Achievements ── */}
      <div className="sd-mid-row">
        {/* Subject Progress */}
        <SdCard testid="subject-progress-card">
          <div style={{display:"flex",justifyContent:"space-between",marginBottom:10}}>
            <span style={{fontWeight:700,fontSize:".88rem"}}>Subject Progress</span>
            <button onClick={function(){nav("analytics");}} style={{background:"none",border:"none",color:"#6366f1",fontSize:".73rem",fontWeight:600,cursor:"pointer"}}>View all</button>
          </div>
          {Object.entries(mt.subject_averages||{}).length===0?(
            <div style={{color:"var(--text-muted,#94a3b8)",fontSize:".82rem"}}>Complete mock tests to track progress.</div>
          ):(
            Object.entries(mt.subject_averages||{}).slice(0,4).map(function([s,avg]){return(
              <div key={s} style={{marginBottom:8}}>
                <div style={{display:"flex",justifyContent:"space-between",fontSize:".78rem",marginBottom:2}}>
                  <span style={{fontWeight:600}}>{s}</span>
                  <span style={{fontWeight:700,color:subjCol(s)}}>{avg}%</span>
                </div>
                <ProgBar pct={avg} color={subjCol(s)}/>
              </div>
            );})
          )}
        </SdCard>

        {/* Recent Mock Tests */}
        <SdCard testid="recent-mock-tests-card">
          <div style={{display:"flex",justifyContent:"space-between",marginBottom:10}}>
            <span style={{fontWeight:700,fontSize:".88rem"}}>Recent Mock Tests</span>
            <button onClick={function(){nav("mockTest");}} style={{background:"none",border:"none",color:"#6366f1",fontSize:".73rem",fontWeight:600,cursor:"pointer"}}>View all</button>
          </div>
          {(mt.recent||[]).length===0?(
            <div style={{color:"var(--text-muted,#94a3b8)",fontSize:".82rem",marginBottom:10}}>No tests taken yet.</div>
          ):(
            (mt.recent||[]).slice(0,3).map(function(t,i){
              var sc=safePct(t.score);
              var col=sc===null?"#94a3b8":sc>=60?"#22c55e":sc>=40?"#f59e0b":"#ef4444";
              return(
                <div key={i} style={{display:"flex",justifyContent:"space-between",padding:"5px 0",borderBottom:"1px solid var(--border,#f1f5f9)",fontSize:".78rem"}}>
                  <div>
                    <div style={{fontWeight:600}}>{t.subject||"—"}</div>
                    <div style={{fontSize:".68rem",color:"var(--text-muted,#94a3b8)"}}>{t.date}</div>
                  </div>
                  <span style={{fontWeight:700,color:col}}>{sc!==null?sc+"%":"N/A"}</span>
                </div>
              );
            })
          )}
          <div style={{marginTop:10}}>
            <SdBtn small onClick={function(){nav("mockTest");}}>Take a Mock Test →</SdBtn>
          </div>
        </SdCard>

        {/* Weak Topics */}
        <SdCard testid="weak-topics-card">
          <div style={{display:"flex",justifyContent:"space-between",marginBottom:10}}>
            <span style={{fontWeight:700,fontSize:".88rem"}}>Weak Topics</span>
            <button onClick={function(){nav("lessons");}} style={{background:"none",border:"none",color:"#6366f1",fontSize:".73rem",fontWeight:600,cursor:"pointer"}}>View all</button>
          </div>
          {weak.length===0?(
            <div style={{color:"var(--text-muted,#94a3b8)",fontSize:".82rem"}}>No weak areas detected. Keep practising!</div>
          ):(
            weak.slice(0,3).map(function(t,i){return(
              <div key={i} style={{display:"flex",justifyContent:"space-between",alignItems:"center",padding:"5px 0",borderBottom:"1px solid var(--border,#f1f5f9)"}}>
                <div>
                  <div style={{fontSize:".78rem",fontWeight:600}}>{t.chapter}</div>
                  <div style={{fontSize:".68rem",color:"var(--text-muted,#94a3b8)"}}>{t.subject}</div>
                </div>
                <SdBtn small outline onClick={function(){nav("lessons");}}>Practice →</SdBtn>
              </div>
            );}
          ))}
        </SdCard>

        {/* Achievements */}
        <SdCard testid="achievements-card">
          <div style={{display:"flex",justifyContent:"space-between",marginBottom:10}}>
            <span style={{fontWeight:700,fontSize:".88rem"}}>Achievements</span>
          </div>
          {(ach.length>0?ach:[
            {type:"streak",title:"Day Streak",icon:"🔥",value:s.study_streak_days||0},
            {type:"lessons",title:"Lessons Completed",icon:"📖",value:s.lessons_completed||0},
            {type:"first_test",title:"First Mock Test",icon:"🏆",value:mt.total||0},
          ]).map(function(a,i){return(
            <div key={i} style={{display:"flex",alignItems:"center",gap:10,padding:"6px 0",borderBottom:"1px solid var(--border,#f1f5f9)"}}>
              <span style={{fontSize:"1.2rem"}}>{a.icon}</span>
              <div>
                <div style={{fontSize:".8rem",fontWeight:700}}>{a.title}</div>
                <div style={{fontSize:".68rem",color:"var(--text-muted,#94a3b8)"}}>{a.value>0?(a.type==="streak"?"Keep it going!":a.type==="first_test"?"Great start!":"Amazing!"):"Start your journey!"}</div>
              </div>
            </div>
          );})}
        </SdCard>
      </div>

      {/* ── UTILITY ROW ── */}
      <div className="sd-util-row" data-testid="student-utility-cards">
        {/* Revision Center */}
        <SdCard>
          <div style={{fontWeight:700,fontSize:".85rem",marginBottom:4}}>Revision Center</div>
          <div style={{fontSize:".75rem",color:"var(--text-muted,#64748b)",marginBottom:3}}>Today's Revision</div>
          <div style={{fontWeight:800,fontSize:"1.1rem"}}>{weak.length||0} Chapters</div>
          <div style={{fontSize:".7rem",color:"var(--text-muted,#94a3b8)",marginBottom:10}}>Keep your concepts sharp</div>
          <SdBtn small outline onClick={function(){nav("lessons");}}>Review Now →</SdBtn>
        </SdCard>
        {/* AI Doubt Solver */}
        <SdCard>
          <div style={{fontWeight:700,fontSize:".85rem",marginBottom:4}}>AI Doubt Solver</div>
          <div style={{fontSize:".75rem",color:"var(--text-muted,#64748b)",marginBottom:8}}>
            {(act.feature_counts?.doubt||0)>0?"Continue your last chat":"Start asking doubts"}
          </div>
          {isFree&&feat.ask_doubts_limited&&<div style={{fontSize:".7rem",color:"#f59e0b",marginBottom:6}}>Limited (Free Tier)</div>}
          <SdBtn small outline onClick={function(){nav("askDoubt");}}>Continue Chat →</SdBtn>
        </SdCard>
        {/* Upcoming Exams — real data */}
        <SdCard testid="upcoming-exams-card">
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:8}}>
            <span style={{fontWeight:700,fontSize:".85rem"}}>Upcoming Exams</span>
            <button onClick={function(){setShowAddExam(true);setExamMsg(null);}} style={{background:"#6366f1",border:"none",color:"#fff",borderRadius:6,padding:"3px 10px",fontSize:".7rem",fontWeight:600,cursor:"pointer"}}>+ Add</button>
          </div>
          {exams.length===0?(
            <>
              <div style={{color:"var(--text-muted,#94a3b8)",fontSize:".78rem",marginBottom:6}}>No upcoming exams added yet.</div>
              <div style={{fontSize:".7rem",color:"var(--text-muted,#64748b)",marginBottom:10}}>You or your parent can add exam dates.</div>
              <SdBtn small outline onClick={function(){nav("mockTest");}}>Practise Now →</SdBtn>
            </>
          ):(
            exams.slice(0,3).map(function(ex){return(
              <div key={ex.id} style={{display:"flex",justifyContent:"space-between",alignItems:"center",padding:"5px 0",borderBottom:"1px solid var(--border,#f1f5f9)"}}>
                <div>
                  <div style={{fontSize:".78rem",fontWeight:600}}>{ex.subject}</div>
                  <div style={{fontSize:".68rem",color:"var(--text-muted,#94a3b8)"}}>{ex.title} · {ex.exam_date}</div>
                </div>
                <div style={{textAlign:"right"}}>
                  <div style={{fontWeight:800,fontSize:".88rem",color:ex.days_until<=7?"#ef4444":"#6366f1"}}>{ex.days_until}d</div>
                  <button onClick={function(){handleCancelExam(ex.id);}} style={{background:"none",border:"none",color:"#94a3b8",fontSize:".65rem",cursor:"pointer"}}>Cancel</button>
                </div>
              </div>
            );})
          )}
        </SdCard>
        {/* Quick Actions — clear destinations or explicit disabled state */}
        <SdCard testid="quick-actions-card">
          <div style={{fontWeight:700,fontSize:".85rem",marginBottom:8}}>Quick Actions</div>

          {/* Watch Concept Videos → Learn More (resources) */}
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",padding:"5px 0",borderBottom:"1px solid var(--border,#f8fafc)"}}>
            <span style={{fontSize:".75rem"}}>Watch Concept Videos</span>
            <button data-testid="qa-watch-concept-videos" onClick={function(){nav("resources");}}
              style={{background:"none",border:"none",color:"#6366f1",fontWeight:700,cursor:"pointer",fontSize:".8rem"}}
              title="Opens Learn More — concept videos & resources">›</button>
          </div>

          {/* Practice Questions → Mock Test (nearest available practice flow) */}
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",padding:"5px 0",borderBottom:"1px solid var(--border,#f8fafc)"}}>
            <span style={{fontSize:".75rem"}}>Practice Questions</span>
            <button data-testid="qa-practice-questions" onClick={function(){nav("mockTest");}}
              style={{background:"none",border:"none",color:"#6366f1",fontWeight:700,cursor:"pointer",fontSize:".8rem"}}
              title="Practice via Mock Tests">›</button>
          </div>

          {/* Formula Sheet → Formula Sheet page */}
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",padding:"5px 0",borderBottom:"1px solid var(--border,#f8fafc)"}}>
            <span style={{fontSize:".75rem"}}>Formula Sheet</span>
            <button data-testid="qa-formula-sheet" onClick={function(){nav("formulaSheet");}}
              style={{background:"none",border:"none",color:"#6366f1",fontWeight:700,cursor:"pointer",fontSize:".8rem"}}
              title="CBSE formula reference sheets">›</button>
          </div>

          {/* Study Materials → Learn More (resources) */}
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",padding:"5px 0",borderBottom:"1px solid var(--border,#f8fafc)"}}>
            <span style={{fontSize:".75rem"}}>Study Materials</span>
            <button data-testid="qa-study-materials" onClick={function(){nav("resources");}}
              style={{background:"none",border:"none",color:"#6366f1",fontWeight:700,cursor:"pointer",fontSize:".8rem"}}
              title="Opens Learn More — study materials & videos">›</button>
          </div>
        </SdCard>
      </div>

      {/* ── MOTIVATION ── */}
      <div className="sd-motivation" data-testid="motivation-card">
        <div style={{flex:1}}>
          <div style={{fontWeight:700,fontSize:"1rem",marginBottom:4}}>Motivation for You 💡</div>
          <div style={{fontSize:".9rem",fontStyle:"italic",marginBottom:4}}>&ldquo;{qItem.q}&rdquo;</div>
          <div style={{fontSize:".75rem",opacity:.8}}>— {qItem.a}</div>
        </div>
        <div style={{fontSize:"4rem",opacity:.6}}>📚</div>
      </div>

      {/* Add Exam Modal */}
      {showAddExam&&(
        <div style={{position:"fixed",inset:0,background:"rgba(0,0,0,.5)",zIndex:500,display:"flex",alignItems:"center",justifyContent:"center",padding:16}}>
          <div style={{background:"var(--panel,#fff)",borderRadius:14,padding:"16px 18px",width:"100%",maxWidth:400,boxShadow:"0 8px 32px rgba(0,0,0,.2)"}}>
            <div style={{display:"flex",justifyContent:"space-between",marginBottom:14}}>
              <h4 style={{margin:0,fontSize:".95rem"}}>Add Exam Date</h4>
              <button onClick={function(){setShowAddExam(false);}} style={{background:"none",border:"none",cursor:"pointer",fontSize:"1.1rem"}}>✕</button>
            </div>
            <form onSubmit={handleAddExam} style={{display:"flex",flexDirection:"column",gap:8}}>
              <input placeholder="Exam Title *" value={examForm.title} onChange={function(ev){setExamForm(function(p){return{...p,title:ev.target.value};});}} required style={{padding:"8px 12px",borderRadius:8,border:"1px solid var(--border,#e5e7eb)",fontFamily:"inherit",fontSize:".85rem"}}/>
              <input placeholder="Subject *" value={examForm.subject} onChange={function(ev){setExamForm(function(p){return{...p,subject:ev.target.value};});}} required style={{padding:"8px 12px",borderRadius:8,border:"1px solid var(--border,#e5e7eb)",fontFamily:"inherit",fontSize:".85rem"}}/>
              <input type="date" value={examForm.exam_date} onChange={function(ev){setExamForm(function(p){return{...p,exam_date:ev.target.value};});}} required style={{padding:"8px 12px",borderRadius:8,border:"1px solid var(--border,#e5e7eb)",fontFamily:"inherit",fontSize:".85rem"}}/>
              <select value={examForm.exam_type} onChange={function(ev){setExamForm(function(p){return{...p,exam_type:ev.target.value};});}} style={{padding:"8px 12px",borderRadius:8,border:"1px solid var(--border,#e5e7eb)",fontFamily:"inherit",fontSize:".85rem"}}>
                <option value="">Exam Type (optional)</option>
                <option value="Unit Test">Unit Test</option>
                <option value="Mid-Term">Mid-Term</option>
                <option value="Final Exam">Final Exam</option>
                <option value="Board Exam">Board Exam</option>
                <option value="Other">Other</option>
              </select>
              {examMsg&&<div style={{color:"#dc2626",fontSize:".8rem"}}>{examMsg}</div>}
              <button type="submit" disabled={examLoading} style={{padding:"9px",borderRadius:8,border:"none",background:"#6366f1",color:"#fff",fontFamily:"inherit",fontWeight:700,fontSize:".85rem",cursor:examLoading?"not-allowed":"pointer"}}>
                {examLoading?"Saving…":"Add Exam"}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
