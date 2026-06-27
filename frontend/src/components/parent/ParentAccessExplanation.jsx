/**
 * ParentAccessExplanation.jsx
 * Clear Platform Access explanation for Free Tier vs paid vs expired.
 * Uses "Platform Access" terminology, not "CBSE Access".
 */

var FEATURE_LABELS={
  LESSONS:"AI Lessons",MOCK_TEST:"Mock Tests",EXEMPLAR:"Exemplar Practice",
  EXEMPLAR_RESEARCH:"Exemplar Research",ASK_DOUBTS:"Ask Doubts",AI_ASSISTANT:"AI Assistant",
};
var FEATURE_ICONS={LESSONS:"📖",MOCK_TEST:"📝",EXEMPLAR:"🔬",EXEMPLAR_RESEARCH:"🧪",ASK_DOUBTS:"❓",AI_ASSISTANT:"🤖"};

function AccessBadge({state}){
  var s={
    full:  {bg:"rgba(34,197,94,.1)",color:"#166534",label:"✓ Full Access"},
    limited:{bg:"rgba(245,158,11,.1)",color:"#92400e",label:"~ Limited"},
    locked: {bg:"rgba(239,68,68,.08)",color:"#dc2626",label:"🔒 Locked"},
  }[state]||{bg:"#f1f5f9",color:"#64748b",label:state};
  return <span style={{fontSize:".68rem",fontWeight:700,padding:"2px 7px",borderRadius:4,background:s.bg,color:s.color}}>{s.label}</span>;
}

export default function ParentAccessExplanation({plan, featureBadges, subscription, onUpgrade}){
  if(!plan) return null;
  var cpk=plan.canonical_plan_key||subscription?.canonical_plan_key||"FREE_TIER";
  var isFree=cpk==="FREE_TIER";
  var isExpired=!plan.has_full_access&&(cpk!=="FREE_TIER"&&cpk!=="ADMIN_GRANT");
  var isExpiring=plan.expiry_warning;

  return(
    <div data-testid="parent-access-explanation">
      {/* Status block */}
      <div style={{
        background:isFree?"rgba(239,68,68,.06)":isExpiring?"rgba(245,158,11,.08)":"rgba(34,197,94,.06)",
        border:"1px solid "+(isFree?"#fca5a5":isExpiring?"#fcd34d":"#86efac"),
        borderRadius:10,padding:"10px 14px",marginBottom:10
      }}>
        <div style={{fontWeight:700,fontSize:".88rem",color:isFree?"#dc2626":isExpiring?"#d97706":"#166534"}}>
          {isFree?"🔒 Restricted Platform Access":isExpired?"⚠️ Plan Expired":isExpiring?"⚠️ Plan Expiring Soon":"✅ Full Platform Access"}
        </div>
        <div style={{fontSize:".78rem",color:"#64748b",marginTop:3}}>{plan.description}</div>
        {isExpiring&&plan.days_remaining!=null&&(
          <div style={{fontSize:".73rem",color:"#d97706",fontWeight:600,marginTop:3}}>
            Expires in {plan.days_remaining} day{plan.days_remaining!==1?"s":""}
          </div>
        )}
        {plan.expires_at&&!isExpiring&&(
          <div style={{fontSize:".7rem",color:"#94a3b8",marginTop:3}}>Valid until: {new Date(plan.expires_at).toLocaleDateString()}</div>
        )}
      </div>

      {/* Feature list */}
      {featureBadges&&featureBadges.length>0&&(
        <div style={{marginBottom:10}}>
          <div style={{fontWeight:600,fontSize:".78rem",marginBottom:6,color:"#64748b"}}>Platform Features</div>
          <div style={{display:"flex",flexDirection:"column",gap:4}}>
            {featureBadges.map(function(b){return(
              <div key={b.feature} style={{display:"flex",justifyContent:"space-between",alignItems:"center",padding:"4px 0",borderBottom:"1px solid var(--border,#f1f5f9)"}}>
                <span style={{fontSize:".78rem"}}>{FEATURE_ICONS[b.feature]||"•"} {FEATURE_LABELS[b.feature]||b.label}</span>
                <AccessBadge state={b.state}/>
              </div>
            );})}
          </div>
        </div>
      )}

      {/* Upgrade CTA */}
      {(isFree||isExpired)&&onUpgrade&&(
        <div style={{padding:"10px 14px",background:"rgba(99,102,241,.07)",border:"1px solid rgba(167,139,250,.3)",borderRadius:8}}>
          <div style={{fontSize:".82rem",fontWeight:700,color:"#6366f1",marginBottom:4}}>
            {isFree?"Unlock Full Access":"Renew for Full Access"}
          </div>
          <div style={{fontSize:".75rem",color:"#64748b",marginBottom:8}}>
            {isFree
              ?"Upgrade to unlock Exemplar practice, unlimited mock tests, and full AI lessons."
              :"Your plan has expired. Renew to restore full access without interruption."}
          </div>
          <button onClick={onUpgrade} style={{padding:"6px 14px",borderRadius:7,border:"none",background:"#6366f1",color:"#fff",fontFamily:"inherit",fontSize:".78rem",fontWeight:600,cursor:"pointer"}}>
            🚀 {isFree?"Upgrade Now":"Renew Plan"}
          </button>
        </div>
      )}
    </div>
  );
}
