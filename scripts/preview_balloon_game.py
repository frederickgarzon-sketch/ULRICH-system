"""Existing balloon renderer/input preview, without database, AI or real APIs."""
import re
from http.server import ThreadingHTTPServer
from preview_shape_game import Preview, ROOT

BOOTSTRAP = r'''
  const demoMenu=document.createElement('div');
  demoMenu.style.cssText='position:relative;z-index:100;background:#fff1cc;color:#193d50;padding:12px;display:flex;gap:12px;flex-wrap:wrap;align-items:center';
  const demoLabel=document.createElement('strong');demoLabel.textContent='LOCAL DEMO · Not recorded · No session/backend test';demoMenu.append(demoLabel);
  const demoStart=document.createElement('button');demoStart.textContent='Try 8 colorful balloons';demoMenu.append(demoStart);
  const demoShapes=document.createElement('a');demoShapes.href='http://127.0.0.1:8765/shape-matching';demoShapes.textContent='Shape Matching ↗';demoMenu.append(demoShapes);document.body.prepend(demoMenu);
  $('stimulus').addEventListener('pointerdown',registerBalloonTap);
  $('stimulus').addEventListener('click',e=>{if(e.detail===0&&accepting)registerBalloonTap(e)});
  document.addEventListener('keydown',e=>{if(['Space','Enter'].includes(e.code)&&!e.repeat&&accepting){e.preventDefault();registerBalloonTap()}});
  $('theme-toggle').onclick=()=>document.body.classList.toggle('calm-theme');
  $('exit-fullscreen').onclick=()=>{if(document.fullscreenElement)document.exitFullscreen()};
  show('waiting-screen');$('waiting-screen').querySelector('h1').textContent='Try Pop the Balloon';
  $('waiting-screen').querySelector('p:not(.eyebrow)').textContent='Tap each balloon, or use Space / Enter. Eight colors, one attempt per color. A missed balloon advances after its timeout.';
  $('waiting-screen').querySelector('small').textContent='Visual/input demo only. The real backend, target-color rules, pairing and recorded-session flow are not running.';
  $('waiting-connection').textContent='Ready · Click Try 8 colorful balloons above';setConnection(true,'Local demo only');
  demoStart.onclick=async()=>{
    if(runningLoop)return;runningLoop=true;demoStart.disabled=true;participantPhase='recording';let popped=0;
    try{
      show('trial-screen');$('goal-label').textContent='DEMO: 8 color attempts';$('game-instruction').textContent='Pop every balloon! · Demo only';
      let i=0;
      for(const [color,hex] of Object.entries(COLOR_HEX)){
        $('progress').textContent=`Color ${i+1} of 8 · ${popped} popped`;$('progress-bar').style.width=`${i/8*100}%`;
        $('stimulus').hidden=true;$('fixation').hidden=false;await wait(600);$('fixation').hidden=true;
        const item={color,color_label:color,color_hex:hex,x_percent:30+(i%3)*20,y_percent:42,size_px:170,speed:'slow'};
        setBalloon($('stimulus'),item);const response=await waitForBalloon($('stimulus'),item,8000,false,false);
        if(response.responded)popped++;i++;await wait(300);
      }
      participantPhase='complete';show('complete-screen');$('complete-heading').textContent='Demo finished';$('complete-copy').textContent=`${popped} of 8 balloons popped. No attempts were saved. Try again with the button above.`;
    }finally{runningLoop=false;accepting=false;demoStart.disabled=false;currentTrial=null}
  };
'''


class BalloonPreview(Preview):
    def do_GET(self):
        from urllib.parse import urlsplit
        path = urlsplit(self.path).path
        if path in {"/", "/balloon"}:
            html = (ROOT / "templates/attention-task.html").read_text(encoding="utf-8")
            html = re.sub(r"{% if request.url.path.endswith\('/operator'\) %}.*?{% endif %}", "", html)
            html = html.replace("{{ app_name }}", "LOCAL DEMO — Not recorded")
            html = html.replace("Recorded activity", "Visual demo · Not recorded")
            html = html.replace('/static/js/ui-help.js', '/empty.js')
            self.send(200, html.encode(), "text/html")
        elif path == "/static/js/attention-task.js":
            source = (ROOT / "static/js/attention-task.js").read_text(encoding="utf-8")
            needle = 'loadCatalog().then(()=>operatorMode?initOperator():initParticipant())'
            if needle not in source:
                self.send(500, b"Controller changed; preview requires review", "text/plain"); return
            # Remove only the automatic backend initialization, not renderer or
            # input logic. Real application source is not modified.
            source = source.replace(needle, 'Promise.resolve()')
            source = source.replace('})();', BOOTSTRAP + '\n})();')
            self.send(200, source.encode(), "text/javascript")
        elif path == "/static/css/attention-task.css":
            self.send(200, (ROOT / "static/css/attention-task.css").read_bytes(), "text/css")
        elif path == "/static/img/brand/behavior-monitor-icon.png":
            self.send(200, (ROOT / "static/img/brand/behavior-monitor-icon.png").read_bytes(), "image/png")
        elif path == "/empty.js":
            self.send(200, b"/* No application helpers needed for visual demo */", "text/javascript")
        else:
            self.send(404, b"Balloon visual demo only; no backend API", "text/plain")


if __name__ == "__main__":
    print("Balloon visual DEMO: http://127.0.0.1:8766/balloon", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8766), BalloonPreview).serve_forever()
