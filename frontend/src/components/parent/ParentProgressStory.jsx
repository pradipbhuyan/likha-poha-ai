/**
 * ParentProgressStory.jsx
 * Visual progress story for a child — uses analytics data.
 * No fake data. Shows "No data yet" explanation for new children.
 */

function ScoreBadge({score}){
  if(score==null) return <span style={{color:"#94a3b8"}}>—</span>;
  var col=score>=70?"#22c55e":score>=50?"#f59e0b":"#ef4444";
  return <span style={{fontWeight:700,color:col}}>{score}%</span>;
}

function SubjectProgressCard({subject,data}){
  var total=data.total||0;
  var completed=data.completed||0;
  var inProg=data.in_progress||0;
  var pct=total>0?Math.round((completed/total)*100):0;
  return(
    <div style={{background:"var(--surface2,#f8fafc)",border:"1px solid var(--border,#e5e7eb)",borderRadius:8,padding:"8px 12px"}}>
      <div style={{display:"flex",justifyContent:"space-between",marginBottom:4}}>
        <span style={{fontWeight:600,fontSize:".78rem"}}>{subject}</span>
        <span style={{fontSize:".72rem",color:"#64748b"}}>{completed}/{total}</span>
      </div>
      <div style={{height:5,background:"var(--border,#e5e7eb)",borderRadius:3,overflow:"hidden",marginBottom:3}}>
        <div style={{height:"100%",width:pct+"%",background:"#6366f1",borderRadius:3,transition:"width .4s"}}/>
      </div>
      <div style={{fontSize:".65rem",color:"#94a3b8"}}>{inProg>0?inProg+" in progress":completed===total&&total>0?"All done":"Not started"}</div>
    </div>
  );
}

function TrendBar({trend}){
  if(!trend||!trend.length) return null;
  return(
    <div>
      <div style={{fontWeight:600,fontSize:".78rem",marginBottom:6,color:"#64748b"}}>Score Trend</div>
      <div style={{display:"flex",gap:3,alignItems:"flex-end",height:44}}>
        {trend.map(function(t,i){
          var sc=t.score!=null?t.score:0;
          var h=Math.max(4,Math.round(sc/100*44));
          var col=sc>=60?"#22c55e":sc>=40?"#f59e0b":"#ef4444";
          return <div key={i} title={t.subject+": "+sc+"%"} style={{flex:1,height:h,background:col,borderRadius:2,minWidth:6,maxWidth:20}}/>;
        })}
      </div>
      <div style={{display:"flex",justifyContent:"space-between",fontSize:".6rem",color:"#94a3b8",marginTop:2}}>
        <span>Oldest</span><span>Most Recent</span>
      </div>
    </div>
  );
}

