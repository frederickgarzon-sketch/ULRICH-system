const byId=id=>document.getElementById(id), set=(id,value)=>{const el=byId(id);if(el)el.textContent=value;};
let activeSessionId=null, previousTaskTotal=0, cachedSessions=[], cachedParticipantCodes={},calibrationReady=false;
let calibrationGateRequest=0;

const chartPoints=[];
function installQualityIndicators(){const grid=byId("camera-grid");if(!grid)return;const legend=document.createElement("div");legend.className="quality-legend";legend.innerHTML='<span><i class="health-dot green"></i>Ready</span><span><i class="health-dot yellow"></i>Review</span><span><i class="health-dot red"></i>Do not record</span><small>Measured FPS, latency, AI response, and tracking.</small>';grid.before(legend);for(const name of ["face","body"]){const badge=byId(`${name}-status`);if(!badge)continue;badge.classList.add("health-badge","unknown");const reason=document.createElement("small");reason.id=`${name}-health-reason`;reason.className="health-reason";reason.textContent="Waiting for measurements";const container=document.createElement("div");container.style.cssText="display:grid;justify-items:end";badge.replaceWith(container);container.append(badge,reason)}}
function showHealth(name,health){const badge=byId(`${name}-status`);if(!badge)return;badge.classList.remove("unknown","green","yellow","red");badge.classList.add(health.level);badge.innerHTML=`<i class="health-dot ${health.level}"></i>${health.label}`;badge.title=health.issues?.join(" · ")||health.reason;set(`${name}-health-reason`,health.reason)}

function render(d){
  set("session-time",`${Number(d.session_time).toFixed(1)} s`);set("face-status",d.face_camera_status);set("body-status",d.body_camera_status);
  set("blink-rate",`${d.blink_rate} / min`);set("total-blinks",d.total_blinks);set("eye-state",d.eye_closed?"CLOSED":"OPEN");
  set("yaw",`${d.yaw}°`);set("pitch",`${d.pitch}°`);set("roll",`${d.roll}°`);set("head-movements",d.head_movements);
  set("body-movement",d.body_movement);set("movement-events",d.movement_events);set("posture-changes",d.posture_changes);
  set("task-correct",d.task_correct);set("task-incorrect",d.task_incorrect);set("task-missed",d.task_missed);set("task-accuracy",`${d.task_accuracy}%`);set("reaction-time",`${d.reaction_time_ms} ms`);
  const total=d.task_correct+d.task_incorrect+d.task_missed;
  if(byId("live-chart")){chartPoints.push({blink:d.blink_rate,head:Math.hypot(d.yaw,d.pitch,d.roll),body:d.body_movement*30,task:total>previousTaskTotal?25:0});while(chartPoints.length>120)chartPoints.shift();drawLiveChart();}
  previousTaskTotal=total;
}
function connect(){const protocol=location.protocol==="https:"?"wss":"ws",socket=new WebSocket(`${protocol}://${location.host}/ws/monitor`);socket.onopen=()=>set("connection","Live");socket.onmessage=e=>render(JSON.parse(e.data));socket.onclose=()=>{set("connection","Reconnecting…");setTimeout(connect,2000)};socket.onerror=()=>socket.close();}connect();

