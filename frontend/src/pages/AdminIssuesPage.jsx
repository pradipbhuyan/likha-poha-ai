/**
 * AdminIssuesPage.jsx -- Product Bugs / Student Feedback
 * Features: Hide-Closed toggle, per-row Close, checkboxes, Bulk Close + Bulk Copy for Codex
 */
import { useCallback, useEffect, useState } from "react";
import { authFetch } from "../api/authClient";

const SC={"open":"#6366f1","triaged":"#f59e0b","in_progress":"#0ea5e9","fixed":"#22c55e","wont_fix":"#94a3b8","duplicate":"#cbd5e1"};
const VC={"critical":"#ef4444","high":"#f97316","medium":"#f59e0b","low":"#94a3b8"};
const ITL={"content_issue":"Content Issue","wrong_explanation":"Wrong Explanation","missing_section":"Missing Section","wrong_formula":"Wrong Formula","wrong_answer":"Wrong Answer/MCQ","broken_page":"Broken Page","login_issue":"Login/Access","other":"Other"};
const CLOSED=new Set(["fixed","wont_fix"]);
const CTYPE=new Set(["content_issue","wrong_explanation","missing_section","wrong_formula","wrong_answer"]);
const STATS=["open","triaged","in_progress","fixed","wont_fix","duplicate"];

function Badge({label,color}){
  return <span style={{fontSize:".68rem",fontWeight:700,padding:"2px 8px",borderRadius:8,background:color+"20",color}}>{label}</span>;
}

function SCard({label,value,color,testid}){
  return(
    <div data-testid={testid} style={{background:"var(--panel,#fff)",border:"1px solid var(--border,#e5e7eb)",borderRadius:10,padding:"14px 18px",flex:"1 1 130px",minWidth:120}}>
      <div style={{fontWeight:800,fontSize:"1.5rem",color:color||"#6366f1"}}>{value??0}</div>
      <div style={{fontSize:".75rem",color:"#64748b",marginTop:3}}>{label}</div>
    </div>
  );
}

function mkPrompt(iss){
  const bi=iss.browser_info||{},p=[];
  p.push("# Bug Report -- Likhapoha AI Platform","","**Defect:** "+(iss.defect_number||iss.id));
  p.push("**Type:** "+(iss.issue_type||"").replace(/_/g," "));
  p.push("**Severity:** "+iss.severity,"**Status:** "+iss.status);
  p.push("**Reported:** "+(iss.created_at?new Date(iss.created_at).toLocaleString():"?"),"");
  p.push("## Description",iss.description||"","## Context");
  p.push("- Route: "+(iss.route||"?"),"- Grade: "+(iss.grade||"?"),"- Subject: "+(iss.subject||"?"));
  p.push("- Chapter: "+(iss.chapter||"?"),"- Step: "+(iss.lesson_step||"?"),"");
  p.push("## Browser","- Platform: "+(bi.platform||"?"),"- Viewport: "+bi.viewportWidth+"x"+bi.viewportHeight,"");
  if(bi.recentJsErrors&&bi.recentJsErrors.length>0){p.push("## JS Errors");bi.recentJsErrors.forEach(e=>p.push("- "+(e.message||"")));}
  p.push("## Admin Notes",iss.admin_notes||"(none)","","---","Platform: Likhapoha AI -- React+FastAPI+Supabase. Please investigate and fix.");
  return p.join("\n");
}

function mkBulk(issues){
  const hdr=["# Bulk Bug Report -- Likhapoha AI Platform","**Issues:** "+issues.length,"**Generated:** "+new Date().toLocaleString(),"","Please fix all issues. Platform: Likhapoha AI.","","===",""].join("\n");
  return hdr+issues.map((iss,i)=>"## Issue "+(i+1)+" of "+issues.length+"\n\n"+mkPrompt(iss)+"\n\n").join("\n");
}

function clip(text,cb){
  if(navigator.clipboard){navigator.clipboard.writeText(text).then(()=>cb(true)).catch(()=>{const t=document.createElement("textarea");t.value=text;document.body.appendChild(t);t.select();document.execCommand("copy");document.body.removeChild(t);cb(true);});}
  else{const t=document.createElement("textarea");t.value=text;document.body.appendChild(t);t.select();document.execCommand("copy");document.body.removeChild(t);cb(true);}
}

