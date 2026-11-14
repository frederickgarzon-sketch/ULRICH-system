"use strict";
const id=x=>document.getElementById(x),sid=document.body.dataset.sessionId;
const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const label=v=>String(v??"Not recorded").replaceAll("_"," ");
const number=(v,suffix="")=>v==null||v===""||!Number.isFinite(Number(v))?"Not available":Number(v).toLocaleString(undefined,{maximumFractionDigits:1})+suffix;
const metric=(name,value)=>`<div><b>${esc(value)}</b><span>${esc(name)}</span></div>`;
const detail=(name,value)=>`<div><span>${esc(name)}</span><strong>${esc(value)}</strong></div>`;
// SQLite returns naive UTC timestamps; do not reinterpret them as local time.
const localDate=value=>value?new Date(/([zZ]|[+-]\d{2}:\d{2})$/.test(value)?value:value+"Z").toLocaleString():"Not available";
const printClosedDetails=[];
window.addEventListener("beforeprint",()=>{document.querySelectorAll("details:not([open])").forEach(node=>{printClosedDetails.push(node);node.open=true})});
window.addEventListener("afterprint",()=>{printClosedDetails.splice(0).forEach(node=>node.open=false)});
function plot(trials){
 const canvas=id("reaction-chart"),ctx=canvas.getContext("2d"),w=canvas.width,h=canvas.height;
 const points=trials.map((t,i)=>({x:i,y:t.is_target&&t.responded&&t.reaction_time_ms!=null?Number(t.reaction_time_ms):null}));
 const valid=points.filter(p=>p.y!=null&&Number.isFinite(p.y));ctx.clearRect(0,0,w,h);
 if(!valid.length){ctx.fillStyle="#506879";ctx.font="18px Segoe UI";ctx.fillText("No saved response times",50,100);return}
 const maximum=Math.ceil(Math.max(...valid.map(p=>p.y),100)/100)*100;
 const left=65,right=w-25,top=20,bottom=h-40;ctx.font="14px Segoe UI";
 for(let i=0;i<=4;i++){const y=bottom-(bottom-top)*i/4;ctx.strokeStyle="#dce8e9";ctx.beginPath();ctx.moveTo(left,y);ctx.lineTo(right,y);ctx.stroke();ctx.fillStyle="#506879";ctx.fillText(Math.round(maximum*i/4)+"",5,y+4)}
 ctx.strokeStyle="#159b9c";ctx.lineWidth=3;ctx.beginPath();let connected=false;
 points.forEach(p=>{if(p.y==null||!Number.isFinite(p.y)){connected=false;return}const x=left+p.x*(right-left)/Math.max(points.length-1,1),y=bottom-p.y/maximum*(bottom-top);if(connected)ctx.lineTo(x,y);else ctx.moveTo(x,y);connected=true});ctx.stroke();
 valid.forEach(p=>{const x=left+p.x*(right-left)/Math.max(points.length-1,1),y=bottom-p.y/maximum*(bottom-top);ctx.fillStyle="#159b9c";ctx.beginPath();ctx.arc(x,y,4,0,Math.PI*2);ctx.fill()});
 ctx.fillStyle="#506879";ctx.fillText("Presentation 1",left,h-10);ctx.fillText("Presentation "+trials.length,right-110,h-10);
}
fetch(`/api/reports/${sid}`,{cache:"no-store"}).then(r=>{if(!r.ok)throw Error("Records unavailable or access denied");return r.json()}).then(d=>{
 const s=d.session,p=d.participant||{},a=d.attention,q=d.data_quality||{},vp=q.valid_pct||{};
 const run=(d.attention_configuration||[]).filter(x=>x.task_key==="pop_balloon").at(-1),config=run?.configuration||{};
 id("loading").hidden=true;id("report").hidden=false;id("synthetic-banner").hidden=!["mock","synthetic"].includes(s.mode);
 id("session-summary").innerHTML=[["Participant",p.code||s.participant_code],["Name",p.full_name||"Not recorded"],["Session","#"+s.id],["Date",localDate(s.start_time)],["Duration",number(s.duration_seconds," s")],["Status",label(s.status)]].map(x=>detail(...x)).join("");
 id("task-status").textContent=label(a.termination_reason||run?.status||"No recorded activity");
 id("game-config").textContent=run?`Mode: ${label(config.game_mode)} · Target: ${config.game_mode==="target_color"?label(config.target_color_label||config.target_color):"Any color"} · Goal: ${a.required_pops} correct pops · Level: ${label(run.difficulty)}`:"No Pop the Balloon run attached. Historical activity records are shown below.";
 const trials=a.trials||[],complete=trials.filter(t=>t.correct||t.missed||t.false_response||t.responded);
 const waiting=complete.filter(t=>!t.is_target&&!t.responded&&t.correct).length;
 id("task-counts").innerHTML=[["Correct pops",number(a.correct_pops)],["Incorrect pops",number(a.incorrect_pops)],["Missed targets",number(a.missed)],["Correct waiting",number(waiting)],["Completed attempts",number(a.total_attempts)],["Accuracy",a.total_attempts?number(a.accuracy,"%"):"Not available"]].map(x=>metric(...x)).join("");
 id("timing-metrics").innerHTML=[["Average",number(a.average_reaction_time_ms," ms")],["Median",number(a.median_reaction_time_ms," ms")],["Standard deviation",number(a.reaction_time_sd_ms," ms")],["Fastest",number(a.fastest_reaction_time_ms," ms")],["Slowest",number(a.slowest_reaction_time_ms," ms")],["Goal completion",number(a.completion_seconds," s")]].map(x=>metric(...x)).join("");
 plot(trials);id("chart-note").textContent="Target response time (ms) by presentation across recorded runs. Distractors, nonresponses and unfinished trials remain gaps; they are not plotted as zero. Goal/completion refer to the latest game; attempt counts cover the session.";
 const eyesAvailable=vp.blink!=null&&vp.blink>0;
 id("blink-metrics").innerHTML=[["Saved blink events",number(d.blink.total)],["Session event rate",eyesAvailable?number(d.blink.average_rate," /min"):"Not available"],["Valid eye samples",number(vp.blink,"%")]].map(x=>metric(...x)).join("");
 id("movement-metrics").innerHTML=[["Head events",q.head_sample_count&&vp.head>0?number(d.head.movement_count):"Not available"],["Body events",q.body_sample_count&&vp.body>0?number(d.body.movement_events):"Not available"],["Posture changes",q.body_sample_count&&vp.body>0?number(d.body.posture_changes):"Not available"]].map(x=>metric(...x)).join("");
 const phases=(d.phases||[]).slice().sort((x,y)=>x.time-y.time),duration=s.duration_seconds;
 id("phase-timeline").innerHTML=phases.map((v,i)=>{const end=phases[i+1]?.time??duration,seconds=end==null?null:Math.max(0,end-v.time);return `<div style="flex:${Math.max(seconds||0,1)}" title="${esc(number(v.time," s"))}"><strong>${esc(label(v.phase))}</strong><span>${esc(number(seconds," s"))}</span></div>`}).join("");
 id("phase-records").textContent=phases.length?phases.map(x=>label(x.phase)+" at "+number(x.time," s")).join(" → "):"No phase markers recorded.";
 id("validity-metrics").innerHTML=[["Eye coverage",number(vp.blink,"%")],["Head coverage",number(vp.head,"%")],["Body coverage",number(vp.body,"%")],["Task tracking",number(a.valid_tracking_attempt_pct,"%")],["Head samples",number(q.head_sample_count)],["Body samples",number(q.body_sample_count)]].map(x=>metric(...x)).join("");
 id("coverage-status").textContent=(q.warnings||[]).length?"Review coverage":"Stored-data checks complete";
 id("quality-warning").innerHTML=(q.warnings||[]).map(w=>`<p>${esc(w)}</p>`).join("");
 id("trial-rows").innerHTML=trials.map(t=>{const outcome=t.missed?"Missed target":t.false_response?"Incorrect pop":t.correct?(t.responded?"Correct pop":"Correct waiting"):"Unfinished";return `<tr><td>${esc(t.trial)}</td><td>${esc(label(t.balloon?.color_label||t.balloon?.color||t.stimulus))}</td><td>${t.is_target?"Yes":"No"}</td><td>${t.responded?"Tapped":"No tap"}</td><td>${esc(outcome)}</td><td>${esc(t.responded?number(t.reaction_time_ms):"—")}</td><td>${esc(label(t.phase))}</td></tr>`}).join("");
 const shapeSection=document.createElement('section');shapeSection.className='report-section';
 const shapeTitle=document.createElement('h2');shapeTitle.textContent='Shape Matching · Separate behavioral records';shapeSection.append(shapeTitle);
 for(const run of d.shape_matching||[]){const p=document.createElement('p'),m=run.summary;p.textContent=`Run #${run.id} · ${run.status} · ${m.saved_trials}/${m.planned_trials} attempts saved · ${m.matched} matched · ${m.wrong_drops} wrong choices · First-attempt accuracy: ${m.first_attempt_accuracy_pct??'Not available'}${m.first_attempt_accuracy_pct==null?'':'%'} · Active time: ${m.active_ms} ms (browser reported)`;shapeSection.append(p);const details=document.createElement('details'),title=document.createElement('summary'),pre=document.createElement('pre');title.textContent='Saved Shape Matching attempts';pre.textContent=JSON.stringify(run.rows,null,2);details.append(title,pre);shapeSection.append(details)}
 if(!(d.shape_matching||[]).length){const p=document.createElement('p');p.textContent='No Shape Matching run recorded.';shapeSection.append(p)}
 id('notes').parentElement.before(shapeSection);
 id("notes").textContent=s.notes||"No session notes recorded.";
}).catch(error=>{id("loading").textContent=error.message;id("loading").hidden=false;id("report").hidden=true});
