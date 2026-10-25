const $=id=>document.getElementById(id);
const esc=value=>String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

function render(users){
  $("user-list").innerHTML=users.map(u=>{
    const pin=u.access_token;
    const token=pin
      ? `<span class="account-pin" aria-label="Access PIN">${esc(pin)}</span><button class="secondary copy-pin" data-pin="${esc(pin)}">Copy</button>`
      : `<span class="legacy-pin">Legacy token ending ${esc(u.token_hint)}</span><button class="secondary regenerate-pin" data-regenerate="${u.id}">Create 6-digit PIN</button>`;
    return `<article class="account-row"><div><strong>${esc(u.full_name)}</strong><small>${esc(u.professional_title||"No title")}${u.organization?` · ${esc(u.organization)}`:""}</small><small>${u.expires_at?`Expires ${new Date(u.expires_at).toLocaleDateString()}`:"No expiry"}</small></div><div class="pin-actions">${token}</div><span class="account-role">${esc(u.role)}</span><div class="account-actions"><button class="${u.active?"secondary":""}" data-user="${u.id}" data-active="${!u.active}">${u.active?"Revoke":"Reactivate"}</button><button class="danger-outline delete-account" data-delete-user="${u.id}" data-name="${esc(u.full_name)}">Delete</button></div></article>`;
  }).join("")||"<p>No named accounts created yet.</p>";
  document.querySelectorAll("[data-user]").forEach(b=>b.onclick=async()=>{await fetch(`/api/users/${b.dataset.user}/status?active=${b.dataset.active}`,{method:"POST"});load()});
  document.querySelectorAll(".copy-pin").forEach(b=>b.onclick=async()=>{await navigator.clipboard.writeText(b.dataset.pin);b.textContent="Copied";setTimeout(()=>b.textContent="Copy",1200)});
  document.querySelectorAll(".regenerate-pin").forEach(b=>b.onclick=async()=>{if(!confirm("Replace the old token with a new six-digit PIN? The old token will stop working."))return;const response=await fetch(`/api/users/${b.dataset.regenerate}/regenerate-token`,{method:"POST"});const body=await response.json();if(!response.ok)return alert(MonitorHelp.errorMessage(body,response.status));load()});
  document.querySelectorAll(".delete-account").forEach(b=>b.onclick=async()=>{if(!confirm(`Permanently delete the account for ${b.dataset.name}? Use Revoke instead if it owns research records.`))return;const response=await fetch(`/api/users/${b.dataset.deleteUser}?confirm=true`,{method:"DELETE"});if(!response.ok){const body=await response.json();alert(MonitorHelp.errorMessage(body,response.status));return}load()});
}

async function load(){const response=await fetch("/api/users");if(response.status===403){$("user-list").innerHTML="<p>Administrator access is required.</p>";return}render(await response.json())}
$("refresh-users").onclick=load;
$("user-form").onsubmit=async e=>{e.preventDefault();const payload={full_name:$("user-name").value,professional_title:$("professional-title").value||null,organization:$("organization").value||null,role:$("user-role").value,expires_in_days:Number($("expires-days").value)};const response=await fetch("/api/users",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)}),body=await response.json();if(!response.ok){$("user-message").textContent=MonitorHelp.errorMessage(body,response.status);return}$("generated-token").textContent=body.access_token;$("token-result").hidden=false;$("user-message").textContent=`Account created for ${body.full_name}.`;e.target.reset();load()};
load();