function IssueDrawer({issue,onClose,onUpdate,onCloseIssue}){
  const[notes,setNotes]=useState(issue?issue.admin_notes||"":"");
  const[status,setStatus]=useState(issue?issue.status||"open":"open");
  const[saving,setSaving]=useState(false);
  const[closing,setClosing]=useState(false);
  const[rewarming,setRewarming]=useState(false);
  const[autoFixing,setAutoFixing]=useState(false);
  const[msg,setMsg]=useState(null);
  useEffect(()=>{if(issue){setNotes(issue.admin_notes||"");setStatus(issue.status||"open");}},[issue]);
  if(!issue)return null;
  const isClosed=CLOSED.has(issue.status);
  const isContent=CTYPE.has(issue.issue_type)&&issue.grade&&issue.subject&&issue.chapter;
  const ctxRows=[["Role",issue.reporter_role],["Grade",issue.grade],["Subject",issue.subject],["Chapter",issue.chapter],["Step",issue.lesson_step],["Route",issue.route],["Viewport",issue.browser_info?.viewportWidth?issue.browser_info.viewportWidth+"x"+issue.browser_info.viewportHeight:null],["DPR",issue.browser_info?.devicePixelRatio?String(issue.browser_info.devicePixelRatio):null],["Platform",issue.browser_info?.platform||null],["JS Errs",issue.browser_info?.recentJsErrors?.length>0?issue.browser_info.recentJsErrors.length+" logged":null],["Reported",issue.created_at?new Date(issue.created_at).toLocaleString():null]].filter(r=>r[1]);
  const commitMsg=(issue.status==="fixed"?"fix":"wip")+"("+(issue.defect_number||"DEF")+"): "+(issue.title||issue.description||"").slice(0,60);
  const lbl={fontSize:".78rem",fontWeight:600,display:"block",marginBottom:4};
  const inp={width:"100%",padding:"8px 10px",borderRadius:7,border:"1px solid var(--border,#e5e7eb)",fontFamily:"inherit",fontSize:".82rem",boxSizing:"border-box"};
  async function save(){setSaving(true);setMsg(null);try{const r=await authFetch("/api/admin/issues/"+issue.id,{method:"PATCH",body:JSON.stringify({status,admin_notes:notes})});if(r.success){setMsg("Saved");onUpdate(r.issue);}}catch(e){setMsg("Error: "+e.message);}finally{setSaving(false);}}
  async function closeIssue(){if(!window.confirm("Mark "+(issue.defect_number||issue.id)+" as fixed and remove from view?"))return;setClosing(true);setMsg(null);try{const r=await authFetch("/api/admin/issues/"+issue.id,{method:"PATCH",body:JSON.stringify({status:"fixed",admin_notes:notes||"Closed by admin."})});if(r.success){setMsg("Closed");onCloseIssue(r.issue);}}catch(e){setMsg("Error: "+e.message);}finally{setClosing(false);}}
  async function rewarm(){if(!window.confirm("Clear cache + regenerate "+issue.chapter+"?"))return;setRewarming(true);setMsg(null);try{const r=await authFetch("/api/admin/issues/"+issue.id+"/fix-and-rewarm",{method:"POST"});if(r.success){setMsg(r.message);onUpdate(r.issue);}}catch(e){setMsg("Error: "+e.message);}finally{setRewarming(false);}}
  async function autoFix(){setAutoFixing(true);setMsg(null);try{const r=await authFetch("/api/admin/issues/"+issue.id+"/auto-fix",{method:"POST"});if(r.success&&r.auto_fixable){setMsg("Auto-fixed: "+r.rule_applied);setNotes(r.fix_note);setStatus("fixed");onUpdate(r.issue);}else{setMsg(r.message||"Not auto-fixable");}}catch(e){setMsg("Error: "+e.message);}finally{setAutoFixing(false);}}
  return(
    <div data-testid="issue-drawer" style={{position:"fixed",right:0,top:0,bottom:0,width:420,maxWidth:"95vw",background:"var(--panel,#fff)",boxShadow:"-8px 0 30px rgba(0,0,0,.15)",zIndex:1000,overflowY:"auto",padding:"20px 22px"}}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:16}}>
        <h3 style={{margin:0,fontWeight:800,fontSize:".95rem"}}>Issue Details</h3>
        <div style={{display:"flex",gap:8,alignItems:"center"}}>
          {!isClosed&&<button data-testid="close-issue-btn" onClick={closeIssue} disabled={closing} style={{padding:"5px 12px",borderRadius:7,border:"none",background:closing?"#94a3b8":"#22c55e",color:"#fff",fontWeight:700,fontSize:".74rem",cursor:closing?"not-allowed":"pointer",fontFamily:"inherit"}}>{closing?"Closing…":"✓ Close Issue"}</button>}
          {isClosed&&<span style={{fontSize:".72rem",color:"#22c55e",fontWeight:700,padding:"4px 10px",background:"#f0fdf4",borderRadius:6}}>✓ Closed</span>}
          <button onClick={onClose} style={{background:"none",border:"none",cursor:"pointer",fontSize:"1.2rem",color:"#94a3b8"}}>✕</button>
        </div>
      </div>
      {issue.defect_number&&(<div style={{background:"rgba(99,102,241,.08)",borderRadius:8,padding:"6px 12px",marginBottom:10,display:"flex",alignItems:"center",justifyContent:"space-between"}}><span style={{fontWeight:900,fontSize:"1rem",color:"#6366f1",fontFamily:"monospace"}}>{issue.defect_number}</span><button onClick={()=>{navigator.clipboard?.writeText(issue.defect_number);setMsg("Copied");setTimeout(()=>setMsg(null),2000);}} style={{background:"none",border:"none",cursor:"pointer",fontSize:".72rem",color:"#6366f1",fontWeight:700}}>Copy</button></div>)}
      <div style={{display:"flex",gap:6,flexWrap:"wrap",marginBottom:14}}>
        <Badge label={issue.severity} color={VC[issue.severity]||"#94a3b8"}/>
        <Badge label={(issue.status||"").replace(/_/g," ")} color={SC[issue.status]||"#94a3b8"}/>
        <Badge label={ITL[issue.issue_type]||issue.issue_type} color="#6366f1"/>
      </div>
      {issue.title&&<p style={{fontWeight:700,margin:"0 0 8px",fontSize:".9rem"}}>{issue.title}</p>}
      <div style={{background:"var(--surface2,#f8fafc)",borderRadius:8,padding:"10px 12px",marginBottom:14}}><div style={{fontSize:".72rem",fontWeight:600,color:"#64748b",marginBottom:4}}>DESCRIPTION</div><p style={{margin:0,fontSize:".83rem",lineHeight:1.6}}>{issue.description}</p></div>
      {issue.browser_info?.screenshotDataUrl&&(<div style={{marginBottom:14}}><div style={{fontSize:".72rem",fontWeight:700,color:"#64748b",marginBottom:6}}>SCREENSHOT</div><img src={issue.browser_info.screenshotDataUrl} alt="screenshot" data-testid="issue-screenshot" style={{width:"100%",borderRadius:8,maxHeight:280,objectFit:"contain",background:"#000"}}/></div>)}
      <div style={{background:"var(--surface2,#f8fafc)",borderRadius:8,padding:"10px 12px",marginBottom:14,fontSize:".78rem"}}><div style={{fontWeight:600,color:"#64748b",marginBottom:6}}>CONTEXT</div>{ctxRows.map(([k,v])=><div key={k} style={{display:"flex",gap:6,marginBottom:3}}><span style={{fontWeight:600,minWidth:70}}>{k}:</span><span style={{color:"#374151"}}>{v}</span></div>)}</div>
      <div style={{marginBottom:12}}><label style={lbl}>Status</label><select value={status} onChange={e=>setStatus(e.target.value)} data-testid="issue-status-select" style={{...inp,padding:"8px"}}>{STATS.map(s=><option key={s} value={s}>{s.replace(/_/g," ")}</option>)}</select></div>
      <div style={{marginBottom:14}}><label style={lbl}>Admin Notes</label><textarea value={notes} onChange={e=>setNotes(e.target.value)} rows={4} data-testid="admin-notes-input" placeholder="Internal notes…" style={{...inp,resize:"vertical"}}/></div>
      <button onClick={save} disabled={saving} data-testid="save-issue-btn" style={{width:"100%",padding:"10px",borderRadius:8,border:"none",background:saving?"#94a3b8":"#6366f1",color:"#fff",fontWeight:700,fontSize:".85rem",cursor:saving?"not-allowed":"pointer",fontFamily:"inherit"}}>{saving?"Saving…":"Save Changes"}</button>
      {msg&&<div style={{marginTop:8,fontSize:".78rem",color:msg.startsWith("Error")?"#dc2626":"#22c55e"}}>{msg}</div>}
      {isContent&&(<div style={{marginTop:14,borderTop:"1px solid var(--border,#e5e7eb)",paddingTop:14}}><div style={{fontSize:".76rem",fontWeight:600,color:"#64748b",marginBottom:6}}>🔧 Fix Content + Rewarm</div><p style={{fontSize:".74rem",color:"#64748b",margin:"0 0 10px",lineHeight:1.5}}>Clears lesson cache for <strong>{issue.chapter}</strong>{issue.lesson_step?" (step: "+issue.lesson_step+")":""} and regenerates.</p><button data-testid="fix-and-rewarm-btn" disabled={rewarming||issue.status==="fixed"} onClick={rewarm} style={{width:"100%",padding:"10px",borderRadius:8,border:"none",background:rewarming||issue.status==="fixed"?"#94a3b8":"#10b981",color:"#fff",fontWeight:700,fontSize:".85rem",cursor:rewarming||issue.status==="fixed"?"not-allowed":"pointer",fontFamily:"inherit"}}>{rewarming?"⏳ Rewarming…":issue.status==="fixed"?"✓ Already Fixed":"🔧 Fix with AI + Rewarm"}</button></div>)}
      {!isClosed&&(<div style={{marginTop:14,borderTop:"1px solid var(--border,#e5e7eb)",paddingTop:14}}><div style={{fontSize:".76rem",fontWeight:600,color:"#64748b",marginBottom:6}}>⚡ Cosmetic Auto-Fix</div><button data-testid="auto-fix-btn" disabled={autoFixing} onClick={autoFix} style={{width:"100%",padding:"10px",borderRadius:8,border:"none",background:autoFixing?"#94a3b8":"linear-gradient(135deg,#f59e0b,#d97706)",color:"#fff",fontWeight:700,fontSize:".85rem",cursor:autoFixing?"not-allowed":"pointer",fontFamily:"inherit"}}>{autoFixing?"⏳ Analysing…":"⚡ Apply Cosmetic Auto-Fix"}</button></div>)}
      <div style={{marginTop:14,borderTop:"1px solid var(--border,#e5e7eb)",paddingTop:14}}><div style={{fontSize:".76rem",fontWeight:600,color:"#64748b",marginBottom:6}}>🤖 Copy for Codex</div><button data-testid="copy-for-codex-btn" onClick={()=>clip(mkPrompt(issue),ok=>setMsg(ok?"✅ Copied for Codex":"Copy failed"))} style={{width:"100%",padding:"9px",borderRadius:8,border:"1px solid #6366f1",background:"transparent",color:"#6366f1",fontWeight:700,fontSize:".82rem",cursor:"pointer",fontFamily:"inherit"}}>📋 Copy Bug Report for Codex</button></div>
      {issue.defect_number&&(<div style={{marginTop:14,borderTop:"1px solid var(--border,#e5e7eb)",paddingTop:14}}><div style={{fontSize:".76rem",fontWeight:600,color:"#64748b",marginBottom:6}}>🔗 Git Commit Message</div><div style={{background:"var(--surface2,#f0f0ff)",borderRadius:7,padding:"8px 10px",fontFamily:"monospace",fontSize:".76rem",color:"#1e293b",marginBottom:6,wordBreak:"break-all",border:"1px solid rgba(99,102,241,.2)"}}>{commitMsg}</div><button data-testid="copy-commit-msg-btn" onClick={()=>{navigator.clipboard?.writeText(commitMsg);setMsg("Commit message copied");setTimeout(()=>setMsg(null),3000);}} style={{width:"100%",padding:"8px",borderRadius:7,border:"1px solid rgba(99,102,241,.4)",background:"transparent",color:"#6366f1",fontWeight:700,fontSize:".78rem",cursor:"pointer",fontFamily:"inherit"}}>Copy Commit Message</button></div>)}
    </div>
  );
}

