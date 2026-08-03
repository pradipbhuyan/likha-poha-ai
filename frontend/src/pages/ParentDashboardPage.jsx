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
var GRADES=["Grade 5","Grade 6","Grade 7","Grade 8","Grade 9","Grade 10","Grade 11","Grade 12"];
var STREAMS=[
  {key:"PCM",label:"Science (PCM)"},
  {key:"PCB",label:"Science (PCB)"},
  {key:"PCMB",label:"Science (PCMB)"},
  {key:"Commerce",label:"Commerce"},
  {key:"Humanities",label:"Arts / Humanities"},
];

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
function AddChildModal({onClose, onAdded, canAdd, _planName, childCount}){
  var [form,setForm]=useState({username:"",grade:"Grade 9",password:"",email:"",stream:""});
  var needsStream = form.grade==="Grade 11"||form.grade==="Grade 12";
  var [loading,setLoading]=useState(false);
  var [msg,setMsg]=useState(null);
  var [creds,setCreds]=useState(null); // {login_id, password, login_email}

  function copyToClipboard(text){
    navigator.clipboard&&navigator.clipboard.writeText(text).catch(function(){});
  }

  // Credentials panel shown after successful creation
  if(creds){
    return(
      <div style={{position:"fixed",inset:0,background:"rgba(0,0,0,.4)",zIndex:400,display:"flex",alignItems:"center",justifyContent:"center",padding:16}}>
        <div style={{background:"var(--panel,#fff)",border:"1px solid #86efac",borderRadius:14,padding:"16px 18px",width:"100%",maxWidth:420,boxShadow:"0 8px 32px rgba(0,0,0,.2)"}}>
          <div style={{fontWeight:800,fontSize:"1rem",color:"#166534",marginBottom:4}}>Child account created</div>
          <div style={{fontSize:".78rem",color:"#64748b",marginBottom:14}}>
            Share these credentials with your child. The password will not be shown again.
          </div>
          <div style={{background:"rgba(34,197,94,.06)",border:"1px solid #86efac",borderRadius:8,padding:"10px 14px",marginBottom:8}}>
            <div style={{fontSize:".72rem",color:"#64748b",marginBottom:2}}>Login ID (username)</div>
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
              <code style={{fontWeight:700,fontSize:".9rem",color:"#1e293b"}}>{creds.login_id}</code>
              <button onClick={function(){copyToClipboard(creds.login_id);}} style={{border:"1px solid #86efac",background:"none",borderRadius:5,padding:"2px 8px",fontSize:".7rem",cursor:"pointer",color:"#166534",fontFamily:"inherit"}}>Copy</button>
            </div>
          </div>
          <div style={{background:"rgba(99,102,241,.06)",border:"1px solid rgba(167,139,250,.3)",borderRadius:8,padding:"10px 14px",marginBottom:14}}>
            <div style={{fontSize:".72rem",color:"#64748b",marginBottom:2}}>Temporary Password</div>
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
              <code style={{fontWeight:700,fontSize:".9rem",color:"#1e293b"}}>{creds.password}</code>
              <button onClick={function(){copyToClipboard(creds.password);}} style={{border:"1px solid rgba(167,139,250,.3)",background:"none",borderRadius:5,padding:"2px 8px",fontSize:".7rem",cursor:"pointer",color:"#6366f1",fontFamily:"inherit"}}>Copy</button>
            </div>
          </div>
          <div style={{fontSize:".73rem",color:"#64748b",marginBottom:12,background:"rgba(245,158,11,.06)",border:"1px solid #fcd34d",borderRadius:6,padding:"6px 10px"}}>
            ℹ️ Your child logs in at <strong>likhapoha.in</strong> using their <strong>Login ID</strong> and this password. They are on <strong>Free Tier</strong> with limited access.
          </div>
          {/* What to do next */}
          <div style={{background:"rgba(34,197,94,.06)",border:"1px solid #86efac",borderRadius:8,padding:"10px 14px",marginBottom:12}}>
            <div style={{fontWeight:700,fontSize:".82rem",color:"#166534",marginBottom:6}}>What to do next</div>
            <div style={{fontSize:".75rem",color:"#374151",display:"flex",flexDirection:"column",gap:5}}>
              <div>1. Share the Login ID and password with your child</div>
              <div>2. Your child opens <strong>likhapoha.in</strong> and signs in</div>
              <div>3. They select their subject and start their first lesson</div>
              <div>4. You can track their progress from your Parent Dashboard</div>
            </div>
          </div>
          <button onClick={function(){onAdded();onClose();}} style={{padding:"8px 16px",borderRadius:8,border:"none",background:"#6366f1",color:"#fff",fontFamily:"inherit",fontSize:".82rem",fontWeight:700,cursor:"pointer",width:"100%"}}>Got it — Go to Dashboard</button>
        </div>
      </div>
    );
  }

  async function submit(e){
    e.preventDefault();
    if(!form.username||!form.password){setMsg("Name and password required.");return;}
    if(needsStream&&!form.stream){setMsg("Please choose a stream for Grade 11/12.");return;}
    setLoading(true);
    var d=await createStudent({...form,email:form.email||undefined}).catch(function(e2){return{success:false,error:e2.message};});
    setLoading(false);
    if(d.success!==false){
      // Show credentials panel with login ID and password
      setCreds({login_id:d.login_id||form.username, password:form.password, login_email:d.login_email});
      onAdded(); // refresh dashboard in background
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
        {/* If limit reached AND parent already has children: show a guide card on
            how the child logs in, with an upgrade option at the bottom.
            Never block the first child addition — always show the form for new parents. */}
        {!canAdd && childCount > 0 ?(
          <div>
            {/* Guide card — how child logs in */}
            <div style={{background:"rgba(34,197,94,.06)",border:"1px solid #86efac",borderRadius:10,padding:"14px 16px",marginBottom:12}}>
              <div style={{fontSize:".92rem",fontWeight:800,color:"#166534",marginBottom:8}}>🎉 Your child's account is ready!</div>
              <div style={{fontSize:".78rem",color:"#374151",marginBottom:12,lineHeight:1.6}}>
                Here's how your child can log in and start learning:
              </div>
              <div style={{display:"flex",flexDirection:"column",gap:7,fontSize:".78rem",color:"#374151"}}>
                <div style={{display:"flex",gap:10,alignItems:"flex-start"}}>
                  <span style={{minWidth:22,height:22,borderRadius:"50%",background:"#6366f1",color:"#fff",display:"inline-flex",alignItems:"center",justifyContent:"center",fontSize:".68rem",fontWeight:800,flexShrink:0}}>1</span>
                  <span>Go to <strong>likhapoha.in</strong> and click <strong>Log In</strong></span>
                </div>
                <div style={{display:"flex",gap:10,alignItems:"flex-start"}}>
                  <span style={{minWidth:22,height:22,borderRadius:"50%",background:"#6366f1",color:"#fff",display:"inline-flex",alignItems:"center",justifyContent:"center",fontSize:".68rem",fontWeight:800,flexShrink:0}}>2</span>
                  <span>Enter the <strong>Login ID (username)</strong> and <strong>password</strong> you set when creating the account</span>
                </div>
                <div style={{display:"flex",gap:10,alignItems:"flex-start"}}>
                  <span style={{minWidth:22,height:22,borderRadius:"50%",background:"#6366f1",color:"#fff",display:"inline-flex",alignItems:"center",justifyContent:"center",fontSize:".68rem",fontWeight:800,flexShrink:0}}>3</span>
                  <span>The child selects their <strong>Grade, Subject and Chapter</strong> and clicks <strong>Generate Lesson</strong></span>
                </div>
                <div style={{display:"flex",gap:10,alignItems:"flex-start"}}>
                  <span style={{minWidth:22,height:22,borderRadius:"50%",background:"#6366f1",color:"#fff",display:"inline-flex",alignItems:"center",justifyContent:"center",fontSize:".68rem",fontWeight:800,flexShrink:0}}>4</span>
                  <span>You can track their progress and scores from <strong>your Parent Dashboard</strong></span>
                </div>
              </div>
            </div>
            {/* Upgrade nudge — secondary */}
            <div style={{background:"rgba(99,102,241,.06)",border:"1px solid rgba(167,139,250,.3)",borderRadius:8,padding:"10px 14px",marginBottom:10,textAlign:"center"}}>
              <div style={{fontSize:".76rem",color:"#64748b",marginBottom:6}}>
                Want to add a second child? Upgrade to <strong>Family Premium</strong>.
              </div>
              <button onClick={onClose} style={{padding:"6px 18px",borderRadius:7,border:"none",background:"#6366f1",color:"#fff",fontFamily:"inherit",fontSize:".78rem",fontWeight:700,cursor:"pointer"}}>Upgrade Plan</button>
            </div>
            <button onClick={onClose} style={{background:"none",border:"none",color:"#64748b",cursor:"pointer",fontFamily:"inherit",fontSize:".82rem",width:"100%",textAlign:"center",padding:"6px 0"}}>Close</button>
          </div>
        ):(
          <>
            <div data-testid="add-child-free-tier-notice" style={{background:"rgba(99,102,241,.07)",border:"1px solid rgba(167,139,250,.3)",borderRadius:8,padding:"10px 14px",marginBottom:10}}>
              <div style={{fontSize:".78rem",color:"#6366f1",fontWeight:600}}>ℹ️ New children start on Free Tier</div>
              <div style={{fontSize:".72rem",color:"#64748b",marginTop:2}}>The child will have limited access until you upgrade your plan.</div>
            </div>
            <form onSubmit={submit} style={{display:"flex",flexDirection:"column",gap:8}}>
              <label><span style={{fontSize:".78rem",fontWeight:600}}>Child's Name *</span>
                <input value={form.username} onChange={function(e){setForm(function(p){return{...p,username:e.target.value};});}} required style={{...inp,marginTop:2}}/></label>
              <label><span style={{fontSize:".78rem",fontWeight:600}}>Grade *</span>
                <select value={form.grade} onChange={function(e){setForm(function(p){return{...p,grade:e.target.value};});}} style={{...inp,marginTop:2}}>
                  {GRADES.map(function(g){return <option key={g} value={g}>{g}</option>;})}</select></label>
              {needsStream&&(
                <label><span style={{fontSize:".78rem",fontWeight:600}}>Stream *</span>
                  <select value={form.stream} onChange={function(e){setForm(function(p){return{...p,stream:e.target.value};});}} style={{...inp,marginTop:2}}>
                    <option value="">Choose a stream…</option>
                    {STREAMS.map(function(s){return <option key={s.key} value={s.key}>{s.label}</option>;})}</select></label>
              )}
              <label><span style={{fontSize:".78rem",fontWeight:600}}>Password *</span>
                <input type="text" value={form.password} onChange={function(e){setForm(function(p){return{...p,password:e.target.value};});}} required placeholder="Share with child" style={{...inp,marginTop:2}}/></label>
              <label><span style={{fontSize:".78rem",fontWeight:600}}>Email (optional)</span>
                <input type="email" value={form.email} onChange={function(e){setForm(function(p){return{...p,email:e.target.value};});}} style={{...inp,marginTop:2}}/></label>
              {msg&&<div style={{fontSize:".82rem",color:msg.startsWith("✅")?"#166534":"#dc2626"}}>{msg}</div>}
              <button type="submit" disabled={loading} style={btn1}>{loading?"Adding…":"Add Child"}</button>
            </form>
          </>
        )}
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
    // Retry once on auth errors — new Google OAuth parents may have a brief
    // window where the session token hasn't propagated to the backend yet
    if(d&&d.success===false&&d.error&&(d.error.includes("session")||d.error.includes("Unauthorized")||d.error.includes("403"))){
      await new Promise(function(r){setTimeout(r,2000);});
      d=await getParentDashboardSummary().catch(function(e){return{success:false,error:e.message};});
    }
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
          childCount={children.length}
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
