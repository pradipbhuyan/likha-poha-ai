/**
 * ParentActionPlan.jsx
 * "Things to Do Tonight" — action-oriented section from recommendations/notifications
 */

var PRIO_COLOR={"high":"#ef4444","medium":"#f59e0b","low":"#22c55e"};
var ACTION_ICONS={
  upgrade:"🚀", mock_test:"📝", inactive:"😴", expiry:"⚠️",
  exemplar:"🔬", low_score:"📉", mock_test_completed:"✅",
  strong_improvement:"🌟", feature_locked:"🔒", start_mock_test:"📝",
  improve_score:"📉", maintain_progress:"🌟", revise_topic:"🔄",
};

function ActionCard({action, onAction, onView}){
  var icon=ACTION_ICONS[action.type||action.action]||"💡";
  var pcolor=PRIO_COLOR[action.priority||"medium"]||"#6366f1";
  var isUpgrade=(action.action==="upgrade"||action.type==="upgrade"||action.type==="feature_locked");

  return(
    <div data-testid="parent-action-card"
      style={{background:"var(--panel,#fff)",border:"1px solid var(--border,#e5e7eb)",borderRadius:10,padding:"10px 14px",display:"flex",gap:10,alignItems:"flex-start"}}>
      <span style={{fontSize:"1.1rem",flexShrink:0,marginTop:1}}>{icon}</span>
      <div style={{flex:1,minWidth:0}}>
        <div style={{fontWeight:700,fontSize:".82rem",color:pcolor,marginBottom:2}}>{action.title}</div>
        <div style={{fontSize:".76rem",color:"#64748b",lineHeight:1.4}}>{action.body||action.description||action.message}</div>
        {action.child_name&&<div style={{fontSize:".7rem",color:"#94a3b8",marginTop:2}}>👤 {action.child_name}</div>}
      </div>
      <div style={{flexShrink:0,display:"flex",flexDirection:"column",gap:4,alignItems:"flex-end"}}>
        {isUpgrade&&onAction&&(
          <button onClick={function(){onAction("upgrade");}} style={{padding:"4px 10px",borderRadius:6,border:"none",background:"#6366f1",color:"#fff",fontFamily:"inherit",fontSize:".72rem",fontWeight:600,cursor:"pointer",whiteSpace:"nowrap"}}>Upgrade</button>
        )}
        {!isUpgrade&&onView&&(
          <button onClick={function(){onView(action);}} style={{padding:"4px 10px",borderRadius:6,border:"1px solid var(--border,#e5e7eb)",background:"var(--surface2,#f8fafc)",fontFamily:"inherit",fontSize:".72rem",cursor:"pointer",color:"var(--text,#374151)",whiteSpace:"nowrap"}}>View →</button>
        )}
      </div>
    </div>
  );
}

export default function ParentActionPlan({ children, onUpgrade, onOpenChild }){
  // Gather actions from all children's recommendations + notifications
  var actions=[];

  (children||[]).forEach(function(child){
    // From recommendations
    (child.recommendations||[]).forEach(function(r){
      actions.push({...r, child_name:child.name, child_id:child.id, _child:child});
    });
    // From high-priority notifications not already covered
    (child.notifications||[]).filter(function(n){return n.priority==="high";}).forEach(function(n){
      if(!actions.some(function(a){return a.type===n.type&&a.child_id===child.id;})){
        actions.push({...n, child_name:child.name, child_id:child.id, _child:child});
      }
    });
  });

  // Sort by priority
  var prioOrder={"high":0,"medium":1,"low":2};
  actions.sort(function(a,b){return(prioOrder[a.priority||"low"]||2)-(prioOrder[b.priority||"low"]||2);});

  // Top 5
  var top=actions.slice(0,5);

  if(!top.length) return(
    <div data-testid="parent-action-plan-empty" style={{background:"rgba(34,197,94,.06)",border:"1px solid #86efac",borderRadius:10,padding:"12px 16px"}}>
      <div style={{fontWeight:700,fontSize:".88rem",color:"#166534"}}>🌟 All clear — nothing urgent today!</div>
      <div style={{fontSize:".78rem",color:"#64748b",marginTop:3}}>Keep encouraging daily practice for best results.</div>
    </div>
  );

  return(
    <div data-testid="parent-action-plan">
      <h2 style={{margin:"0 0 10px",fontSize:".95rem",fontWeight:800}}>📋 Things to Do Tonight</h2>
      <div style={{display:"flex",flexDirection:"column",gap:8}}>
        {top.map(function(action,i){return(
          <ActionCard key={i} action={action}
            onAction={function(type){if(type==="upgrade")onUpgrade();}}
            onView={function(){if(action._child)onOpenChild(action._child);}}
          />
        );})}
      </div>
    </div>
  );
}
