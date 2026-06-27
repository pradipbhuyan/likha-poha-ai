/**
 * ParentDashboardPage.jsx — Parent Experience Phase 1
 * Design: clean parent-facing workspace showing each child's learning status
 * Uses canonical /api/parent/dashboard/summary endpoint.
 * Safety: parentId alone NEVER implies paid access — badge states from backend.
 */
import { useCallback, useEffect, useState } from "react";
import {
  getParentDashboardSummary,
  getChildDetail,
  createStudent,
} from "../api/parentDashboard";

// ── Design tokens ─────────────────────────────────────────────────────────────
const STATUS_STYLE = {
  restricted: { bg:"rgba(239,68,68,.07)",  border:"#fca5a5", text:"#dc2626", badge:"#ef4444" },
  paid:       { bg:"rgba(34,197,94,.07)",  border:"#86efac", text:"#15803d", badge:"#22c55e" },
  admin:      { bg:"rgba(99,102,241,.07)", border:"#c7d2fe", text:"#4f46e5", badge:"#6366f1" },
};
const BADGE_STATE = {
  full:    { bg:"rgba(34,197,94,.1)",   color:"#166534", label:"✓" },
  limited: { bg:"rgba(245,158,11,.1)",  color:"#92400e", label:"~" },
  locked:  { bg:"rgba(239,68,68,.08)",  color:"#dc2626", label:"🔒" },
};
function card(x){return{background:"var(--panel,#fff)",border:"1px solid var(--border,#e5e7eb)",borderRadius:14,padding:"16px 18px",marginBottom:14,...(x||{})};}
const inp  = {padding:"8px 12px",borderRadius:8,border:"1px solid var(--border,#e5e7eb)",fontFamily:"inherit",fontSize:".85rem",background:"var(--surface2,#f8fafc)",color:"var(--text,#1e293b)",width:"100%"};
const btn1 = {padding:"8px 16px",borderRadius:8,border:"none",background:"#6366f1",color:"#fff",fontFamily:"inherit",fontSize:".82rem",fontWeight:700,cursor:"pointer"};
const btn2 = {padding:"6px 12px",borderRadius:7,border:"1px solid var(--border,#e5e7eb)",background:"var(--panel,#fff)",fontFamily:"inherit",fontSize:".78rem",cursor:"pointer",color:"var(--text,#374151)"};
const GRADES=Array.from({length:12},function(_,i){return"Grade "+(i+1);});

function greet(){var h=new Date().getHours();return h<12?"Good morning":h<17?"Good afternoon":"Good evening";}

function Skel(){
  return(
    <div style={{maxWidth:960,margin:"0 auto",padding:"24px 14px"}}>
      <div style={{height:26,background:"var(--border,#e5e7eb)",borderRadius:6,width:"40%",marginBottom:8}}/>
      <div style={{height:14,background:"var(--border,#e5e7eb)",borderRadius:4,width:"60%",marginBottom:24}}/>
      <div style={{display:"flex",gap:12}}>
        {[1,2].map(i=><div key={i} style={{flex:1,height:220,background:"var(--border,#e5e7eb)",borderRadius:14}}/>)}
      </div>
    </div>
  );
}

// ── Feature Badge Row ─────────────────────────────────────────────────────────
function FeatureBadges({badges}){
  if(!badges||badges.length===0) return null;
  return(
    <div style={{display:"flex",flexWrap:"wrap",gap:6,marginTop:8}}>
      {badges.map(function(b){
        var st=BADGE_STATE[b.state]||BADGE_STATE.locked;
        return(
          <span key={b.feature} title={b.label+": "+b.state}
            style={{fontSize:".7rem",fontWeight:700,padding:"2px 8px",borderRadius:999,background:st.bg,color:st.color,display:"inline-flex",alignItems:"center",gap:4}}>
            {b.icon} {b.label}
            {b.state==="limited"&&<span style={{fontSize:".62rem",opacity:.8}}>limited</span>}
            {b.state==="locked"&&<span style={{fontSize:".62rem",opacity:.8}}>locked</span>}
          </span>
        );
      })}
    </div>
  );
}

