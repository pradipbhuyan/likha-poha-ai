import pathlib, textwrap

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0f172a;color:#e2e8f0;font-family:-apple-system,sans-serif;font-size:13px;padding:20px}
.page{max-width:1080px;margin:0 auto}
.ob{background:rgba(99,102,241,.07);border:1px solid rgba(99,102,241,.28);border-radius:12px;padding:14px 18px;margin:24px 0 14px;display:flex;gap:12px}
.ob h2{font-size:1rem;font-weight:800;color:#a5b4fc}
.ob p{font-size:.73rem;color:#64748b;margin-top:4px;line-height:1.5}
.ob ul{font-size:.71rem;color:#94a3b8;margin-top:5px;padding-left:16px;line-height:1.85}
.card{background:#1e293b;border:1px solid #334155;border-radius:12px;overflow:hidden;margin-bottom:10px}
.lbl{font-size:.59rem;color:#64748b;font-weight:700;text-transform:uppercase;letter-spacing:.04em;display:block;margin-bottom:3px}
.fg{margin-bottom:9px}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.g3{display:grid;grid-template-columns:1fr 1fr 1fr;border-top:1px solid #334155}
.gc{padding:16px 18px;border-right:1px solid #334155}
.gc:last-child{border-right:none}
.chd{font-size:.59rem;font-weight:800;text-transform:uppercase;letter-spacing:.07em;color:#6366f1;margin-bottom:12px;padding-bottom:7px;border-bottom:1px solid rgba(99,102,241,.15)}
.badge{display:inline-flex;background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.25);color:#4ade80;padding:2px 9px;border-radius:20px;font-size:.58rem;font-weight:700;margin-top:6px}
.chip{display:inline-flex;padding:2px 7px;border-radius:20px;font-size:.57rem;font-weight:700;margin-right:4px}
.cg{background:rgba(34,197,94,.12);color:#4ade80;border:1px solid rgba(34,197,94,.2)}
.ca{background:rgba(245,158,11,.1);color:#fbbf24;border:1px solid rgba(245,158,11,.2)}
.cp{background:rgba(99,102,241,.12);color:#a5b4fc;border:1px solid rgba(99,102,241,.2)}
.calc{background:rgba(99,102,241,.08);border:1px solid rgba(99,102,241,.18);border-radius:7px;padding:8px 11px;margin-bottom:10px}
.cr{display:flex;justify-content:space-between;font-size:.63rem;margin-bottom:2px;color:#64748b}
.crt{display:flex;justify-content:space-between;font-size:.7rem;font-weight:800;color:#a5b4fc}
.fi{background:#0f172a;border:1px solid #334155;border-radius:6px;padding:6px 9px;color:#e2e8f0;font-size:.77rem;font-family:inherit;width:100%}
.ta{background:#0f172a;border:1px solid #334155;border-radius:6px;padding:6px 9px;color:#e2e8f0;font-size:.75rem;font-family:inherit;resize:vertical;width:100%;height:70px}
.tog{display:flex;align-items:center;justify-content:space-between;padding:7px 9px;background:#0f172a;border:1px solid #334155;border-radius:7px;margin-bottom:6px}
.tog .tl{font-size:.74rem;font-weight:600}
.tog .td{font-size:.57rem;color:#64748b;margin-top:1px}
.swoff{width:30px;height:17px;background:#334155;border-radius:17px;position:relative;cursor:pointer;flex-shrink:0;margin-left:10px;display:inline-block}
.swoff::after{content:"";position:absolute;left:3px;top:2.5px;width:12px;height:12px;background:#64748b;border-radius:50%}
.swon{width:30px;height:17px;background:#6366f1;border-radius:17px;position:relative;cursor:pointer;flex-shrink:0;margin-left:10px;display:inline-block}
.swon::after{content:"";position:absolute;left:15px;top:2.5px;width:12px;height:12px;background:#fff;border-radius:50%}
.save-bar{background:rgba(99,102,241,.05);border-top:1px solid #334155;padding:11px 18px;display:flex;justify-content:space-between;align-items:center}
.btn-p{padding:9px 22px;background:linear-gradient(135deg,#6366f1,#8b5cf6);border:none;border-radius:8px;color:#fff;font-weight:700;font-size:.82rem;cursor:pointer}
.btn-s{padding:5px 12px;border-radius:6px;font-size:.7rem;font-weight:700;cursor:pointer;border:1px solid rgba(99,102,241,.3);background:rgba(99,102,241,.1);color:#a5b4fc}
.tabs{display:flex;gap:3px;background:#1e293b;border:1px solid #334155;border-radius:10px;padding:4px;margin-bottom:12px;overflow-x:auto}
.tab{padding:7px 13px;border-radius:7px;font-size:.73rem;font-weight:600;color:#64748b;white-space:nowrap;border:none;background:none;cursor:pointer;display:flex;flex-direction:column;align-items:flex-start}
.tabon{padding:7px 13px;border-radius:7px;font-size:.73rem;font-weight:600;color:#e2e8f0;white-space:nowrap;border:none;background:#334155;cursor:pointer;display:flex;flex-direction:column;align-items:flex-start}
.tp{font-size:.57rem;color:#475569;margin-top:1px}
.dot{width:6px;height:6px;border-radius:50%;background:#22c55e;display:inline-block;margin-right:4px}
.tbl{width:100%;border-collapse:collapse}
.tbl th,.tbl td{padding:10px 14px;border-bottom:1px solid #334155;font-size:.77rem;text-align:left}
.tbl th{font-size:.58rem;color:#64748b;font-weight:700;text-transform:uppercase;letter-spacing:.05em;background:#0f172a}
.tbl tr:last-child td{border-bottom:none}
.tbl tr:hover td{background:rgba(99,102,241,.04)}
.tag{font-size:.57rem;padding:2px 7px;border-radius:10px;font-weight:700}
.tg{background:rgba(34,197,94,.1);color:#4ade80}
.tr{background:rgba(239,68,68,.1);color:#f87171}
.edb{padding:4px 10px;background:rgba(99,102,241,.1);border:1px solid rgba(99,102,241,.25);border-radius:6px;color:#a5b4fc;font-size:.67rem;font-weight:700;cursor:pointer}
.sp{background:#1e293b;border:2px solid #6366f1;border-radius:12px;overflow:hidden;margin-top:10px}
.sp-h{background:rgba(99,102,241,.1);border-bottom:1px solid #334155;padding:12px 16px;display:flex;justify-content:space-between;align-items:center}
.sp-b{padding:16px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px}
.sp-hd{font-size:.58rem;font-weight:800;text-transform:uppercase;letter-spacing:.07em;color:#6366f1;margin-bottom:10px;padding-bottom:7px;border-bottom:1px solid rgba(99,102,241,.15)}
hr{border:none;border-top:2px solid #334155;margin:36px 0}
"""

INP = '<input class="fi" type="text" value="{v}" />'
INPN = '<input class="fi" type="number" value="{v}" />'
INPE = '<input class="fi" type="text" placeholder="{v}" />'
TA4 = '<textarea class="ta" style="height:80px">{v}</textarea>'
TA2 = '<textarea class="ta" style="height:50px">{v}</textarea>'
SWON = '<div class="swon"></div>'
SWOFF = '<div class="swoff"></div>'

def tog(label, desc, on=True):
    sw = SWON if on else SWOFF
    return f'<div class="tog"><div><div class="tl">{label}</div><div class="td">{desc}</div></div>{sw}</div>'

BODY = f"""
<div class="page">
<h1 style="font-size:1.4rem;font-weight:900">Design Options: Subscription Settings Page</h1>
<p style="color:#64748b;font-size:.8rem;margin-top:4px">Two layouts to choose from. Both show the same data, just arranged differently.</p>

<!-- ========= OPTION A ========= -->
<div class="ob">
  <div>
    <h2>Option A &mdash; Tabbed Plan Editor (One Plan at a Time)</h2>
    <p>Tab bar at top to switch between plans. Each plan uses a compact 3-column panel. Contact row compressed to one line. No vertical scrolling for normal edits.</p>
    <ul>
      <li>Clean: only one plan visible, zero vertical scroll for core fields</li>
      <li>3 columns: Pricing & Validity | Display & Limits | Feature Flags</li>
      <li>Live Razorpay charge calculator (price minus discount)</li>
      <li>Toggle switches instead of checkboxes</li>
      <li>Tradeoff: cannot see two plans at the same time</li>
    </ul>
  </div>
</div>

<div style="margin-bottom:14px">
  <div style="font-size:1.2rem;font-weight:800">Subscription Settings</div>
  <div style="color:#64748b;font-size:.78rem;margin-top:2px">Manage pricing, validity, features and content for all tiers.</div>
  <span class="badge">Source: database</span>
</div>

<div class="card" style="margin-bottom:12px">
  <div style="padding:10px 15px;display:flex;gap:10px;align-items:center;flex-wrap:wrap">
    <span style="font-size:.65rem;font-weight:700;color:#64748b;text-transform:uppercase;white-space:nowrap">Support Contact</span>
    <input class="fi" style="flex:1;min-width:170px" value="likhapohaai@gmail.com" />
    <input class="fi" style="flex:1;min-width:130px" placeholder="WhatsApp" />
    <input class="fi" style="flex:1;min-width:120px" placeholder="Phone" />
    <button class="btn-s">Save</button>
  </div>
</div>

<div class="tabs">
  <button class="tabon"><span><span class="dot"></span>Nano</span><span class="tp">&#8377;99 &middot; 8 days</span></button>
  <button class="tab"><span>Premium</span><span class="tp">&#8377;299 &middot; 30d</span></button>
  <button class="tab"><span>Family Premium</span><span class="tp">&#8377;499 &middot; 30d</span></button>
  <button class="tab"><span>6-Month</span><span class="tp">&#8377;1,495</span></button>
  <button class="tab"><span>Annual</span><span class="tp">&#8377;2,999</span></button>
  <button class="tab"><span>Family Annual</span><span class="tp">&#8377;4,999</span></button>
</div>

<div class="card">
  <div style="background:rgba(99,102,241,.07);border-bottom:1px solid #334155;padding:12px 18px;display:flex;justify-content:space-between;align-items:flex-start">
    <div>
      <div style="font-size:.9rem;font-weight:800">Premium Nano <code style="background:#0f172a;padding:2px 6px;border-radius:4px;font-size:.67rem;color:#64748b">key: free</code></div>
      <div style="margin-top:5px">
        <span class="chip cg">Visible</span>
        <span class="chip ca">Exam Prep ON</span>
        <span class="chip cp">Exemplar ON</span>
      </div>
    </div>
    <div style="text-align:right">
      <div style="font-size:1.8rem;font-weight:900;color:#a5b4fc;line-height:1">&#8377;99</div>
      <div style="font-size:.57rem;color:#64748b;margin-top:2px">Razorpay charge</div>
    </div>
  </div>
  <div class="g3">
    <div class="gc">
      <div class="chd">Pricing & Validity</div>
      <div class="calc">
        <div class="cr"><span>Base price</span><span>&#8377;99</span></div>
        <div class="cr"><span>Discount</span><span>0%</span></div>
        <div class="crt"><span>Razorpay charge</span><span>&#8377;99</span></div>
      </div>
      <div class="g2 fg">
        <div class="fg"><span class="lbl">Price (&#8377;)</span>{INPN.format(v='99')}</div>
        <div class="fg"><span class="lbl">Discount %</span>{INPN.format(v='0')}</div>
      </div>
      <div class="fg"><span class="lbl">Discount Label</span>{INPE.format(v='e.g. Summer offer')}</div>
      <div class="g2 fg">
