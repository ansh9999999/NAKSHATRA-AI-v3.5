const APP_VERSION='INDIA-3.0-FAST';
let symbol='NIFTY50';
let selectedDisplayName='NIFTY 50';
const $=id=>document.getElementById(id);
const esc=v=>String(v??'—').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;');
const num=v=>{const n=Number(v);return Number.isFinite(n)?n:null};
const fmt=(v,d=2)=>{const n=num(v);return n===null?'—':n.toLocaleString('en-IN',{maximumFractionDigits:d})};
function set(id,v){if($(id))$(id).textContent=v??'—'}
function paint(id,v){const el=$(id);if(!el)return;const s=String(v||'').toUpperCase();el.classList.remove('bull','bear','wait');if(s.includes('BULL')||s.includes('BUY'))el.classList.add('bull');else if(s.includes('BEAR')||s.includes('SELL'))el.classList.add('bear');else if(s.includes('WAIT')||s.includes('SIDEWAYS')||s.includes('NEUTRAL'))el.classList.add('wait')}
async function selectSymbol(s,name){
 const requested=String(s).toUpperCase(); symbol=requested; selectedDisplayName=name||symbol;
 document.querySelectorAll('.symbol').forEach(b=>b.classList.toggle('active',b.dataset.symbol===symbol));
 set('marketSymbol',selectedDisplayName); set('dataState','● FETCHING QUOTE');
 await loadQuote(requested);
 if(symbol===requested)loadAll(requested);
}
function renderQuote(a,requested){
 if(requested && symbol!==requested)return;
 const t=a?.ticker||{}; const price=t.ltp??t.price??t.close; const ch=t.percent_change??t.per_change??t.change;
 set('marketSymbol',selectedDisplayName); set('price',fmt(price)); set('change',ch==null?'—':`${num(ch)>=0?'▲':'▼'} ${fmt(Math.abs(ch))}%`);
 set('dayChange',ch==null?'—':`${num(ch)>=0?'▲':'▼'} ${fmt(Math.abs(ch))}%`); set('dayChangePct',t.change==null?'—':fmt(t.change));
 set('dayHigh',fmt(t.high)); set('dayLow',fmt(t.low)); set('dayVolume',fmt(t.volume,0)); set('openInterest',fmt(t.oi,0));
 set('dataState',a?.status==='OK'?'● LIVE • KOTAK NEO':'● QUOTE READY');
}
function renderCore(a){
 if(!a || a.status==='LOADING' || a.status==='ERROR') return;
 if(a.symbol && String(a.symbol).toUpperCase()!==String(symbol).toUpperCase()) return;
 const t=a?.ticker||{}, x=a?.analysis||{}; const price=t.ltp??t.price??t.close??x.price; const ch=t.percent_change??t.per_change??t.change;
 set('marketSymbol',selectedDisplayName); set('price',fmt(price)); set('change',ch==null?'—':`${num(ch)>=0?'▲':'▼'} ${fmt(Math.abs(ch))}%`); set('dayChange',ch==null?'—':`${num(ch)>=0?'▲':'▼'} ${fmt(Math.abs(ch))}%`); set('dayChangePct',t.change==null?'—':fmt(t.change)); set('dayHigh',fmt(t.high)); set('dayLow',fmt(t.low)); set('dayVolume',fmt(t.volume,0)); set('openInterest',fmt(t.oi,0));
 set('dataState',a?.status==='OK'?'● LIVE • KOTAK NEO':(a?.status||'LOADING')); paint('dataState',a?.status==='OK'?'BULLISH':'WAIT');
 const decision=String(x.recommendation||x.signal||'WAIT').toUpperCase();set('decision',decision);paint('decision',decision);const conf=num(x.confidence??x.overall_confidence);set('confidence',conf==null?'Strength —':`Strength ${fmt(conf,0)}/100`);if($('confidenceBar'))$('confidenceBar').style.width=`${Math.max(0,Math.min(100,conf||0))}%`;
 const tr=x.derived_timeframes||{};['5m','15m','1h','1d','1w'].forEach(tf=>set('tf'+({'5m':'5','15m':'15','1h':'1h','1d':'1d','1w':'1w'}[tf]),tr[tf]?.trend||'UNKNOWN'));
 set('intra5',tr['5m']?.trend||'UNKNOWN');set('intra15',tr['15m']?.trend||'UNKNOWN');set('intra1h',tr['1h']?.trend||'UNKNOWN');
 set('agreementMini',x.agreement||x.agreement_detail?.final||'—');set('agreementMini2',x.agreement||x.agreement_detail?.final||'—');
 set('moduleTechnical',x.technical?.signal||x.signal||'—');set('moduleOption',x.option_chain?.signal||'—');set('moduleAstrology',x.astrology?.signal||'—');set('moduleAstrology2',x.astrology?.signal||'—');set('moduleNumerology',x.numerology?.signal||'—');set('moduleNumerology2',x.numerology?.signal||'—');
 set('agreeTechnical',x.technical?.signal||'—');set('agreeOptions',x.option_chain?.signal||'—');set('agreeAstrology',x.astrology?.signal||'—');set('agreeNumerology',x.numerology?.signal||'—');set('agreeFinal',x.agreement_detail?.final||x.agreement||decision);
 const reasons=x.reasons||x.reason||x.agreement_detail?.reasons||[];const arr=Array.isArray(reasons)?reasons:[String(reasons)];if($('reasons'))$('reasons').innerHTML=arr.slice(0,8).map(r=>`<div>${esc(r)}</div>`).join('')||'<div>Waiting for complete market data.</div>';
 renderTradePlan(x,price);renderOptionTradePlan(a?.option_trade||x.option_trade);renderPositionShift(a?.position_shift);renderMarketShift(a?.market_shift||x.market_shift);renderFutures(x.futures_intelligence||a?.futures_intelligence);
}
function renderTradePlan(x,price){const p=x.trade_plan||{};const side=String(p.side||x.recommendation||x.signal||'WAIT').toUpperCase();if(p.entry_zone){set('entryZone',p.entry_zone);set('stopLoss',fmt(p.stop_loss));set('tp1',fmt(p.target1));set('tp2',fmt(p.target2));set('tp3',fmt(p.target3));set('rr',p.risk_reward||'—')}else{['entryZone','stopLoss','tp1','tp2','tp3','rr'].forEach(id=>set(id,'—'))}set('riskState',side==='BUY'||side==='SELL'?side:'WAIT');paint('riskState',side)}
function renderOptionTradePlan(p){p=p||{};set('optionBuy',p.status==='READY'?`${p.action||'BUY'} • ${p.contract||''}`:'WAIT • NO OPTION BUY');set('optionLtp',p.ltp==null?'—':fmt(p.ltp));set('optionExpiry',p.expiry||'—');paint('optionBuy',p.status==='READY'?'BUY':'WAIT')}
function renderPositionShift(x){x=x||{};set('shiftStatus',`● ${x.status||'NO DATA'}`);set('shiftBias',x.bias||'WAIT');set('shiftPhase',x.phase||'—');set('shiftStrength',`${x.strength||0}/100`);set('shiftAction',x.action||'WAIT');set('shiftNote',x.note||x.message||'Collecting snapshots…')}
function renderMarketShift(x){x=x||{};set('marketShiftStatus',`● ${x.status||'NO DATA'}`);set('marketShiftBias',x.bias||'WAIT');set('marketShiftPhase',x.phase||'—');set('marketShiftStrength',`${x.strength??0}/100`);set('marketShiftAction',x.action||'WAIT');set('marketShift5Score',x.score_5m==null?'—':x.score_5m);set('marketShift15Score',x.confirm_15m?.score==null?'—':Math.round(x.confirm_15m.score));set('marketShiftDelta',x.score_change==null?'—':Math.round(x.score_change));set('marketShiftType',x.shift_type||'—');set('marketShiftReason',(x.current_5m?.reasons||[]).join(' • ')||x.error||'Waiting for valid 5M data.');set('marketShiftNote',x.note||'No new regime shift detected.')}
function renderFutures(d){const f=d?.futures||{},c=d?.combined||{};set('futureStatus',`● ${f.status||'NO DATA'}`);set('futureContract',f.contract||'—');set('futurePrice',fmt(f.price));set('futureOi',fmt(f.oi,0));set('futureVolume',fmt(f.volume,0));set('futureBasis',f.basis==null?'—':fmt(f.basis,2));set('futureDoi',f.snapshot_oi_change==null?'WARMING':fmt(f.snapshot_oi_change,0));set('futureBuild',f.buildup||'NO DATA');set('foCompare',c.view||'WAIT');set('foAction',c.action||'WAIT');set('futureNote',f.note||f.reason||'Kotak Neo futures data unavailable.')}
function renderOption(o,price){o=o||{};set('expiry',o.expiry?`Expiry ${o.expiry}`:'Expiry —');set('optionStatus',o.status==='OK'?'● LIVE':'● NO DATA');set('pcrOi',fmt(o.pcr_oi_calc??o.pcr,2));set('pcrVol',fmt(o.pcr_volume_calc??o.volume_pcr,2));set('ceVolume',fmt(o.call_volume,0));set('peVolume',fmt(o.put_volume,0));set('atm',fmt(o.atm_strike,0));set('maxPain',fmt(o.max_pain,0));set('support',fmt(o.max_put_oi_support,0));set('resistance',fmt(o.max_call_oi_resistance,0));set('optionView',o.signal||'SIDEWAYS');set('optionViewReason',o.reason||'NSE option-chain data');set('optionNote',o.status==='OK'?`${o.source||'NSE'} • ${o.row_count||0} rows`:'Option chain unavailable')}
function renderNse(d){const rows=d?.fii_dii?.rows||[];const fii=rows.find(x=>String(x.category||'').toUpperCase().includes('FII'))||{};const dii=rows.find(x=>String(x.category||'').toUpperCase()==='DII')||{};set('fiiNet',fii.net_cr==null?'—':`${fii.net_cr>=0?'+':''}${fmt(fii.net_cr,0)} Cr`);set('diiNet',dii.net_cr==null?'—':`${dii.net_cr>=0?'+':''}${fmt(dii.net_cr,0)} Cr`);set('indiaVix',fmt(d?.india_vix?.value,2));set('positionSentiment',d?.sentiment?.bias||'—');set('participantStatus',d?.status==='OK'?'● EOD DATA':'● PARTIAL / NO DATA');set('participantReason',d?.sentiment?.note||'NSE participant data is EOD, not live order flow.');}
async function getJson(url,options={}){const r=await fetch(url,{cache:'no-store',...options});return await r.json()}
async function loadQuote(requested=symbol){try{const d=await getJson(`/api/quote?symbol=${encodeURIComponent(requested)}&_=${Date.now()}`);if(symbol===requested)renderQuote(d,requested);return d}catch(e){return null}}
async function load(requested=symbol){try{const d=await getJson(`/api/live?symbol=${encodeURIComponent(requested)}&_=${Date.now()}`);if(symbol!==requested)return;if(d?.status==='OK')renderCore(d);else if(d?.status==='LOADING')set('dataState','● ANALYSIS REFRESHING • QUOTE LIVE')}catch(e){if(symbol===requested)set('dataState','● QUOTE RETRYING')}}
async function loadOptions(requested=symbol){try{const d=await getJson(`/api/options?symbol=${encodeURIComponent(requested)}&_=${Date.now()}`);if(symbol===requested)renderOption(d,num($('price')?.textContent?.replaceAll(',','')))}catch(e){if(symbol===requested)set('optionStatus','● ERROR')}}
async function loadFutures(requested=symbol){try{const d=await getJson(`/api/futures?symbol=${encodeURIComponent(requested)}&_=${Date.now()}`);if(symbol===requested)renderFutures(d)}catch(e){if(symbol===requested)set('futureStatus','● ERROR')}}
async function loadNse(requested=symbol){try{const d=await getJson(`/api/nse-intelligence?symbol=${encodeURIComponent(requested)}&_=${Date.now()}`);if(symbol===requested)renderNse(d)}catch(e){if(symbol===requested)set('participantStatus','● ERROR')}}
async function loadShift(requested=symbol){try{const [p,m]=await Promise.all([getJson(`/api/position-shift?symbol=${encodeURIComponent(requested)}&_=${Date.now()}`),getJson(`/api/market-shift?symbol=${encodeURIComponent(requested)}&_=${Date.now()}`)]);if(symbol===requested){renderPositionShift(p);renderMarketShift(m)}}catch(e){}}
async function loadCatalysts(requested=symbol){try{const d=await getJson(`/api/catalysts?symbol=${encodeURIComponent(requested)}&_=${Date.now()}`);if(symbol!==requested)return;set('eventRisk',d.items?.length?'NORMAL':'NO DATA');set('eventDisclaimer',d.note||'Verified catalyst feed only.');if($('catalyst'))$('catalyst').innerHTML=(d.items||[]).slice(0,8).map(x=>`<div class=\"catalyst-row\"><strong>${esc(x.title)}</strong><small>${esc(x.effect||'Confirm with live market data.')}</small></div>`).join('')||'<div class=\"catalyst-row\">No verified catalyst available.</div>'}catch(e){}}
async function loadAll(requested=symbol){await Promise.allSettled([load(requested),loadOptions(requested),loadFutures(requested),loadNse(requested),loadShift(requested),loadCatalysts(requested)])}
let equitySearchTimer=null;
let equitySearchSeq=0;
let equitySearchController=null;
async function searchEquitiesUI(q){
 const box=$('equityResults'); if(!box)return;
 q=String(q||'').trim();
 const seq=++equitySearchSeq;
 if(equitySearchController) equitySearchController.abort();
 if(q.length<2){box.style.display='none';box.innerHTML='';return;}
 equitySearchController=new AbortController();
 box.style.display='block'; box.innerHTML='<div class="equity-result"><small>Searching…</small></div>';
 try{
   const d=await getJson(`/api/equity-search?q=${encodeURIComponent(q)}&limit=12&_=${Date.now()}`,{signal:equitySearchController.signal});
   if(seq!==equitySearchSeq)return;
   const current=String($('equitySearch')?.value||'').trim();
   if(current!==q)return;
   const rows=d?.results||[];
   box.innerHTML=rows.length?rows.map((r,i)=>`<div class="equity-result" data-i="${i}"><span><b>${esc(r.trading_symbol||r.symbol||'—')}</b><small>${esc(r.name||'')}</small></span><span class="equity-exchange">${esc(r.exchange||r.segment||'')}</span></div>`).join(''):'<div class="equity-result"><small>No matching equity found.</small></div>';
   box.querySelectorAll('.equity-result[data-i]').forEach(el=>el.addEventListener('click',async()=>{
      const r=rows[Number(el.dataset.i)]; if(!r)return;
      const nextSymbol=String(r.symbol||'').toUpperCase(); if(!nextSymbol)return;
      symbol=nextSymbol; selectedDisplayName=r.name||r.trading_symbol||nextSymbol;
      document.querySelectorAll('.symbol').forEach(b=>b.classList.remove('active'));
      set('marketSymbol',selectedDisplayName); set('dataState','● REGISTERING • KOTAK NEO');
      box.style.display='none'; if($('equitySearch'))$('equitySearch').value=''; equitySearchSeq++;
      if(equitySearchController)equitySearchController.abort();
      try{await getJson(`/api/equity-register?symbol=${encodeURIComponent(nextSymbol)}&_=${Date.now()}`)}catch(e){}
      if(symbol!==nextSymbol)return; await loadQuote(nextSymbol);
      if(symbol===nextSymbol)loadAll(nextSymbol);
   }));
 }catch(e){
   if(e?.name==='AbortError')return;
   if(seq!==equitySearchSeq)return;
   box.innerHTML='<div class="equity-result"><small>Search unavailable. Check Kotak Neo connection.</small></div>';
 }
}
async function loadAll(){
 const tasks=[load(),loadOptions(),loadFutures(),loadNse(),loadShift(),loadCatalysts()];
 await Promise.allSettled(tasks);
}
document.addEventListener('DOMContentLoaded',()=>{
 document.querySelectorAll('.symbol').forEach(btn=>btn.addEventListener('click',()=>selectSymbol(btn.dataset.symbol,btn.textContent.trim())));
 const es=$('equitySearch');
 if(es) es.addEventListener('input',()=>{clearTimeout(equitySearchTimer);equitySearchTimer=setTimeout(()=>searchEquitiesUI(es.value),220)});
 loadQuote('NIFTY50').then(()=>loadAll('NIFTY50'));setInterval(()=>load(symbol),15000);setInterval(()=>loadOptions(symbol),30000);setInterval(()=>loadFutures(symbol),30000);setInterval(()=>loadNse(symbol),120000);
});
