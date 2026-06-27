/**
 * ParentNotificationGroups.jsx
 * Groups notifications by: Needs Attention | Good News | Upcoming | Subscription
 */
import { useState } from "react";
import { markNotificationRead, markAllNotificationsRead } from "../../api/parentDashboard";

var GROUPS=[
  {key:"attention",  label:"Needs Attention",  icon:"⚠️",  types:["child_inactive","low_mock_score","plan_expired","payment_failed"]},
  {key:"good",       label:"Good News",         icon:"🌟",  types:["strong_improvement","mock_test_completed"]},
  {key:"upcoming",   label:"Upcoming",          icon:"📅",  types:["plan_expiring","recommendation"]},
  {key:"access",     label:"Platform Access",   icon:"🔑",  types:["feature_locked","upgrade_suggestion"]},
];

function groupNotifs(notifs){
  var grouped={attention:[],good:[],upcoming:[],access:[],other:[]};
  (notifs||[]).forEach(function(n){
    var matched=false;
    for(var i=0;i<GROUPS.length;i++){
      if(GROUPS[i].types.includes(n.type)){
        grouped[GROUPS[i].key].push(n);
        matched=true;
        break;
      }
    }
    if(!matched) grouped.other.push(n);
  });
  return grouped;
}

function NotifRow({n, onRead}){
  var isUnread=n.status!=="read";
  var sevColor={"critical":"#ef4444","warning":"#f59e0b","info":"#6366f1","success":"#22c55e"}[n.severity||"info"]||"#6366f1";
  return(
    <div style={{display:"flex",gap:8,padding:"7px 0",borderBottom:"1px solid var(--border,#f1f5f9)",alignItems:"flex-start",opacity:isUnread?1:.65}}>
      <span style={{fontSize:".95rem",flexShrink:0}}>{n.icon||"•"}</span>
      <div style={{flex:1}}>
        <div style={{fontSize:".8rem",fontWeight:isUnread?700:500,color:sevColor}}>{n.title}</div>
        <div style={{fontSize:".73rem",color:"#64748b",marginTop:1}}>{n.message||n.body}</div>
      </div>
      {isUnread&&onRead&&(
        <button onClick={function(){onRead(n.id);}} style={{background:"none",border:"1px solid var(--border,#e5e7eb)",borderRadius:5,fontSize:".65rem",padding:"1px 6px",cursor:"pointer",color:"#94a3b8",flexShrink:0,fontFamily:"inherit"}}>✓</button>
      )}
    </div>
  );
}

export default function ParentNotificationGroups({notifications, onRefresh}){
  var [filter,setFilter]=useState("all");
  var [marking,setMarking]=useState(false);

  var all=notifications||[];
  var unread=all.filter(function(n){return n.status!=="read";}).length;
  var grouped=groupNotifs(all);

  var filters=[{key:"all",label:"All"},{key:"attention",label:"⚠️ Urgent"},{key:"good",label:"🌟 Good News"},{key:"access",label:"🔑 Access"}];

  async function handleReadAll(){
    setMarking(true);
    await markAllNotificationsRead().catch(function(){});
    if(onRefresh) onRefresh();
    setMarking(false);
  }

  async function handleRead(id){
    if((id||"").startsWith("rule-")) return; // stateless
    await markNotificationRead(id).catch(function(){});
    if(onRefresh) onRefresh();
  }

  if(!all.length) return(
    <div style={{color:"#94a3b8",fontSize:".82rem",padding:"8px 0"}}>No notifications.</div>
  );

  var display=filter==="all"?all:(grouped[filter]||[]);

  return(
    <div data-testid="parent-notification-groups">
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:8,flexWrap:"wrap",gap:6}}>
        <div style={{fontWeight:700,fontSize:".9rem"}}>
          🔔 Notifications {unread>0&&<span style={{fontSize:".75rem",fontWeight:700,color:"#ef4444",marginLeft:4}}>{unread} unread</span>}
        </div>
        {unread>0&&(
          <button disabled={marking} onClick={handleReadAll} style={{border:"1px solid var(--border,#e5e7eb)",background:"var(--surface2,#f8fafc)",borderRadius:6,fontSize:".72rem",padding:"3px 10px",cursor:"pointer",fontFamily:"inherit",color:"#64748b"}}>
            Mark all read
          </button>
        )}
      </div>
      {/* Filter tabs */}
      <div style={{display:"flex",gap:4,overflowX:"auto",WebkitOverflowScrolling:"touch",marginBottom:8,paddingBottom:2}}>
        {filters.map(function(f){return(
          <button key={f.key} onClick={function(){setFilter(f.key);}}
            style={{padding:"3px 10px",borderRadius:15,border:"1px solid var(--border,#e5e7eb)",background:filter===f.key?"#6366f1":"var(--surface2,#f8fafc)",color:filter===f.key?"#fff":"#64748b",fontSize:".72rem",cursor:"pointer",fontFamily:"inherit",whiteSpace:"nowrap",fontWeight:filter===f.key?700:400}}>
            {f.label}
          </button>
        );})}
      </div>
      {/* List */}
      {display.length===0
        ?<div style={{color:"#94a3b8",fontSize:".78rem",padding:"4px 0"}}>No notifications in this category.</div>
        :display.slice(0,10).map(function(n,i){return <NotifRow key={n.id||i} n={n} onRead={handleRead}/>;})
      }
    </div>
  );
}