async function updateCameraStatus(){try{
  const [data,health]=await Promise.all([MonitorHelp.requestJSON("/api/cameras/status"),MonitorHelp.requestJSON("/api/performance/health")]);set("system-mode",data.mode==="real"?"LIVE":"TEST");set("overview-face",data.face.status);set("overview-body",data.body.status);set("ready-face",data.face.status);set("ready-body",data.body.status);set("ready-mode",data.mode==="real"?"LIVE":"TEST");
  for(const name of ["face","body"]){const c=data[name];set(`${name}-status`,c.status);set(`${name}-fps`,`${c.capture_fps} FPS`);set(`${name}-latency`,`${c.frame_latency_ms} ms`);set(`${name}-dropped`,`${c.dropped_frames} dropped`);}
  const face=await MonitorHelp.requestJSON("/api/face/status");set("average-ear",face.average_ear??"—");set("eye-state",face.eye_closed?"CLOSED":"OPEN");if(face.yaw!==null)set("yaw",`${face.yaw}°`);if(face.pitch!==null)set("pitch",`${face.pitch}°`);if(face.roll!==null)set("roll",`${face.roll}°`);set("head-movements",face.head_movements??0);set("head-direction",face.head_direction??"CENTER");set("head-magnitude",`${face.head_movement_magnitude??0}°`);
  const body=await MonitorHelp.requestJSON("/api/body/status");set("body-movement",body.movement_magnitude??0);set("movement-events",body.movement_events??0);set("posture-changes",body.posture_changes??0);set("person-count",body.person_count??0);set("posture-angle",body.posture_angle===null?"—":`${body.posture_angle}°`);set("body-device",body.device??"—");set("overview-device",body.device??"—");for(const [region,value] of Object.entries(body.regional_movement??{}))set(`region-${region}`,value);showHealth("face",health.face);showHealth("body",health.body);
}catch(_){}}
installQualityIndicators();updateCameraStatus();setInterval(updateCameraStatus,2000);

