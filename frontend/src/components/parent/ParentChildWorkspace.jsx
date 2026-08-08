/**
 * ParentChildWorkspace.jsx
 * Redesigned child detail workspace — story-driven, parent-friendly.
 * 9 meaningful sections: Overview, Today's Plan, Progress Story,
 * Strengths & Needs, Mock Tests, Homework & Exams, Notifications,
 * Platform Access, Report
 */
import { useCallback, useEffect, useRef, useState } from "react";
import {
  getChildDetail,
  getChildAnalytics,
  getChildAcademicInsights,
  getChildProgressReport,
} from "../../api/parentDashboard";
import ParentAccessExplanation from "./ParentAccessExplanation";
import ParentProgressStory from "./ParentProgressStory";
import ParentNotificationGroups from "./ParentNotificationGroups";

// Lazy-loaded on click — jsPDF + jspdf-autotable + the embedded Devanagari
// font add ~250KB and have no reason to be in every parent's initial bundle.
function downloadProgressReportPdf(report){
  import("../../utils/progressReportPdf").then(function(mod){
    mod.generateProgressReportPdf(report);
  });
}

// ── Design tokens ─────────────────────────────────────────────────────────────
var btn1={padding:"7px 14px",borderRadius:8,border:"none",background:"#6366f1",color:"#fff",fontFamily:"inherit",fontSize:".8rem",fontWeight:700,cursor:"pointer"};
var card={background:"var(--panel,#fff)",border:"1px solid var(--border,#e5e7eb)",borderRadius:12,padding:"14px 16px",marginBottom:12};

// ── Fetch error banner — distinct from an empty/no-data state ────────────────
function FetchErrorBanner({message, onRetry}){
  return(
    <div role="alert" data-testid="workspace-fetch-error"
      style={{background:"#fef2f2",border:"1px solid #fecaca",borderRadius:8,padding:"10px 14px",marginBottom:12,display:"flex",justifyContent:"space-between",alignItems:"center",gap:10,flexWrap:"wrap"}}>
      <span style={{fontSize:".8rem",color:"#dc2626"}}>⚠ {message}</span>
      <button data-testid="workspace-retry-btn" onClick={onRetry}
        style={{padding:"4px 12px",borderRadius:6,border:"1px solid #dc2626",background:"none",color:"#dc2626",fontFamily:"inherit",fontSize:".75rem",fontWeight:700,cursor:"pointer"}}>
        Retry
      </button>
    </div>
  );
}

// ── Section tab bar ───────────────────────────────────────────────────────────
var TABS=[
  {key:"overview",    label:"Overview"},
  {key:"plan",        label:"Today's Plan"},
  {key:"progress",    label:"Progress"},
  {key:"strengths",   label:"Strengths"},
  {key:"mock",        label:"Mock Tests"},
  {key:"homework",    label:"Homework"},
  {key:"notifs",      label:"Notifications"},
  {key:"access",      label:"Access"},
  {key:"report",      label:"Report"},
];

