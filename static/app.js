const APP_VERSION='INDIA-2.0';
let symbol='NIFTY50';
let selectedDisplayName='NIFTY 50';
const $=id=>document.getElementById(id);
const esc=v=>String(v??'—').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;');
const num=v=>{const n=Number(v);return Number.isFinite(n)?n:null};
const fmt=(v,d=2)=>{const n=num(v);return n===null?'—':n.toLocaleString('en-IN',{maximumFractionDigits:d})};
function set(id,v){if($(id))$(id).textContent=v??'—'}
function paint(id,v){const el=$(id);if(!el)return;const s=String(v||'').toUpperCase();el.classList.remove('bull','bear','wait');if(s.includes('BULL')||s.includes('BUY'))el.classList.add('bull');else if(s.includes('BEAR')||s.includes('SELL'))el.classList.add('bear');else if(s.includes('WAIT')||s.includes('SIDEWAYS')||s.includes('NEUTRAL'))el.classList.add('wait')}
let viewSeq=0;
const requestControllers=new Set();
function beginView(){
 viewSeq++;
 for(const c of requestControllers){try{c.abort()}catch(e){}}
 requestControllers.clear();
 return viewSeq;
}
function isCurrent(seq,target){return seq===viewSeq && target===symbol}
function controller(){
 const c=new AbortController();
 requestControllers.add(c);
 return c;
}
async function getJson(url,options={}){
 const c=options.signal?null:controller();
 try{
  const r=await fetch(url,{cache:'no-store',...options,signal:options.signal||c.signal});
  return await r.json();
 }finally{
  if(c)requestControllers.delete(c);
 }
}
function selectSymbol(s,name){
 symbol=String(s).toUpperCase();
 selectedDisplayName=name||symbol;
 document.querySelectorAll('.symbol').forEach(b=>b.classList.toggle('active',b.dataset.symbol===symbol));
 set('marketSymbol',selectedDisplayName);
 set('dataState','● LOADING');
 const seq=beginView();
 loadAll(seq,symbol);
}
function renderQuote(q,target){
 if(!q||!isCurrent(viewSeq,target))return;
 const t=q.ticker||{};
 const price=t.ltp??t.price??t.close;
 const ch=t.percent_change??t.per_change??t.change;
 if(price!=null)set('price',fmt(price));
 if(ch!=null){
  set('change',`${num(ch)>=0?'▲':'▼'} ${fmt(Math.abs(ch))}%`);
  set('dayChange',`${num(ch)>=0?'▲':'▼'} ${fmt(Math.abs(ch))}%`);
 }
 if(t.high!=null)set('dayHigh',fmt(t.high));
 if(t.low!=null)set('dayLow',fmt(t.low));
}
async function load(seq=viewSeq,target=symbol){
 try{
  const d=await getJson(`/api/live?symbol=${encodeURIComponent(target)}&_=${Date.now()}`);
  if(!isCurrent(seq,target))return;
  if(d?.status==='OK')renderCore(d);
  else if(d?.status==='LOADING'){
   set('dataState','● REFRESHING • KOTAK NEO');
   try{renderQuote(await getJson(`/api/quote?symbol=${encodeURIComponent(target)}&_=${Date.now()}`),target)}catch(e){}
  }
 }catch(e){
  if(isCurrent(seq,target))set('dataState','● LAST DATA • CONNECTION RETRYING');
 }
}
async function loadOptions(seq=viewSeq,target=symbol){
 try{
  const d=await getJson(`/api/options?symbol=${encodeURIComponent(target)}&_=${Date.now()}`);
  if(isCurrent(seq,target))renderOption(d,num($('price')?.textContent?.replaceAll(',','')));
 }catch(e){if(isCurrent(seq,target))set('optionStatus','● ERROR')}
}
async function loadFutures(seq=viewSeq,target=symbol){
 try{
  const d=await getJson(`/api/futures?symbol=${encodeURIComponent(target)}&_=${Date.now()}`);
  if(isCurrent(seq,target))renderFutures(d);
 }catch(e){if(isCurrent(seq,target))set('futureStatus','● ERROR')}
}
async function loadNse(seq=viewSeq,target=symbol){
 try{
  const d=await getJson(`/api/nse-intelligence?symbol=${encodeURIComponent(target)}&_=${Date.now()}`);
  if(isCurrent(seq,target))renderNse(d);
 }catch(e){if(isCurrent(seq,target))set('participantStatus','● ERROR')}
}
async function loadShift(seq=viewSeq,target=symbol){
 try{
  const [p,m]=await Promise.all([
   getJson(`/api/position-shift?symbol=${encodeURIComponent(target)}&_=${Date.now()}`),
   getJson(`/api/market-shift?symbol=${encodeURIComponent(target)}&_=${Date.now()}`)
  ]);
  if(isCurrent(seq,target)){renderPositionShift(p);renderMarketShift(m)}
 }catch(e){}
}
async function loadCatalysts(seq=viewSeq,target=symbol){
 try{
  const d=await getJson(`/api/catalysts?symbol=${encodeURIComponent(target)}&_=${Date.now()}`);
  if(!isCurrent(seq,target))return;
  set('eventRisk',d.items?.length?'NORMAL':'NO DATA');
  set('eventDisclaimer',d.note||'Verified catalyst feed only.');
  if($('catalyst'))$('catalyst').innerHTML=(d.items||[]).slice(0,8).map(x=>`<div class="catalyst-row"><strong>${esc(x.title)}</strong><small>${esc(x.effect||'Confirm with live market data.')}</small></div>`).join('')||'<div class="catalyst-row">No verified catalyst available.</div>';
 }catch(e){}
}
let equitySearchTimer=null;
let equitySearchSeq=0;
let equitySearchController=null;
async function searchEquitiesUI(q){
 const box=$('equityResults');if(!box)return;
 q=String(q||'').trim();
 const seq=++equitySearchSeq;
 if(equitySearchController){try{equitySearchController.abort()}catch(e){}}
 if(q.length<2){box.style.display='none';box.innerHTML='';return;}
 equitySearchController=new AbortController();
 box.style.display='block';
 box.innerHTML='<div class="equity-result"><small>Searching…</small></div>';
 try{
  const d=await getJson(`/api/equity-search?q=${encodeURIComponent(q)}&limit=12&_=${Date.now()}`,{signal:equitySearchController.signal});
  if(seq!==equitySearchSeq)return;
  if(String($('equitySearch')?.value||'').trim()!==q)return;
  const rows=d?.results||[];
  box.innerHTML=rows.length
   ?rows.map((r,i)=>`<div class="equity-result" data-i="${i}"><span><b>${esc(r.trading_symbol||r.symbol||'—')}</b><small>${esc(r.name||'')}</small></span><span class="equity-exchange">${esc(r.exchange||r.segment||'')}</span></div>`).join('')
   :'<div class="equity-result"><small>No matching equity found.</small></div>';
  box.querySelectorAll('.equity-result[data-i]').forEach(el=>el.addEventListener('click',()=>{
   const r=rows[Number(el.dataset.i)];if(!r)return;
   const nextSymbol=String(r.symbol||'').toUpperCase();if(!nextSymbol)return;
   symbol=nextSymbol;
   selectedDisplayName=r.name||r.trading_symbol||nextSymbol;
   document.querySelectorAll('.symbol').forEach(b=>b.classList.remove('active'));
   set('marketSymbol',selectedDisplayName);
   set('dataState','● LOADING');
   box.style.display='none';
   if($('equitySearch'))$('equitySearch').value='';
   equitySearchSeq++;
   if(equitySearchController){try{equitySearchController.abort()}catch(e){}}
   const nextSeq=beginView();
   loadAll(nextSeq,nextSymbol);
  }));
 }catch(e){
  if(e?.name==='AbortError'||seq!==equitySearchSeq)return;
  box.innerHTML='<div class="equity-result"><small>Search unavailable. Check Kotak Neo connection.</small></div>';
 }
}
async function loadAll(seq=viewSeq,target=symbol){
 await Promise.allSettled([
  load(seq,target),
  loadOptions(seq,target),
  loadFutures(seq,target),
  loadNse(seq,target),
  loadShift(seq,target),
  loadCatalysts(seq,target)
 ]);
}
document.addEventListener('DOMContentLoaded',()=>{
 document.querySelectorAll('.symbol').forEach(btn=>btn.addEventListener('click',()=>selectSymbol(btn.dataset.symbol,btn.textContent.trim())));
 const es=$('equitySearch');
 if(es)es.addEventListener('input',()=>{clearTimeout(equitySearchTimer);equitySearchTimer=setTimeout(()=>searchEquitiesUI(es.value),180)});
 const initialSeq=beginView();
 loadAll(initialSeq,symbol);
 setInterval(()=>{const seq=viewSeq;load(seq,symbol)},15000);
 setInterval(()=>{const seq=viewSeq;loadOptions(seq,symbol);loadFutures(seq,symbol)},30000);
 setInterval(()=>{const seq=viewSeq;loadNse(seq,symbol)},120000);
});
