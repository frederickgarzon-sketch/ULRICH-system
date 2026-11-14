// Isolated browser regression runner. Never point this at a real server/database.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const pw=require(process.env.PLAYWRIGHT_PACKAGE||'C:/Users/Freecom/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const BASE='http://127.0.0.1:8011';
const OUT=path.resolve(__dirname,'../docs/qa/followup');
const colors=['coral','sky','turquoise','yellow','purple','orange','green','pink'];
let passed=0;
function pass(name){passed++;console.log('PASS '+name)}
async function json(api,url,data){const r=data===undefined?await api.get(BASE+url):await api.post(BASE+url,{data});assert.ok(r.ok(),url+': '+r.status()+' '+await r.text());return r.json()}
async function tap(page,selector='#stimulus',touch=false){const n=page.locator(selector);await n.waitFor({state:'visible'});if(touch)await n.tap({force:true});else await n.click({force:true});await n.waitFor({state:'hidden'})}
async function mockGame(browser,color,mode,fault='none'){
 const ctx=await browser.newContext({viewport:{width:900,height:700},hasTouch:true,reducedMotion:'reduce'}),p=await ctx.newPage();
 let phase='recording',index=0,pops=0,active=null,submitted=[],nextCalls=0,failed=false,pauseCalls=0;
 const items=mode==='any'?[true,true]:[true,false,true];
 const status=()=>({phase,run_id:41,practice_generation:1,game_mode:mode==='any'?'any':'target_color',target_color:color,target_color_label:color,required_pops:2,correct_pops:pops,sound_enabled:false,termination_reason:phase==='complete'?'goal_reached':null});
 await p.route('**/api/participant-task/**',async route=>{
  const u=new URL(route.request().url()),s=u.pathname;
  let data=status(),code=200;
  if(s.endsWith('/recover'))active=null;
  else if(s.endsWith('/pause')){phase='paused';active=null;pauseCalls++;data=status()}
  else if(s.endsWith('/trials/next')){
   nextCalls++;assert.equal(phase,'recording');assert.ok(index<items.length);active=index+1;
   const target=items[index];data={id:active,trial_number:index+1,is_target:target,display_ms:mode==='any'?2200:1600,intertrial_ms:300,
    stimulus_data:{color:target?color:(color==='sky'?'coral':'sky'),is_target:target,color_label:target?color:'other',size_px:148,x_percent:50,y_percent:40}};
  }else if(s.endsWith('/complete')){
   const body=route.request().postDataJSON();
   if(fault==='reject'&&!failed){failed=true;code=500;data={detail:'Injected submission failure'}}
   else{assert.ok(active);submitted.push(body);if(items[index]&&body.responded)pops++;index++;active=null;if(index===items.length)phase='complete';data=status();if(fault==='lost_ack'&&!failed){failed=true;code=503;data={detail:'Injected lost acknowledgement'}}}
  }else if(/\/trials\/\d+\/status$/.test(s))data={...status(),completed:fault==='lost_ack'&&failed};
  await route.fulfill({status:code,contentType:'application/json',body:JSON.stringify(data)});
 });
 await p.goto(BASE+'/attention-task?token=isolated-browser-test-token');
 if(fault==='reject'){
  await tap(p);await p.locator('#connection-screen').waitFor({state:'visible'});
  assert.match(await p.locator('#connection-message').innerText(),/Injected submission failure/);
  await p.waitForTimeout(2200);assert.equal(nextCalls,1,'must not silently replay');assert.equal(pauseCalls,1);
  await p.locator('#retry-connection').click();await p.locator('#pause-screen').waitFor({state:'visible'});phase='recording';
 }
 while(index<items.length){
  const previous=index;
  if(items[index])await tap(p,'#stimulus',index===0);
  else{await p.locator('#stimulus').waitFor({state:'visible'});await p.locator('#stimulus').waitFor({state:'hidden'})}
  // The DOM hides before submission resolves; wait for the saved completion,
  // not just the animation, before deciding what to do on the next trial.
  const deadline=Date.now()+4000;
  while(index===previous&&Date.now()<deadline)await p.waitForTimeout(20);
  assert.ok(index>previous,'presentation did not complete');
 }
 await p.locator('#complete-screen').waitFor({state:'visible'});
 assert.equal(pops,2,JSON.stringify({color,mode,submitted,nextCalls}));assert.equal(submitted.length,items.length);
 if(mode!=='any')assert.equal(submitted[1].responded,false);
 assert.equal(submitted.filter(x=>x.responded).length,2);
 await ctx.close();pass(`browser ${mode} ${color} ${fault}`);
}
async function actualGame(browser,api){
 const participant=await json(api,'/api/participants',{participant_code:'FOLLOWUP-'+Date.now(),age_group:'Child'});
 const session=await json(api,'/api/sessions/start',{participant_id:participant.id});
 const pair=await json(api,'/api/participant-display/info');const token=new URL(pair.url).searchParams.get('token');
 await json(api,'/api/participant-task/status?token='+token);
 const config={task_key:'pop_balloon',age_profile:'child',difficulty:'easy',game_mode:'any',target_color:'sky',required_pops:5,sound_enabled:false};
 const practice=await json(api,'/api/attention/practice',config);
 const ctx=await browser.newContext({reducedMotion:'reduce',hasTouch:true}),p=await ctx.newPage();
 await p.goto(BASE+'/attention-task?token='+token);
 for(let i=0;i<5;i++){
  await p.locator('#practice-balloon').waitFor({state:'visible'});
  console.log('PRACTICE',i+1,await p.locator('#practice-progress').innerText(),await p.locator('#practice-balloon').getAttribute('aria-label'));
  await tap(p,'#practice-balloon',i%2===0);
 }
 await p.locator('#waiting-screen').waitFor({state:'visible'});
 assert.equal((await json(api,'/api/attention/status')).phase,'ready',await p.locator('body').innerText());
 assert.equal((await json(api,`/api/attention/sessions/${session.id}/summary`)).total_attempts,0);
 pass('real API practice completes and is excluded from recorded data');
 await json(api,'/api/attention/start',config);
 await p.locator('#stimulus').waitFor({state:'visible'});
 await json(api,'/api/attention/pause',{});await p.locator('#pause-screen').waitFor({state:'visible'});
 await json(api,'/api/attention/resume',{});await tap(p);
 pass('real API browser operator pause/resume');
 await p.locator('#stimulus').waitFor({state:'visible'});await p.reload();await tap(p);
 pass('real API browser unfinished-trial refresh recovery');
 await p.locator('#stimulus').waitFor({state:'visible'});await ctx.setOffline(true);await p.waitForTimeout(9500);
 assert.equal((await json(api,'/api/attention/status')).phase,'paused');
 await ctx.setOffline(false);await tap(p);
 pass('real API browser disconnect auto-pause and reconnect');
 await tap(p);await tap(p);await p.locator('#complete-screen').waitFor({state:'visible'});
 await json(api,`/api/sessions/${session.id}/stop`,{});
 const report=await json(api,`/api/reports/${session.id}`),a=report.attention;
 assert.equal(a.correct_pops,5);assert.equal(a.total_attempts,5);
 const rt=a.trials.filter(t=>t.is_target&&t.responded).map(t=>t.reaction_time_ms);
 assert.ok(Math.abs(a.average_reaction_time_ms-rt.reduce((x,y)=>x+y,0)/rt.length)<.11);
 assert.equal(report.research_screening.score,null);
 for(const ext of ['json','zip'])assert.ok((await api.get(BASE+`/api/exports/sessions/${session.id}.${ext}`)).ok());
 pass('real stored counts/timing/export consistency');await ctx.close();return report;
}
async function reportChecks(browser,report){
 const ctx=await browser.newContext(),p=await ctx.newPage(),errors=[];p.on('pageerror',e=>errors.push(e.message));
 const fixture=structuredClone(report);
 fixture.session.duration_seconds=120;fixture.session.notes='QA only: <script>not executable</script>';
 fixture.data_quality.valid_pct={head:null,body:null,blink:null};fixture.data_quality.head_sample_count=0;fixture.data_quality.body_sample_count=0;
 fixture.attention.average_reaction_time_ms=null;fixture.attention.valid_tracking_attempt_pct=null;
 fixture.attention.trials=Array.from({length:45},(_,i)=>({trial:i+1,stimulus:'BALLOON_SKY',is_target:true,responded:i%2===0,correct:i%2===0,missed:i%2!==0,reaction_time_ms:i%2===0?300+i:null,phase:'recorded',balloon:{color_label:'Sky blue'}}));
 await p.route('**/api/reports/*',r=>r.fulfill({contentType:'application/json',body:JSON.stringify(fixture)}));
 await p.goto(BASE+'/reports/'+report.session.id);await p.locator('#report').waitFor({state:'visible'});
 assert.match(await p.locator('#timing-metrics').innerText(),/Not available/);
 assert.match(await p.locator('#movement-metrics').innerText(),/Not available/);
 await p.locator('details summary').click();assert.equal(await p.locator('tbody tr').count(),45);
 assert.equal(await p.locator('tbody tr').nth(1).locator('td').nth(5).innerText(),'—');
 assert.match(await p.locator('#notes').innerText(),/<script>/);
 pass('report missing-data wording, nonresponses and escaped notes');
 for(const width of [390,768,1280]){
  await p.setViewportSize({width,height:900});
  assert.ok(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'page overflow at '+width);
  await p.screenshot({path:path.join(OUT,`report-${width}.png`),fullPage:true});
  pass('report responsive width '+width);
 }
 for(const zoom of [1.25,1.5]){
  await p.evaluate(z=>document.documentElement.style.zoom=String(z),zoom);
  assert.ok(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'zoom overflow '+zoom);
  await p.screenshot({path:path.join(OUT,`report-zoom-${zoom}.png`),fullPage:true});pass('CSS zoom reflow '+zoom);
 }
 await p.evaluate(()=>document.documentElement.style.zoom='1');
 await p.locator('details summary').click();
 await p.pdf({path:path.join(OUT,'report-print.pdf'),format:'A4',printBackground:true,preferCSSPageSize:true});
 assert.equal(await p.locator('details').getAttribute('open'),null,'print restores collapsed details');
 assert.deepEqual(errors,[]);pass('PDF generation, print-detail restore and no report JS errors');
 await ctx.close();
}
(async()=>{
 fs.mkdirSync(OUT,{recursive:true});const api=await pw.request.newContext();assert.equal((await json(api,'/api/system/status')).camera.mode,'mock');
 const old=await json(api,'/api/sessions/active');if(old.active){await json(api,'/api/attention/abort',{});await json(api,`/api/sessions/${old.session_id}/stop`,{})}
 const browser=await pw.chromium.launch({headless:true,executablePath:process.env.QA_CHROME||'C:/Program Files/Google/Chrome/Application/chrome.exe'});
 try{for(const mode of ['any','target_color'])for(const color of colors)if(!process.env.QA_ONLY_COLOR||color===process.env.QA_ONLY_COLOR)await mockGame(browser,color,mode);
 await mockGame(browser,'sky','target_color','reject');await mockGame(browser,'sky','target_color','lost_ack');
 const report=await actualGame(browser,api);await reportChecks(browser,report);
 console.log(`BROWSER FOLLOWUP: ${passed} checks passed`);fs.writeFileSync(path.join(OUT,'results.json'),JSON.stringify({passed,date:new Date().toISOString(),scope:'isolated mock, not physical device acceptance'},null,2));
 }finally{await browser.close();await api.dispose()}
})().catch(e=>{console.error(e);process.exitCode=1});
