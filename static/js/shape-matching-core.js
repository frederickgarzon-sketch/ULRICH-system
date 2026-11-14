/* Pure, deterministic task state: no network, DOM or participant data. */
(function(root){
  'use strict';
  const shapes=['circle','square','triangle','star'];
  class ShapeGame {
    constructor(count=10,random=Math.random){
      if(!Number.isInteger(count)||count<1||count>50)throw Error('Choose 1–50 trials');
      this.random=random;this.plan=Array.from({length:count},(_,i)=>shapes[i%4]);
      for(let i=count-1;i>0;i--){const j=Math.floor(random()*(i+1));[this.plan[i],this.plan[j]]=[this.plan[j],this.plan[i]]}
      this.rows=[];this.index=0;this.activeMs=0;this.wrong=0;this.selected=false;this.paused=false;this.stopped=false;
      this.targets=this.shuffleTargets();
    }
    shuffleTargets(){return shapes.map(s=>({s,key:this.random()})).sort((a,b)=>a.key-b.key).map(x=>x.s)}
    get done(){return this.index>=this.plan.length||this.stopped}
    get current(){return this.done?null:this.plan[this.index]}
    select(){if(!this.done&&!this.paused)this.selected=true}
    tick(ms){if(!Number.isFinite(ms)||ms<0)throw Error('Invalid elapsed time');if(this.done||this.paused)return null;this.activeMs=Math.min(30000,this.activeMs+ms);if(this.activeMs>=30000)return this.finish('timeout');return null}
    match(target){
      if(this.done||this.paused||!this.selected)return {ignored:true};
      this.selected=false;
      if(target===this.current)return this.finish('matched');
      this.wrong++;
      if(this.wrong>=3)return this.finish('assistance_limit');
      return {wrong:true,remaining:3-this.wrong};
    }
    finish(outcome){
      const row={trial:this.index+1,shape:this.current,outcome,active_ms:Math.round(this.activeMs),wrong_drops:this.wrong,first_attempt_correct:outcome==='matched'&&this.wrong===0};
      this.rows.push(row);this.index++;this.activeMs=0;this.wrong=0;this.selected=false;this.targets=this.shuffleTargets();return {advanced:true,row,done:this.done};
    }
    pause(){if(!this.done){this.paused=true;this.selected=false}}
    resume(){this.paused=false}
    stop(){if(!this.done)this.finish('stopped');this.stopped=true;this.selected=false}
  }
  const api={ShapeGame,shapes};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.ShapeMatching=api;
})(typeof window==='undefined'?globalThis:window);
