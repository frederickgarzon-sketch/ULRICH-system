const id=x=>document.getElementById(x),esc=value=>MonitorHelp.escapeHTML(String(value??''));
async function load(){
  const d=await MonitorHelp.requestJSON('/api/hardware/validation');
  id('score').textContent=`${d.passed}/${d.total}`;
  id('readiness').textContent=d.ready?'Automatic checks passed':'Hardware validation incomplete';
  id('readiness').style.color=d.ready?'#4ddda0':'#ffc45c';
  id('topology').textContent=`Configured topology: ${d.topology==='raspberry-pi'?'Raspberry Pi network streams':'Direct USB cameras'}`;
  id('checks').innerHTML=d.checks.map(c=>`<div class="check ${c.passed?'':'fail'}"><div>${esc(c.label)}<span>${esc(c.detail)}</span></div><b>${c.passed?'PASS':'PENDING'}</b></div>`).join('');
  id('sources').innerHTML=Object.entries(d.sources).map(([name,s])=>`<div class="source"><strong>${esc(name.toUpperCase())}</strong><span>${esc(s.kind)}</span>${esc(s.value)}</div>`).join('');
  id('rpi').innerHTML=d.node_health_url?`<p>Configured health URL:</p><div class="source">${esc(d.node_health_url)}</div>`:'<p>Not configured. Current inputs are direct USB sources.</p>';
  id('physical').innerHTML=d.requires_physical_validation.map(x=>`<li>${esc(x)}</li>`).join('');
}
id('run-checks').addEventListener('click',load);
id('probe-rpi').addEventListener('click',async()=>{
  id('rpi').textContent='Probing…';
  const d=await MonitorHelp.requestJSON('/api/hardware/rpi-health');
  id('rpi').innerHTML=`<p>${d.reachable?'Node reachable':'Node not reachable/configured'}</p><div class="source">${esc(d.url??d.detail??'')}</div>`;
});
load();
