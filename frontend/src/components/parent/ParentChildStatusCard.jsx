/**
 * ParentChildStatusCard.jsx
 * Rich at-a-glance card per child on the parent dashboard.
 * Shows status, progress snapshot, mock test snapshot, last active, top action.
 */

// ── Status resolver ───────────────────────────────────────────────────────────
function childStatus(child){
  var plan=child.plan||{};
  var notifs=child.notifications||[];
  var hasExpiry=plan.expiry_warning;
  var isRestricted=plan.status_color==="restricted";
  var hasLowScore=notifs.some(function(n){return n.type==="low_mock_score";});
  var isInactive=notifs.some(function(n){return n.type==="child_inactive";});

  if(hasExpiry) return{label:"Plan Expiring",icon:"⚠️",color:"#d97706",bg:"rgba(245,158,11,.08)",border:"#fcd34d"};
  if(isRestricted) return{label:"Restricted Access",icon:"🔒",color:"#ef4444",bg:"rgba(239,68,68,.06)",border:"#fca5a5"};
  if(hasLowScore) return{label:"Needs Attention",icon:"📉",color:"#ef4444",bg:"rgba(239,68,68,.06)",border:"#fca5a5"};
  if(isInactive) return{label:"Inactive",icon:"😴",color:"#f59e0b",bg:"rgba(245,158,11,.06)",border:"#fcd34d"};
  if(plan.has_full_access) return{label:"Doing Well",icon:"✅",color:"#22c55e",bg:"rgba(34,197,94,.06)",border:"#86efac"};
  return{label:"Active",icon:"📚",color:"#6366f1",bg:"rgba(99,102,241,.06)",border:"#c7d2fe"};
}

function StatPill({label,value,color}){
  return(
    <div style={{background:"var(--surface2,#f8fafc)",border:"1px solid var(--border,#e5e7eb)",borderRadius:8,padding:"5px 10px",textAlign:"center",minWidth:72}}>
      <div style={{fontWeight:800,fontSize:".88rem",color:color||"#6366f1"}}>{value??0}</div>
      <div style={{fontSize:".63rem",color:"#64748b"}}>{label}</div>
    </div>
  );
}

function ProgressMini({completed,inProgress,total}){
  if(!total) return <div style={{fontSize:".73rem",color:"#94a3b8"}}>No progress yet</div>;
  var pct=Math.round((completed/total)*100);
  return(
    <div>
      <div style={{display:"flex",justifyContent:"space-between",fontSize:".7rem",color:"#64748b",marginBottom:2}}>
        <span>{completed} done</span><span>{inProgress} in progress</span>
      </div>
      <div style={{height:5,background:"var(--border,#e5e7eb)",borderRadius:3,overflow:"hidden"}}>
        <div style={{height:"100%",width:pct+"%",background:"#22c55e",borderRadius:3,transition:"width .4s"}}/>
      </div>
    </div>
  );
}

function TopRecommendation({recommendations,plan,onUpgrade,onView}){
  var recs=recommendations||[];
  if(!recs.length){
    if(plan?.has_full_access){
      return <div style={{fontSize:".73rem",color:"#22c55e",fontWeight:600}}>✅ No action needed</div>;
    }
    return null;
  }
  var top=recs.sort(function(a,b){
    var p={"high":0,"medium":1,"low":2};
    return (p[a.priority]??2)-(p[b.priority]??2);
  })[0];
  var pcolor={"high":"#ef4444","medium":"#f59e0b","low":"#22c55e"}[top.priority]||"#6366f1";
  return(
    <div style={{background:"rgba(99,102,241,.05)",border:"1px solid rgba(167,139,250,.2)",borderRadius:8,padding:"7px 10px",marginTop:6}}>
      <div style={{fontSize:".73rem",fontWeight:700,color:pcolor}}>{top.title}</div>
      {top.action==="upgrade"&&onUpgrade&&(
        <button onClick={function(e){e.stopPropagation();onUpgrade();}} style={{marginTop:4,fontSize:".68rem",padding:"2px 8px",borderRadius:5,border:"none",background:"#6366f1",color:"#fff",cursor:"pointer",fontFamily:"inherit"}}>Upgrade</button>
      )}
      {top.action!=="upgrade"&&onView&&(
        <button onClick={function(e){e.stopPropagation();onView();}} style={{marginTop:4,fontSize:".68rem",padding:"2px 8px",borderRadius:5,border:"1px solid var(--border,#e5e7eb)",background:"var(--panel,#fff)",cursor:"pointer",fontFamily:"inherit"}}>View →</button>
      )}
    </div>
  );
}

