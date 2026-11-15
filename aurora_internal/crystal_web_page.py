# Authors: Sunni (Sir) Morningstar & Cael Devo
"""The one page of the concept web: search, a force-laid web of ties, and a card of everything a crystal holds.  No outside scripts, styles or fonts; every
value from the store is written with textContent (never as markup)."""

PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Aurora · subsurface hub</title>
<style>
:root{--bg:#0f1218;--panel:#171c25;--line:#2a3140;--ink:#e6e9ef;--mute:#8d96a8;--accent:#8fb4ff;--l1:#6b7a99;--l2:#e0b25c;--l3:#e07a8f;--l4:#9be0b0}
@media (prefers-color-scheme:light){:root{--bg:#f6f7fa;--panel:#fff;--line:#d9dde6;--ink:#1c2030;--mute:#5d667a;--accent:#2f5fd0;--l1:#7d8aa6;--l2:#b9831e;--l3:#c24a67;--l4:#2f9460}}
*{box-sizing:border-box}html,body{height:100%;margin:0}body{background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,sans-serif;display:flex;flex-direction:column}
header{display:flex;gap:8px;align-items:center;padding:8px 10px;border-bottom:1px solid var(--line);background:var(--panel);flex-wrap:wrap}
header h1{font-size:14px;margin:0 8px 0 0;font-weight:600}
nav{display:flex;gap:4px}nav button.on{border-color:var(--accent);color:var(--accent)}#panel{display:block;overflow:auto;padding:12px 16px;flex:1}#panel[hidden]{display:none}#panel h2{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--mute);margin:16px 0 6px}
table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:4px 8px;border-bottom:1px solid var(--line);vertical-align:top;font-size:13px}th{color:var(--mute);font-weight:500}.ok{color:var(--l4)}.off{color:var(--mute)}.bad{color:var(--l3)}
input,select,button{background:var(--bg);color:var(--ink);border:1px solid var(--line);border-radius:6px;padding:6px 8px;font:inherit}
input{flex:1;min-width:160px}button{cursor:pointer}
main{flex:1;display:flex;min-height:0}main[hidden]{display:none}
#left{width:230px;border-right:1px solid var(--line);overflow:auto;background:var(--panel)}
#left h2,#card h2{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--mute);margin:10px 10px 4px}
.row{padding:5px 10px;cursor:pointer;display:flex;justify-content:space-between;gap:6px;border-bottom:1px solid var(--line)}
.row:hover{background:var(--bg)}.row small{color:var(--mute)}
#stage{flex:1;position:relative;min-width:0}canvas{width:100%;height:100%;display:block;touch-action:none}
#note{position:absolute;left:10px;bottom:8px;color:var(--mute);font-size:12px}
#card{width:340px;border-left:1px solid var(--line);overflow:auto;background:var(--panel);padding-bottom:20px}
#card .k{padding:2px 10px}#card .big{font-size:18px;font-weight:600;padding:8px 10px 0}
.pill{display:inline-block;border:1px solid var(--line);border-radius:10px;padding:0 7px;margin:2px 3px 2px 0;font-size:12px;cursor:pointer}
.mono{font:12px ui-monospace,monospace;color:var(--mute);word-break:break-word}
.bar{height:6px;background:var(--line);border-radius:3px;margin:2px 10px 6px}.bar i{display:block;height:100%;background:var(--accent);border-radius:3px}
@media (max-width:900px){main{flex-direction:column}#left,#card{width:auto;max-height:34%;border:0;border-top:1px solid var(--line)}#left{order:3}}
</style></head><body>
<header><h1>Aurora · subsurface hub</h1><nav id="tabs"><button data-t="web" class="on">Concepts</button><button data-t="ledger">Ledger</button><button data-t="strata">Strata link</button><button data-t="pass">Crystal pass</button></nav><input id="q" placeholder="search a word or concept" autocomplete="off">
<select id="depth"><option value="1" selected>1 step</option><option value="2">2 steps</option><option value="3">3 steps</option></select>
<button id="reset">whole-store hubs</button></header>
<main id="panel" hidden></main>
<main id="webmain"><div id="left"><h2 id="lt">Most connected</h2><div id="list"></div></div>
<div id="stage"><canvas id="cv"></canvas><div id="note"></div></div>
<div id="card"><div class="big">Pick a concept</div></div></main>
<script>
const T=new URLSearchParams(location.search).get('t')||'';
const $=id=>document.getElementById(id);
function api(path,params){const u=new URLSearchParams(params||{});if(T)u.set('t',T);return fetch(path+'?'+u).then(r=>r.ok?r.json():null).catch(()=>null)}
function el(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e}
const css=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const cv=$('cv'),cx=cv.getContext('2d');let W=0,H=0,dpr=1;
function size(){dpr=window.devicePixelRatio||1;const r=cv.getBoundingClientRect();W=r.width;H=r.height;cv.width=W*dpr;cv.height=H*dpr;cx.setTransform(dpr,0,0,dpr,0,0)}
addEventListener('resize',size);
let nodes=[],edges=[],byId={},root=null,drag=null,hover=null,alpha=1;
function layout(g){
  const old=byId;nodes=g.nodes.map((n,i)=>{const o=old[n.id];const a=i*2.4;const r=30+n.depth*90;
    return Object.assign({},n,{x:o?o.x:W/2+Math.cos(a)*r,y:o?o.y:H/2+Math.sin(a)*r,vx:0,vy:0})});
  byId={};nodes.forEach(n=>byId[n.id]=n);
  edges=g.edges.filter(e=>byId[e.a]&&byId[e.b]).map(e=>({a:byId[e.a],b:byId[e.b],s:e.strength}));root=g.root;alpha=1;
  $('note').textContent=nodes.length+' concepts, '+edges.length+' ties'+(g.truncated?' (trimmed to the strongest)':'')}
function step(){
  if(alpha>0.01){
    for(let i=0;i<nodes.length;i++){const a=nodes[i];
      for(let j=i+1;j<nodes.length;j++){const b=nodes[j];let dx=a.x-b.x,dy=a.y-b.y,d2=dx*dx+dy*dy+1,f=6000/d2*alpha,d=Math.sqrt(d2);dx/=d;dy/=d;a.vx+=dx*f;a.vy+=dy*f;b.vx-=dx*f;b.vy-=dy*f}
      a.vx+=(W/2-a.x)*0.002*alpha;a.vy+=(H/2-a.y)*0.002*alpha}
    for(const e of edges){const dx=e.b.x-e.a.x,dy=e.b.y-e.a.y,d=Math.sqrt(dx*dx+dy*dy)+0.1,want=60+110*(1-Math.min(1,e.s)),f=(d-want)*0.02*alpha,fx=dx/d*f,fy=dy/d*f;e.a.vx+=fx;e.a.vy+=fy;e.b.vx-=fx;e.b.vy-=fy}
    for(const n of nodes){if(n===drag)continue;n.vx*=0.6;n.vy*=0.6;n.x+=n.vx;n.y+=n.vy}
    alpha*=0.985}
  draw();requestAnimationFrame(step)}
const col=l=>css('--l'+Math.min(4,Math.max(1,l)));
function rad(n){return 5+Math.min(14,Math.sqrt(n.ties)*1.4)+(n.id===root?3:0)}
function draw(){
  cx.clearRect(0,0,W,H);
  for(const e of edges){cx.globalAlpha=0.15+0.6*Math.min(1,e.s);cx.strokeStyle=css('--mute');cx.lineWidth=0.5+2.5*Math.min(1,e.s);cx.beginPath();cx.moveTo(e.a.x,e.a.y);cx.lineTo(e.b.x,e.b.y);cx.stroke()}
  cx.globalAlpha=1;cx.font='12px system-ui';cx.textAlign='center';
  for(const n of nodes){cx.fillStyle=col(n.level);cx.beginPath();cx.arc(n.x,n.y,rad(n),0,6.283);cx.fill();
    if(n.id===root||n===hover){cx.strokeStyle=css('--ink');cx.lineWidth=2;cx.stroke()}
    cx.fillStyle=css('--ink');cx.globalAlpha=n.depth>1&&n!==hover?0.6:1;cx.fillText(n.concept,n.x,n.y-rad(n)-4);cx.globalAlpha=1}}
function at(ev){const r=cv.getBoundingClientRect(),x=ev.clientX-r.left,y=ev.clientY-r.top;let best=null,bd=1e9;
  for(const n of nodes){const d=Math.hypot(n.x-x,n.y-y);if(d<rad(n)+6&&d<bd){best=n;bd=d}}return{n:best,x,y}}
let moved=false;
cv.addEventListener('pointerdown',ev=>{const h=at(ev);if(h.n){drag=h.n;moved=false;cv.setPointerCapture(ev.pointerId)}});
cv.addEventListener('pointermove',ev=>{const h=at(ev);if(drag){moved=true;drag.x=h.x;drag.y=h.y;alpha=Math.max(alpha,0.3)}else hover=h.n});
cv.addEventListener('pointerup',()=>{if(drag&&!moved)show(drag.concept,false);drag=null});
cv.addEventListener('dblclick',ev=>{const h=at(ev);if(h.n)show(h.n.concept,true)});
async function web(name){const g=await api('/api/web',{name,depth:$('depth').value,max:70});if(g)layout(g)}
async function card(name){
  const c=await api('/api/concept',{name}),box=$('card');box.replaceChildren();if(!c){box.append(el('div','big','Unknown concept'));return null}
  box.append(el('div','big',c.concept),el('div','k',c.level_name+' · used '+c.usage+' times · '+c.tie_count+' ties'));
  if(c.standing){box.append(el('h2',null,'Standing (which levels she has earned)'));
    for(const k of Object.keys(c.standing)){const r=el('div','k','level '+k+'  '+c.standing[k].toFixed(2));box.append(r);const b=el('div','bar'),i=el('i');i.style.width=Math.round(100*c.standing[k])+'%';b.append(i);box.append(b)}}
  if(c.maturity){box.append(el('h2',null,'Maturity points'));const m=el('div','k');m.textContent=Object.entries(c.maturity).map(([k,v])=>k+' '+(v===null?'–':v)).join(' · ');box.append(m)}
  if(c.interior&&c.interior.layers.length){box.append(el('h2',null,'Interior (grown inward, depth '+c.interior.depth+')'));
    for(const l of c.interior.layers){box.append(el('div','k',(l.anchor||'aspect')+': '+l.members.join(', ')+(l.inner?' · '+l.inner+' inner':'')))}}
  if(c.ties.length){box.append(el('h2',null,'Ties (strongest first)'));const t=el('div','k');
    for(const x of c.ties){const p=el('span','pill',x.concept+' '+x.strength.toFixed(2));p.onclick=()=>show(x.concept,false);t.append(p)}box.append(t)}
  if(c.evidence.length){box.append(el('h2',null,'Placed evidence'));for(const e of c.evidence){box.append(el('div','k',e.kind+' · '+e.key+' · '+e.degree));if(e.content&&e.content!==e.key)box.append(el('div','k mono',e.content))}}
  for(const g of Object.keys(c.facets)){box.append(el('h2',null,g));for(const f of c.facets[g]){box.append(el('div','k mono',f.role+' ('+f.confidence+') '+f.content))}}
  return c}
async function show(name,recenter){const c=await card(name);if(!c)return;if(recenter||!byId[c.id])await web(c.concept);else{root=c.id;alpha=Math.max(alpha,0.2)}}
async function search(){const q=$('q').value.trim();const l=$('list');l.replaceChildren();
  if(!q){$('lt').textContent='Most connected';const o=await api('/api/overview',{top:60});if(o)for(const h of o.hubs)add(l,h.concept,h.ties+' ties');return}
  $('lt').textContent='Matches';const r=await api('/api/search',{q,limit:40});if(r)for(const x of r.results)add(l,x.concept,x.match+(x.ties?' · '+x.ties:''))}
function add(l,name,sub){const r=el('div','row');r.append(el('span',null,name),el('small',null,sub));r.onclick=()=>show(name,true);l.append(r)}
let tm=0;$('q').addEventListener('input',()=>{clearTimeout(tm);tm=setTimeout(search,150)});
$('q').addEventListener('keydown',async ev=>{if(ev.key==='Enter'){const r=await api('/api/search',{q:$('q').value.trim(),limit:1});if(r&&r.results[0])show(r.results[0].concept,true)}});
$('depth').onchange=()=>{if(root)web(byId[root]?byId[root].concept:'')};
$('reset').onclick=async()=>{$('q').value='';await search();const o=await api('/api/overview',{top:1});if(o&&o.hubs[0])show(o.hubs[0].concept,true)};

function tbl(rows,heads){const t=el('table'),h=el('tr');for(const x of heads)h.append(el('th',null,x));t.append(h);for(const r of rows){const tr=el('tr');for(const v of r){const td=el('td',null,v===null||v===undefined?'–':String(v));tr.append(td)}t.append(tr)}return t}
function kv(obj){return tbl(Object.entries(obj).map(([k,v])=>[k,typeof v==='object'&&v!==null?JSON.stringify(v):v]),['field','value'])}
function flag(ok,yes,no){const s=el('span',ok?'ok':'off',ok?yes:no);return s}
function ago(s){if(s===null||s===undefined)return '–';if(s<90)return Math.round(s)+' s ago';if(s<5400)return Math.round(s/60)+' min ago';if(s<172800)return Math.round(s/3600)+' h ago';return Math.round(s/86400)+' days ago'}
async function renderPanel(t){const p=$('panel');p.replaceChildren(el('div','mono','loading…'));
  if(t==='ledger'){const d=await api('/api/ledger',{top:60});p.replaceChildren();if(!d||!d.present){p.append(el('h2',null,'Resolution ledger'),el('div',null,'No ledger research is on the crystals yet (it keeps its state there as hyp: facets once it has observed).'));return}
    p.append(el('h2',null,'Resolution ledger'),kv({'demands submitted':d.demands_submitted,'demands unsubmitted':d.demands_unsubmitted,'hypotheses held':d.hypotheses,'last emission':d.last_emission,'streams (next index)':d.streams,'word-class structure keys':d.lexical_structure_keys.join(', ')}),
      el('h2',null,'Observations per subject'),tbl(Object.entries(d.subjects),['subject','observations']),
      el('h2',null,'Paths under test (most evidence first)'),tbl(d.under_test.map(h=>[h.subject,h.path,h.crystal,h.observations,h.gain_per_obs,h.null_per_obs,h.blocks]),['subject','path','on crystal','obs','gain/obs','null/obs','blocks']));return}
  if(t==='strata'){const d=await api('/api/strata');p.replaceChildren();if(!d){p.append(el('div',null,'unavailable'));return}
    p.append(el('h2',null,'Link'));const l={};l['configured']=d.configured?'yes':'no';l['paired']=d.paired?'yes':'no';l['seeded']=d.seeded?'yes':'no';l['downlink (projection to phone)']=d.downlink_enabled?'on':'off';
    if(d.server){l['epoch']=d.server.epoch;l['owner']=d.server.owner||'–';l['handoff pending']=d.server.handoff_pending?'yes':'no';l['migrations']=d.server.migrations}
    if(d.client){l['client down applied']=d.client.down_applied;l['client holds a link key']=d.client.has_link_key?'yes':'no'}p.append(kv(l));
    if(d.server){p.append(el('h2',null,'Surfaces seen'),tbl(Object.keys(d.server.last_seen_seconds_ago).map(k=>[k,ago(d.server.last_seen_seconds_ago[k]),d.server.applied[k]]),['surface','last seen','records applied']))}
    p.append(el('h2',null,'Queues'),tbl([['uplink (phone → laptop)',d.up_outbox?d.up_outbox.pending:'–',d.up_outbox?d.up_outbox.overflow_dropped:'–'],['downlink (laptop → phone)',d.down_outbox?d.down_outbox.pending:'–',d.down_outbox?d.down_outbox.overflow_dropped:'–']],['queue','pending','dropped on overflow']));
    p.append(el('h2',null,'Processes'),tbl(Object.entries(d.processes).map(([k,v])=>[k,v===null?'no pid file':(v?'running':'not running')]),['process','state']));
    if(d.frame)p.append(el('h2',null,'Present frame (last saved '+ago(d.frame.saved_seconds_ago)+')'),kv({crest:d.frame.crest,action:d.frame.action,mode:d.frame.mode,readiness:d.frame.readiness,coherence:d.frame.coherence}));return}
  if(t==='pass'){const d=await api('/api/pass');p.replaceChildren();p.append(el('h2',null,'Crystal pass'));if(!d||!d.present){p.append(el('div',null,'No pass has been recorded yet (it runs on her saves and writes its report here).'));return}
    const r=d.report;p.append(kv(Object.fromEntries(Object.entries(r).map(([k,v])=>[k,v]))),el('h2',null,'Recent passes'));
    const keys=['seconds','links','facets','generalizations','generalizations_raised','sensory_crystals_created'];p.append(tbl(d.history.slice().reverse().map(h=>[new Date(h.at*1000).toLocaleString()].concat(keys.map(k=>h[k]))),['when'].concat(keys)))}}
document.querySelectorAll('#tabs button').forEach(b=>b.onclick=()=>{document.querySelectorAll('#tabs button').forEach(x=>x.classList.toggle('on',x===b));const t=b.dataset.t,web=t==='web';$('webmain').hidden=!web;$('panel').hidden=web;$('q').style.visibility=web?'visible':'hidden';$('depth').style.visibility=web?'visible':'hidden';$('reset').style.visibility=web?'visible':'hidden';if(!web)renderPanel(t);else size()});
size();search();requestAnimationFrame(step);
</script></body></html>
"""