export default function ParentProgressStory({analytics}){
  if(!analytics){
    return(
      <div style={{color:"#94a3b8",fontSize:".82rem",padding:"8px 0",textAlign:"center"}}>
        <div style={{fontSize:"1.5rem",marginBottom:4}}>📊</div>
        Progress will appear here after your child completes lessons or mock tests.
      </div>
    );
  }

  var progress=analytics.progress||{};
  var mockTests=analytics.mock_tests||{};
  var strengths=analytics.strengths||{};
  var weaknesses=analytics.weaknesses||{};
  var activity=analytics.activity||{};
  var subjWise=progress.subject_wise||{};

  return(
    <div data-testid="parent-progress-story">
      {/* Progress summary */}
      {progress.available?(
        <div style={{marginBottom:14}}>
          <div style={{fontWeight:700,fontSize:".85rem",marginBottom:8}}>Learning Progress</div>
          <div style={{display:"flex",gap:8,flexWrap:"wrap",marginBottom:8}}>
            {[
              {label:"Completed",value:progress.completed_chapters?.value??0,color:"#22c55e"},
              {label:"In Progress",value:progress.in_progress_chapters?.value??0,color:"#6366f1"},
              {label:"Not Started",value:progress.not_started?.value??0,color:"#94a3b8"},
            ].map(function(s){return(
              <div key={s.label} style={{background:"var(--surface2,#f8fafc)",border:"1px solid var(--border,#e5e7eb)",borderRadius:8,padding:"7px 12px",textAlign:"center",flex:"1 1 70px",minWidth:70}}>
                <div style={{fontWeight:800,fontSize:"1.1rem",color:s.color}}>{s.value}</div>
                <div style={{fontSize:".63rem",color:"#64748b"}}>{s.label}</div>
              </div>
            );})}
          </div>
          {Object.keys(subjWise).length>0&&(
            <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(140px,1fr))",gap:6}}>
              {Object.entries(subjWise).slice(0,6).map(function([subj,data]){return(
                <SubjectProgressCard key={subj} subject={subj} data={data}/>
              );})}
            </div>
          )}
        </div>
      ):(
        <div style={{color:"#64748b",fontSize:".78rem",marginBottom:10}}>
          {progress.status==="no_activity"?"No lessons completed yet. Encourage your child to start their first lesson!":"Progress data not available yet."}
        </div>
      )}

      {/* Mock test summary */}
      {mockTests.available?(
        <div style={{marginBottom:14}}>
          <div style={{fontWeight:700,fontSize:".85rem",marginBottom:8}}>Mock Test Performance</div>
          <div style={{display:"flex",gap:8,flexWrap:"wrap",marginBottom:8}}>
            <div style={{background:"var(--surface2,#f8fafc)",border:"1px solid var(--border,#e5e7eb)",borderRadius:8,padding:"7px 14px",textAlign:"center"}}>
              <div style={{fontWeight:800,fontSize:"1.1rem",color:"#0ea5e9"}}>{mockTests.total_tests?.value||0}</div>
              <div style={{fontSize:".63rem",color:"#64748b"}}>Tests Taken</div>
            </div>
            <div style={{background:"var(--surface2,#f8fafc)",border:"1px solid var(--border,#e5e7eb)",borderRadius:8,padding:"7px 14px",textAlign:"center"}}>
              <div style={{fontWeight:800,fontSize:"1.1rem"}}>
                <ScoreBadge score={parseFloat(mockTests.average_score?.value)||null}/>
              </div>
              <div style={{fontSize:".63rem",color:"#64748b"}}>Avg Score</div>
            </div>
          </div>
          <TrendBar trend={mockTests.trend}/>
        </div>
      ):(
        <div style={{color:"#64748b",fontSize:".78rem",marginBottom:10}}>
          {mockTests.status==="no_activity"?"No mock tests attempted yet.":"Mock test data not available."}
        </div>
      )}

      {/* Strengths */}
      {strengths.available&&strengths.strong_subjects?.length>0&&(
        <div style={{marginBottom:10}}>
          <div style={{fontWeight:700,fontSize:".82rem",color:"#22c55e",marginBottom:5}}>Strong Subjects</div>
          <div style={{display:"flex",flexWrap:"wrap",gap:5}}>
            {strengths.strong_subjects.map(function(s,i){return(
              <span key={i} style={{background:"rgba(34,197,94,.1)",color:"#166534",fontSize:".73rem",fontWeight:600,padding:"2px 8px",borderRadius:5}}>{s}</span>
            );})}
          </div>
        </div>
      )}

      {/* Weaknesses */}
      {weaknesses.available&&(weaknesses.weak_subjects?.length>0||weaknesses.weak_topics?.length>0)&&(
        <div style={{marginBottom:10}}>
          <div style={{fontWeight:700,fontSize:".82rem",color:"#ef4444",marginBottom:5}}>Needs Practice</div>
          {weaknesses.weak_topics?.slice(0,3).map(function(t,i){return(
            <div key={i} style={{fontSize:".75rem",padding:"3px 0",borderBottom:"1px solid var(--border,#f1f5f9)",display:"flex",justifyContent:"space-between"}}>
              <span>{t.subject} — {t.chapter}</span>
              {t.score!=null&&<span style={{color:"#ef4444",fontWeight:600}}>{t.score}%</span>}
            </div>
          );})}
        </div>
      )}

      {/* Activity */}
      {activity.available&&(
        <div>
          <div style={{fontWeight:700,fontSize:".82rem",marginBottom:5}}>Recent Activity</div>
          <div style={{display:"flex",gap:8,flexWrap:"wrap"}}>
            <div style={{background:"var(--surface2,#f8fafc)",border:"1px solid var(--border,#e5e7eb)",borderRadius:8,padding:"5px 10px",textAlign:"center"}}>
              <div style={{fontWeight:700,fontSize:".88rem",color:"#6366f1"}}>{activity.lessons_this_month?.value||0}</div>
              <div style={{fontSize:".63rem",color:"#64748b"}}>Lessons</div>
            </div>
            <div style={{background:"var(--surface2,#f8fafc)",border:"1px solid var(--border,#e5e7eb)",borderRadius:8,padding:"5px 10px",textAlign:"center"}}>
              <div style={{fontWeight:700,fontSize:".88rem",color:"#0ea5e9"}}>{activity.doubts_this_month?.value||0}</div>
              <div style={{fontSize:".63rem",color:"#64748b"}}>Doubts</div>
            </div>
            <div style={{background:"var(--surface2,#f8fafc)",border:"1px solid var(--border,#e5e7eb)",borderRadius:8,padding:"5px 10px",textAlign:"center"}}>
              <div style={{fontWeight:700,fontSize:".88rem",color:"#22c55e"}}>{activity.active_days?.value||0}</div>
              <div style={{fontSize:".63rem",color:"#64748b"}}>Active Days</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