export default function ParentChildStatusCard({child, onView, onUpgrade}){
  var status=childStatus(child);
  var mockSummary=child.mock_test_summary||{};
  var progress=child.progress||{};  // from detail if available
  var actSummary=child.activity_summary||{};
  var plan=child.plan||{};

  var completed=progress.completed_chapters||0;
  var inProg=progress.in_progress_chapters||0;
  var total=(completed+inProg+(progress.not_started||0))||0;

  var lastActiveStr="";
  if(actSummary.last_active){
    try{
      var d=new Date(actSummary.last_active);
      var daysAgo=Math.floor((Date.now()-d.getTime())/(1000*60*60*24));
      lastActiveStr=daysAgo===0?"Today":daysAgo===1?"Yesterday":daysAgo+" days ago";
    }catch(e){lastActiveStr="";}
  }

  return(
    <div data-testid="parent-child-status-card"
      onClick={function(){onView(child);}}
      style={{background:"var(--panel,#fff)",border:"1px solid var(--border,#e5e7eb)",borderRadius:14,overflow:"hidden",cursor:"pointer",boxShadow:"0 1px 4px rgba(0,0,0,.04)",transition:"box-shadow .2s"}}>
      {/* Status bar */}
      <div style={{background:status.bg,borderBottom:"1px solid "+status.border,padding:"8px 14px",display:"flex",justifyContent:"space-between",alignItems:"center"}}>
        <div style={{display:"flex",gap:6,alignItems:"center"}}>
          <span style={{fontSize:"1rem"}}>{status.icon}</span>
          <span style={{fontWeight:700,fontSize:".8rem",color:status.color}}>{status.label}</span>
        </div>
        <span style={{fontSize:".7rem",color:"#64748b"}}>{plan.plan_name||"Free Tier"}</span>
      </div>
      {/* Body */}
      <div style={{padding:"12px 14px"}}>
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:8}}>
          <div>
            <div style={{fontWeight:800,fontSize:"1rem"}}>{child.name||"Student"}</div>
            <div style={{fontSize:".75rem",color:"#64748b"}}>{child.grade||"—"}{lastActiveStr&&" · Last active: "+lastActiveStr}</div>
          </div>
          <button onClick={function(e){e.stopPropagation();onView(child);}}
            style={{padding:"4px 10px",borderRadius:6,border:"1px solid var(--border,#e5e7eb)",background:"var(--panel,#fff)",fontSize:".73rem",cursor:"pointer",fontFamily:"inherit",fontWeight:600,color:"#6366f1",flexShrink:0}}>
            Open →
          </button>
        </div>

        {/* Stats row */}
        <div style={{display:"flex",gap:8,flexWrap:"wrap",marginBottom:8}}>
          <StatPill label="Mock Tests" value={mockSummary.count??0}/>
          <StatPill label="Avg Score" value={mockSummary.average_score!=null?mockSummary.average_score+"%":"—"} color={mockSummary.average_score>=60?"#22c55e":mockSummary.average_score>=40?"#f59e0b":"#ef4444"}/>
          {total>0&&<StatPill label="Chapters" value={completed+"/"+total} color="#0ea5e9"/>}
        </div>

        {/* Progress mini bar */}
        {total>0&&<ProgressMini completed={completed} inProgress={inProg} total={total}/>}

        {/* Plan expiry warning */}
        {plan.expiry_warning&&plan.days_remaining!=null&&(
          <div style={{fontSize:".72rem",color:"#d97706",fontWeight:600,marginTop:6}}>
            ⚠️ Plan expires in {plan.days_remaining} day{plan.days_remaining!==1?"s":""}
          </div>
        )}

        {/* Top recommendation */}
        <TopRecommendation
          recommendations={child.recommendations}
          plan={plan}
          onUpgrade={onUpgrade}
          onView={function(){onView(child);}}
        />
      </div>
    </div>
  );
}