// ── Plan Status Chip ──────────────────────────────────────────────────────────
function PlanChip({plan}){
  if(!plan) return null;
  var color=plan.status_color||"restricted";
  var st=STATUS_STYLE[color]||STATUS_STYLE.restricted;
  return(
    <span style={{fontSize:".72rem",fontWeight:700,padding:"3px 9px",borderRadius:999,background:st.bg,color:st.text,border:"1px solid "+st.border,display:"inline-block"}}>
      {plan.has_full_access?"✓":"⊘"} {plan.status_label||plan.plan_name}
    </span>
  );
}

// ── Child Card (overview) ─────────────────────────────────────────────────────
function ChildCard({child, onView}){
  var plan=child.plan||{};
  var st=STATUS_STYLE[plan.status_color]||STATUS_STYLE.restricted;
  return(
    <div style={{...card(),borderTop:"3px solid "+st.badge,cursor:"pointer"}} onClick={function(){onView(child);}}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",gap:8,flexWrap:"wrap"}}>
        <div>
          <div style={{display:"flex",alignItems:"center",gap:8,flexWrap:"wrap",marginBottom:4}}>
            <strong style={{fontSize:"1rem"}}>{child.name||"Student"}</strong>
            <span style={{fontSize:".75rem",color:"#64748b"}}>{child.grade||"—"}</span>
            <PlanChip plan={plan}/>
          </div>
          <div style={{fontSize:".78rem",color:"#64748b"}}>{plan.description}</div>
          {plan.expiry_warning&&plan.days_remaining!=null&&(
            <div style={{fontSize:".72rem",color:"#dc2626",fontWeight:600,marginTop:2}}>
              ⚠️ Plan expires in {plan.days_remaining} day{plan.days_remaining!==1?"s":""}
            </div>
          )}
          <FeatureBadges badges={child.feature_badges}/>
        </div>
        <button style={btn2}>View →</button>
      </div>

      {/* Quick stats */}
      <div style={{display:"flex",gap:10,flexWrap:"wrap",marginTop:12}}>
        {[{label:"Mock Tests",value:child.mock_test_summary?.count??0},
          {label:"Avg Score",value:child.mock_test_summary?.average_score!=null?child.mock_test_summary.average_score+"%":"—"},
          {label:"Last Active",value:child.activity_summary?.last_active?new Date(child.activity_summary.last_active).toLocaleDateString():"Never"},
        ].map(function(k){return(
          <div key={k.label} style={{background:"var(--surface2,#f8fafc)",border:"1px solid var(--border,#e5e7eb)",borderRadius:8,padding:"6px 10px",textAlign:"center",minWidth:80}}>
            <div style={{fontWeight:700,fontSize:".88rem"}}>{k.value}</div>
            <div style={{fontSize:".65rem",color:"#64748b"}}>{k.label}</div>
          </div>
        );})}
      </div>

      {/* Upgrade CTA for free tier */}
      {plan.status_color==="restricted"&&(
        <div style={{marginTop:10,padding:"8px 12px",background:"rgba(99,102,241,.07)",border:"1px solid rgba(167,139,250,.3)",borderRadius:8,display:"flex",gap:8,alignItems:"center"}}>
          <span style={{fontSize:".78rem",color:"#6366f1",flex:1}}>🔒 This child is on Free Tier — limited access.</span>
        </div>
      )}
    </div>
  );
}

