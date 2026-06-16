import { useState } from "react";
import { submitLeadClaim } from "../api/sales";

const GRADES = ["Grade 5","Grade 6","Grade 7","Grade 8","Grade 9","Grade 10"];
const PKGS = [
  { key:"starter", label:"Starter" },
  { key:"family_premium", label:"Family Premium" },
  { key:"free", label:"Free / Trial" },
];
const iS = {
  width:"100%",background:"var(--panel)",border:"1px solid var(--border)",
  borderRadius:10,padding:"11px 14px",color:"var(--text)",
  fontFamily:"inherit",fontSize:"0.93rem",boxSizing:"border-box",
};

export default function SalesLeadForm({ onSuccess }) {
  const [form,setForm]=useState({student_name:"",student_email:"",student_phone:"",grade:"Grade 9",package_key:"starter"});
  const [sub,setSub]=useState(false);
  const [err,setErr]=useState("");
  const [ok,setOk]=useState("");

  async function onSubmit(e){
    e.preventDefault();setErr("");setOk("");
    if(!form.student_name.trim()){setErr("Student name is required.");return;}
    if(!form.student_email.includes("@")){setErr("Valid email is required.");return;}
    setSub(true);
    try{
      const r=await submitLeadClaim(form);
      setOk(r.message||"Lead submitted! You will see it turn green when they pay.");
      setForm({student_name:"",student_email:"",student_phone:"",grade:"Grade 9",package_key:"starter"});
      if(onSuccess)onSuccess();
    }catch(e){setErr(e.message||"Could not submit. Try again.");}
    finally{setSub(false);}
  }

  return (
    <div className="card" style={{padding:"20px 18px",position:"sticky",top:20}}>
      <h3 style={{fontSize:"1.05rem",fontWeight:800,marginBottom:16,color:"var(--text)"}}>➕ Submit New Lead</h3>
      <p style={{fontSize:".8rem",color:"var(--muted)",marginBottom:16}}>
        Enter the student's details. When they sign up and pay, your commission is auto-confirmed.
      </p>
      <form onSubmit={onSubmit} style={{display:"flex",flexDirection:"column",gap:12}}>
        <label style={{display:"flex",flexDirection:"column",gap:5,fontSize:".87rem",color:"var(--text)"}}>
          Student Name *
          <input style={iS} value={form.student_name} onChange={e=>setForm(p=>({...p,student_name:e.target.value}))} required placeholder="Full name" />
        </label>
        <label style={{display:"flex",flexDirection:"column",gap:5,fontSize:".87rem",color:"var(--text)"}}>
          Student Email *
          <input style={iS} type="email" value={form.student_email} onChange={e=>setForm(p=>({...p,student_email:e.target.value}))} required placeholder="student@email.com" />
        </label>
        <label style={{display:"flex",flexDirection:"column",gap:5,fontSize:".87rem",color:"var(--text)"}}>
          Phone (optional)
          <input style={iS} value={form.student_phone} onChange={e=>setForm(p=>({...p,student_phone:e.target.value}))} placeholder="Mobile number" />
        </label>
        <label style={{display:"flex",flexDirection:"column",gap:5,fontSize:".87rem",color:"var(--text)"}}>
          Grade
          <select style={iS} value={form.grade} onChange={e=>setForm(p=>({...p,grade:e.target.value}))}>
            {GRADES.map(g=><option key={g}>{g}</option>)}
          </select>
        </label>
        <label style={{display:"flex",flexDirection:"column",gap:5,fontSize:".87rem",color:"var(--text)"}}>
          Package Discussed
          <select style={iS} value={form.package_key} onChange={e=>setForm(p=>({...p,package_key:e.target.value}))}>
            {PKGS.map(p=><option key={p.key} value={p.key}>{p.label}</option>)}
          </select>
        </label>
        {err && <div style={{background:"rgba(220,38,38,.08)",border:"1px solid rgba(220,38,38,.25)",borderRadius:8,padding:"9px 12px",fontSize:".82rem",color:"#dc2626"}}>{err}</div>}
        {ok  && <div style={{background:"rgba(4,120,87,.08)", border:"1px solid rgba(4,120,87,.25)", borderRadius:8,padding:"9px 12px",fontSize:".82rem",color:"#047857"}}>{ok}</div>}
        <button type="submit" disabled={sub}
          style={{background:"linear-gradient(135deg,#2563eb,#7c3aed)",color:"#fff",border:"none",borderRadius:10,padding:"12px",fontSize:".95rem",fontWeight:700,cursor:sub?"not-allowed":"pointer",fontFamily:"inherit",opacity:sub?0.7:1}}>
          {sub ? "Submitting…" : "Submit Lead Claim"}
        </button>
        <p style={{fontSize:".72rem",color:"var(--muted)",textAlign:"center",margin:0}}>
          First claim wins · Max 15 leads/day · Commission auto-confirmed on payment
        </p>
      </form>
    </div>
  );
}