// ── Overview section ──────────────────────────────────────────────────────────
function OverviewSection({child, detail, analytics: _analytics, onUpgrade}){
  var plan=detail?.plan||child?.plan||{};
  var isFree=plan.canonical_plan_key==="FREE_TIER"||!plan.has_full_access;
  var mt=detail?.mock_tests||{};
  var act=detail?.ai_activity||{};
  var progress=detail?.progress||{};
  var weakTopics=progress.weak_topics||[];
  var lastActive=act.last_active?new Date(act.last_active).toLocaleDateString():"Never";

  var recs=detail?.recommendations||[];
  var topRec=recs.sort(function(a,b){var p={"high":0,"medium":1,"low":2};return(p[a.priority||"low"]||2)-(p[b.priority||"low"]||2);})[0];

  return(
    <div data-testid="workspace-section-overview">
      {/* Hero status */}
      <div style={{...card,background:isFree?"rgba(239,68,68,.04)":"rgba(34,197,94,.04)",border:"1px solid "+(isFree?"#fca5a5":"#86efac")}}>
        <div style={{fontWeight:800,fontSize:".95rem",color:isFree?"#dc2626":"#166534"}}>
          {isFree?"Free Tier":"Full Platform Access"}
        </div>
        <div style={{fontSize:".78rem",color:"#64748b",marginTop:2}}>{plan.description}</div>
        {plan.expiry_warning&&<div style={{fontSize:".72rem",color:"#d97706",fontWeight:600,marginTop:2}}>Expires in {plan.days_remaining} day{plan.days_remaining!==1?"s":""}</div>}
      </div>

      {/* Quick stats */}
      <div style={{display:"flex",gap:8,flexWrap:"wrap",marginBottom:12}}>
        {[
          {label:"Mock Tests",value:mt.count??0,color:"#0ea5e9"},
          {label:"Avg Score",value:mt.average_score!=null?mt.average_score+"%":"—",color:mt.average_score>=60?"#22c55e":mt.average_score>=40?"#f59e0b":"#ef4444"},
          {label:"Last Active",value:lastActive,color:"#6366f1"},
        ].map(function(s){return(
          <div key={s.label} style={{background:"var(--surface2,#f8fafc)",border:"1px solid var(--border,#e5e7eb)",borderRadius:8,padding:"7px 12px",textAlign:"center",flex:"1 1 80px"}}>
            <div style={{fontWeight:800,fontSize:".88rem",color:s.color}}>{s.value}</div>
            <div style={{fontSize:".63rem",color:"#64748b"}}>{s.label}</div>
          </div>
        );})}
      </div>

      {/* Top recommendation */}
      {topRec&&(
        <div style={{...card,borderLeft:"3px solid "+({high:"#ef4444",medium:"#f59e0b",low:"#22c55e"}[topRec.priority]||"#6366f1")}}>
          <div style={{fontWeight:700,fontSize:".82rem",marginBottom:2}}>{topRec.title}</div>
          <div style={{fontSize:".76rem",color:"#64748b"}}>{topRec.body}</div>
          {topRec.action==="upgrade"&&onUpgrade&&(
            <button onClick={onUpgrade} style={{...btn1,marginTop:8,fontSize:".75rem",padding:"5px 12px",background:"transparent",border:"1px solid #6366f1",color:"#6366f1"}}>View Plans</button>
          )}
        </div>
      )}
      {!topRec&&plan.has_full_access&&(
        <div style={{...card,background:"rgba(34,197,94,.06)",border:"1px solid #86efac"}}>
          <div style={{fontWeight:700,fontSize:".82rem",color:"#166534"}}>All good!</div>
          <div style={{fontSize:".76rem",color:"#64748b",marginTop:2}}>Your child is on track. Keep encouraging regular practice.</div>
        </div>
      )}

      {/* Weak topics preview */}
      {weakTopics.length>0&&(
        <div style={card}>
          <div style={{fontWeight:700,marginBottom:6,fontSize:".82rem",color:"#ef4444"}}>Needs Practice</div>
          {weakTopics.slice(0,2).map(function(t,i){return(
            <div key={i} style={{fontSize:".75rem",padding:"3px 0",borderBottom:"1px solid var(--border,#f1f5f9)"}}>{t.subject} — {t.chapter}</div>
          );})}
        </div>
      )}
    </div>
  );
}

