/**
 * TeacherDashboardPage.jsx — Teacher Productivity Command Center
 * Design: Notion x Linear x Google Classroom x Duolingo Teacher
 */
import { useCallback, useEffect, useState } from "react";
import { LayoutDashboard, GraduationCap, Building2, Mail, CheckSquare } from "lucide-react";
import {
  getTeacherClassroomSummary, listTeacherStudents,
  listTeacherInvitations, createTeacherInvitation,
  resendTeacherInvitation, cancelTeacherInvitation,
  listTeacherClassrooms, createTeacherClassroom,
  updateTeacherClassroom, archiveTeacherClassroom,
  addStudentToClassroom, createTeacherStudent,
  getInterventions, listTeacherTasks,
  createTeacherTask, completeTeacherTask, dismissTeacherTask,
} from "../api/teacherDashboard";
import StudentWorkspace   from "../components/teacher/StudentWorkspace";
import SuggestedTaskModal from "../components/teacher/SuggestedTaskModal";
import ClassroomAnalyticsCard from "../components/teacher/ClassroomAnalyticsCard";

const SEV = {
  critical:{ bg:"rgba(239,68,68,.07)",  border:"#fca5a5", text:"#dc2626", dot:"#ef4444" },
  medium:  { bg:"rgba(245,158,11,.07)", border:"#fcd34d", text:"#d97706", dot:"#f59e0b" },
  low:     { bg:"rgba(99,102,241,.06)", border:"#c7d2fe", text:"#4f46e5", dot:"#6366f1" },
};
const PC = { critical:"#dc2626", medium:"#d97706", low:"#64748b" };
const PB = { critical:"rgba(239,68,68,.07)", medium:"rgba(245,158,11,.07)", low:"rgba(148,163,184,.07)" };
const SS = {
  active:  { background:"rgba(34,197,94,.1)",  color:"#166534" },
  inactive:{ background:"rgba(148,163,184,.1)", color:"#64748b" },
  archived:{ background:"rgba(148,163,184,.1)", color:"#64748b" },
  pending: { background:"rgba(245,158,11,.1)",  color:"#92400e" },
  accepted:{ background:"rgba(34,197,94,.1)",   color:"#166534" },
  expired: { background:"rgba(239,68,68,.1)",   color:"#dc2626" },
  cancelled:{ background:"rgba(148,163,184,.1)",color:"#64748b" },
};
function card(x){ return { background:"var(--panel,#fff)", border:"1px solid var(--border,#e5e7eb)", borderRadius:14, padding:"16px 18px", marginBottom:16, ...(x||{}) }; }
const inp  = { padding:"8px 12px", borderRadius:8, border:"1px solid var(--border,#e5e7eb)", fontFamily:"inherit", fontSize:".85rem", background:"var(--surface2,#f8fafc)", color:"var(--text,#1e293b)", width:"100%" };
const btn1 = { padding:"7px 14px", borderRadius:8, border:"none", background:"#6366f1", color:"#fff", fontFamily:"inherit", fontSize:".82rem", fontWeight:700, cursor:"pointer" };
const btn2 = { padding:"5px 10px", borderRadius:7, border:"1px solid var(--border,#e5e7eb)", background:"var(--panel,#fff)", fontFamily:"inherit", fontSize:".75rem", cursor:"pointer", color:"var(--text,#374151)" };
function bsm(c){ c=c||"#6366f1"; return { padding:"4px 9px", borderRadius:6, border:"1px solid "+c, background:c+"18", color:c, fontFamily:"inherit", fontSize:".72rem", fontWeight:600, cursor:"pointer" }; }
const GRADES = Array.from({length:12},function(_,i){ return "Grade "+(i+1); });
function greet(){ var h=new Date().getHours(); return h<12?"Good morning":h<17?"Good afternoon":"Good evening"; }

