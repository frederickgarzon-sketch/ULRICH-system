// Deterministic tests of the actual participant controller, without cameras/data.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
test('practice balloon stays hidden until its timed presentation starts',()=>{
  const template=fs.readFileSync(path.join(__dirname,'../templates/attention-task.html'),'utf8');
  const controller=fs.readFileSync(path.join(__dirname,'../static/js/attention-task.js'),'utf8');
  assert.match(template,/<button[^>]*id="practice-balloon"[^>]*\bhidden\b/);
  assert.match(controller,/\$\("practice-balloon"\)\.hidden=true;show\("practice-screen"\)/);
});
function harness(animationFails=false, fetchImpl=undefined) {
  let now=0, nextId=1; const timers=new Map(), nodes=new Map();
  function node(id) {
    if(!nodes.has(id)) nodes.set(id,{hidden:false,textContent:'',dataset:{},
      style:{setProperty(){}},classList:{add(){},remove(){},toggle(){}},
      setAttribute(){},addEventListener(){},append(){},offsetWidth:100,
      replaceChildren(){if(animationFails&&id.includes('particles'))throw Error('animation failed')}});
    return nodes.get(id);
  }
  const context={document:{getElementById:node,body:{dataset:{}},querySelector(){return null},
    createElement(){return node('created')},createTextNode(text){return {textContent:text}},addEventListener(){}},
    location:{pathname:'/attention-task',search:'?token=test'},URLSearchParams,
    window:{addEventListener(){}},console:{warn(){}},performance:{now:()=>now},AbortController,fetch:fetchImpl,
    setTimeout:(fn,delay)=>{const id=nextId++;timers.set(id,{fn,delay});return id},
    clearTimeout:id=>timers.delete(id),setInterval:()=>nextId++,clearInterval(){}};
  let source=fs.readFileSync(path.join(__dirname,'../static/js/attention-task.js'),'utf8');
  source=source.replace('loadCatalog().then(()=>operatorMode?initOperator():initParticipant())',
    'Promise.resolve()');
  source=source.replace('})();','window.balloonTest={waitForBalloon,participantHeartbeat,practiceLoop,phase:()=>participantPhase,setPhase:p=>participantPhase=p};})();');
  vm.runInNewContext(source,context);
  return {api:context.window.balloonTest,node,setNow:n=>now=n,
    fire(delay){const entry=[...timers].find(([,t])=>t.delay===delay);assert.ok(entry,'timer '+delay);timers.delete(entry[0]);entry[1].fn()}};
}
for(const color of ['coral','sky','turquoise','yellow','purple','orange','green','pink']) {
  test(color+' tap resolves exactly once',async()=>{
    const h=harness();h.api.setPhase('recording');const n=h.node('stimulus');
    const promise=h.api.waitForBalloon(n,{color},100,false,false);
    h.setNow(40);n._pop();n._pop();h.fire(180);
    const result=await promise;assert.equal(result.responded,true);assert.equal(result.reaction,40);assert.equal(n._pop,null);
  });
  test(color+' timeout advances with no fabricated reaction',async()=>{
    const h=harness();h.api.setPhase('practice');
    const promise=h.api.waitForBalloon(h.node('practice-balloon'),{color},100,true,false);
    h.setNow(100);h.fire(100);h.fire(0);const result=await promise;
    assert.equal(result.responded,false);assert.equal(result.reaction,null);
  });
}
test('late tap is a nonresponse, not a rejected over-window reaction',async()=>{
  const h=harness();h.api.setPhase('recording');const n=h.node('stimulus');
  const promise=h.api.waitForBalloon(n,{color:'sky'},100,false,false);
  h.setNow(101);n._pop();h.fire(0);const result=await promise;
  assert.equal(result.responded,false);assert.equal(result.reaction,null);
});
test('animation exception cannot strand a blue balloon promise',async()=>{
  const h=harness(true);h.api.setPhase('recording');const n=h.node('stimulus');
  const promise=h.api.waitForBalloon(n,{color:'sky'},100,false,false);
  h.setNow(50);n._pop();h.fire(180);assert.equal((await promise).responded,true);
});

test('completed practice generation cannot restart from a stale status response',async()=>{
  let completions=0;
  const status={phase:'practice',practice_generation:7,practice_stimuli:[],game_mode:'any'};
  const h=harness(false,async url=>({ok:true,json:async()=>{
    if(url.includes('practice-complete')){completions++;return {phase:'ready'}}
    return status;
  }}));
  h.api.setPhase('practice');
  await h.api.practiceLoop(status);
  assert.equal(h.api.phase(),'ready');
  await h.api.participantHeartbeat();
  await Promise.resolve();await Promise.resolve();
  assert.equal(completions,1);
});

test('participant heartbeat allows only one outstanding status request',async()=>{
  let requests=0;const releases=[];
  const h=harness(false,async()=>{requests++;await new Promise(r=>releases.push(r));return {ok:true,json:async()=>({phase:'waiting'})}});
  const first=h.api.participantHeartbeat();
  const second=h.api.participantHeartbeat();
  const observed=requests;releases.forEach(r=>r());await Promise.all([first,second]);
  assert.equal(observed,1);
});
