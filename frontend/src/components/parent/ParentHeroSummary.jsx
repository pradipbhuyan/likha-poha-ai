/**
 * ParentHeroSummary.jsx
 * At-a-glance parent greeting + summary bar
 */


function greet(){var h=new Date().getHours();return h<12?"Good morning":h<17?"Good afternoon":"Good evening";}

function PlanChip({plan}){
  var col={restricted:"#ef4444",paid:"#22c55e",admin:"#6366f1"}[plan?.status_color||"restricted"]||"#ef4444";
  return(
    <span style={{fontSize:".72rem",fontWeight:700,padding:"2px 8px",borderRadius:999,background:col+"18",color:col,border:"1px solid "+col+"40"}}>
      {plan?.has_full_access?"✓ "+plan?.plan_name||"Paid":"⊘ Free Tier"}
    </span>
  );
}

function UrgentBanner({notifications}){
  var urgent=(notifications||[]).filter(function(n){return n.priority==="high"||n.severity==="warning"||n.severity==="critical";});
  if(!urgent.length) return null;
  var top=urgent[0];
  return(
    <div style={{background:"rgba(245,158,11,.08)",border:"1px solid #fcd34d",borderRadius:10,padding:"10px 14px",marginBottom:12,display:"flex",gap:8,alignItems:"center"}}>
      <span style={{fontSize:"1rem"}}>{top.icon||"⚠️"}</span>
      <div style={{flex:1}}>
        <div style={{fontWeight:700,fontSize:".82rem",color:"#d97706"}}>{top.title}</div>
        <div style={{fontSize:".74rem",color:"#64748b"}}>{top.message||top.body}</div>
      </div>
      {urgent.length>1&&<span style={{fontSize:".7rem",color:"#d97706",fontWeight:600,whiteSpace:"nowrap"}}>+{urgent.length-1} more</span>}
    </div>
  );
}

export default function ParentHeroSummary({ summary, parentName, onAddChild, onUpgrade }){
  var children   = summary?.children||[];
  var notifs     = summary?.notifications||[];
  var parentPlan = summary?.parent_plan||{};
  var unread     = notifs.filter(function(n){return n.status!=="read";}).length;
  var canAdd     = summary?.can_add_child!==false;

  // Compute top-level status
  var hasUrgent  = notifs.some(function(n){return n.priority==="high"||n.severity==="warning";});
  var allGood    = !hasUrgent && children.length>0 && children.every(function(c){return c.plan?.has_full_access;});

  return(
    <div data-testid="parent-hero-summary" style={{marginBottom:20}}>
      {/* Greeting row */}
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",flexWrap:"wrap",gap:8,marginBottom:10}}>
        <div>
          <h1 style={{margin:0,fontSize:"1.25rem",fontWeight:800}}>
            {greet()}{parentName?", "+parentName:""} 👋
          </h1>
          <div style={{fontSize:".83rem",color:"#64748b",marginTop:2,display:"flex",gap:10,flexWrap:"wrap",alignItems:"center"}}>
            <span>👨‍👩‍👧 {children.length} child{children.length!==1?"ren":""}</span>
            <PlanChip plan={parentPlan}/>
            {unread>0&&<span style={{fontWeight:700,color:"#ef4444",fontSize:".75rem"}}>🔔 {unread} unread</span>}
            {allGood&&<span style={{fontWeight:700,color:"#22c55e",fontSize:".75rem"}}>✅ All children on track</span>}
          </div>
        </div>
        <div style={{display:"flex",gap:6,flexWrap:"wrap"}}>
          {canAdd&&<button onClick={onAddChild} style={{padding:"6px 12px",borderRadius:7,border:"1px solid #6366f1",background:"rgba(99,102,241,.07)",color:"#6366f1",fontFamily:"inherit",fontSize:".78rem",fontWeight:600,cursor:"pointer"}}>＋ Add Child</button>}
          {children.some(function(c){return!c.plan?.has_full_access;})&&(
            <button onClick={onUpgrade} style={{padding:"6px 12px",borderRadius:7,border:"1px solid var(--border,#e5e7eb)",background:"transparent",color:"#6366f1",fontFamily:"inherit",fontSize:".78rem",fontWeight:600,cursor:"pointer"}}>View Plans →</button>
          )}
        </div>
      </div>
      {/* Urgent banner */}
      <UrgentBanner notifications={notifs}/>
    </div>
  );
}