export default function AdminIssuesPage({user:_user}){
  const[summary,setSummary]=useState(null);
  const[issues,setIssues]=useState([]);
  const[loading,setLoading]=useState(true);
  const[selectedIssue,setSelectedIssue]=useState(null);
  const[filters,setFilters]=useState({status:"",severity:"",issue_type:"",grade:"",subject:""});
  const[hideClosed,setHideClosed]=useState(true);
  const[selected,setSelected]=useState(new Set());
  const[bulkMsg,setBulkMsg]=useState(null);
  const[bulkBusy,setBulkBusy]=useState(false);

  const loadSummary=useCallback(async()=>{try{const r=await authFetch("/api/admin/issues/summary");if(r.success)setSummary(r);}catch{setSummary(null);}},[]);
  const loadIssues=useCallback(async()=>{setLoading(true);try{const p=new URLSearchParams();Object.entries(filters).forEach(([k,v])=>{if(v)p.append(k,v);});const r=await authFetch("/api/admin/issues?"+p.toString());if(r.success)setIssues(r.issues||[]);}catch{setIssues([]);}finally{setLoading(false);}},[filters]);
  useEffect(()=>{loadSummary();},[loadSummary]);
  useEffect(()=>{loadIssues();},[loadIssues]);

  const visible=hideClosed?issues.filter(i=>!CLOSED.has(i.status)):issues;

  function handleUpdate(upd){setIssues(prev=>prev.map(i=>i.id===upd.id?upd:i));setSelectedIssue(upd);loadSummary();}
  function handleCloseIssue(upd){setIssues(prev=>prev.map(i=>i.id===upd.id?upd:i));setSelectedIssue(null);setSelected(prev=>{const n=new Set(prev);n.delete(upd.id);return n;});loadSummary();}
  function toggleSelect(id){setSelected(prev=>{const n=new Set(prev);if(n.has(id))n.delete(id);else n.add(id);return n;});}
  function selectAll(){setSelected(new Set(visible.map(i=>i.id)));}
  function clearSelect(){setSelected(new Set());}

  async function bulkClose(status){
    if(selected.size===0)return;
    if(!window.confirm("Mark "+selected.size+" issue(s) as '"+status+"'?"))return;
    setBulkBusy(true);setBulkMsg(null);
    try{
      const r=await authFetch("/api/admin/issues/bulk-close",{method:"POST",body:JSON.stringify({issue_ids:[...selected],status})});
      if(r.success){setBulkMsg("✅ "+r.message);setSelected(new Set());loadIssues();loadSummary();}
    }catch(e){setBulkMsg("Error: "+e.message);}
    finally{setBulkBusy(false);}
  }
  function bulkCopyCodex(){
    if(selected.size===0)return;
    const sel=visible.filter(i=>selected.has(i.id));
    clip(mkBulk(sel),ok=>setBulkMsg(ok?"✅ "+sel.length+" issues copied for Codex":"Copy failed"));
  }

  const sel={background:"var(--panel,#fff)",padding:"7px 10px",borderRadius:7,border:"1px solid var(--border,#e5e7eb)",fontFamily:"inherit",fontSize:".8rem"};
  return(
    <div data-testid="admin-issues-page" style={{maxWidth:1100,margin:"0 auto",padding:"0 0 60px"}}>
      <div style={{marginBottom:20}}>
        <h2 style={{fontWeight:800,fontSize:"1.2rem",margin:"0 0 3px"}}>🐛 Product Bugs / Student Feedback</h2>
        <div style={{fontSize:".85rem",color:"#64748b"}}>Issue reports submitted by users. Use bulk actions to close or send to Codex.</div>
      </div>

      {summary&&(
        <div data-testid="issue-summary-cards" style={{display:"flex",flexWrap:"wrap",gap:10,marginBottom:24}}>
          <SCard label="Open" value={summary.open} color="#6366f1" testid="stat-open"/>
          <SCard label="Critical" value={summary.critical} color="#ef4444" testid="stat-critical"/>
          <SCard label="High" value={summary.high} color="#f97316" testid="stat-high"/>
          <SCard label="Content Issues" value={summary.content_issues} color="#0ea5e9" testid="stat-content"/>
          <SCard label="Fixed This Week" value={summary.fixed_this_week} color="#22c55e" testid="stat-fixed"/>
        </div>
      )}

      {/* Filters row */}
      <div data-testid="issue-filters" style={{display:"flex",flexWrap:"wrap",gap:8,marginBottom:12,alignItems:"center"}}>
        {[{key:"status",opts:["","open","triaged","in_progress","fixed","wont_fix","duplicate"],lbl:"Status"},{key:"severity",opts:["","critical","high","medium","low"],lbl:"Severity"},{key:"issue_type",opts:["","content_issue","wrong_explanation","missing_section","wrong_formula","wrong_answer","broken_page","login_issue","other"],lbl:"Type"}].map(({key,opts,lbl})=>(
          <select key={key} value={filters[key]} style={sel} data-testid={"filter-"+key} onChange={e=>setFilters(p=>({...p,[key]:e.target.value}))}>
            <option value="">{lbl}</option>
            {opts.filter(Boolean).map(o=><option key={o} value={o}>{ITL[o]||o.replace(/_/g," ")}</option>)}
          </select>
        ))}
        <input placeholder="Grade" value={filters.grade} style={{...sel,width:130}} data-testid="filter-grade" onChange={e=>setFilters(p=>({...p,grade:e.target.value}))}/>
        <input placeholder="Subject" value={filters.subject} style={{...sel,width:110}} data-testid="filter-subject" onChange={e=>setFilters(p=>({...p,subject:e.target.value}))}/>
        <button onClick={()=>setFilters({status:"",severity:"",issue_type:"",grade:"",subject:""})} style={{...sel,cursor:"pointer",color:"#6366f1",fontWeight:600}}>Clear</button>
        {/* Hide-closed toggle */}
        <button data-testid="hide-closed-toggle" onClick={()=>setHideClosed(p=>!p)}
          style={{...sel,cursor:"pointer",fontWeight:700,color:hideClosed?"#22c55e":"#94a3b8",borderColor:hideClosed?"#22c55e":"#e5e7eb"}}>
          {hideClosed?"✓ Hiding Closed":"Show All"}
        </button>
      </div>

      {/* Bulk action toolbar — appears when rows selected */}
      {selected.size>0&&(
        <div data-testid="bulk-toolbar" style={{display:"flex",gap:8,flexWrap:"wrap",alignItems:"center",marginBottom:12,padding:"10px 14px",background:"#f0f0ff",borderRadius:10,border:"1px solid rgba(99,102,241,.2)"}}>
          <span style={{fontWeight:700,fontSize:".82rem",color:"#6366f1"}}>{selected.size} selected</span>
          <button onClick={()=>bulkClose("fixed")} disabled={bulkBusy} data-testid="bulk-close-btn" style={{padding:"6px 14px",borderRadius:7,border:"none",background:bulkBusy?"#94a3b8":"#22c55e",color:"#fff",fontWeight:700,fontSize:".78rem",cursor:bulkBusy?"not-allowed":"pointer",fontFamily:"inherit"}}>✓ Close Selected (fixed)</button>
          <button onClick={()=>bulkClose("wont_fix")} disabled={bulkBusy} style={{padding:"6px 14px",borderRadius:7,border:"none",background:bulkBusy?"#94a3b8":"#94a3b8",color:"#fff",fontWeight:700,fontSize:".78rem",cursor:bulkBusy?"not-allowed":"pointer",fontFamily:"inherit"}}>✗ Won't Fix</button>
          <button onClick={bulkCopyCodex} data-testid="bulk-copy-codex-btn" style={{padding:"6px 14px",borderRadius:7,border:"1px solid #6366f1",background:"transparent",color:"#6366f1",fontWeight:700,fontSize:".78rem",cursor:"pointer",fontFamily:"inherit"}}>📋 Copy All for Codex ({selected.size})</button>
          <button onClick={clearSelect} style={{padding:"6px 10px",borderRadius:7,border:"none",background:"none",color:"#94a3b8",fontSize:".78rem",cursor:"pointer"}}>Deselect All</button>
          <button onClick={selectAll} style={{padding:"6px 10px",borderRadius:7,border:"none",background:"none",color:"#6366f1",fontSize:".78rem",cursor:"pointer",fontWeight:600}}>Select All Visible</button>
          {bulkMsg&&<span style={{fontSize:".78rem",color:bulkMsg.startsWith("✅")?"#22c55e":"#dc2626"}}>{bulkMsg}</span>}
        </div>
      )}

      {loading?(
        <div style={{textAlign:"center",padding:40,color:"#94a3b8"}}>Loading…</div>
      ):visible.length===0?(
        <div data-testid="no-issues" style={{textAlign:"center",padding:40}}>
          <div style={{fontSize:"2rem"}}>✅</div>
          <p style={{fontWeight:600}}>{issues.length>0&&hideClosed?"All visible issues are closed. Toggle 'Show All' to see them.":"No issues found matching filters."}</p>
        </div>
      ):(
        <div style={{border:"1px solid var(--border,#e5e7eb)",borderRadius:10,overflow:"hidden"}}>
          {/* Header */}
          <div style={{display:"grid",gridTemplateColumns:"36px 100px 80px 100px 130px 1fr 80px 90px",background:"var(--surface2,#f8fafc)",padding:"8px 14px",fontSize:".72rem",fontWeight:700,color:"#64748b",textTransform:"uppercase",letterSpacing:".04em",alignItems:"center"}}>
            <input type="checkbox" checked={selected.size===visible.length&&visible.length>0} onChange={e=>e.target.checked?selectAll():clearSelect()} style={{cursor:"pointer"}}/>
            <span>Defect</span><span>Severity</span><span>Status</span><span>Type</span><span>Description</span><span>Date</span><span>Action</span>
          </div>
          {visible.map(issue=>(
            <div key={issue.id} data-testid="issue-row"
              onClick={()=>setSelectedIssue(issue)}
              style={{display:"grid",gridTemplateColumns:"36px 100px 80px 100px 130px 1fr 80px 90px",padding:"10px 14px",borderTop:"1px solid var(--border,#f1f5f9)",alignItems:"center",background:selectedIssue?.id===issue.id?"var(--surface2,#f0f0ff)":"var(--panel,#fff)",cursor:"pointer"}}>
              <input type="checkbox" checked={selected.has(issue.id)} onClick={e=>e.stopPropagation()} onChange={()=>toggleSelect(issue.id)} style={{cursor:"pointer"}}/>
              <span style={{fontFamily:"monospace",fontSize:".72rem",fontWeight:700,color:"#6366f1",overflow:"hidden",textOverflow:"ellipsis"}}>{issue.defect_number||"—"}</span>
              <span><Badge label={issue.severity} color={VC[issue.severity]||"#94a3b8"}/></span>
              <span><Badge label={(issue.status||"").replace(/_/g," ")} color={SC[issue.status]||"#94a3b8"}/></span>
              <span style={{fontSize:".78rem"}}>{ITL[issue.issue_type]||issue.issue_type}</span>
              <span style={{fontSize:".78rem",overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{issue.title||issue.description?.slice(0,80)}</span>
              <span style={{fontSize:".72rem",color:"#94a3b8"}}>{issue.created_at?new Date(issue.created_at).toLocaleDateString():"—"}</span>
              <button onClick={e=>{e.stopPropagation();if(!CLOSED.has(issue.status)&&window.confirm("Close "+issue.defect_number+"?")){authFetch("/api/admin/issues/"+issue.id,{method:"PATCH",body:JSON.stringify({status:"fixed",admin_notes:"Closed by admin."})}).then(r=>{if(r.success)handleCloseIssue(r.issue);});}}} disabled={CLOSED.has(issue.status)}
                style={{padding:"4px 8px",borderRadius:6,border:"none",background:CLOSED.has(issue.status)?"#f0fdf4":"#22c55e",color:CLOSED.has(issue.status)?"#22c55e":"#fff",fontWeight:700,fontSize:".7rem",cursor:CLOSED.has(issue.status)?"default":"pointer",fontFamily:"inherit"}}>
                {CLOSED.has(issue.status)?"✓":"Close"}
              </button>
            </div>
          ))}
        </div>
      )}

      {selectedIssue&&(
        <IssueDrawer issue={selectedIssue} onClose={()=>setSelectedIssue(null)} onUpdate={handleUpdate} onCloseIssue={handleCloseIssue}/>
      )}

      <ReporterAccessPanel/>
    </div>
  );
}

function ReporterAccessPanel(){
  const[reporters,setReporters]=useState([]);
  const[loadingRep,setLoadingRep]=useState(false);
  const[searchUser,setSearchUser]=useState("");
  const[searchResults,setSearchResults]=useState([]);
  const[searching,setSearching]=useState(false);
  const[toggling,setToggling]=useState({});
  const[msg,setMsg]=useState(null);

  async function loadReporters(){setLoadingRep(true);try{const r=await authFetch("/api/admin/users/issue-reporters");if(r.success)setReporters(r.reporters||[]);}catch{setReporters([]);}finally{setLoadingRep(false);}}
  async function searchUsers(){if(!searchUser.trim())return;setSearching(true);setMsg(null);try{const r=await authFetch("/api/admin/users/search?q="+encodeURIComponent(searchUser)+"&limit=10");if(r.success){setSearchResults(r.users||[]);if(!r.users||r.users.length===0)setMsg("No users found.");}else{setSearchResults([]);setMsg("Search failed: "+(r.error||"Unknown"));}}catch(e){setSearchResults([]);setMsg("Error: "+e.message);}finally{setSearching(false);}}
  async function toggleAccess(userId,enabled){setToggling(p=>({...p,[userId]:true}));setMsg(null);try{const r=await authFetch("/api/admin/users/"+userId+"/can-report-issues?enabled="+enabled,{method:"PATCH"});if(r.success){setMsg(enabled?"✅ Access granted":"✅ Access revoked");loadReporters();setSearchResults(prev=>prev.map(u=>u.id===userId?{...u,can_report_issues:enabled}:u));}}catch(e){setMsg("❌ "+e.message);}finally{setToggling(p=>({...p,[userId]:false}));}}

  const inp={padding:"7px 10px",borderRadius:7,border:"1px solid var(--border,#e5e7eb)",fontFamily:"inherit",fontSize:".82rem",background:"var(--panel,#fff)"};
  return(
    <div data-testid="reporter-access-panel" style={{marginTop:32,padding:"20px 22px",background:"var(--panel,#fff)",border:"1px solid var(--border,#e5e7eb)",borderRadius:12}}>
      <div style={{fontWeight:700,fontSize:".95rem",marginBottom:4}}>🔐 Report Issue Access</div>
      <div style={{fontSize:".82rem",color:"#64748b",marginBottom:16}}>Control which users can see the "Report Issue" button. Off by default.</div>
      <div style={{display:"flex",gap:8,marginBottom:14,flexWrap:"wrap"}}>
        <input value={searchUser} onChange={e=>setSearchUser(e.target.value)} placeholder="Search username or email..." style={{...inp,flex:"1 1 200px"}} data-testid="reporter-search-input" onKeyDown={e=>{if(e.key==="Enter")searchUsers();}}/>
        <button onClick={searchUsers} disabled={searching} style={{...inp,cursor:"pointer",background:"#6366f1",color:"#fff",border:"none",fontWeight:600}}>{searching?"Searching…":"Search"}</button>
        <button onClick={loadReporters} style={{...inp,cursor:"pointer",color:"#6366f1",fontWeight:600}}>Refresh</button>
      </div>
      {msg&&<div style={{marginBottom:10,fontSize:".8rem",color:msg.startsWith("✅")?"#22c55e":"#dc2626"}}>{msg}</div>}
      {searchResults.length>0&&(
        <div style={{marginBottom:16}}>
          <div style={{fontSize:".76rem",fontWeight:600,color:"#64748b",marginBottom:6}}>SEARCH RESULTS</div>
          {searchResults.map(u=>(
            <div key={u.id} style={{display:"flex",alignItems:"center",gap:10,padding:"6px 0",borderBottom:"1px solid var(--border,#f1f5f9)",flexWrap:"wrap"}}>
              <span style={{fontSize:".8rem",flex:1}}>{u.username||u.email} <span style={{color:"#94a3b8"}}>({u.role})</span></span>
              <button onClick={()=>toggleAccess(u.id,!u.can_report_issues)} disabled={toggling[u.id]} data-testid={"toggle-reporter-"+u.id} style={{padding:"4px 12px",borderRadius:7,border:"none",cursor:"pointer",fontFamily:"inherit",fontWeight:600,fontSize:".76rem",background:u.can_report_issues?"#fef2f2":"#f0fdf4",color:u.can_report_issues?"#dc2626":"#16a34a"}}>{toggling[u.id]?"…":u.can_report_issues?"Revoke":"Grant Access"}</button>
            </div>
          ))}
        </div>
      )}
      <div>
        <div style={{fontSize:".76rem",fontWeight:600,color:"#64748b",marginBottom:6}}>USERS WITH REPORT ACCESS ({reporters.length})</div>
        {loadingRep?<div style={{color:"#94a3b8",fontSize:".8rem"}}>Loading…</div>:reporters.length===0?<div style={{color:"#94a3b8",fontSize:".8rem"}}>No users have report access yet.</div>:reporters.map(u=>(
          <div key={u.id} style={{display:"flex",alignItems:"center",gap:10,padding:"5px 0",borderBottom:"1px solid var(--border,#f1f5f9)",flexWrap:"wrap"}}>
            <span style={{fontSize:".8rem",flex:1}}>{u.username||u.email} <span style={{color:"#94a3b8"}}>({u.role})</span></span>
            <button onClick={()=>toggleAccess(u.id,false)} disabled={toggling[u.id]} style={{padding:"4px 12px",borderRadius:7,border:"none",cursor:"pointer",fontFamily:"inherit",fontWeight:600,fontSize:".76rem",background:"#fef2f2",color:"#dc2626"}}>{toggling[u.id]?"…":"Revoke"}</button>
          </div>
        ))}
      </div>
    </div>
  );
}