// ── Notification Card ─────────────────────────────────────────────────────────
function NotificationPanel({notifications, onUpgrade}){
  if(!notifications||notifications.length===0) return null;
  var prio={"high":"#dc2626","medium":"#f59e0b","low":"#64748b"};
  return(
    <div style={card()}>
      <div style={{fontWeight:700,marginBottom:8,fontSize:".9rem"}}>🔔 Notifications</div>
      {notifications.slice(0,5).map(function(n,i){return(
        <div key={i} style={{display:"flex",gap:8,padding:"6px 0",borderBottom:"1px solid var(--border,#f1f5f9)",alignItems:"flex-start"}}>
          <span style={{fontSize:"1rem",flexShrink:0}}>{n.icon||"•"}</span>
          <div style={{flex:1}}>
            <div style={{fontSize:".82rem",fontWeight:600,color:prio[n.priority||"low"]}}>{n.title}</div>
            <div style={{fontSize:".75rem",color:"#64748b"}}>{n.body}</div>
          </div>
          {n.type==="upgrade"&&onUpgrade&&(
            <button onClick={onUpgrade} style={{...btn1,padding:"3px 10px",fontSize:".72rem",flexShrink:0,whiteSpace:"nowrap"}}>Upgrade</button>
          )}
        </div>
      );})}
    </div>
  );
}
// ── Child Detail Drawer ───────────────────────────────────────────────────────
function ChildDetailDrawer({child, onClose, onUpgrade}){
  var [detail, setDetail]   = useState(null);
  var [loading, setLoading] = useState(true);
  var [section, setSection] = useState("overview");

  useEffect(function(){
    if(!child?.id) return;
    setLoading(true);
    setDetail(null);
    getChildDetail(child.id)
      .then(function(d){setDetail(d);setLoading(false);})
      .catch(function(){setLoading(false);});
  },[child?.id]);

  var SECTIONS=[
    {key:"overview",     label:"Overview",    icon:"👤"},
    {key:"progress",     label:"Progress",    icon:"📈"},
    {key:"mock_tests",   label:"Mock Tests",  icon:"📝"},
    {key:"activity",     label:"Activity",    icon:"⏱️"},
    {key:"access",       label:"Access",      icon:"🔑"},
    {key:"recommend",    label:"Actions",     icon:"💡"},
  ];

  var plan=detail?.plan||child?.plan||{};
  var st=STATUS_STYLE[plan.status_color||"restricted"]||STATUS_STYLE.restricted;

  return(
    <div data-testid="child-detail-drawer"
      style={{position:"fixed",top:0,right:0,width:Math.min(620,window.innerWidth),height:"100vh",background:"var(--panel,#fff)",boxShadow:"-4px 0 32px rgba(0,0,0,.15)",zIndex:300,display:"flex",flexDirection:"column",overflow:"hidden"}}>
      {/* Header */}
      <div style={{padding:"14px 16px 0",borderBottom:"1px solid var(--border,#e5e7eb)",flexShrink:0}}>
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:10}}>
          <div>
            <h3 style={{margin:0,fontSize:"1rem"}}>{child?.name||"Student"}</h3>
            <span style={{fontSize:".75rem",color:"#64748b"}}>{child?.grade||"—"} · </span>
            <PlanChip plan={plan}/>
          </div>
          <button onClick={onClose} style={{background:"none",border:"none",fontSize:"1.2rem",cursor:"pointer"}}>✕</button>
        </div>
        {/* Section tabs */}
        <div style={{display:"flex",gap:2,overflowX:"auto",WebkitOverflowScrolling:"touch"}}>
          {SECTIONS.map(function(s){return(
            <button key={s.key} data-testid={"child-tab-"+s.key} onClick={function(){setSection(s.key);}}
              style={{padding:"6px 10px",border:"none",background:"none",cursor:"pointer",fontFamily:"inherit",fontSize:".78rem",fontWeight:section===s.key?700:400,color:section===s.key?"#6366f1":"#64748b",borderBottom:section===s.key?"2px solid #6366f1":"2px solid transparent",whiteSpace:"nowrap",marginBottom:-1}}>
              {s.icon} {s.label}
            </button>
          );})}
        </div>
      </div>
      {/* Body */}
      <div style={{flex:1,overflowY:"auto",padding:16}}>
        {loading&&<div style={{color:"#94a3b8",padding:20}}>Loading child details…</div>}
        {!loading&&!detail&&<div style={{color:"#dc2626",padding:20}}>Could not load child details.</div>}
        {!loading&&detail&&(
          <>
            {section==="overview"&&<ChildOverview child={child} detail={detail} plan={plan} st={st}/>}
            {section==="progress"&&<ChildProgress detail={detail}/>}
            {section==="mock_tests"&&<ChildMockTests detail={detail} plan={plan} onUpgrade={onUpgrade}/>}
            {section==="activity"&&<ChildActivity detail={detail}/>}
            {section==="access"&&<ChildAccess detail={detail} plan={plan} onUpgrade={onUpgrade}/>}
            {section==="recommend"&&<ChildRecommendations detail={detail} onUpgrade={onUpgrade}/>}
          </>
        )}
      </div>
    </div>
  );
}

function NA(){return <div style={{color:"#94a3b8",fontSize:".8rem",padding:"8px 0"}}>Not available yet.</div>;}

