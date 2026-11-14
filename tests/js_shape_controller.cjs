const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const core=require('../static/js/shape-matching-core.js');
function harness(fetchImpl=async()=>{throw Error('unexpected network')},paired=false){
 const nodes=new Map();let now=0;const intervals=[];
 function node(id){if(!nodes.has(id)){const n={hidden:false,value:'5',disabled:false,dataset:{},children:[],textContent:'',style:{setProperty(){}},classList:{add(){},remove(){},toggle(){}},attributes:{},listeners:{},setAttribute(k,v){this.attributes[k]=v},append(...v){this.children.push(...v)},replaceChildren(...v){this.children=v},addEventListener(k,v){this.listeners[k]=v},setPointerCapture(){},querySelector(q){return node(id+q)},getBoundingClientRect(){return {left:0,right:100,top:0,bottom:100}}};nodes.set(id,n)}return nodes.get(id)}
 const document={hidden:false,getElementById:node,querySelectorAll(q){return q==='.target'?node('targets').children:[]},createElement(tag){return node('created'+nodes.size+tag)},addEventListener(){}};
 const ctx={document,ShapeMatching:core,performance:{now:()=>now},location:{search:paired?'?token=synthetic-token-value':''},URLSearchParams,AbortController,fetch:fetchImpl,confirm:()=>true,setTimeout,clearTimeout,setInterval:fn=>intervals.push(fn)};
 let source=fs.readFileSync(require.resolve('../static/js/shape-matching.js'),'utf8');source=source.replace('})();','globalThis.controller={start,choose,pause,stop,restore,state:()=>({game,recorded,pending,saving}),select:()=>game.select()};})();');
 vm.runInNewContext(source,ctx);return {api:ctx.controller,node,intervals,advance:ms=>{now+=ms;intervals.forEach(fn=>fn())}};
}
test('practice completes without sending network requests',async()=>{const h=harness();await h.api.start(true);while(!h.api.state().game.done){h.api.select();h.api.choose(h.api.state().game.current)}assert.equal(h.api.state().game.rows.length,4);assert.equal(h.node('complete').hidden,false);assert.match(h.node('save-note').textContent,/Not recorded/)});
test('wrong target requires reselection and local timeout advances',async()=>{const h=harness();await h.api.start(false);h.api.select();h.api.choose(core.shapes.find(x=>x!==h.api.state().game.current));assert.equal(h.api.state().game.wrong,1);h.api.choose(h.api.state().game.current);assert.equal(h.api.state().game.index,0);h.advance(30000);assert.equal(h.api.state().game.index,1)});
test('pause freezes timer and resume restores game',async()=>{const h=harness();await h.api.start(false);h.advance(1000);await h.api.pause();h.advance(50000);assert.equal(h.api.state().game.activeMs,1000);await h.node('resume').onclick();assert.equal(h.api.state().game.paused,false);assert.equal(h.node('game').hidden,false)});
test('restoring saved progress resumes at next unsaved shape',()=>{const h=harness();h.api.restore({id:1,session_id:8,status:'recording',plan:['circle','star','square','triangle','star'],rows:[{trial:1,shape:'circle',outcome:'matched',active_ms:100,wrong_drops:0,first_attempt_correct:true}]});assert.equal(h.api.state().game.current,'star');assert.equal(h.api.state().game.paused,true);assert.equal(h.node('paused').hidden,false)});
test('recorded save failure blocks play and retry reuses exact attempt',async()=>{
 let writes=0;let rows=[];const status={id:1,session_id:8,status:'recording',plan:['circle','star','square','triangle','star'],rows};
 const h=harness(async(url,opt)=>{if(url.includes('/trial')){writes++;const row=JSON.parse(opt.body);if(!rows.length)rows.push(row);else assert.deepEqual(rows[0],row);if(writes===1)throw Error('response lost');return {ok:true,json:async()=>({...status,rows})}}return {ok:true,json:async()=>({...status,rows})}});
 h.api.restore(status);await h.node('resume').onclick();h.api.select();h.api.choose('circle');await new Promise(setImmediate);
 assert.equal(h.node('connection').hidden,false);assert.equal(h.api.state().game.paused,true);assert.ok(h.api.state().pending);
 await h.node('retry-save').onclick();assert.equal(writes,2);assert.equal(rows.length,1);assert.equal(h.api.state().pending,null);assert.equal(h.api.state().game.index,1);
});
test('recorded completion is displayed only after save resolves',async()=>{let release;const h=harness(async()=>{await new Promise(r=>release=r);return {ok:true,json:async()=>({id:1,session_id:8,status:'complete'})}});h.api.restore({id:1,session_id:8,status:'recording',plan:['circle'],rows:[]});h.api.state().game.resume();h.node('complete').hidden=true;h.api.select();h.api.choose('circle');assert.equal(h.node('complete').hidden,true);assert.equal(h.api.state().saving,true);release();await new Promise(setImmediate);assert.equal(h.node('complete').hidden,false);assert.match(h.node('save-note').textContent,/saved/)});

test('rapid recorded-start taps send only one start request',async()=>{
 let starts=0,release;const status={id:1,session_id:8,status:'waiting',plan:['circle','star','square','triangle','star'],rows:[]};
 const h=harness(async url=>{if(url.includes('action/start')){starts++;await new Promise(r=>release=r);return {ok:true,json:async()=>({...status,status:'recording'})}}return {ok:true,json:async()=>status}},true);
 await new Promise(setImmediate);const first=h.api.start(false);await h.api.start(false);assert.equal(starts,1);release();await first;assert.equal(h.api.state().recorded,true);
});

test('begin recorded run resumes server state after practice on a paused pairing',async()=>{
 const calls=[];const status={id:1,session_id:8,status:'paused',plan:['circle','star','square','triangle','star'],rows:[]};
 const h=harness(async url=>{calls.push(url);return {ok:true,json:async()=>({...status,status:url.includes('resume')?'recording':'paused'})}},true);
 await new Promise(setImmediate);await h.api.start(true);await h.api.start(false);
 assert.ok(calls.some(x=>x.includes('action/resume')));assert.equal(h.api.state().game.paused,false);
});