function Bdg({ status }){
  var s=SS[status]||SS.inactive;
  return <span style={{...s,display:"inline-block",fontSize:".7rem",padding:"1px 7px",borderRadius:5,fontWeight:600}}>{status}</span>;
}
function Skel(){
  return (
    <div style={{maxWidth:1040,margin:"0 auto",padding:"24px 14px"}}>
      <div style={{height:28,background:"var(--border,#e5e7eb)",borderRadius:6,width:"38%",marginBottom:8}}/>
      <div style={{height:14,background:"var(--border,#e5e7eb)",borderRadius:4,width:"58%",marginBottom:24}}/>
      <div style={{display:"flex",gap:10,marginBottom:16}}>
        {[1,2,3,4].map(function(i){return <div key={i} style={{flex:1,height:84,background:"var(--border,#e5e7eb)",borderRadius:14}}/>;  })}
      </div>
      <div style={{height:200,background:"var(--border,#e5e7eb)",borderRadius:14,marginBottom:16}}/>
      <div style={{height:260,background:"var(--border,#e5e7eb)",borderRadius:14}}/>
    </div>
  );
}
function TRow({ task, onComplete, onDismiss }){
  var pc=PC[task.priority]||"#64748b", pb=PB[task.priority]||"rgba(148,163,184,.07)";
  return (
    <div style={{...card(),marginBottom:8,borderLeft:"3px solid "+pc,background:pb,padding:"10px 14px"}}>
      <div style={{display:"flex",justifyContent:"space-between",gap:8,flexWrap:"wrap",alignItems:"center"}}>
        <div style={{flex:1}}>
          <span style={{fontWeight:600,fontSize:".85rem"}}>{task.title}</span>
          <span style={{marginLeft:6,fontSize:".68rem",padding:"1px 5px",borderRadius:4,background:pb,color:pc,fontWeight:700}}>{task.priority}</span>
          {task.description&&<div style={{fontSize:".75rem",color:"#64748b",marginTop:2}}>{task.description}</div>}
          {task.due_date&&<div style={{fontSize:".7rem",color:"#94a3b8",marginTop:1}}>Due: {task.due_date}</div>}
        </div>
        {task.status==="open"&&(
          <div style={{display:"flex",gap:5}}>
            <button onClick={function(){onComplete(task.id);}} style={bsm("#22c55e")}>✓ Done</button>
            <button onClick={function(){onDismiss(task.id);}} style={bsm("#94a3b8")}>Dismiss</button>
          </div>
        )}
        {task.status!=="open"&&<span style={{fontSize:".72rem",color:"#94a3b8"}}>{task.status}</span>}
      </div>
    </div>
  );
}
function SCard({ student, sev, onOpen }){
  var sv=sev?SEV[sev]:null;
  return (
    <div data-testid="student-card" onClick={onOpen} style={{...card(),cursor:"pointer",padding:"10px 14px",marginBottom:8,borderLeft:sv?"3px solid "+sv.dot:"3px solid transparent"}}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",gap:8}}>
        <div style={{flex:1,minWidth:0}}>
          <div style={{display:"flex",alignItems:"center",gap:6,flexWrap:"wrap"}}>
            <span style={{fontWeight:700,fontSize:".87rem"}}>{student.username}</span>
            <Bdg status={student.account_status||"active"}/>
            {sv&&<span style={{fontSize:".68rem",background:sv.bg,color:sv.text,padding:"1px 6px",borderRadius:4,fontWeight:700,border:"1px solid "+sv.border}}>{sev==="critical"?"⚠ Critical":"↩ Review"}</span>}
          </div>
          <div style={{fontSize:".71rem",color:"#94a3b8",marginTop:2}}>{student.grade||"—"}{student.email?" · "+student.email:""}</div>
        </div>
        <span style={{fontSize:".75rem",color:"#6366f1",fontWeight:600,flexShrink:0}}>View →</span>
      </div>
    </div>
  );
}
function IRow({ inv, onView, onTask }){
  var s=SEV[inv.severity]||SEV.low;
  return (
    <div style={{...card(),marginBottom:8,background:s.bg,borderColor:s.border,padding:"10px 14px"}}>
      <div style={{display:"flex",justifyContent:"space-between",gap:8,flexWrap:"wrap",alignItems:"flex-start"}}>
        <div style={{flex:1}}>
          <div style={{display:"flex",alignItems:"center",gap:6,marginBottom:3}}>
            <span style={{width:8,height:8,borderRadius:"50%",background:s.dot,display:"inline-block",flexShrink:0}}/>
            <strong style={{fontSize:".85rem"}}>{inv.student_name}</strong>
            <span style={{fontSize:".7rem",color:"#64748b"}}>{inv.grade}</span>
          </div>
          <div style={{display:"flex",flexWrap:"wrap",gap:4}}>
            {(inv.reasons||[]).map(function(r,i){return <span key={i} style={{fontSize:".7rem",background:"rgba(0,0,0,.04)",padding:"1px 6px",borderRadius:4,color:"#64748b"}}>{r}</span>;})}
          </div>
        </div>
        <div style={{display:"flex",gap:5,alignSelf:"center",flexShrink:0}}>
          {inv.student_id&&onView&&<button onClick={function(){onView(inv);}} style={bsm("#6366f1")}>View</button>}
          {inv.student_id&&onTask&&<button onClick={function(){onTask(inv);}} style={bsm("#8b5cf6")}>+ Task</button>}
        </div>
      </div>
    </div>
  );
}
function InvCard({ inv, onResend, onCancel }){
  var sc=SS[inv.status]||SS.inactive;
  return (
    <div style={{...card(),marginBottom:8,padding:"10px 14px"}}>
      <div style={{display:"flex",justifyContent:"space-between",gap:8,flexWrap:"wrap",alignItems:"center"}}>
        <div>
          <span style={{fontWeight:600,fontSize:".85rem"}}>{inv.student_name}</span>
          <span style={{...sc,display:"inline-block",fontSize:".7rem",padding:"1px 7px",borderRadius:5,fontWeight:600,marginLeft:7}}>{inv.status}</span>
          <div style={{fontSize:".72rem",color:"#94a3b8",marginTop:2}}>{inv.email} · {inv.grade} · Expires {(inv.expires_at||"").slice(0,10)}</div>
        </div>
        <div style={{display:"flex",gap:5}}>
          {(inv.status==="pending"||inv.status==="expired")&&<button onClick={function(){onResend(inv.id);}} style={bsm("#6366f1")}>Resend</button>}
          {inv.status==="pending"&&<button onClick={function(){onCancel(inv.id);}} style={bsm("#ef4444")}>Cancel</button>}
        </div>
      </div>
    </div>
  );
}
// ─────────────────────────────────────────────────────────────────────────────
// Main Export
// ─────────────────────────────────────────────────────────────────────────────
export default function TeacherDashboardPage({ user }) {
  var isPaid = !!(user && user.isPaid);
  var uname  = (user && user.username) || "Teacher";

  var [summary,    setSummary]    = useState(null);
  var [interv,     setInterv]     = useState([]);
  var [tasks,      setTasks]      = useState([]);
  var [students,   setStudents]   = useState([]);
  var [classrooms, setClassrooms] = useState([]);
  var [invites,    setInvites]    = useState([]);
  var [loading,    setLoading]    = useState(true);

  var [workspace,    setWorkspace]    = useState(null);
  var [taskModal,    setTaskModal]    = useState(null);
  var [view,         setView]         = useState("home");
  var [stuQ,         setStuQ]         = useState("");
  var [showAdd,      setShowAdd]      = useState(false);
  var [showTask,     setShowTask]     = useState(false);
  var [newTask,      setNewTask]      = useState({ title:"", priority:"medium" });
  var [flashMsg,     setFlashMsg]     = useState(null);
  var [taskFilter,   setTaskFilter]   = useState("open");
  var [taskViewData, setTaskViewData] = useState([]);
  var [invFilter,    setInvFilter]    = useState("");
  var [invAll,       setInvAll]       = useState([]);
  var [clsForm,      setClsForm]      = useState({ name:"", description:"" });
  var [invForm,      setInvForm]      = useState({ student_name:"", grade:"Grade 9", email:"" });
  var [addStuForm,   setAddStuForm]   = useState({ username:"", grade:"Grade 9", password:"", email:"" });
  var [addStuMsg,    setAddStuMsg]    = useState(null);
  var [invMsg,       setInvMsg]       = useState(null);
  var [clsMsg,       setClsMsg]       = useState(null);

  var loadAll = useCallback(async function(){
    setLoading(true);
    var [s,iv,t,st,cl,in2] = await Promise.all([
      getTeacherClassroomSummary().catch(function(){return null;}),
      getInterventions().catch(function(){return null;}),
      listTeacherTasks("open").catch(function(){return null;}),
      listTeacherStudents({sort:"name"}).catch(function(){return null;}),
      listTeacherClassrooms("active").catch(function(){return null;}),
      listTeacherInvitations("pending").catch(function(){return null;}),
    ]);
    setSummary(s); setInterv((iv&&iv.interventions)||[]);
    setTasks((t&&t.tasks)||[]); setStudents((st&&st.students)||[]);
    setClassrooms((cl&&cl.classrooms)||[]); setInvites((in2&&in2.invitations)||[]);
    setLoading(false);
  },[]);

  var loadTasks = useCallback(async function(f){
    var d=await listTeacherTasks(f).catch(function(){return null;});
    setTaskViewData((d&&d.tasks)||[]);
  },[]);

  var loadInvAll = useCallback(async function(f){
    var d=await listTeacherInvitations(f||null).catch(function(){return null;});
    setInvAll((d&&d.invitations)||[]);
  },[]);

  useEffect(function(){loadAll();},[loadAll]);
  useEffect(function(){if(view==="tasks")loadTasks(taskFilter);},[view,taskFilter,loadTasks]);
  useEffect(function(){if(view==="invitations")loadInvAll(invFilter);},[view,invFilter,loadInvAll]);

  function flash(m){ setFlashMsg(m); setTimeout(function(){setFlashMsg(null);},3000); }

  async function doComplete(id){
    await completeTeacherTask(id).catch(function(){});
    setTasks(function(p){return p.filter(function(t){return t.id!==id;});});
    setTaskViewData(function(p){return p.filter(function(t){return t.id!==id;});});
    flash("✅ Task completed");
  }
  async function doDismiss(id){
    if(!window.confirm("Dismiss this task?"))return;
    await dismissTeacherTask(id).catch(function(){});
    setTasks(function(p){return p.filter(function(t){return t.id!==id;});});
    setTaskViewData(function(p){return p.filter(function(t){return t.id!==id;});});
  }
  async function doCreateTask(e){
    e.preventDefault();
    if(!newTask.title.trim())return;
    var d=await createTeacherTask({...newTask,source:"manual"}).catch(function(){return null;});
    if(d&&d.success){
      setTasks(function(p){return[d.task,...p];});
      setTaskViewData(function(p){return[d.task,...p];});
      setNewTask({title:"",priority:"medium"});
      setShowTask(false);
      flash("✅ Task created");
    }
  }
  async function doAddStudent(e){
    e.preventDefault();
    if(!addStuForm.username||!addStuForm.password){setAddStuMsg("Name and password required.");return;}
    var d=await createTeacherStudent({...addStuForm,email:addStuForm.email||undefined}).catch(function(){return{success:false};});
    if(d&&d.success!==false){setShowAdd(false);setAddStuForm({username:"",grade:"Grade 9",password:"",email:""});loadAll();flash("✅ Student added");}
    else setAddStuMsg("Failed to add student.");
  }
  async function doCreateInv(e){
    e.preventDefault();
    if(!invForm.student_name||!invForm.email){setInvMsg("Name and email required.");return;}
    var d=await createTeacherInvitation(invForm).catch(function(){return{success:false};});
    if(d&&d.success){setInvForm({student_name:"",grade:"Grade 9",email:""});loadInvAll(invFilter);loadAll();flash("✅ Invitation sent");setInvMsg(null);}
    else setInvMsg("Failed to send invitation.");
  }
  async function doCreateCls(e){
    e.preventDefault();
    if(!clsForm.name.trim()){setClsMsg("Name required.");return;}
    var d=await createTeacherClassroom(clsForm).catch(function(){return{success:false};});
    if(d&&d.success){setClsForm({name:"",description:""});loadAll();flash("✅ Classroom created");setClsMsg(null);}
    else setClsMsg("Failed to create classroom.");
  }

  var TABS=[
    {key:"home",       Icon:LayoutDashboard, label:"Dashboard",  tid:"teacher-tab-home"},
    {key:"students",   Icon:GraduationCap,   label:"Students",   tid:"teacher-tab-students"},
    {key:"classrooms", Icon:Building2,       label:"Classrooms", tid:"teacher-tab-classrooms"},
    {key:"invitations",Icon:Mail,            label:"Invitations",tid:"teacher-tab-invitations"},
    {key:"tasks",      Icon:CheckSquare,     label:"Tasks",      tid:"teacher-tab-tasks"},
  ];

  if(loading) return (
    <div style={{fontFamily:"inherit",maxWidth:1040,margin:"0 auto",padding:"0 14px 80px"}}>
      <div style={{display:"flex",gap:2,paddingTop:14,borderBottom:"2px solid var(--border,#e5e7eb)",marginBottom:20,overflowX:"auto"}}>
        {TABS.map(function(t){return(
          <button key={t.key} data-testid={t.tid} onClick={function(){setView(t.key);}}
            style={{padding:"8px 14px",border:"none",background:"none",cursor:"pointer",fontFamily:"inherit",fontSize:".82rem",fontWeight:view===t.key?700:500,color:view===t.key?"#6366f1":"#64748b",borderBottom:view===t.key?"2px solid #6366f1":"2px solid transparent",marginBottom:-2,whiteSpace:"nowrap"}}>
            <t.Icon size={13} strokeWidth={2} style={{display:"inline",verticalAlign:"middle",marginRight:4}} />{t.label}
          </button>
        );})}
      </div>
      <Skel/>
    </div>
  );

  var crit  = interv.filter(function(i){return i.severity==="critical";});
  var med   = interv.filter(function(i){return i.severity==="medium";});
  var open  = tasks.filter(function(t){return t.status==="open";});
  var total = (summary&&summary.totals&&summary.totals.total_students!=null)?summary.totals.total_students:students.length;
  var active= (summary&&summary.totals&&summary.totals.active_students!=null)?summary.totals.active_students:0;
  var avg   = summary&&summary.averages&&summary.averages.mock_test_avg;
  var atLim = ((summary&&summary.totals&&summary.totals.total_students)||0) >= ((summary&&summary.plan_limit)||10);
  var allGood=crit.length===0&&med.length===0&&open.length===0;
  var aidMap={};
  interv.forEach(function(i){if(i.student_id)aidMap[i.student_id]=i.severity;});
  var filtStu=students.filter(function(s){
    return !stuQ||
      (s.username&&s.username.toLowerCase().includes(stuQ.toLowerCase()))||
      (s.email&&s.email.toLowerCase().includes(stuQ.toLowerCase()));
  });

return (
    <div style={{fontFamily:"inherit",maxWidth:1040,margin:"0 auto",padding:"0 14px 80px"}}>

      {/* Flash toast */}
      {flashMsg&&<div style={{position:"fixed",top:16,left:"50%",transform:"translateX(-50%)",background:"#1e293b",color:"#fff",padding:"8px 20px",borderRadius:8,fontSize:".82rem",fontWeight:600,zIndex:999,boxShadow:"0 4px 24px rgba(0,0,0,.25)",whiteSpace:"nowrap"}}>{flashMsg}</div>}

      {/* Overlays */}
      {workspace&&<StudentWorkspace student={workspace} isPaid={isPaid} onClose={function(){setWorkspace(null);loadAll();}}/>}
      {taskModal&&<SuggestedTaskModal intervention={taskModal} onClose={function(){setTaskModal(null);}} onCreated={function(){setTaskModal(null);loadAll();flash("✅ Task created from intervention");}}/>}

      {/* Add Student Modal */}
      {showAdd&&(
        <div style={{position:"fixed",inset:0,background:"rgba(0,0,0,.4)",zIndex:400,display:"flex",alignItems:"center",justifyContent:"center",padding:16}}>
          <div style={{...card(),width:"100%",maxWidth:440,maxHeight:"90vh",overflowY:"auto",boxShadow:"0 8px 32px rgba(0,0,0,.2)"}}>
            <div style={{display:"flex",justifyContent:"space-between",marginBottom:14}}>
              <h4 style={{margin:0}}>➕ Add Student</h4>
              <button onClick={function(){setShowAdd(false);setAddStuMsg(null);}} style={{background:"none",border:"none",cursor:"pointer",fontSize:"1.1rem"}}>✕</button>
            </div>
            <form onSubmit={doAddStudent} style={{display:"flex",flexDirection:"column",gap:9}}>
              <label><span style={{fontSize:".78rem",fontWeight:600}}>Name *</span>
                <input value={addStuForm.username} onChange={function(e){setAddStuForm(function(p){return{...p,username:e.target.value};});}} required style={{...inp,marginTop:2}}/></label>
              <label><span style={{fontSize:".78rem",fontWeight:600}}>Grade *</span>
                <select value={addStuForm.grade} onChange={function(e){setAddStuForm(function(p){return{...p,grade:e.target.value};});}} style={{...inp,marginTop:2}}>
                  {GRADES.map(function(g){return <option key={g} value={g}>{g}</option>;})}</select></label>
              <label><span style={{fontSize:".78rem",fontWeight:600}}>Password *</span>
                <input type="text" value={addStuForm.password} onChange={function(e){setAddStuForm(function(p){return{...p,password:e.target.value};});}} required placeholder="Share with student" style={{...inp,marginTop:2}}/></label>
              <label><span style={{fontSize:".78rem",fontWeight:600}}>Email (optional)</span>
                <input type="email" value={addStuForm.email} onChange={function(e){setAddStuForm(function(p){return{...p,email:e.target.value};});}} style={{...inp,marginTop:2}}/></label>
              {addStuMsg&&<div style={{fontSize:".8rem",color:"#dc2626"}}>{addStuMsg}</div>}
              <button type="submit" style={btn1}>Create Student</button>
            </form>
          </div>
        </div>
      )}

      {/* ── Nav tabs ───────────────────────────────────────────────── */}
      <div style={{display:"flex",gap:2,paddingTop:14,borderBottom:"2px solid var(--border,#e5e7eb)",marginBottom:20,overflowX:"auto",WebkitOverflowScrolling:"touch"}}>
        {TABS.map(function(t){return(
          <button key={t.key} data-testid={t.tid} onClick={function(){setView(t.key);}}
            style={{padding:"8px 14px",border:"none",background:"none",cursor:"pointer",fontFamily:"inherit",fontSize:".82rem",fontWeight:view===t.key?700:500,color:view===t.key?"#6366f1":"#64748b",borderBottom:view===t.key?"2px solid #6366f1":"2px solid transparent",marginBottom:-2,whiteSpace:"nowrap",display:"flex",alignItems:"center",gap:5}}>
            <t.Icon size={13} strokeWidth={2} /><span>{t.label}</span>
            {t.key==="tasks"&&open.length>0&&<span style={{background:"#ef4444",color:"#fff",borderRadius:99,fontSize:".6rem",padding:"1px 5px",fontWeight:800,lineHeight:1.6}}>{open.length}</span>}
            {t.key==="invitations"&&invites.length>0&&<span style={{background:"#f59e0b",color:"#fff",borderRadius:99,fontSize:".6rem",padding:"1px 5px",fontWeight:800,lineHeight:1.6}}>{invites.length}</span>}
          </button>
        );})}
      </div>

      {/* ══ DASHBOARD HOME ══════════════════════════════════════════ */}
      {view==="home"&&(
        <div data-testid="teacher-overview-tab">

          {/* Hero */}
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",gap:12,flexWrap:"wrap",marginBottom:16}}>
            <div>
              <h1 style={{margin:0,fontSize:"1.25rem",fontWeight:800}}>{greet()}, {uname.split(" ")[0]} 👋</h1>
              <p style={{margin:"4px 0 0",fontSize:".83rem",color:"#64748b"}}>
                {allGood?"Everything looks good — no urgent actions today."
                  :[crit.length&&(crit.length+" student"+(crit.length>1?"s":"")+" need"+(crit.length>1?"":"s")+" immediate attention"),
                    med.length&&(med.length+" need review"),
                    open.length&&(open.length+" task"+(open.length>1?"s":"")+" open"),
                    invites.length&&(invites.length+" pending invitation"+(invites.length>1?"s":""))
                   ].filter(Boolean).join(" · ")+"."
                }
              </p>
            </div>
            <button onClick={function(){setShowAdd(true);}} style={btn1}>＋ Add Student</button>
          </div>

          {/* KPI row */}
          <div style={{display:"flex",gap:10,flexWrap:"wrap",marginBottom:20}}>
            {[{icon:"🎓",label:"Students", value:total,  sub:active+" active",  color:"#6366f1"},
              {icon:"📊",label:"Avg Score",value:avg!=null?avg+"%":"—",sub:"mock tests",color:"#0ea5e9"},
              {icon:"🚨",label:"Attention",value:crit.length+med.length,sub:crit.length?crit.length+" critical":"none critical",color:crit.length?"#dc2626":"#64748b"},
              {icon:"✅",label:"Open Tasks",value:open.length,sub:"this session",color:open.length?"#f59e0b":"#22c55e"},
            ].map(function(k){return(
              <div key={k.label} style={{flex:"1 1 100px",...card(),paddingTop:12,paddingBottom:12,textAlign:"center"}}>
                <div style={{fontSize:"1.15rem"}}>{k.icon}</div>
                <div style={{fontSize:"1.5rem",fontWeight:800,color:k.color,lineHeight:1.1,marginTop:2}}>{k.value}</div>
                <div style={{fontSize:".7rem",fontWeight:600,color:"#374151"}}>{k.label}</div>
                <div style={{fontSize:".65rem",color:"#94a3b8"}}>{k.sub}</div>
              </div>
            );})}
          </div>

          {atLim&&<div style={{...card(),background:"#fef2f2",border:"1px solid #fecaca",display:"flex",gap:8,alignItems:"center"}}><span>⚠️</span><span style={{fontSize:".82rem",color:"#dc2626",fontWeight:600}}>Student limit reached — upgrade to add more.</span></div>}

          {/* All-clear banner */}
          {allGood&&(
            <div style={{...card(),background:"linear-gradient(135deg,#f0fdf4,#dcfce7)",border:"1px solid #bbf7d0",display:"flex",gap:10,alignItems:"center"}}>
              <span style={{fontSize:"1.4rem"}}>✅</span>
              <div>
                <div style={{fontWeight:700,fontSize:".9rem",color:"#15803d"}}>All students are on track</div>
                <div style={{fontSize:".75rem",color:"#4ade80"}}>No urgent actions today</div>
              </div>
            </div>
          )}

          {/* 2-col desktop grid */}
          <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(280px,1fr))",gap:16,alignItems:"start"}}>

            {/* LEFT: Attention + Today's Tasks */}
            <div>
              {/* Attention queue */}
              {(crit.length>0||med.length>0)&&(
                <div style={card()}>
                  <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:10}}>
                    <h3 style={{margin:0,fontSize:".9rem",fontWeight:800,color:"#dc2626"}}>🚨 Needs Attention</h3>
                    <span style={{fontSize:".72rem",color:"#64748b"}}>{crit.length+med.length} student{crit.length+med.length>1?"s":""}</span>
                  </div>
                  {[...crit,...med].map(function(inv,i){return(
                    <IRow key={inv.student_id||i} inv={inv}
                      onView={function(){setWorkspace({id:inv.student_id,username:inv.student_name,grade:inv.grade});}}
                      onTask={function(){setTaskModal(inv);}}/>
                  );})}
                  {med.length===0&&crit.length===0&&<div style={{fontSize:".82rem",color:"#94a3b8"}}>No students need attention.</div>}
                </div>
              )}

              {/* Today's Tasks */}
              <div style={card()}>
                <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:10}}>
                  <h3 style={{margin:0,fontSize:".9rem",fontWeight:700}}>✅ Today's Tasks</h3>
                  <button onClick={function(){setShowTask(function(v){return !v;});}} style={{...btn2,background:"#6366f1",color:"#fff",border:"none",fontWeight:600}}>＋ New</button>
                </div>
                {showTask&&(
                  <form onSubmit={doCreateTask} style={{display:"flex",gap:8,flexWrap:"wrap",marginBottom:10}}>
                    <input value={newTask.title} onChange={function(e){setNewTask(function(p){return{...p,title:e.target.value};});}} placeholder="Task title…" required style={{...inp,flex:1,minWidth:140}} data-testid="task-title-input"/>
                    <select value={newTask.priority} onChange={function(e){setNewTask(function(p){return{...p,priority:e.target.value};});}} style={{...inp,width:"auto"}}>
                      <option value="critical">🔴 Critical</option>
                      <option value="medium">🟡 Medium</option>
                      <option value="low">⚪ Low</option>
                    </select>
                    <button type="submit" style={btn1}>Add</button>
                  </form>
                )}
                {open.length===0&&!showTask&&<div style={{fontSize:".82rem",color:"#94a3b8",padding:"6px 0"}}>No open tasks — <button onClick={function(){setShowTask(true);}} style={{background:"none",border:"none",color:"#6366f1",cursor:"pointer",fontFamily:"inherit",fontSize:".82rem",fontWeight:600}}>create one</button></div>}
                {open.map(function(t){return <TRow key={t.id} task={t} onComplete={doComplete} onDismiss={doDismiss}/>;  })}
                {open.length>0&&<button onClick={function(){setView("tasks");}} style={{...btn2,marginTop:6,width:"100%",textAlign:"center"}}>View all tasks →</button>}
              </div>
            </div>

            {/* RIGHT: Pending Invitations + Students preview */}
            <div>
              {/* Pending invitations */}
              {invites.length>0&&(
                <div style={card()}>
                  <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:10}}>
                    <h3 style={{margin:0,fontSize:".9rem",fontWeight:700}}>✉️ Pending Invitations</h3>
                    <button onClick={function(){setView("invitations");}} style={{...btn2,fontSize:".7rem"}}>View all →</button>
                  </div>
                  {invites.slice(0,3).map(function(inv){return(
                    <InvCard key={inv.id} inv={inv}
                      onResend={async function(id){ await resendTeacherInvitation(id).catch(function(){}); loadAll(); flash("✅ Invitation resent"); }}
                      onCancel={async function(id){ if(!window.confirm("Cancel invitation?"))return; await cancelTeacherInvitation(id).catch(function(){}); loadAll(); flash("Invitation cancelled"); }}/>
                  );})}
                </div>
              )}

              {/* Recent students preview */}
              <div style={card()}>
                <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:10}}>
                  <h3 style={{margin:0,fontSize:".9rem",fontWeight:700}}>🎓 Students</h3>
                  <button onClick={function(){setView("students");}} style={{...btn2,fontSize:".7rem"}}>View all →</button>
                </div>
                <input value={stuQ} onChange={function(e){setStuQ(e.target.value);}} placeholder="Search students…" style={{...inp,marginBottom:10}} data-testid="student-search-input"/>
                {filtStu.length===0&&<div style={{fontSize:".82rem",color:"#94a3b8"}}>No students found.</div>}
                {filtStu.slice(0,5).map(function(s){return(
                  <SCard key={s.id} student={s} sev={aidMap[s.id]}
                    onOpen={function(){setWorkspace(s);}}/>
                );})}
{filtStu.length>5&&<button onClick={function(){setView("students");}} style={{...btn2,marginTop:4,width:"100%",textAlign:"center"}}>See all {filtStu.length} students →</button>}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ══ STUDENTS VIEW ═══════════════════════════════════════════ */}
      {view==="students"&&(
        <div data-testid="teacher-students-tab">
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:14,flexWrap:"wrap",gap:8}}>
            <h2 style={{margin:0,fontSize:"1.05rem",fontWeight:800}}>🎓 Students</h2>
            <button onClick={function(){setShowAdd(true);}} style={btn1}>＋ Add Student</button>
          </div>
          <input value={stuQ} onChange={function(e){setStuQ(e.target.value);}} placeholder="Search by name or email…" style={{...inp,marginBottom:12}} data-testid="student-search-input"/>
          {filtStu.length===0&&(
            <div style={{...card(),textAlign:"center",padding:32,color:"#94a3b8"}}>
              <div style={{fontSize:"2rem",marginBottom:8}}>🎓</div>
              <div style={{fontWeight:600}}>No students found.</div>
              <div style={{fontSize:".82rem",marginTop:4}}>Add a student or send an invitation.</div>
              <button onClick={function(){setShowAdd(true);}} style={{...btn1,marginTop:12}}>＋ Add Student</button>
            </div>
          )}
          {filtStu.map(function(s){return(
            <SCard key={s.id} student={s} sev={aidMap[s.id]}
              onOpen={function(){setWorkspace(s);}}/>
          );})}
        </div>
      )}

      {/* ══ CLASSROOMS VIEW ═════════════════════════════════════════ */}
      {view==="classrooms"&&(
        <div data-testid="teacher-classrooms-tab">
          <h2 style={{margin:"0 0 14px",fontSize:"1.05rem",fontWeight:800}}>🏫 Classrooms</h2>

          {/* Create classroom */}
          <div style={card()}>
            <h4 style={{margin:"0 0 10px",fontSize:".88rem"}}>Create Classroom</h4>
            <form onSubmit={doCreateCls} style={{display:"flex",gap:8,flexWrap:"wrap"}}>
              <input value={clsForm.name} onChange={function(e){setClsForm(function(p){return{...p,name:e.target.value};});}} placeholder="Classroom name *" required data-testid="classroom-name-input" style={{...inp,flex:1,minWidth:140}}/>
              <input value={clsForm.description} onChange={function(e){setClsForm(function(p){return{...p,description:e.target.value};});}} placeholder="Description (optional)" style={{...inp,flex:1,minWidth:140}}/>
              <button type="submit" style={btn1}>Create</button>
            </form>
            {clsMsg&&<div style={{marginTop:6,fontSize:".8rem",color:"#dc2626"}}>{clsMsg}</div>}
          </div>

          {classrooms.length===0&&(
            <div style={{...card(),textAlign:"center",padding:24,color:"#94a3b8"}}>
              <div style={{fontSize:"2rem",marginBottom:8}}>🏫</div>
              <div style={{fontWeight:600}}>No classrooms yet</div>
              <div style={{fontSize:".82rem",marginTop:4}}>Create a classroom above to organise your students.</div>
            </div>
          )}

          {classrooms.map(function(cls){return(
            <div key={cls.id} style={card()}>
              <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",gap:8,flexWrap:"wrap",marginBottom:10}}>
                <div>
                  <strong style={{fontSize:".92rem"}}>{cls.name}</strong>
                  <span style={{marginLeft:8,fontSize:".72rem",color:"#94a3b8"}}>{cls.student_count||0} students</span>
                </div>
                <div style={{display:"flex",gap:6}}>
                  <button onClick={async function(){
                    var n=window.prompt("Rename classroom:",cls.name);
                    if(!n||!n.trim())return;
                    await updateTeacherClassroom(cls.id,{name:n.trim()}).catch(function(){});
                    loadAll(); flash("✅ Classroom renamed");
                  }} style={btn2}>Rename</button>
                  <button onClick={async function(){
                    if(!window.confirm("Archive "+cls.name+"?"))return;
                    await archiveTeacherClassroom(cls.id).catch(function(){});
                    loadAll(); flash("Classroom archived");
                  }} style={{...btn2,color:"#dc2626",border:"1px solid #fca5a5"}}>Archive</button>
                </div>
              </div>
              <ClassroomAnalyticsCard classroomId={cls.id} classroomName={cls.name}/>
              <div style={{marginTop:8}}>
                <select onChange={async function(e){
                  if(!e.target.value)return;
                  await addStudentToClassroom(cls.id,e.target.value).catch(function(){});
                  e.target.value="";
                  loadAll(); flash("✅ Student added to classroom");
                }} style={{...inp,width:"auto",maxWidth:"100%"}}>
                  <option value="">＋ Add student to classroom…</option>
                  {students.map(function(s){return <option key={s.id} value={s.id}>{s.username} ({s.grade||"—"})</option>;})}
                </select>
              </div>
            </div>
          );})}
        </div>
      )}
{/* ══ INVITATIONS VIEW ════════════════════════════════════════ */}
      {view==="invitations"&&(
        <div data-testid="teacher-invitations-tab">
          <h2 style={{margin:"0 0 14px",fontSize:"1.05rem",fontWeight:800}}>✉️ Invitations</h2>

          {/* Create invitation */}
          <div style={card()}>
            <h4 style={{margin:"0 0 10px",fontSize:".88rem"}}>Invite a Student</h4>
            <form onSubmit={doCreateInv} style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:8}}>
              <label style={{gridColumn:"1 / -1"}}><span style={{fontSize:".78rem",fontWeight:600}}>Student Name *</span>
                <input value={invForm.student_name} onChange={function(e){setInvForm(function(p){return{...p,student_name:e.target.value};});}} required style={{...inp,marginTop:2}}/></label>
              <label><span style={{fontSize:".78rem",fontWeight:600}}>Grade</span>
                <select value={invForm.grade} onChange={function(e){setInvForm(function(p){return{...p,grade:e.target.value};});}} style={{...inp,marginTop:2}}>
                  {GRADES.map(function(g){return <option key={g} value={g}>{g}</option>;})}</select></label>
              <label><span style={{fontSize:".78rem",fontWeight:600}}>Email *</span>
                <input type="email" value={invForm.email} onChange={function(e){setInvForm(function(p){return{...p,email:e.target.value};});}} required style={{...inp,marginTop:2}}/></label>
              {invMsg&&<div style={{gridColumn:"1 / -1",fontSize:".8rem",color:"#dc2626"}}>{invMsg}</div>}
              <button type="submit" style={btn1}>Send Invitation</button>
            </form>
          </div>

          {/* Filter tabs */}
          <div style={{display:"flex",gap:6,marginBottom:12,flexWrap:"wrap"}}>
            {["","pending","accepted","expired","cancelled"].map(function(f){return(
              <button key={f} onClick={function(){setInvFilter(f);}}
                style={{...btn2,background:invFilter===f?"#6366f1":"var(--panel,#fff)",color:invFilter===f?"#fff":"var(--text,#374151)",border:invFilter===f?"1px solid #6366f1":"1px solid var(--border,#e5e7eb)"}}>
                {f||"All"}
              </button>
            );})}
          </div>

          {invAll.length===0&&<div style={{...card(),textAlign:"center",padding:24,color:"#94a3b8"}}><div style={{fontSize:"2rem",marginBottom:8}}>✉️</div><div style={{fontWeight:600}}>No invitations.</div></div>}
          {invAll.map(function(inv){return(
            <InvCard key={inv.id} inv={inv}
              onResend={async function(id){ await resendTeacherInvitation(id).catch(function(){}); loadInvAll(invFilter); flash("✅ Invitation resent"); }}
              onCancel={async function(id){ if(!window.confirm("Cancel invitation?"))return; await cancelTeacherInvitation(id).catch(function(){}); loadInvAll(invFilter); loadAll(); flash("Invitation cancelled"); }}/>
          );})}
        </div>
      )}

      {/* ══ TASKS VIEW ══════════════════════════════════════════════ */}
      {view==="tasks"&&(
        <div data-testid="teacher-tasks-tab">
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:14,flexWrap:"wrap",gap:8}}>
            <h2 style={{margin:0,fontSize:"1.05rem",fontWeight:800}}>✅ Tasks</h2>
            <button onClick={function(){setShowTask(function(v){return !v;});}} style={btn1}>＋ New Task</button>
          </div>

          {showTask&&(
            <div style={card()}>
              <form onSubmit={doCreateTask} style={{display:"flex",flexDirection:"column",gap:8}}>
                <input value={newTask.title} onChange={function(e){setNewTask(function(p){return{...p,title:e.target.value};});}} placeholder="Task title *" required style={inp} data-testid="task-title-input"/>
                <select value={newTask.priority} onChange={function(e){setNewTask(function(p){return{...p,priority:e.target.value};});}} style={{...inp,width:"auto"}}>
                  <option value="critical">🔴 Critical</option>
                  <option value="medium">🟡 Medium</option>
                  <option value="low">⚪ Low</option>
                </select>
                <div style={{display:"flex",gap:8}}>
                  <button type="submit" style={btn1}>Create Task</button>
                  <button type="button" onClick={function(){setShowTask(false);}} style={btn2}>Cancel</button>
                </div>
              </form>
            </div>
          )}

          {/* Task filter */}
          <div style={{display:"flex",gap:6,marginBottom:12,flexWrap:"wrap"}}>
            {["open","completed","dismissed"].map(function(f){return(
              <button key={f} onClick={function(){setTaskFilter(f);}}
                style={{...btn2,background:taskFilter===f?"#6366f1":"var(--panel,#fff)",color:taskFilter===f?"#fff":"var(--text,#374151)",border:taskFilter===f?"1px solid #6366f1":"1px solid var(--border,#e5e7eb)",fontWeight:600,textTransform:"capitalize"}}>
                {f}
                {f==="open"&&taskViewData.filter(function(t){return t.status==="open";}).length>0&&(
                  <span style={{marginLeft:5,background:"#ef4444",color:"#fff",borderRadius:99,fontSize:".6rem",padding:"1px 5px",fontWeight:800}}>
                    {taskViewData.filter(function(t){return t.status==="open";}).length}
                  </span>
                )}
              </button>
            );})}
          </div>

          {taskViewData.length===0&&(
            <div style={{...card(),textAlign:"center",padding:24,color:"#94a3b8"}}>
              <div style={{fontSize:"2rem",marginBottom:8}}>✅</div>
              <div style={{fontWeight:600}}>No {taskFilter} tasks.</div>
              {taskFilter==="open"&&<div style={{fontSize:".82rem",marginTop:4}}>Create a task above to get started.</div>}
            </div>
          )}

          {taskViewData.map(function(t){return(
            <TRow key={t.id} task={t} onComplete={doComplete} onDismiss={doDismiss}/>
          );})}
        </div>
      )}

    </div>
  );
}