function ChildOverview({child, detail, plan, st}){
  var info=detail?.child||child||{};
  return(
    <div data-testid="child-section-overview">
      <div style={{display:"flex",flexWrap:"wrap",gap:8,marginBottom:12}}>
        {[["Name",info.name||info.username||"—"],["Grade",info.grade||"—"],["Status",info.account_status||"active"],["Plan",plan.plan_name||"Free Tier"]].map(function([k,v]){return(
          <div key={k} style={{background:"var(--surface2,#f8fafc)",border:"1px solid var(--border,#e5e7eb)",borderRadius:8,padding:"7px 12px"}}>
            <div style={{fontSize:".67rem",color:"#64748b"}}>{k}</div>
            <div style={{fontSize:".82rem",fontWeight:700}}>{v}</div>
          </div>
        );})}
      </div>
      <div style={{...card(),background:st.bg,border:"1px solid "+st.border}}>
        <div style={{fontWeight:700,fontSize:".88rem",color:st.text}}>{plan.status_label}</div>
        <div style={{fontSize:".78rem",color:"#64748b",marginTop:2}}>{plan.description}</div>
        {plan.expires_at&&<div style={{fontSize:".72rem",color:"#94a3b8",marginTop:4}}>Expires: {new Date(plan.expires_at).toLocaleDateString()}</div>}
      </div>
      {detail?.feature_badges&&<FeatureBadges badges={detail.feature_badges}/>}
    </div>
  );
}

function ChildProgress({detail}){
  var prog=detail?.progress||{};
  if(!prog.available) return <NA/>;
  return(
    <div data-testid="child-section-progress">
      <div style={{display:"flex",gap:10,flexWrap:"wrap",marginBottom:12}}>
        {[["Completed",prog.completed_chapters??0],["In Progress",prog.in_progress_chapters??0]].map(function([k,v]){return(
          <div key={k} style={{background:"var(--surface2,#f8fafc)",border:"1px solid var(--border,#e5e7eb)",borderRadius:8,padding:"8px 14px",textAlign:"center",flex:"1 1 80px"}}>
            <div style={{fontWeight:800,fontSize:"1.4rem",color:"#6366f1"}}>{v}</div>
            <div style={{fontSize:".7rem",color:"#64748b"}}>{k} chapters</div>
          </div>
        );})}
      </div>
      {(prog.weak_topics||[]).length>0&&(
        <div style={card()}>
          <div style={{fontWeight:700,marginBottom:6}}>⚠ Weak Topics</div>
          {prog.weak_topics.map(function(t,i){return(
            <div key={i} style={{fontSize:".8rem",padding:"3px 0",borderBottom:"1px solid var(--border,#f1f5f9)"}}>
              {t.subject} — {t.chapter}{t.score!=null?" ("+t.score+"%)":""}
            </div>
          );})}
        </div>
      )}
    </div>
  );
}

