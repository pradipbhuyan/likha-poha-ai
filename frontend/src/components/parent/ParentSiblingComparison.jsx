/**
 * ParentSiblingComparison.jsx
 * Side-by-side comparison for families with 2+ linked children.
 * Uses only data already present in the dashboard summary payload — no new fetch.
 */

var rowLabelStyle={fontSize:".73rem",color:"#64748b",fontWeight:600,padding:"8px 8px 8px 0",whiteSpace:"nowrap",verticalAlign:"middle"};
var cellStyle={padding:"8px 12px",borderTop:"1px solid var(--border,#f1f5f9)",verticalAlign:"middle"};

function lastActiveStr(child){
  var act=child.activity_summary||{};
  if(!act.last_active) return "Never";
  try{
    var d=new Date(act.last_active);
    var daysAgo=Math.floor((Date.now()-d.getTime())/(1000*60*60*24));
    return daysAgo===0?"Today":daysAgo===1?"Yesterday":daysAgo+" days ago";
  }catch(e){return "—";}
}

export default function ParentSiblingComparison({children, onOpenChild}){
  if(!children||children.length<2) return null;

  return(
    <div data-testid="parent-sibling-comparison" style={{background:"var(--panel,#fff)",border:"1px solid var(--border,#e5e7eb)",borderRadius:14,padding:"14px 16px"}}>
      <h2 style={{fontSize:".95rem",fontWeight:800,margin:"0 0 12px"}}>⚖️ Compare Your Children</h2>
      <div style={{overflowX:"auto"}}>
        <table style={{width:"100%",borderCollapse:"collapse",minWidth:360}}>
          <thead>
            <tr>
              <th style={{textAlign:"left",padding:"4px 8px 8px 0"}}></th>
              {children.map(function(c){return(
                <th key={c.id} style={{textAlign:"left",padding:"4px 12px 8px"}}>
                  <button data-testid={"sibling-open-"+c.id} onClick={function(){onOpenChild&&onOpenChild(c);}}
                    style={{background:"none",border:"none",cursor:"pointer",fontFamily:"inherit",padding:0,textAlign:"left"}}>
                    <div style={{fontWeight:800,fontSize:".85rem",color:"#1e293b"}}>{c.name}</div>
                    <div style={{fontSize:".68rem",color:"#64748b",fontWeight:500}}>{c.grade}</div>
                  </button>
                </th>
              );})}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td style={rowLabelStyle}>Access</td>
              {children.map(function(c){
                var plan=c.plan||{};
                return(
                  <td key={c.id} style={cellStyle}>
                    <span style={{fontSize:".72rem",fontWeight:700,color:plan.has_full_access?"#22c55e":"#ef4444"}}>
                      {plan.has_full_access?"✓ "+(plan.plan_name||"Full Access"):"⊘ "+(plan.plan_name||"Free Tier")}
                    </span>
                  </td>
                );
              })}
            </tr>
            <tr>
              <td style={rowLabelStyle}>Mock Tests</td>
              {children.map(function(c){return(
                <td key={c.id} style={cellStyle}>{(c.mock_test_summary||{}).count??0}</td>
              );})}
            </tr>
            <tr>
              <td style={rowLabelStyle}>Avg Score</td>
              {children.map(function(c){
                var score=(c.mock_test_summary||{}).average_score;
                var color=score>=60?"#22c55e":score>=40?"#f59e0b":"#ef4444";
                return(
                  <td key={c.id} style={cellStyle}>
                    <div style={{display:"flex",alignItems:"center",gap:6}}>
                      <span style={{fontWeight:700,fontSize:".78rem",color:score!=null?color:"#94a3b8",minWidth:32}}>{score!=null?score+"%":"—"}</span>
                      <div style={{flex:1,height:5,minWidth:40,background:"var(--border,#e5e7eb)",borderRadius:3,overflow:"hidden"}}>
                        <div style={{height:"100%",width:(score!=null?score:0)+"%",background:color,borderRadius:3}}/>
                      </div>
                    </div>
                  </td>
                );
              })}
            </tr>
            <tr>
              <td style={rowLabelStyle}>Last Active</td>
              {children.map(function(c){return(
                <td key={c.id} style={cellStyle}>{lastActiveStr(c)}</td>
              );})}
            </tr>
            <tr>
              <td style={rowLabelStyle}>Open Items</td>
              {children.map(function(c){
                var recs=c.recommendations||[];
                var top=recs[0];
                return(
                  <td key={c.id} style={cellStyle}>
                    {recs.length===0
                      ?<span style={{color:"#22c55e",fontSize:".73rem",fontWeight:600}}>All clear</span>
                      :<span style={{fontSize:".73rem",color:"#374151"}} title={top?top.title:""}>{recs.length} — {top?top.title:""}</span>
                    }
                  </td>
                );
              })}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
