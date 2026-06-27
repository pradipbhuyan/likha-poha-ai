/**
 * ParentDashboardPage.jsx — Parent Experience Phase 3
 * Redesigned parent portal using extracted components.
 * Safety: parentId alone NEVER implies paid access — all feature data from backend.
 */
import { useCallback, useEffect, useState } from "react";
import { getParentDashboardSummary, createStudent } from "../api/parentDashboard";
import ParentHeroSummary from "../components/parent/ParentHeroSummary";
import ParentChildStatusCard from "../components/parent/ParentChildStatusCard";
import ParentActionPlan from "../components/parent/ParentActionPlan";
import ParentChildWorkspace from "../components/parent/ParentChildWorkspace";

// ── Design tokens (shared) ────────────────────────────────────────────────────
var inp={padding:"8px 12px",borderRadius:8,border:"1px solid var(--border,#e5e7eb)",fontFamily:"inherit",fontSize:".85rem",background:"var(--surface2,#f8fafc)",color:"var(--text,#1e293b)",width:"100%"};
var btn1={padding:"8px 16px",borderRadius:8,border:"none",background:"#6366f1",color:"#fff",fontFamily:"inherit",fontSize:".82rem",fontWeight:700,cursor:"pointer"};
var GRADES=Array.from({length:12},function(_,i){return"Grade "+(i+1);});

// ── Skeleton loader ───────────────────────────────────────────────────────────
function Skel(){
  return(
    <div style={{maxWidth:960,margin:"0 auto",padding:"24px 14px"}}>
      <div style={{height:26,background:"var(--border,#e5e7eb)",borderRadius:6,width:"40%",marginBottom:8}}/>
      <div style={{height:14,background:"var(--border,#e5e7eb)",borderRadius:4,width:"60%",marginBottom:24}}/>
      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(280px,1fr))",gap:14}}>
        {[1,2].map(function(i){return <div key={i} style={{height:220,background:"var(--border,#e5e7eb)",borderRadius:14}}/>;})}</div>
    </div>
  );
}