function ChildMockTests({detail, plan, onUpgrade}){
  var mt=detail?.mock_tests||{};
  var isFree=plan?.canonical_plan_key==="FREE_TIER";
  return(
    <div data-testid="child-section-mock-tests">
      {isFree&&mt.free_daily_limit&&(
        <div style={{...card(),background:"rgba(245,158,11,.07)",border:"1px solid #fcd34d",marginBottom:8}}>
          <div style={{fontSize:".82rem",fontWeight:600,color:"#d97706"}}>📊 Free Tier: {mt.free_daily_limit} mock tests per day</div>
          <div style={{fontSize:".75rem",color:"#64748b",marginTop:3}}>Upgrade for unlimited mock tests and full score analysis.</div>
          {onUpgrade&&<button onClick={onUpgrade} style={{...btn1,marginTop:8,fontSize:".75rem",padding:"5px 12px"}}>Upgrade for unlimited</button>}
        </div>
      )}
      {!mt.available?<NA/>:(
        <>
          <div style={{display:"flex",gap:10,flexWrap:"wrap",marginBottom:12}}>
            {[["Tests Done",mt.count??0],["Avg Score",mt.average_score!=null?mt.average_score+"%":"—"]].map(function([k,v]){return(
              <div key={k} style={{background:"var(--surface2,#f8fafc)",border:"1px solid var(--border,#e5e7eb)",borderRadius:8,padding:"8px 14px",textAlign:"center",flex:"1 1 80px"}}>
                <div style={{fontWeight:800,fontSize:"1.4rem",color:"#0ea5e9"}}>{v}</div>
                <div style={{fontSize:".7rem",color:"#64748b"}}>{k}</div>
              </div>
            );})}
          </div>
          {(mt.recent||[]).length>0&&(
            <div style={card()}>
              <div style={{fontWeight:700,marginBottom:6}}>Recent Tests</div>
              {mt.recent.map(function(t,i){var pct=t.total>0?Math.round((t.score/t.total)*100):0;return(
                <div key={i} style={{display:"flex",justifyContent:"space-between",padding:"4px 0",borderBottom:"1px solid var(--border,#f1f5f9)",fontSize:".78rem"}}>
                  <span>{t.subject||"—"}</span>
                  <span style={{fontWeight:700,color:pct>=60?"#166534":pct>=40?"#d97706":"#dc2626"}}>{pct}%</span>
                </div>
              );})}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function ChildActivity({detail}){
  var act=detail?.ai_activity||{};
  return(
    <div data-testid="child-section-activity">
      {!act.available?<NA/>:(
        <>
          <div style={{marginBottom:8,fontSize:".82rem",color:"#64748b"}}>
            Last active: <strong>{act.last_active?new Date(act.last_active).toLocaleString():"Unknown"}</strong>
          </div>
          {act.is_limited&&<div style={{...card(),background:"rgba(245,158,11,.07)",border:"1px solid #fcd34d",fontSize:".78rem",color:"#d97706"}}>📊 Limited AI access (Free Tier — DKB only)</div>}
          {Object.keys(act.feature_counts||{}).length>0&&(
            <div style={card()}>
              <div style={{fontWeight:700,marginBottom:6}}>Activity Breakdown</div>
              {Object.entries(act.feature_counts||{}).map(function([f,c]){return(
                <div key={f} style={{display:"flex",justifyContent:"space-between",padding:"3px 0",fontSize:".78rem"}}>
                  <span style={{textTransform:"capitalize"}}>{f}</span>
                  <span style={{fontWeight:700}}>{c}</span>
                </div>
              );})}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function ChildAccess({detail, plan, onUpgrade}){
  // subscription and features available via detail?.subscription and detail?.features
  return(
    <div data-testid="child-section-access">
      <div style={{...card(),background:STATUS_STYLE[plan.status_color||"restricted"].bg,border:"1px solid "+STATUS_STYLE[plan.status_color||"restricted"].border}}>
        <div style={{fontWeight:700}}>{plan.status_label||"—"}</div>
        <div style={{fontSize:".78rem",color:"#64748b",marginTop:2}}>{plan.description}</div>
        {plan.expires_at&&<div style={{fontSize:".72rem",color:"#94a3b8",marginTop:4}}>Expires: {new Date(plan.expires_at).toLocaleDateString()}</div>}
      </div>
      {detail?.feature_badges&&<FeatureBadges badges={detail.feature_badges}/>}
      {plan.status_color==="restricted"&&onUpgrade&&(
        <button onClick={onUpgrade} style={{...btn1,marginTop:12,width:"100%"}}>🚀 Upgrade for Full Access</button>
      )}
    </div>
  );
}

function ChildRecommendations({detail, onUpgrade}){
  var recs=detail?.recommendations||[];
  if(recs.length===0) return <div style={{color:"#94a3b8",fontSize:".8rem",padding:"8px 0"}}>No recommendations at this time.</div>;
  var prio={"high":"#dc2626","medium":"#f59e0b","low":"#64748b"};
  return(
    <div data-testid="child-section-recommendations">
      {recs.map(function(r,i){return(
        <div key={i} style={{...card(),borderLeft:"3px solid "+(prio[r.priority||"low"]||"#64748b")}}>
          <div style={{fontWeight:700,fontSize:".85rem",color:prio[r.priority||"low"]}}>{r.title}</div>
          <div style={{fontSize:".78rem",color:"#64748b",marginTop:3}}>{r.body}</div>
          {r.action==="upgrade"&&onUpgrade&&(
            <button onClick={onUpgrade} style={{...btn1,marginTop:8,fontSize:".75rem",padding:"5px 12px"}}>Upgrade</button>
          )}
        </div>
      );})}
    </div>
  );
}

// ── Add Child Form ────────────────────────────────────────────────────────────
function AddChildModal({onClose, onAdded, canAdd, planName}){
  var [form, setForm] = useState({username:"",grade:"Grade 9",password:"",email:""});
  var [loading, setLoading] = useState(false);
  var [msg, setMsg] = useState(null);

  async function submit(e){
    e.preventDefault();
    if(!form.username||!form.password){setMsg("Name and password required.");return;}
    setLoading(true);
    var d=await createStudent({...form,email:form.email||undefined}).catch(function(e){return{success:false,error:e.message};});
    setLoading(false);
    if(d.success!==false){
setMsg("✅ Child added! They are on Free Tier with limited access.");
      setTimeout(function(){onAdded();onClose();},1500);
    } else {
      setMsg("⚠ "+(d.error||"Failed to add child."));
    }
  }

  return(
    <div style={{position:"fixed",inset:0,background:"rgba(0,0,0,.4)",zIndex:400,display:"flex",alignItems:"center",justifyContent:"center",padding:16}}>
      <div style={{...card(),width:"100%",maxWidth:420,maxHeight:"90vh",overflowY:"auto",boxShadow:"0 8px 32px rgba(0,0,0,.2)"}}>
        <div style={{display:"flex",justifyContent:"space-between",marginBottom:14}}>
          <h4 style={{margin:0}}>➕ Add Child</h4>
          <button onClick={onClose} style={{background:"none",border:"none",cursor:"pointer",fontSize:"1.1rem"}}>✕</button>
        </div>
        {!canAdd&&(
          <div style={{...card(),background:"#fef2f2",border:"1px solid #fecaca",marginBottom:10}}>
            <div style={{fontSize:".82rem",color:"#dc2626",fontWeight:600}}>Child limit reached for {planName}.</div>
            <div style={{fontSize:".75rem",color:"#64748b",marginTop:3}}>Upgrade to Family Premium to add a second child.</div>
          </div>
        )}
        <div data-testid="add-child-free-tier-notice" style={{...card(),background:"rgba(99,102,241,.07)",border:"1px solid rgba(167,139,250,.3)",marginBottom:10}}>
          <div style={{fontSize:".78rem",color:"#6366f1",fontWeight:600}}>ℹ️ New children start on Free Tier</div>
          <div style={{fontSize:".72rem",color:"#64748b",marginTop:2}}>The child will have limited access until you upgrade your plan.</div>
        </div>
        <form onSubmit={submit} style={{display:"flex",flexDirection:"column",gap:8}}>
          <label><span style={{fontSize:".78rem",fontWeight:600}}>Child's Name *</span>
            <input value={form.username} onChange={function(e){setForm(function(p){return{...p,username:e.target.value};});}} required style={{...inp,marginTop:2}} disabled={!canAdd}/></label>
          <label><span style={{fontSize:".78rem",fontWeight:600}}>Grade *</span>
            <select value={form.grade} onChange={function(e){setForm(function(p){return{...p,grade:e.target.value};});}} style={{...inp,marginTop:2}} disabled={!canAdd}>
              {GRADES.map(function(g){return <option key={g} value={g}>{g}</option>;})}</select></label>
          <label><span style={{fontSize:".78rem",fontWeight:600}}>Password *</span>
            <input type="text" value={form.password} onChange={function(e){setForm(function(p){return{...p,password:e.target.value};});}} required placeholder="Share with child" style={{...inp,marginTop:2}} disabled={!canAdd}/></label>
          <label><span style={{fontSize:".78rem",fontWeight:600}}>Email (optional)</span>
            <input type="email" value={form.email} onChange={function(e){setForm(function(p){return{...p,email:e.target.value};});}} style={{...inp,marginTop:2}} disabled={!canAdd}/></label>
          {msg&&<div style={{fontSize:".82rem",color:msg.startsWith("✅")?"#166534":"#dc2626"}}>{msg}</div>}
          <button type="submit" disabled={loading||!canAdd} style={btn1}>{loading?"Adding…":"Add Child"}</button>
        </form>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main Export
// ─────────────────────────────────────────────────────────────────────────────
export default function ParentDashboardPage({ user, setActivePage }) {
  var [summary,     setSummary]     = useState(null);
  var [loading,     setLoading]     = useState(true);
  var [error,       setError]       = useState(null);
  var [selected,    setSelected]    = useState(null); // open child detail
  var [showAdd,     setShowAdd]     = useState(false);
  var [flashMsg,    setFlashMsg]    = useState(null);

  var loadSummary = useCallback(async function(){
    setLoading(true);
    var d = await getParentDashboardSummary().catch(function(e){return{success:false,error:e.message};});
    if(d&&d.success!==false) setSummary(d);
    else setError((d&&d.error)||"Could not load dashboard.");
    setLoading(false);
  },[]);

  useEffect(function(){loadSummary();},[loadSummary]);

  function flash(m){setFlashMsg(m);setTimeout(function(){setFlashMsg(null);},3000);}

  function goUpgrade(){if(setActivePage) setActivePage("subscriptionPlans");}

  if(loading) return <Skel/>;
  if(error) return(
    <div style={{maxWidth:960,margin:"0 auto",padding:"32px 14px"}}>
      <div style={{...card(),background:"#fef2f2",border:"1px solid #fecaca",color:"#dc2626"}}>⚠ {error}</div>
    </div>
  );

  var children   = summary?.children||[];
  var notifs     = summary?.notifications||[];
  var parentPlan = summary?.parent_plan||{};
  var canAdd     = summary?.can_add_child!==false;
  var parentName = (user?.username||summary?.parent?.username||"").split(" ")[0];

  return(
    <div style={{fontFamily:"inherit",maxWidth:960,margin:"0 auto",padding:"0 14px 60px"}}>

      {/* Flash */}
      {flashMsg&&<div style={{position:"fixed",top:16,left:"50%",transform:"translateX(-50%)",background:"#1e293b",color:"#fff",padding:"8px 20px",borderRadius:8,fontSize:".82rem",fontWeight:600,zIndex:999,boxShadow:"0 4px 24px rgba(0,0,0,.25)",whiteSpace:"nowrap"}}>{flashMsg}</div>}

      {/* Overlays */}
      {selected&&<ChildDetailDrawer child={selected} onClose={function(){setSelected(null);}} onUpgrade={goUpgrade}/>}
      {showAdd&&<AddChildModal canAdd={canAdd} planName={parentPlan.plan_name||"your plan"} onClose={function(){setShowAdd(false);}} onAdded={function(){loadSummary();flash("✅ Child added — on Free Tier with limited access.");}}/>}

      {/* Hero */}
      <div style={{padding:"18px 0 4px",display:"flex",justifyContent:"space-between",alignItems:"flex-start",gap:12,flexWrap:"wrap",marginBottom:16}}>
        <div>
          <h1 style={{margin:0,fontSize:"1.2rem",fontWeight:800}}>{greet()}{parentName?", "+parentName:""} 👋</h1>
          <p style={{margin:"4px 0 0",fontSize:".83rem",color:"#64748b"}}>
            {children.length===0?"No children linked yet.":`Managing ${children.length} child${children.length>1?"ren":""}.`}
            {" "}{parentPlan.plan_name&&<span><strong>{parentPlan.plan_name}</strong></span>}
          </p>
        </div>
        <button onClick={function(){setShowAdd(true);}} style={{...btn1,display:"flex",alignItems:"center",gap:4}}>
          ＋ Add Child
        </button>
      </div>

      {/* Notifications */}
      {notifs.length>0&&<NotificationPanel notifications={notifs} onUpgrade={goUpgrade}/>}

      {/* No children */}
      {children.length===0&&(
        <div data-testid="parent-no-children" style={{...card(),textAlign:"center",padding:40,color:"#94a3b8"}}>
          <div style={{fontSize:"2.5rem",marginBottom:8}}>🎓</div>
          <div style={{fontWeight:600,marginBottom:4}}>No children linked yet</div>
          <div style={{fontSize:".82rem",marginBottom:16}}>Add your child to track their progress and manage their learning.</div>
          <button onClick={function(){setShowAdd(true);}} style={btn1}>＋ Add Child</button>
        </div>
      )}

      {/* Child Cards */}
      {children.length>0&&(
        <div data-testid="parent-children-list">
          <h2 style={{fontSize:".95rem",fontWeight:800,margin:"0 0 12px"}}>🎓 Your Children</h2>
          <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(280px,1fr))",gap:14}}>
            {children.map(function(child){return(
              <ChildCard key={child.id} child={child} onView={function(c){setSelected(c);}}/>
            );})}
          </div>
          {!canAdd&&(
            <div style={{fontSize:".78rem",color:"#64748b",marginTop:8}}>
              Child limit reached for <strong>{parentPlan.plan_name}</strong>.
              {" "}<button onClick={goUpgrade} style={{background:"none",border:"none",color:"#6366f1",cursor:"pointer",fontFamily:"inherit",fontWeight:600,fontSize:".78rem"}}>Upgrade to Family Premium</button> for a second child.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