// ── Today's Plan section ──────────────────────────────────────────────────────
function TodaysPlanSection({detail, onUpgrade, onSectionNav}){
  var recs=(detail?.recommendations||[]).slice();
  recs.sort(function(a,b){var p={"high":0,"medium":1,"low":2};return(p[a.priority||"low"]||2)-(p[b.priority||"low"]||2);});
  var plan=detail?.plan||{};

  if(!recs.length){
    return(
      <div data-testid="workspace-section-plan">
        {plan.has_full_access?(
          <div style={{...card,background:"rgba(34,197,94,.06)",border:"1px solid #86efac"}}>
            <div style={{fontWeight:700,color:"#166534"}}>Nothing urgent today</div>
            <div style={{fontSize:".78rem",color:"#64748b",marginTop:3}}>Encourage daily practice. Try a mock test or lesson to keep the momentum going.</div>
            <button onClick={function(){onSectionNav("mock");}} style={{...btn1,marginTop:8,fontSize:".75rem",padding:"5px 12px"}}>📝 Start Mock Test</button>
          </div>
        ):(
          <div style={card}>
            <div style={{fontWeight:700}}>Limited access — upgrade to unlock</div>
            <div style={{fontSize:".78rem",color:"#64748b",marginTop:3}}>Upgrade to unlock all lessons, mock tests, and Exemplar practice.</div>
            {onUpgrade&&<button onClick={onUpgrade} style={{...btn1,marginTop:8,fontSize:".75rem",padding:"5px 12px",background:"transparent",border:"1px solid #6366f1",color:"#6366f1"}}>View Plans</button>}
          </div>
        )}
      </div>
    );
  }

  var prioColor={"high":"#ef4444","medium":"#f59e0b","low":"#22c55e"};
  return(
    <div data-testid="workspace-section-plan">
      <div style={{fontWeight:700,marginBottom:10,fontSize:".85rem"}}>Recommended for Today</div>
      {recs.map(function(r,i){return(
        <div key={i} style={{...card,borderLeft:"3px solid "+(prioColor[r.priority]||"#6366f1"),marginBottom:8}}>
          <div style={{fontWeight:700,fontSize:".82rem",color:prioColor[r.priority]||"#6366f1"}}>{r.title}</div>
          <div style={{fontSize:".76rem",color:"#64748b",marginTop:2}}>{r.body}</div>
          <div style={{display:"flex",gap:6,marginTop:8,flexWrap:"wrap"}}>
            {r.action==="upgrade"&&onUpgrade&&<button onClick={onUpgrade} style={{...btn1,fontSize:".72rem",padding:"4px 10px",background:"transparent",border:"1px solid #6366f1",color:"#6366f1"}}>View Plans</button>}
            {r.action==="mock_tests"&&<button onClick={function(){onSectionNav("mock");}} style={{...btn1,fontSize:".72rem",padding:"4px 10px",background:"#0ea5e9"}}>Mock Tests</button>}
            {r.action==="view_progress"&&<button onClick={function(){onSectionNav("progress");}} style={{...btn1,fontSize:".72rem",padding:"4px 10px",background:"#6366f1"}}>Progress</button>}
          </div>
        </div>
      );})}
    </div>
  );
}