function ensureCalibrationGate(){const bar=document.querySelector('.control-bar');if(!bar||byId('calibration-gate'))return;bar.insertAdjacentHTML('afterend','<div id="calibration-gate" class="calibration-gate warning"><div><i id="calibration-gate-icon">!</i><span><strong id="calibration-gate-title">Calibration required</strong><small id="calibration-gate-message">Checking system calibration…</small></span></div><a id="calibration-gate-action" href="/calibration">Open calibration →</a></div>')}
async function updateRoomValidity(){const bar=document.querySelector('.control-bar');if(!bar)return;let card=byId('room-validity');if(!card){card=document.createElement('article');card.id='room-validity';card.className='panel';card.style.cssText='margin:16px 0;padding:18px';bar.before(card)}try{const response=await fetch('/api/calibration/status');if(!response.ok)throw new Error();const data=await response.json();card.replaceChildren();const title=document.createElement('strong');title.textContent=data.setup_changed?'Setup changed — recalibration required':data.system_ready?'Room setup: Ready':'Room setup: Calibration required';const detail=document.createElement('p');detail.textContent=data.system_calibrated_at?`Accepted ${new Date(data.system_calibrated_at).toLocaleString()}. Repeat after moving cameras or changing lighting, furniture, or settings.`:'Complete and accept the room setup before monitoring.';const action=document.createElement('a');action.href='/calibration';action.textContent=data.setup_changed?'Create replacement setup →':'Open guided calibration →';card.append(title,detail,action)}catch(e){card.textContent='Room setup status unavailable. Retry when the server reconnects.'}}
updateRoomValidity();setInterval(updateRoomValidity,15000);
async function updateCalibrationGate(){
  const select=byId('participant-select'),button=byId('session-button');
  if(!select||!button||activeSessionId!==null)return;
  const participant=select.value,requestId=++calibrationGateRequest;
  ensureCalibrationGate();
  try{
    const data=await MonitorHelp.requestJSON(`/api/calibration/status${participant?`?participant_id=${encodeURIComponent(participant)}`:''}`);
    if(requestId!==calibrationGateRequest||activeSessionId!==null||select.value!==participant)return;
    calibrationReady=Boolean(data.ready);
    const gate=byId('calibration-gate');gate.classList.toggle('ready',calibrationReady);gate.classList.toggle('warning',!calibrationReady);gate.classList.remove('session-active');
    set('calibration-gate-icon',calibrationReady?'✓':'!');set('calibration-gate-title',calibrationReady?'Ready to record':'Next step required');set('calibration-gate-message',data.message);
    const action=byId('calibration-gate-action');action.hidden=calibrationReady;action.textContent='Open System Setup →';action.href='/system-setup';
    button.disabled=!participant||!calibrationReady;button.title=calibrationReady?'Start a monitored session':data.message;
  }catch(error){
    if(requestId!==calibrationGateRequest||activeSessionId!==null||select.value!==participant)return;
    calibrationReady=false;button.disabled=true;
    set('calibration-gate-title','Readiness unavailable');set('calibration-gate-message',error.message);
  }
}
function updateParticipantDeleteButton(value){const button=byId('delete-participant');if(button)button.disabled=!value||activeSessionId!==null;}
async function loadParticipants(){const select=byId("participant-select");if(!select)return;const participants=await MonitorHelp.requestJSON("/api/participants"),selected=select.value||localStorage.getItem('monitor-participant')||'';select.innerHTML='<option value="">Select participant</option>';for(const p of participants){const option=document.createElement("option");option.value=p.id;option.textContent=p.display_name?`${p.participant_code} — ${p.display_name}`:p.participant_code;select.appendChild(option);}select.value=[...select.options].some(o=>o.value===String(selected))?String(selected):'';updateParticipantDeleteButton(select.value);await updateCalibrationGate();await refreshGuidedWorkflow();}
byId("participant-select")?.addEventListener("change",async e=>{globalThis.localStorage?.setItem('monitor-participant',e.target.value);updateParticipantDeleteButton(e.target.value);await updateCalibrationGate();if(typeof refreshGuidedWorkflow==='function')await refreshGuidedWorkflow();});
setInterval(()=>updateCalibrationGate(),5000);
byId("open-participant-panel")?.addEventListener("click",()=>{const panel=byId('participant-panel');if(!panel)return location.assign('/participants');panel.open=true;panel.scrollIntoView({behavior:'smooth',block:'center'});byId('participant-code')?.focus();});
byId("camera-layout")?.addEventListener("change",e=>byId("camera-grid").className=`monitor-grid ${e.target.value==="split"?"":e.target.value}`);
byId("add-participant")?.addEventListener("click",async()=>{const payload={participant_code:byId("participant-code").value,display_name:byId("display-name").value||null,age_group:byId("age-group").value||null},response=await fetch("/api/participants",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)}),data=await response.json();if(!response.ok){set("participant-message",data.detail?.[0]?.msg??data.detail??"Unable to add participant");return;}set("participant-message",`Participant ${data.participant_code} added. Select Start session when ready.`);byId("participant-code").value=byId("display-name").value=byId("age-group").value="";await loadParticipants();byId("participant-select").value=data.id;await updateCalibrationGate();});
byId("session-button")?.addEventListener("click",async()=>{const button=byId("session-button");if(activeSessionId===null){await updateCalibrationGate();if(!calibrationReady){set("participant-message","Complete the one-time System Setup before starting.");await refreshGuidedWorkflow();return}const response=await fetch("/api/sessions/start",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({participant_id:Number(byId("participant-select").value)})}),data=await response.json();if(!response.ok){set("participant-message",MonitorHelp.errorMessage(data,response.status));await updateCalibrationGate();await refreshGuidedWorkflow();return;}activeSessionId=data.id;button.textContent="Stop session";button.disabled=false;byId("participant-select").disabled=true;set("overview-session",`Active #${data.id}`);await refreshGuidedWorkflow();location.href="/attention-task/operator";}else{if(!confirm("Stop this monitoring session and create its final report? Any active task will end."))return;const id=activeSessionId,response=await fetch(`/api/sessions/${id}/stop`,{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"}),data=await response.json();if(!response.ok){set("participant-message",MonitorHelp.errorMessage(data,response.status));return;}activeSessionId=null;button.textContent="Start session";byId("participant-select").disabled=false;set("overview-session","Idle");location.href=`/reports/${id}`;}});
byId("delete-participant")?.addEventListener("click",async()=>{const select=byId("participant-select"),id=select.value,label=select.options[select.selectedIndex]?.textContent;if(!id||!confirm(`Permanently delete participant ${label}? Only participants without sessions can be deleted.`))return;const response=await fetch(`/api/participants/${id}?confirm=true`,{method:"DELETE"});if(!response.ok){set("participant-message",MonitorHelp.errorMessage(await response.json(),response.status));return;}set("participant-message",`Participant ${label} deleted.`);await loadParticipants();});
loadParticipants();

function drawLiveChart(){const canvas=byId("live-chart");if(!canvas)return;const ctx=canvas.getContext("2d"),w=canvas.width,h=canvas.height,dark=document.documentElement.dataset.theme==="dark";ctx.clearRect(0,0,w,h);ctx.strokeStyle=dark?"#33414c":"#dce3e7";ctx.lineWidth=1;for(let i=1;i<5;i++){const y=i*h/5;ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();}for(const [key,color]of [["blink","#55d8ff"],["head","#ffc857"],["body","#52e0a0"],["task","#ff668f"]]){ctx.strokeStyle=color;ctx.lineWidth=2;ctx.beginPath();chartPoints.forEach((p,i)=>{const x=i*Math.max(w/(chartPoints.length-1||1),1),y=h-Math.min(Number(p[key])||0,60)/60*h;i?ctx.lineTo(x,y):ctx.moveTo(x,y)});ctx.stroke();}}
const formatDuration=s=>{if(!s.end_time)return"—";const seconds=Math.max(0,(new Date(s.end_time)-new Date(s.start_time))/1000);return seconds<60?`${seconds.toFixed(0)}s`:`${Math.floor(seconds/60)}m ${Math.round(seconds%60)}s`;};
async function fetchSessions(){const [sessions,participants]=await Promise.all([MonitorHelp.requestJSON("/api/sessions"),MonitorHelp.requestJSON("/api/participants")]);cachedSessions=sessions;cachedParticipantCodes=Object.fromEntries(participants.map(p=>[p.id,p.participant_code]));}
async function loadRecentSessions(){const list=byId("recent-sessions");if(!list)return;await fetchSessions();const recent=cachedSessions.slice(0,4);list.innerHTML=recent.length?recent.map(s=>`<a href="/reports/${s.id}"><span><b>#${s.id} · ${MonitorHelp.escapeHTML(cachedParticipantCodes[s.participant_id]??s.participant_id)}</b><small>${new Date(s.start_time).toLocaleString()}</small></span><em>${s.status}</em></a>`).join(""):'<p class="empty-state">No sessions recorded yet.</p>';}
function renderSessionHistory(){const body=byId("session-history");if(!body)return;const filter=byId("history-filter").value,sessions=cachedSessions.filter(s=>filter==="all"||s.status===filter);body.innerHTML="";for(const s of sessions){const row=document.createElement("tr"),report=s.status==="completed"?'<option value="report">Open report</option><option value="export">Export data</option>':"",remove=s.status!=="active"?'<option value="delete">Delete session</option>':"";row.innerHTML=`<td data-label="Session"><strong>#${s.id}</strong></td><td data-label="Participant">${MonitorHelp.escapeHTML(cachedParticipantCodes[s.participant_id]??s.participant_id)}</td><td data-label="Started">${new Date(s.start_time).toLocaleString()}</td><td data-label="Duration">${formatDuration(s)}</td><td data-label="Status"><span class="status-pill">${s.status}</span></td><td data-label="Mode">${s.mode}</td><td class="record-actions"><select class="session-action" aria-label="Actions for session ${s.id}" data-session-id="${s.id}"><option value="">Actions…</option>${report}${remove}</select></td>`;body.appendChild(row);}byId("history-empty").hidden=sessions.length>0;document.querySelectorAll(".session-action").forEach(control=>control.addEventListener("change",async()=>{const id=control.dataset.sessionId,action=control.value;control.value="";if(action==="report")location.href=`/reports/${id}`;else if(action==="export")location.href=`/api/exports/sessions/${id}.zip`;else if(action==="delete"&&confirm(`Permanently delete session #${id} and all measurements?`)){const response=await fetch(`/api/sessions/${id}?confirm=true`,{method:"DELETE"});if(!response.ok){alert(MonitorHelp.errorMessage(await response.json(),response.status));return;}set("participant-message",`Session #${id} deleted.`);await loadSessionHistory();}}));}
async function loadSessionHistory(){if(!byId("session-history"))return;await fetchSessions();renderSessionHistory();}byId("refresh-history")?.addEventListener("click",loadSessionHistory);byId("history-filter")?.addEventListener("change",renderSessionHistory);loadSessionHistory();loadRecentSessions();

async function loadProtocolCatalog(){const host=byId("protocol-catalog");if(!host)return;try{const protocols=await fetch("/api/research-tasks/protocols").then(r=>{if(!r.ok)throw new Error("Protocol catalog unavailable");return r.json()});host.innerHTML=protocols.map(p=>{const state=p.implementation_status==="validation_required"?"Validation required":p.implementation_status==="planned"?"Planned":"Available";return `<article class="protocol-card"><header><div><span class="overline">${p.version}</span><h3>${p.name}</h3></div><span class="protocol-state ${p.implementation_status==="available"?"available":""}">${state}</span></header><p>${p.description}</p><div class="protocol-meta"><span>~${p.estimated_minutes} min</span><span>${p.requires_validated_gaze?"Validated gaze required":"Task events"}</span><span>Non-diagnostic</span></div></article>`}).join("")}catch(error){host.innerHTML=`<article class="protocol-card"><strong>Unable to load protocols</strong><p>${error.message}</p></article>`}}loadProtocolCatalog();

let activeSessionRefreshBusy=false;
async function syncActiveSession(){
  if(activeSessionRefreshBusy)return;
  activeSessionRefreshBusy=true;
  try{
    const data=await MonitorHelp.requestJSON('/api/sessions/active');
    const previous=activeSessionId;activeSessionId=data.active?data.session_id:null;
    const select=byId('participant-select'),button=byId('session-button');
    set('overview-session',data.active?`Active #${data.session_id}`:'Idle');
    if(!select||!button)return;
    select.disabled=!!data.active;
    if(data.active){
      if(data.participant)select.value=String(data.participant.id);
      button.textContent='Stop session';button.disabled=false;
      ensureCalibrationGate();set('calibration-gate-title','Session running');set('calibration-gate-message','Next: open task setup, pair the participant screen, then complete practice.');
      const action=byId('calibration-gate-action');action.hidden=false;action.href='/attention-task/operator';action.textContent='Next: configure participant task →';
    }else if(previous!==null){button.textContent='Start session';await updateCalibrationGate();}
  }catch(e){set('overview-session','Session status unavailable');}
  finally{activeSessionRefreshBusy=false;}
}
syncActiveSession();setInterval(syncActiveSession,3000);
MonitorHelp.requestJSON("/api/auth/me").then(user=>{const nav=document.querySelector("#sidebar nav"),tools=document.querySelector(".side-tools");if(nav&&!nav.querySelector('[href="/participants"]'))nav.insertAdjacentHTML("beforeend",'<a class="nav-link" href="/participants"><span class="nav-icon">◯</span><span class="nav-label">Participants</span></a>');if(tools&&["owner","admin"].includes(user.role)&&!tools.querySelector('[href="/users"]'))tools.querySelector(".nav-section-label")?.insertAdjacentHTML("afterend",'<a href="/users"><span class="nav-icon">＋</span><span class="nav-label">Access management</span></a>');if(tools&&!tools.querySelector(".signed-user")){const identity=document.createElement('span');identity.className='signed-user nav-label';const name=document.createElement('strong');name.textContent=user.full_name||'Local user';const role=document.createElement('small');role.textContent=user.role||'owner';identity.append(name,role);tools.querySelector('form')?.before(identity)}if(!["owner","admin"].includes(user.role)){tools?.querySelector('[href="/system-setup"]')?.remove();document.querySelector('.dropdown-menu a[href="/system-setup"]')?.remove();document.querySelector('.dropdown-menu a[href="/api/exports/database-backup.zip"]')?.remove();document.querySelector('.operation-secondary a[href="/system-setup"]')?.remove();}const manage=byId("open-participant-panel");if(manage)manage.textContent="Add participant";});
const sidebar=byId("sidebar"),shell=document.querySelector(".app-shell"),applySidebarState=collapsed=>{shell.classList.toggle("sidebar-collapsed",collapsed);localStorage.setItem("monitor-sidebar",collapsed?"collapsed":"expanded");byId("menu-toggle").setAttribute("aria-label",collapsed?"Expand sidebar":"Collapse sidebar");};applySidebarState(localStorage.getItem("monitor-sidebar")==="collapsed");byId("menu-toggle").addEventListener("click",()=>{if(innerWidth<=850){sidebar.classList.toggle("open");shell.classList.remove("sidebar-collapsed");}else applySidebarState(!shell.classList.contains("sidebar-collapsed"));});
byId("theme-toggle").addEventListener("click",()=>{const next=document.documentElement.dataset.theme==="dark"?"light":"dark";document.documentElement.dataset.theme=next;localStorage.setItem("monitor-theme",next);byId("theme-toggle").setAttribute("aria-label",next==="dark"?"Use light theme":"Use dark theme");drawLiveChart();});byId("theme-toggle").setAttribute("aria-label",document.documentElement.dataset.theme==="dark"?"Use light theme":"Use dark theme");

function installGuidedWorkflow(){
  const heading=document.querySelector('.app-shell[data-page="overview"] .page-heading');
  if(!heading||byId('guided-workflow'))return;
  heading.insertAdjacentHTML('afterend',`<section id="guided-workflow" class="guided-workflow" aria-labelledby="workflow-title">
    <header><div><span class="overline">Guided session</span><h3 id="workflow-title">Start monitoring</h3><p id="workflow-summary">Checking the next required step…</p></div><span id="workflow-state" class="workflow-state">Checking</span></header>
    <ol id="workflow-steps" class="workflow-steps" aria-label="Monitoring workflow"></ol>
    <div id="workflow-blockers" class="workflow-blockers" role="status" hidden></div>
    <footer><div id="workflow-session-controls" class="workflow-session-controls" hidden><button id="workflow-pause" type="button" class="secondary-button">Pause activity</button><button id="workflow-resume" type="button" class="secondary-button">Resume activity</button><button id="workflow-stop" type="button" class="danger-outline">Stop session</button></div><button id="workflow-back" type="button" class="secondary-button" hidden>Back</button><a id="workflow-next" class="workflow-next" href="#">Continue</a></footer>
  </section>`);
}

async function refreshGuidedWorkflow(){
  if(!byId('guided-workflow'))return;
  const participant=byId('participant-select')?.value;
  try{
    const data=await MonitorHelp.requestJSON(`/api/workflow/status${participant?`?participant_id=${encodeURIComponent(participant)}`:''}`);
    const currentIndex=data.steps.findIndex(step=>step.id===data.current_step);
    byId('workflow-steps').innerHTML=data.steps.map((step,index)=>`<li class="${step.complete?'complete':''} ${step.id===data.current_step?'current':''}" aria-current="${step.id===data.current_step?'step':'false'}"><span>${step.complete?'✓':index+1}</span><div><strong>${MonitorHelp.escapeHTML(step.label)}</strong><small>${MonitorHelp.escapeHTML(step.detail)}</small></div></li>`).join('');
    const current=data.steps[currentIndex];
    set('workflow-summary',current?.detail||'Follow the guided steps to begin.');
    set('workflow-state',data.active_session?'Session active':current?.label||'Needs attention');
    const blocker=byId('workflow-blockers');
    blocker.hidden=!data.blockers.length;
    blocker.innerHTML=data.blockers.length?`<strong>Before you continue</strong><ul>${data.blockers.map(item=>`<li>${MonitorHelp.escapeHTML(item)}</li>`).join('')}</ul><button type="button" id="workflow-retry" class="secondary-button">Check again</button>`:'';
    byId('workflow-retry')?.addEventListener('click',refreshGuidedWorkflow);
    const next=byId('workflow-next');next.href=data.next_action.href;next.textContent=`Continue: ${data.next_action.label} →`;
    if(data.current_step==='session'&&data.calibration.ready&&!data.active_session){next.href='/';next.textContent='Start monitored session →';next.onclick=null;}else next.onclick=null;
    const back=byId('workflow-back');back.hidden=currentIndex<=0;back.onclick=()=>{const prior=data.steps[Math.max(0,currentIndex-1)];location.href=prior.href;};
    const controls=byId('workflow-session-controls');controls.hidden=!data.active_session;
    byId('workflow-pause').hidden=data.task.phase!=='recording';byId('workflow-resume').hidden=data.task.phase!=='paused';
    byId('workflow-pause').onclick=()=>workflowTaskCommand('pause');byId('workflow-resume').onclick=()=>workflowTaskCommand('resume');byId('workflow-stop').onclick=()=>byId('session-button')?.click();
  }catch(error){set('workflow-summary','Workflow status unavailable. Check the server connection and retry.');set('workflow-state','Unavailable');const blocker=byId('workflow-blockers');blocker.hidden=false;blocker.innerHTML=`<strong>Unable to check readiness</strong><p>${MonitorHelp.escapeHTML(error.message)}</p><button type="button" id="workflow-retry" class="secondary-button">Retry</button>`;byId('workflow-retry').onclick=refreshGuidedWorkflow;}
}
async function workflowTaskCommand(command){try{await MonitorHelp.requestJSON(`/api/attention/${command}`,{method:'POST'});await refreshGuidedWorkflow();}catch(error){const blocker=byId('workflow-blockers');blocker.hidden=false;blocker.innerHTML=`<strong>Unable to ${command} activity</strong><p>${MonitorHelp.escapeHTML(error.message)}</p>`;}}
let operationBusy=false,operationError='';
async function refreshOperationDashboard(){
  const panel=byId('operation-participant');if(!panel)return;
  try{
    const [setupState,participants,active]=await Promise.all([
      MonitorHelp.requestJSON('/api/setup/status'),MonitorHelp.requestJSON('/api/participants'),
      MonitorHelp.requestJSON('/api/sessions/active')]);
    const selected=panel.value||byId('participant-select')?.value||localStorage.getItem('monitor-participant')||'';
    panel.innerHTML='<option value="">Choose participant…</option>'+participants.map(p=>`<option value="${p.id}">${MonitorHelp.escapeHTML(p.display_name?`${p.participant_code} — ${p.display_name}`:p.participant_code)}</option>`).join('');
    if([...panel.options].some(o=>o.value===String(selected)))panel.value=String(selected);
    const ready=byId('operation-ready');ready.textContent=setupState.status==='ready'?'System ready ✓':setupState.status==='needs_attention'?'Needs attention':'Setup required';ready.className=`operation-ready ${setupState.status==='ready'?'':'warning'}`;
    const warning=byId('operation-alert');warning.hidden=setupState.status==='ready'&&!operationError;
    if(operationError){set('operation-alert-title','Session did not start');set('operation-alert-copy',operationError);set('operation-technical','No participant data was recorded. Correct the camera view and select Start session again.');byId('operation-fix').hidden=true;}
    else{set('operation-alert-title',setupState.status==='needs_attention'?'A device needs attention':'System setup is required');set('operation-alert-copy',setupState.message);set('operation-technical',`Status: ${setupState.status} · Repair step: ${setupState.repair_step||setupState.current_step}`);const fix=byId('operation-fix');fix.hidden=false;fix.href=`/setup?step=${setupState.repair_step||setupState.current_step}`;}
    const hidden=byId('participant-select');if(hidden&&panel.value&&hidden.value!==panel.value){hidden.value=panel.value;hidden.dispatchEvent(new Event('change',{bubbles:true}))}
    const start=byId('operation-start'),activePanel=byId('active-operation');activePanel.hidden=!active.active;start.disabled=operationBusy||active.active||!panel.value||!setupState.can_start;
    if(active.active){set('active-operation-title',`Session #${active.session_id} is running`);set('active-operation-copy',active.participant?`${active.participant.participant_code}${active.participant.display_name?` — ${active.participant.display_name}`:''}`:'Monitoring is active.');}
  }catch(error){const ready=byId('operation-ready');ready.textContent='Status unavailable';ready.className='operation-ready warning';const warning=byId('operation-alert');warning.hidden=false;set('operation-alert-title','Unable to check the system');set('operation-alert-copy','Retry the connection or open System Setup.');set('operation-technical',error.message)}
}
async function startOperationSession(){
  const select=byId('operation-participant'),button=byId('operation-start');
  if(operationBusy||!select?.value)return;
  operationBusy=true;button.disabled=true;button.classList.add('is-loading');button.textContent='Checking cameras…';
  set('operation-start-status','Automatic readiness check in progress (about 2 seconds)…');
  try{
    const response=await fetch('/api/sessions/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({participant_id:Number(select.value)})});
    const data=await response.json();
    if(!response.ok)throw new Error(MonitorHelp.errorMessage(data,response.status));
    operationError='';set('operation-start-status','Ready ✓ Opening the participant activity…');
    localStorage.setItem('monitor-participant',select.value);
    location.href='/attention-task/operator';
  }catch(error){
    operationError=error.message||'Unable to start. Adjust the cameras and try again.';set('operation-start-status',operationError);
    const warning=byId('operation-alert');warning.hidden=false;
    set('operation-alert-title','Session did not start');
    set('operation-alert-copy',operationError);
    set('operation-technical','No participant data was recorded. The automatic start check did not pass.');
    const fix=byId('operation-fix');fix.hidden=true;
  }finally{
    operationBusy=false;button.classList.remove('is-loading');button.textContent='Start session';button.disabled=!select.value;
  }
}
async function stopOperationSession(){
  if(!confirm('Finish this monitoring session and create its final report?'))return;
  try{
    const active=await MonitorHelp.requestJSON('/api/sessions/active');
    if(!active.active)return refreshOperationDashboard();
    await MonitorHelp.requestJSON(`/api/sessions/${active.session_id}/stop`,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
    location.href=`/reports/${active.session_id}`;
  }catch(error){set('operation-start-status',error.message||'Unable to finish the session.');}
}
function installOperationDashboard(){const select=byId('operation-participant');if(!select)return;select.addEventListener('change',()=>{operationError='';localStorage.setItem('monitor-participant',select.value);set('operation-start-status','');refreshOperationDashboard()});byId('operation-start').onclick=startOperationSession;byId('operation-stop').onclick=stopOperationSession;refreshOperationDashboard();setInterval(refreshOperationDashboard,4000)}
installOperationDashboard();
async function setupParticipantDisplay(){if(!document.querySelector('.app-shell[data-page="attention"]'))return;const launch=document.querySelector('a[href="/attention-task/operator"]');if(launch)launch.textContent="Configure & launch ↗";const catalog=byId('protocol-catalog');if(!catalog)return;const panel=document.createElement('section');panel.className='participant-display-panel';panel.innerHTML='<div class="display-copy"><span class="overline">Secure participant pairing</span><h3>Participant task screen</h3><p>Scan this short-lived link on the tablet. It can access only practice and the assigned task—not researcher records or settings.</p><div class="display-actions"><a class="button-link" id="open-display" href="/attention-task" target="_blank" rel="noopener">Open Participant Display ↗</a><button class="secondary-button" id="copy-display" type="button">Copy link</button><button class="secondary-button" id="refresh-display" type="button">New pairing</button></div><code id="display-url">Creating secure pairing…</code></div><div class="display-qr"><img id="display-qr" alt="QR code for participant display"><small>Expires after 30 minutes</small></div>';catalog.before(panel);const loadPairing=async()=>{try{const info=await MonitorHelp.requestJSON('/api/participant-display/info');byId('open-display').href=info.url;byId('display-url').textContent=info.url;byId('display-qr').src=info.qr_url+'&t='+Date.now();byId('copy-display').onclick=async()=>{await navigator.clipboard.writeText(info.url);byId('copy-display').textContent='Copied ✓';setTimeout(()=>byId('copy-display').textContent='Copy link',1600)}}catch(_){byId('display-url').textContent='Participant display address unavailable'}};byId('refresh-display').onclick=loadPairing;loadPairing()}setupParticipantDisplay();