// ── Add Child Modal ───────────────────────────────────────────────────────────
function AddChildModal({onClose, onAdded, canAdd, planName}){
  var [form,setForm]=useState({username:"",grade:"Grade 9",password:"",email:""});
  var [loading,setLoading]=useState(false);
  var [msg,setMsg]=useState(null);

  async function submit(e){
    e.preventDefault();
    if(!form.username||!form.password){setMsg("Name and password required.");return;}
    setLoading(true);
    var d=await createStudent({...form,email:form.email||undefined}).catch(function(e2){return{success:false,error:e2.message};});
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
      <div style={{background:"var(--panel,#fff)",border:"1px solid var(--border,#e5e7eb)",borderRadius:14,padding:"16px 18px",width:"100%",maxWidth:420,maxHeight:"90vh",overflowY:"auto",boxShadow:"0 8px 32px rgba(0,0,0,.2)"}}>
        <div style={{display:"flex",justifyContent:"space-between",marginBottom:14}}>
          <h4 style={{margin:0}}>➕ Add Child</h4>
          <button onClick={onClose} style={{background:"none",border:"none",cursor:"pointer",fontSize:"1.1rem"}}>✕</button>
        </div>
        {!canAdd&&(
          <div style={{background:"#fef2f2",border:"1px solid #fecaca",borderRadius:8,padding:"10px 14px",marginBottom:10}}>
            <div style={{fontSize:".82rem",color:"#dc2626",fontWeight:600}}>Child limit reached for {planName}.</div>
            <div style={{fontSize:".75rem",color:"#64748b",marginTop:3}}>Upgrade to Family Premium to add a second child.</div>
          </div>
        )}
        <div data-testid="add-child-free-tier-notice" style={{background:"rgba(99,102,241,.07)",border:"1px solid rgba(167,139,250,.3)",borderRadius:8,padding:"10px 14px",marginBottom:10}}>
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

// ── Main export ───────────────────────────────────────────────────────────────
export default function ParentDashboardPage({ user, setActivePage }){
  var [summary,    setSummary]    = useState(null);
  var [loading,    setLoading]    = useState(true);
  var [error,      setError]      = useState(null);
  var [selected,   setSelected]   = useState(null);  // open child workspace
  var [showAdd,    setShowAdd]    = useState(false);
  var [flashMsg,   setFlashMsg]   = useState(null);

  var loadSummary=useCallback(async function(){
    setLoading(true);
    var d=await getParentDashboardSummary().catch(function(e){return{success:false,error:e.message};});
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
      <div style={{background:"#fef2f2",border:"1px solid #fecaca",borderRadius:10,padding:"14px 16px",color:"#dc2626"}}>⚠ {error}</div>
    </div>
  );

  var children   = summary?.children||[];
  // var notifs = summary?.notifications||[];  // available for future use
  var parentPlan = summary?.parent_plan||{};
  var canAdd     = summary?.can_add_child!==false;
  var parentName = (user?.username||summary?.parent?.username||"").split(" ")[0];

  return(
    <div style={{fontFamily:"inherit",maxWidth:960,margin:"0 auto",padding:"0 14px 60px"}}>
      {/* Flash toast */}
      {flashMsg&&<div style={{position:"fixed",top:16,left:"50%",transform:"translateX(-50%)",background:"#1e293b",color:"#fff",padding:"8px 20px",borderRadius:8,fontSize:".82rem",fontWeight:600,zIndex:999,boxShadow:"0 4px 24px rgba(0,0,0,.25)",whiteSpace:"nowrap"}}>{flashMsg}</div>}

      {/* Child Workspace drawer */}
      {selected&&(
        <ParentChildWorkspace
          child={selected}
          onClose={function(){setSelected(null);}}
          onUpgrade={goUpgrade}
        />
      )}

      {/* Add Child Modal */}
      {showAdd&&(
        <AddChildModal
          canAdd={canAdd}
          planName={parentPlan.plan_name||"your plan"}
          onClose={function(){setShowAdd(false);}}
          onAdded={function(){loadSummary();flash("✅ Child added — on Free Tier with limited access.");}}
        />
      )}

      {/* Hero summary */}
      <div style={{paddingTop:18}}>
        <ParentHeroSummary
          data-testid="parent-hero-summary"
          summary={summary}
          parentName={parentName}
          onAddChild={function(){setShowAdd(true);}}
          onUpgrade={goUpgrade}
        />
      </div>

      {/* No children */}
      {children.length===0&&(
        <div data-testid="parent-no-children" style={{background:"var(--panel,#fff)",border:"1px solid var(--border,#e5e7eb)",borderRadius:14,padding:"40px 24px",textAlign:"center",color:"#94a3b8",marginBottom:16}}>
          <div style={{fontSize:"2.5rem",marginBottom:8}}>🎓</div>
          <div style={{fontWeight:600,marginBottom:4}}>No children linked yet</div>
          <div style={{fontSize:".82rem",marginBottom:16}}>Add your child to track their progress and manage their learning.</div>
          <button onClick={function(){setShowAdd(true);}} style={btn1}>＋ Add Child</button>
        </div>
      )}

      {/* Children grid */}
      {children.length>0&&(
        <div data-testid="parent-children-list" style={{marginBottom:20}}>
          <h2 style={{fontSize:".95rem",fontWeight:800,margin:"0 0 12px"}}>🎓 Your Children</h2>
          <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(280px,1fr))",gap:14}}>
            {children.map(function(child){return(
              <ParentChildStatusCard
                key={child.id}
                child={child}
                onView={function(c){setSelected(c);}}
                onUpgrade={goUpgrade}
              />
            );})}
          </div>
          {!canAdd&&(
            <div style={{fontSize:".78rem",color:"#64748b",marginTop:8}}>
              Child limit reached for <strong>{parentPlan.plan_name}</strong>.{" "}
              <button onClick={goUpgrade} style={{background:"none",border:"none",color:"#6366f1",cursor:"pointer",fontFamily:"inherit",fontWeight:600,fontSize:".78rem"}}>Upgrade to Family Premium</button> for a second child.
            </div>
          )}
        </div>
      )}

      {/* Action plan */}
      {children.length>0&&(
        <div style={{marginBottom:20}}>
          <ParentActionPlan
            children={children}
            onUpgrade={goUpgrade}
            onOpenChild={function(c){setSelected(c);}}
          />
        </div>
      )}
    </div>
  );
}