// ── Mock Tests section ────────────────────────────────────────────────────────
function MockTestsSection({detail, plan, onUpgrade}){
  var mt=detail?.mock_tests||{};
  var isFree=plan?.canonical_plan_key==="FREE_TIER";
  return(
    <div data-testid="workspace-section-mock">
      {isFree&&mt.free_daily_limit&&(
        <div style={{...card,background:"rgba(245,158,11,.07)",border:"1px solid #fcd34d",marginBottom:8}}>
          <div style={{fontWeight:600,color:"#d97706"}}>Free Tier: {mt.free_daily_limit} mock tests/day</div>
          <div style={{fontSize:".75rem",color:"#64748b",marginTop:2}}>Upgrade for unlimited mock tests and full analysis.</div>
          {onUpgrade&&<button onClick={onUpgrade} style={{...btn1,marginTop:8,fontSize:".75rem",padding:"5px 12px",background:"transparent",border:"1px solid #6366f1",color:"#6366f1"}}>View Plans</button>}
        </div>
      )}
      {!mt.available?(
        <div style={{color:"#64748b",fontSize:".78rem",padding:"8px 0"}}>
          {mt.count===0?"No mock tests attempted yet. Encourage your child to try one!":"Mock test data unavailable."}
        </div>
      ):(
        <>
          <div style={{display:"flex",gap:8,flexWrap:"wrap",marginBottom:12}}>
            <div style={{background:"var(--surface2,#f8fafc)",border:"1px solid var(--border,#e5e7eb)",borderRadius:8,padding:"8px 14px",textAlign:"center",flex:"1 1 80px"}}>
              <div style={{fontWeight:800,fontSize:"1.2rem",color:"#0ea5e9"}}>{mt.count||0}</div>
              <div style={{fontSize:".65rem",color:"#64748b"}}>Tests Done</div>
            </div>
            <div style={{background:"var(--surface2,#f8fafc)",border:"1px solid var(--border,#e5e7eb)",borderRadius:8,padding:"8px 14px",textAlign:"center",flex:"1 1 80px"}}>
              <div style={{fontWeight:800,fontSize:"1.2rem",color:mt.average_score>=60?"#22c55e":mt.average_score>=40?"#f59e0b":"#ef4444"}}>
                {mt.average_score!=null?mt.average_score+"%":"—"}
              </div>
              <div style={{fontSize:".65rem",color:"#64748b"}}>Avg Score</div>
            </div>
          </div>
          {(mt.recent||[]).length>0&&(
            <div style={card}>
              <div style={{fontWeight:700,marginBottom:6,fontSize:".82rem"}}>Recent Tests</div>
              {mt.recent.map(function(t,i){
                var pct=t.score!=null?Math.round(t.score):0;
                return(
                  <div key={i} style={{display:"flex",justifyContent:"space-between",padding:"4px 0",borderBottom:"1px solid var(--border,#f1f5f9)",fontSize:".78rem"}}>
                    <span>{t.subject||"—"}{t.chapter&&<span style={{color:"#94a3b8",fontSize:".7rem"}}> · {t.chapter.substring(0,30)}</span>}</span>
                    <span style={{fontWeight:700,color:pct>=60?"#166534":pct>=40?"#d97706":"#dc2626"}}>{pct}%</span>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ── Homework & Exams section ──────────────────────────────────────────────────
function HomeworkExamsSection({insights}){
  if(!insights) return(
    <div data-testid="workspace-section-homework" style={{color:"#94a3b8",fontSize:".82rem",padding:"8px 0"}}>
      ⏳ Loading homework and exam data…
    </div>
  );
  return(
    <div data-testid="workspace-section-homework">
      <div style={{...card,background:"rgba(148,163,184,.06)"}}>
        <div style={{fontWeight:700,fontSize:".82rem",marginBottom:2}}>Homework</div>
        <div style={{fontSize:".78rem",color:"#94a3b8"}}>{insights.homework?.message||"Homework tracking is not enabled yet."}</div>
      </div>
      <div style={{...card,background:"rgba(148,163,184,.06)"}}>
        <div style={{fontWeight:700,fontSize:".82rem",marginBottom:2}}>Exams</div>
<div style={{fontSize:".78rem",color:"#94a3b8"}}>{insights.exams?.message||"Exam schedule is not available yet."}</div>
      </div>
      {/* Mock test recommendations from insights */}
      {(insights.mock_test_recommendations?.recommendations||[]).length>0&&(
        <div style={card}>
          <div style={{fontWeight:700,fontSize:".82rem",marginBottom:6}}>Mock Test Suggestions</div>
          {insights.mock_test_recommendations.recommendations.map(function(r,i){return(
            <div key={i} style={{fontSize:".78rem",padding:"4px 0",borderBottom:"1px solid var(--border,#f1f5f9)"}}>
              <strong>{r.title}</strong>
              <div style={{fontSize:".73rem",color:"#64748b",marginTop:1}}>{r.description}</div>
            </div>
          );})}
        </div>
      )}
      {/* Revision suggestions */}
      {(insights.revision_suggestions?.topics||[]).length>0&&(
        <div style={card}>
          <div style={{fontWeight:700,fontSize:".82rem",marginBottom:6}}>Revision Suggestions</div>
          {insights.revision_suggestions.topics.map(function(t,i){return(
            <div key={i} style={{fontSize:".75rem",padding:"3px 0",borderBottom:"1px solid var(--border,#f1f5f9)"}}>
              <strong>{t.subject}</strong> — {t.chapter}
            </div>
          );})}
        </div>
      )}
    </div>
  );
}

// ── Report section ────────────────────────────────────────────────────────────
function ReportSection({report, loading}){
  if(loading) return <div style={{color:"#94a3b8",padding:"8px 0"}}>⏳ Loading report…</div>;
  if(!report) return <div style={{color:"#94a3b8",padding:"8px 0"}}>🖨️ Report will load shortly. If it persists, the service may be updating.</div>;
  return(
    <div data-testid="workspace-section-report">
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:12}}>
        <div style={{fontWeight:700,fontSize:".88rem"}}>Progress Report</div>
        <div style={{display:"flex",gap:8}}>
          <button onClick={function(){window.print();}} style={{...btn1,padding:"5px 14px",fontSize:".75rem"}}>🖨️ Print</button>
          <button data-testid="download-pdf-btn" onClick={function(){downloadProgressReportPdf(report);}}
            style={{...btn1,padding:"5px 14px",fontSize:".75rem",background:"#0ea5e9"}}>⬇️ Download PDF</button>
        </div>
      </div>
      <div style={{fontSize:".7rem",color:"#94a3b8",marginBottom:10}}>Generated: {report.generated_at?new Date(report.generated_at).toLocaleString():""}</div>
      {/* Child info */}
      <div style={{...card,background:"var(--surface2,#f8fafc)"}}>
        <div style={{fontWeight:700}}>{report.child?.name}</div>
        <div style={{fontSize:".78rem",color:"#64748b"}}>{report.child?.grade} · {report.child?.board}</div>
      </div>
      {/* Progress */}
      <div style={card}>
        <div style={{fontWeight:700,marginBottom:4}}>Progress</div>
        {report.progress_summary?.available
          ?<div style={{fontSize:".78rem",color:"#64748b"}}>{report.progress_summary.completed_chapters} chapters completed of {report.progress_summary.total_tracked} tracked.</div>
          :<div style={{fontSize:".78rem",color:"#94a3b8"}}>No progress data yet.</div>
        }
      </div>
      {/* Mock tests */}
      <div style={card}>
        <div style={{fontWeight:700,marginBottom:4}}>Mock Tests</div>
        {report.mock_test_summary?.available
          ?<div style={{fontSize:".78rem",color:"#64748b"}}>{report.mock_test_summary.tests_taken} tests · Avg: {report.mock_test_summary.average_score!=null?report.mock_test_summary.average_score+"%":"—"}</div>
          :<div style={{fontSize:".78rem",color:"#94a3b8"}}>No mock test data yet.</div>
        }
      </div>
      {/* Strengths */}
      {(report.strengths||[]).length>0&&(
        <div style={card}>
          <div style={{fontWeight:700,marginBottom:4,color:"#22c55e"}}>Strengths</div>
          {report.strengths.map(function(s,i){return <span key={i} style={{fontSize:".75rem",background:"rgba(34,197,94,.1)",color:"#166534",padding:"2px 7px",borderRadius:5,marginRight:5,display:"inline-block"}}>{s}</span>;})}
        </div>
      )}
      {/* Areas for improvement */}
      {(report.areas_for_improvement||[]).length>0&&(
        <div style={card}>
          <div style={{fontWeight:700,marginBottom:4,color:"#ef4444"}}>Areas for Improvement</div>
          {report.areas_for_improvement.slice(0,3).map(function(a,i){return(
            <div key={i} style={{fontSize:".75rem",padding:"2px 0",borderBottom:"1px solid var(--border,#f1f5f9)"}}>{a.subject} — {a.chapter}</div>
          );})}
        </div>
      )}
      {/* Disclaimer */}
      <div style={{fontSize:".68rem",color:"#94a3b8",borderTop:"1px solid var(--border,#f1f5f9)",paddingTop:8,marginTop:4}}>{report.disclaimer}</div>
    </div>
  );
}

// ── Strengths & Needs section ─────────────────────────────────────────────────
function StrengthsNeedsSection({analytics}){
  if(!analytics) return <div style={{color:"#94a3b8",fontSize:".78rem",padding:"8px 0"}}>⏳ Loading…</div>;
  var strengths=analytics.strengths||{};
  var weaknesses=analytics.weaknesses||{};
  return(
    <div data-testid="workspace-section-strengths">
      <div style={{marginBottom:12}}>
        <div style={{fontWeight:700,fontSize:".85rem",color:"#22c55e",marginBottom:6}}>Strengths</div>
        {strengths.available&&strengths.strong_subjects?.length>0
          ?<div style={{display:"flex",flexWrap:"wrap",gap:5}}>
              {strengths.strong_subjects.map(function(s,i){return <span key={i} style={{background:"rgba(34,197,94,.1)",color:"#166534",fontSize:".75rem",fontWeight:600,padding:"3px 8px",borderRadius:5}}>{s}</span>;})}
            </div>
          :<div style={{fontSize:".78rem",color:"#94a3b8"}}>No strong subjects identified yet. Complete more mock tests to see strengths.</div>
        }
      </div>
      <div>
        <div style={{fontWeight:700,fontSize:".85rem",color:"#ef4444",marginBottom:6}}>Needs Practice</div>
        {weaknesses.available&&(weaknesses.weak_topics||[]).length>0&&(
          weaknesses.weak_topics.slice(0,5).map(function(t,i){return(
            <div key={i} style={{background:"rgba(239,68,68,.04)",border:"1px solid #fca5a5",borderRadius:8,padding:"8px 12px",marginBottom:6}}>
              <div style={{fontSize:".78rem",fontWeight:600}}>{t.subject} — {t.chapter}</div>
              {t.score!=null&&<div style={{fontSize:".72rem",color:"#94a3b8",marginTop:2}}>Best score: {t.score}%</div>}
              <div style={{fontSize:".72rem",color:"#64748b",marginTop:1}}>{t.explanation||"Review this topic for improvement."}</div>
            </div>
          );})
        )}
        {(!weaknesses.available||(weaknesses.weak_topics||[]).length===0)&&(
          <div style={{fontSize:".78rem",color:"#94a3b8"}}>No weak areas detected yet.</div>
        )}
      </div>
    </div>
  );
}

// ── Main workspace drawer ─────────────────────────────────────────────────────
export default function ParentChildWorkspace({child, onClose, onUpgrade}){
  var [tab,setTab]    = useState("overview");
  var [detail,setDetail]   = useState(null);
  var [analytics,setAnalytics] = useState(null);
  var [insights,setInsights]   = useState(null);
  var [report,setReport]       = useState(null);
  var [loadingDetail,setLD]    = useState(true);
  var [loadingReport,setLR]    = useState(true);
  var [detailError,setDetailError]       = useState(null);
  var [analyticsError,setAnalyticsError] = useState(null);
  var [insightsError,setInsightsError]   = useState(null);
  var [reportError,setReportError]       = useState(null);

  var closeBtnRef = useRef(null);
  var panelRef     = useRef(null);

  // Load detail on mount
  var loadDetail = useCallback(function(){
    if(!child?.id) return function(){};
    setLD(true);setDetailError(null);
    var c=false;
    getChildDetail(child?.id)
      .then(function(d){if(!c){setDetail(d);setLD(false);}})
      .catch(function(e){if(!c){setLD(false);setDetailError((e&&e.message)||"Could not load this child's details.");}});
    return function(){c=true;};
  },[child?.id]);

  useEffect(function(){return loadDetail();},[loadDetail]);

  // Load analytics lazily when progress/strengths tabs opened
  var loadAnalytics = useCallback(function(){
    if(!child?.id) return function(){};
    setAnalyticsError(null);
    var c=false;
    getChildAnalytics(child?.id)
      .then(function(d){if(!c)setAnalytics(d);})
      .catch(function(e){if(!c)setAnalyticsError((e&&e.message)||"Could not load progress data.");});
    return function(){c=true;};
  },[child?.id]);

  useEffect(function(){
    if(!child?.id||analytics||analyticsError) return;
    if(tab==="progress"||tab==="strengths") return loadAnalytics();
  },[tab,child?.id,analytics,analyticsError,loadAnalytics]);

  // Load insights lazily
  var loadInsights = useCallback(function(){
    if(!child?.id) return function(){};
    setInsightsError(null);
    var c=false;
    getChildAcademicInsights(child?.id)
      .then(function(d){if(!c)setInsights(d);})
      .catch(function(e){if(!c)setInsightsError((e&&e.message)||"Could not load homework and exam data.");});
    return function(){c=true;};
  },[child?.id]);

  useEffect(function(){
    if(!child?.id||insights||insightsError) return;
    if(tab==="homework") return loadInsights();
  },[tab,child?.id,insights,insightsError,loadInsights]);

  // Load report lazily
  var loadReport = useCallback(function(){
    if(!child?.id) return function(){};
    setLR(true);setReportError(null);
    var c=false;
    getChildProgressReport(child?.id)
      .then(function(d){if(!c){setReport(d);setLR(false);}})
      .catch(function(e){if(!c){setLR(false);setReportError((e&&e.message)||"Could not load the progress report.");}});
    return function(){c=true;};
  },[child?.id]);

  useEffect(function(){
    if(!child?.id||report||reportError) return;
    if(tab==="report") return loadReport();
  },[tab,child?.id,report,reportError,loadReport]);

  // Escape-to-close + basic focus trap while the drawer is open
  useEffect(function(){
    if(closeBtnRef.current) closeBtnRef.current.focus();
    function onKeyDown(e){
      if(e.key==="Escape"){onClose();return;}
      if(e.key==="Tab"&&panelRef.current){
        var focusable=panelRef.current.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
        if(!focusable.length) return;
        var first=focusable[0], last=focusable[focusable.length-1];
        if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}
        else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}
      }
    }
    document.addEventListener("keydown",onKeyDown);
    return function(){document.removeEventListener("keydown",onKeyDown);};
  },[onClose]);

  var plan=detail?.plan||child?.plan||{};
  var allNotifs=[...(detail?.notifications||[]),...(child?.notifications||[])];

  var activeError=null, retryActive=null;
  if(tab==="overview"||tab==="plan"||tab==="mock"){activeError=detailError;retryActive=loadDetail;}
  else if(tab==="progress"||tab==="strengths"){activeError=analyticsError;retryActive=loadAnalytics;}
  else if(tab==="homework"){activeError=insightsError;retryActive=loadInsights;}
  else if(tab==="report"){activeError=reportError;retryActive=loadReport;}

  return(
    <div ref={panelRef} data-testid="parent-child-workspace" role="dialog" aria-modal="true"
      aria-label={"Learning workspace for "+(child?.name||"student")}
      style={{position:"fixed",top:0,right:0,width:Math.min(640,window.innerWidth),height:"100vh",background:"var(--panel,#fff)",boxShadow:"-4px 0 32px rgba(0,0,0,.15)",zIndex:600,display:"flex",flexDirection:"column",overflowY:"hidden",overflowX:"clip"}}>

      {/* Header */}
      <div style={{padding:"14px 16px 0",borderBottom:"1px solid var(--border,#e5e7eb)",flexShrink:0}}>
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:8}}>
          <div>
            <div style={{fontWeight:800,fontSize:"1rem"}}>{child?.name||"Student"}</div>
            <div style={{fontSize:".73rem",color:"#64748b"}}>
              {child?.grade||"—"}
              {plan.plan_name&&<span style={{marginLeft:6,fontSize:".7rem",fontWeight:600,color:plan.has_full_access?"#22c55e":"#ef4444"}}>{plan.has_full_access?"✓ "+plan.plan_name:"⊘ "+plan.plan_name}</span>}
            </div>
          </div>
          <button ref={closeBtnRef} onClick={onClose} aria-label="Close learning workspace" style={{background:"none",border:"none",fontSize:"1.2rem",cursor:"pointer",padding:4}}>✕</button>
        </div>
        {/* Tab bar — horizontal scroll with touch support */}
        <div role="tablist" aria-label="Child workspace sections" style={{display:"flex",gap:0,overflowX:"scroll",overflowY:"hidden",
          WebkitOverflowScrolling:"touch",scrollbarWidth:"thin",scrollbarColor:"#e2e8f0 transparent",
          marginLeft:-16,marginRight:-16,paddingLeft:16,paddingRight:16,paddingBottom:2}}>
          {TABS.map(function(t){return(
            <button key={t.key} data-testid={"ws-tab-"+t.key} role="tab" aria-selected={tab===t.key} onClick={function(){setTab(t.key);}}
              style={{padding:"7px 12px",border:"none",background:"none",cursor:"pointer",
                fontFamily:"inherit",fontSize:".72rem",fontWeight:tab===t.key?700:500,
                color:tab===t.key?"#6366f1":"#64748b",
                borderBottom:tab===t.key?"2px solid #6366f1":"2px solid transparent",
                whiteSpace:"nowrap",marginBottom:-1,flexShrink:0,letterSpacing:"-.01em",
                minWidth:0}}>
              {t.label}
            </button>
          );})}
        </div>
      </div>

      {/* Body */}
      <div role="tabpanel" style={{flex:1,overflowY:"auto",padding:16}}>
        {activeError&&<FetchErrorBanner message={activeError} onRetry={retryActive}/>}
        {!activeError&&(detail?.data_warnings||[]).length>0&&(
          <div role="status" data-testid="workspace-data-warning" style={{background:"rgba(245,158,11,.08)",border:"1px solid #fcd34d",borderRadius:8,padding:"8px 12px",marginBottom:12,fontSize:".76rem",color:"#92400e"}}>
            ⚠ Some data couldn't be loaded: {detail.data_warnings.join(" ")}
          </div>
        )}
        {loadingDetail&&tab==="overview"&&<div style={{color:"#94a3b8",padding:8}}>Loading…</div>}
        {tab==="overview"  &&<OverviewSection child={child} detail={detail} analytics={analytics} onUpgrade={onUpgrade}/>}
        {tab==="plan"      &&<TodaysPlanSection detail={detail} onUpgrade={onUpgrade} onSectionNav={setTab}/>}
        {tab==="progress"  &&<ParentProgressStory analytics={analytics}/>}
        {tab==="strengths" &&<StrengthsNeedsSection analytics={analytics}/>}
        {tab==="mock"      &&<MockTestsSection detail={detail} plan={plan} onUpgrade={onUpgrade}/>}
        {tab==="homework"  &&<HomeworkExamsSection insights={insights}/>}
        {tab==="notifs"    &&<ParentNotificationGroups notifications={allNotifs}/>}
        {tab==="access"    &&<ParentAccessExplanation plan={plan} featureBadges={detail?.feature_badges} subscription={detail?.subscription} onUpgrade={onUpgrade}/>}
        {tab==="report"    &&<ReportSection report={report} loading={loadingReport}/>}
      </div>
    </div>
  );
}
