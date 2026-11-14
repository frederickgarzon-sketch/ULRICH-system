(()=>{
  'use strict';const $=id=>document.getElementById(id);
  const colors={circle:'#ec6b7e',square:'#8e60d2',triangle:'#e8a52b',star:'#179bb2'};
  let game=null,practice=false,previous=performance.now(),drag=null,suppressClickUntil=0;
  const token=new URLSearchParams(location.search).get('token');let run=null,recorded=false,saving=false,pending=null,startBusy=false;
  async function api(path,body){const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),8000);try{const response=await fetch(path,{method:body===undefined?'GET':'POST',headers:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),signal:controller.signal,cache:'no-store'});const value=await response.json();if(!response.ok)throw Error(typeof value.detail==='string'?value.detail:'Request failed');return value}finally{clearTimeout(timer)}}
  const endpoint=(path)=>`/api/participant-task/shape/${path}?token=${encodeURIComponent(token)}`;
  function show(id){['setup','game','paused','complete','connection'].forEach(s=>$(s).hidden=s!==id)}
  function fail(error){if(game)game.pause();clearDrag();$('connection-error').textContent=`${error.message}. Completed attempts remain saved. An unsaved attempt must be retried before continuing.`;show('connection')}
  function restore(status){run=status;game=new ShapeMatching.ShapeGame(status.plan.length);game.plan=[...status.plan];game.rows=[...status.rows];game.index=status.rows.length;game.stopped=['stopped','complete'].includes(status.status);game.targets=game.shuffleTargets();recorded=true;practice=false;previous=performance.now();render();if(!game.done){game.pause();show('paused');$('paused').querySelector('p:not(.eyebrow)').textContent='Resume from the last saved attempt. An unfinished attempt restarts; its earlier unsaved time is not reconstructed.'}}
  async function advance(result){if(!result||!result.advanced)return;if(recorded){pending=result.row;saving=true;game.pause();clearDrag();$('message').textContent='Saving attempt…';try{run=await api(endpoint('trial'),pending);pending=null;saving=false;if(run.status==='stopped')game.stopped=true;game.resume();previous=performance.now()}catch(error){saving=false;fail(error);return}}render();$('message').textContent=result.row.outcome==='matched'?'Matched! Find the next home.':'Let’s try a new shape.'}
  function clearDrag(){drag=null;$('piece').style.transform='';document.querySelectorAll('.target').forEach(n=>n.classList.remove('hover'))}
  function render(){
    clearDrag();if(game.done){show('complete');$('finish-title').textContent=practice?'Practice finished':'Activity finished';$('summary').textContent=recorded?'Saved. Please wait for the researcher.':`Local preview: ${game.rows.filter(r=>r.outcome==='matched').length} matched of ${game.plan.length} planned shapes.`;$('save-note').textContent=recorded?`Shape Matching run #${run.id} saved to monitoring session #${run.session_id}.`:'Not recorded. Practice/local preview attempts are not saved.';return}
    $('mode').textContent=practice?'Practice · Not recorded':recorded?'Shape Matching · Recording':'Local preview · Not recorded';$('progress').textContent=`Shape ${game.index+1} of ${game.plan.length}`;$('bar').max=game.plan.length;$('bar').value=game.index;
    const shape=$('piece').querySelector('.shape');shape.className=`shape ${game.current}`;shape.style.setProperty('--piece-color',colors[game.current]);$('piece').setAttribute('aria-label',`Select ${game.current}`);$('piece').setAttribute('aria-pressed','false');$('shape-name').textContent=game.current;
    $('targets').replaceChildren(...game.targets.map(name=>{const b=document.createElement('button');b.type='button';b.className='target';b.dataset.shape=name;b.setAttribute('aria-label',`Match ${name}`);const s=document.createElement('span');s.className=`shape ${name}`;s.setAttribute('aria-hidden','true');const label=document.createElement('span');label.textContent=name;b.append(s,label);b.addEventListener('click',()=>choose(name));return b}));
  }
  async function start(isPractice){
    if(startBusy||saving||pending)return;
    const n=Number($('count').value);
    if(!isPractice&&(!Number.isInteger(n)||n<5||n>50)){$('error').textContent='Choose a whole number from 5 to 50.';return}
    startBusy=true;$('start').disabled=true;$('practice').disabled=true;
    try{
      recorded=false;practice=isPractice;game=new ShapeMatching.ShapeGame(isPractice?4:n);
      if(token&&!isPractice){
        let status=await api(endpoint('action/start'),{});
        if(status.status==='paused')status=await api(endpoint('action/resume'),{});
        restore(status);if(game.done)return;game.resume();
      }
      $('error').textContent='';$('message').textContent='Tap or drag the shape to its matching outline.';
      previous=performance.now();show('game');render();
    }catch(error){fail(error)}
    finally{startBusy=false;$('start').disabled=false;$('practice').disabled=false}
  }
  function choose(name){if(!game||saving)return;const result=game.match(name);$('piece').setAttribute('aria-pressed',String(game.selected));clearDrag();if(result.ignored){$('message').textContent='Tap the colorful shape first, then its matching outline.';return}if(result.advanced)advance(result);else $('message').textContent=`Not that home. Pick up the shape and try again. ${result.remaining} tries left.`}
  async function pause(){if(!game||game.done||saving)return;game.pause();clearDrag();show('paused');if(recorded)try{run=await api(endpoint('action/pause'),{})}catch(error){fail(error)}}
  async function stop(){if(!game||saving||!confirm(recorded?'End this activity? Completed attempts remain saved.':'End this local preview?'))return;game.stop();if(recorded){pending=game.rows.at(-1);try{if(pending)await api(endpoint('trial'),pending);run=await api(endpoint('action/stop'),{});pending=null}catch(error){fail(error);return}}render()}
  $('practice').onclick=()=>start(true);$('start').onclick=()=>start(false);$('pause').onclick=pause;$('resume').onclick=async()=>{try{if(recorded){run=await api(endpoint('action/resume'),{});if(run.status!=='recording'){restore(run);return}}game.resume();previous=performance.now();show('game');render()}catch(error){fail(error)}};$('stop').onclick=stop;$('paused-stop').onclick=stop;$('again').onclick=()=>{game=null;show('setup')};
  $('pair').onclick=async()=>{if($('pair').disabled)return;$('pair').disabled=true;try{const status=await api('/api/shape-matching/runs',{count:Number($('count').value)});const a=document.createElement('a');a.href=status.url;a.target='_blank';a.rel='noopener';a.textContent=`Open paired Shape Matching · Session #${status.session_id}`;$('pair-result').replaceChildren(a)}catch(error){$('error').textContent=error.message}finally{$('pair').disabled=false}};
  $('operator-stop-shape').hidden=!!token;
  $('operator-stop-shape').onclick=async()=>{if(!confirm('Stop the active Shape Matching run for this monitoring session? Saved attempts remain.'))return;try{await api('/api/shape-matching/stop-active',{});$('pair-result').textContent='Shape Matching stopped. You may create a new run.'}catch(error){$('error').textContent=error.message}};
  $('retry-save').onclick=async()=>{try{if(pending){run=await api(endpoint('trial'),pending);pending=null}restore(await api(endpoint('status')))}catch(error){fail(error)}};
  if(token){$('operator-back').hidden=true;$('pair').hidden=true;$('count').disabled=true;$('recording-note').textContent='Paired participant screen. Practice is not recorded. Begin recorded activity only when the researcher is ready.';$('start').textContent='Begin recorded Shape Matching';api(endpoint('status')).then(status=>{$('count').value=status.plan.length;if(status.status!=='waiting')restore(status)}).catch(fail)}
  $('piece').addEventListener('click',()=>{if(performance.now()<suppressClickUntil)return;if(game&&!game.done&&!game.paused){game.select();$('piece').setAttribute('aria-pressed','true');$('message').textContent='Now choose the matching outline.'}});
  $('piece').addEventListener('pointerdown',e=>{if(!game||game.done||game.paused)return;game.select();$('piece').setAttribute('aria-pressed','true');drag={id:e.pointerId,x:e.clientX,y:e.clientY,moved:false};$('piece').setPointerCapture(e.pointerId)});
  $('piece').addEventListener('pointermove',e=>{if(!drag||drag.id!==e.pointerId)return;const dx=e.clientX-drag.x,dy=e.clientY-drag.y;drag.moved=drag.moved||Math.hypot(dx,dy)>8;if(drag.moved)$('piece').style.transform=`translate(${dx}px,${dy}px)`;document.querySelectorAll('.target').forEach(n=>{const r=n.getBoundingClientRect();n.classList.toggle('hover',e.clientX>=r.left&&e.clientX<=r.right&&e.clientY>=r.top&&e.clientY<=r.bottom)})});
  $('piece').addEventListener('pointerup',e=>{if(!drag||drag.id!==e.pointerId)return;const moved=drag.moved;let target=null;document.querySelectorAll('.target').forEach(n=>{const r=n.getBoundingClientRect();if(e.clientX>=r.left&&e.clientX<=r.right&&e.clientY>=r.top&&e.clientY<=r.bottom)target=n.dataset.shape});clearDrag();if(moved){suppressClickUntil=performance.now()+400;e.preventDefault();if(target)choose(target);else{$('message').textContent='Drop inside a matching outline, or tap an outline.'}}});
  $('piece').addEventListener('pointercancel',()=>{clearDrag();if(game)game.selected=false;$('piece').setAttribute('aria-pressed','false')});
  document.addEventListener('visibilitychange',()=>{if(document.hidden)pause()});document.addEventListener('keydown',e=>{if(e.code==='Escape')pause()});
  setInterval(()=>{const now=performance.now(),delta=now-previous;previous=now;if(game&&!game.done&&!game.paused&&!saving){const result=game.tick(delta);if(result)advance(result)}},100);
})();
