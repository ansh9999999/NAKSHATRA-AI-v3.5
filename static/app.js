function renderCatalysts(d){const items=(d&&d.items)||[];set('eventRisk',items.some(x=>x.importance==='HIGH')?'HIGH':'NORMAL');set('eventDisclaimer',d?.note||'Catalyst feed unavailable.');$('catalyst').innerHTML=items.length?items.slice(0,8).map(x=>{let tm='LATEST';if(x.time){try{tm=new Date(x.time).toLocaleString('en-IN',{timeZone:'Asia/Kolkata',day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'})+' IST'}catch(e){}}return `<div class="catalyst-row"><div class="event-main"><strong>${esc(x.title)}</strong><span class="event-time">🕒 ${esc(tm)} • ${esc(x.region||'')}</span><span class="effect-label">${esc((x.assets||[]).join(' / '))}</span><small>${esc(x.effect||'Confirm with live price/volume.')}</small></div><div class="event-right"><b>${esc(x.importance||'INFO')}</b><small>${esc(x.source||'DATA')}</small></div></div>`}).join(''):'<div class="catalyst-row"><small>No verified catalyst/news item available.</small></div>'}
async function loadCatalysts(){try{const r=await fetch(`/api/catalysts?symbol=${encodeURIComponent(symbol)}&_=${Date.now()}`,{cache:'no-store'});renderCatalysts(await r.json())}catch(e){set('eventRisk','DATA RISK');set('eventDisclaimer','Catalyst feed unavailable')}}


function renderPositionShift(x){x=x||{};set('shiftStatus',`● ${x.status||'NO DATA'}`);set('shiftBias',x.bias||'WAIT');paint('shiftBias',x.bias);set('shiftPhase',x.phase||'—');set('shiftStrength',`${x.strength||0}/100`);set('shiftAction',x.action||'WAIT');paint('shiftAction',x.bias);for(const k of ['1m','3m','5m','15m']){const v=x.windows?.[k]?.score;set('shift'+k.replace('m','m'),v==null?'—':`${v>0?'+':''}${v}`)}set('shiftNote',x.note||x.message||'Collecting live snapshots…')}
async function loadPositionShift(){try{const r=await fetch(`/api/position-shift?symbol=${encodeURIComponent(symbol)}&_=${Date.now()}`,{cache:'no-store'});renderPositionShift(await r.json())}catch(e){set('shiftStatus','● ERROR')}}

function renderMarketShift(x){x=x||{};set('marketShiftStatus',`● ${x.status||'NO DATA'}`);set('marketShiftBias',x.bias||'WAIT');set('marketShiftPhase',x.phase||'—');set('marketShiftStrength',`${x.strength??0}/100`);set('marketShiftAction',x.action||'WAIT');set('marketShift5Score',x.score_5m==null?'—':`${x.score_5m>0?'+':''}${x.score_5m}`);set('marketShift15Score',x.confirm_15m?.score==null?'—':`${x.confirm_15m.score>0?'+':''}${Math.round(x.confirm_15m.score)}`);set('marketShiftDelta',x.score_change==null?'—':`${x.score_change>0?'+':''}${Math.round(x.score_change)}`);set('marketShiftType',x.shift_type||'—');paint('marketShiftBias',x.bias);paint('marketShiftAction',x.action);set('marketShiftReason',(x.current_5m?.reasons||[]).slice(0,4).join(' • ')||x.error||'Waiting for valid 5M market data.');set('marketShiftNote',x.shift_detected?`Shift detected on latest 5M candle: ${x.detected_candle||'latest candle'}.`:(x.note||'No new regime shift detected.'))}
function renderOptionTradePlan(o){const p=o||{};if(p.status==='READY'){set('optionBuy',p.contract?`${p.action} • ${p.contract}`:(p.action||'OPTION BUY'));set('optionLtp',p.ltp!=null?fmt(p.ltp):'—');set('optionExpiry',p.expiry||'—');paint('optionBuy',p.option_type==='CALL'?'BUY':'SELL')}else{set('optionBuy','WAIT • NO OPTION BUY');set('optionLtp','—');set('optionExpiry','—');paint('optionBuy','WAIT')}}
const APP_VERSION='6.9.0';
let symbol='NIFTY50',busy=false;
const $=id=>document.getElementById(id);
const esc=v=>String(v??'—').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;');
const num=v=>{const n=Number(v);return Number.isFinite(n)?n:null};
const fmt=(v,d=2)=>{const n=num(v);return n===null?'—':n.toLocaleString('en-IN',{maximumFractionDigits:d})};
function set(id,v){if($(id))$(id).textContent=v??'—'}
function selectSymbol(s){symbol=s.toUpperCase();document.querySelectorAll('.symbol').forEach(b=>b.classList.toggle('active',b.dataset.symbol===symbol));load()}
function biasClass(v){const s=String(v||'').toUpperCase();return s.includes('BULL')||s.includes('BUY')?'bull':s.includes('BEAR')||s.includes('SELL')?'bear':s.includes('WAIT')||s.includes('SIDEWAYS')||s.includes('NEUTRAL')?'wait':''}
function paint(id,v){const el=$(id);if(el)el.className=(el.className||'').replace(/\b(bull|bear|wait)\b/g,'').trim()+' '+biasClass(v)}
function normalizeRows(o){
 const raw=Array.isArray(o?.rows)?o.rows:(Array.isArray(o?.atm_chain)?o.atm_chain:[]);
 const m=new Map();
 raw.forEach(r=>{
   const strike=num(r.strike??r.strike_price); if(strike===null)return;
   const x=m.get(strike)||{strike,ceLtp:null,ceOi:null,peLtp:null,peOi:null,ceDoi:null,peDoi:null,ceVol:null,peVol:null,atm:Boolean(r.atm)};
   const typ=String(r.type||r.option_type||'').toUpperCase();
   if(typ==='CALL'||typ==='CE'){x.ceLtp=num(r.ltp??r.call_ltp??r.ce_ltp);x.ceOi=num(r.oi??r.call_oi??r.ce_oi);x.ceDoi=num(r.oi_change??r.call_oi_change??r.ce_oi_change);x.ceVol=num(r.volume??r.call_volume??r.ce_volume)}
   else if(typ==='PUT'||typ==='PE'){x.peLtp=num(r.ltp??r.put_ltp??r.pe_ltp);x.peOi=num(r.oi??r.put_oi??r.pe_oi);x.peDoi=num(r.oi_change??r.put_oi_change??r.pe_oi_change);x.peVol=num(r.volume??r.put_volume??r.pe_volume)}
   else {x.ceLtp=num(r.call_ltp??r.ce_ltp??r.ce?.ltp);x.ceOi=num(r.call_oi??r.ce_oi??r.ce?.oi);x.peLtp=num(r.put_ltp??r.pe_ltp??r.pe?.ltp);x.peOi=num(r.put_oi??r.pe_oi??r.pe?.oi);x.ceDoi=num(r.call_oi_change??r.ce_oi_change??r.ce?.oi_change);x.peDoi=num(r.put_oi_change??r.pe_oi_change??r.pe?.oi_change);x.ceVol=num(r.call_volume??r.ce_volume??r.ce?.volume);x.peVol=num(r.put_volume??r.pe_volume??r.pe?.volume)}
   m.set(strike,x);
 });
 return [...m.values()].sort((a,b)=>a.strike-b.strike);
}
function calcOption(o,spot){
 const rows=normalizeRows(o); if(!rows.length)return {rows:[],status:String(o?.status||'NO DATA').toUpperCase(),view:'SIDEWAYS',topCalls:[],topPuts:[]};
 const atm=rows.find(r=>r.atm)?.strike??rows.reduce((a,r)=>Math.abs(r.strike-spot)<Math.abs(a.strike-spot)?r:a).strike;
 const callOi=rows.reduce((s,r)=>s+(r.ceOi||0),0),putOi=rows.reduce((s,r)=>s+(r.peOi||0),0),pcr=callOi?putOi/callOi:null; const callVol=rows.reduce((s,r)=>s+(r.ceVol||0),0),putVol=rows.reduce((s,r)=>s+(r.peVol||0),0),pcrVol=callVol?putVol/callVol:null;
 const support=(rows.filter(r=>r.strike<=atm&&r.peOi!=null).sort((a,b)=>(b.peOi||0)-(a.peOi||0))[0]||{}).strike??null;
 const resistance=(rows.filter(r=>r.strike>=atm&&r.ceOi!=null).sort((a,b)=>(b.ceOi||0)-(a.ceOi||0))[0]||{}).strike??null;
 let view=String(o.signal||'').toUpperCase(); view=view==='BUY'?'BULLISH':view==='SELL'?'BEARISH':'SIDEWAYS';
 if(!o.signal&&pcr!=null)view=pcr>=1.2?'BULLISH':pcr<=.75?'BEARISH':'SIDEWAYS';
 const byStrike=new Map(rows.map(r=>[r.strike,r]));
 const serverCalls=Array.isArray(o.top_call_oi)?o.top_call_oi:[],serverPuts=Array.isArray(o.top_put_oi)?o.top_put_oi:[];
 const topCalls=(serverCalls.length?serverCalls.map(r=>{const x=byStrike.get(num(r.strike))||{};return {...x,strike:num(r.strike),ceOi:num(r.oi??x.ceOi),ceLtp:num(r.ltp??x.ceLtp)}}):rows.filter(r=>r.ceOi!=null).sort((a,b)=>(b.ceOi||0)-(a.ceOi||0)).slice(0,5));
 const topPuts=(serverPuts.length?serverPuts.map(r=>{const x=byStrike.get(num(r.strike))||{};return {...x,strike:num(r.strike),peOi:num(r.oi??x.peOi),peLtp:num(r.ltp??x.peLtp)}}):rows.filter(r=>r.peOi!=null).sort((a,b)=>(b.peOi||0)-(a.peOi||0)).slice(0,5));
 return {rows,atm,pcr,pcrVol,callOi,putOi,callVol,putVol,support,resistance,maxPain:num(o.max_pain),expiry:o.expiry||'—',status:String(o.status||'OK').toUpperCase(),view,topCalls,topPuts};
}
function renderTradePlan(x,price){
 const p=x.trade_plan||{};
 const gamma=x.option_chain?.gamma_squeeze||{};
 let side=String(p.side||x.recommendation||'WAIT').toUpperCase();
 const px=num(price);
 // If the core AI is WAIT but a squeeze setup is forming, show a conditional
 // plan instead of blank fields. This tells the user what must happen first.
 if((side==='WAIT'||side==='NO DATA'||side==='NEUTRAL') && (gamma.side==='CALL'||gamma.side==='PUT')){
   const gside=gamma.side==='CALL'?'BUY CE':'BUY PE';
   set('entryZone',gamma.trigger||'Wait for trigger');
   set('stopLoss','Use trigger invalidation');
   set('tp1','After confirmation');set('tp2','Trail if momentum continues');set('tp3','—');set('rr','Not fixed before trigger');
   set('riskState',`${gside} • ONLY AFTER TRIGGER`);paint('riskState',gamma.side==='CALL'?'BULLISH':'BEARISH');
   return;
 }
 if(p.status==='READY'&&p.entry_zone){set('entryZone',p.entry_zone);set('stopLoss',fmt(p.stop_loss));set('tp1',fmt(p.target1));set('tp2',fmt(p.target2));set('tp3',fmt(p.target3));set('rr',p.risk_reward||'—');set('riskState',`${side} • ${p.when||p.basis||'AI risk model'}`);paint('riskState',side);return}
 const atr=num(p.atr??x.atr??x.technical?.atr??x.technical?.trend?.['5m']?.atr);
 if((side==='BUY'||side==='SELL')&&atr&&px){const risk=Math.max(1.2*atr,px*.0025),half=Math.max(.15*atr,px*.0005);set('entryZone',`${fmt(px-half)} – ${fmt(px+half)}`);if(side==='BUY'){set('stopLoss',fmt(px-risk));set('tp1',fmt(px+1.5*risk));set('tp2',fmt(px+2.5*risk));set('tp3',fmt(px+3.5*risk))}else{set('stopLoss',fmt(px+risk));set('tp1',fmt(px-1.5*risk));set('tp2',fmt(px-2.5*risk));set('tp3',fmt(px-3.5*risk))}set('rr','1 : 2.5');set('riskState',`${side} • ATR based`);paint('riskState',side);return}
 ['entryZone','stopLoss','tp1','tp2','tp3','rr'].forEach(id=>set(id,'—'));set('riskState','WAIT • No confirmed trade');paint('riskState','WAIT');
}
function renderGamma(g){
 const x=g||{};
 const risk=String(x.risk||'NO DATA').toUpperCase();
 const side=String(x.side||'NO CLEAR SIDE').toUpperCase();
 const status=String(x.status||'NO DATA').toUpperCase();
 set('gammaStatus',status==='OK'?(x.expiry_day?'● EXPIRY DAY':'● LIVE'):'● NO DATA');
 set('gammaRisk',risk==='HIGH'?'HIGH ALERT':risk==='ELEVATED'?'SETUP FORMING':risk==='WATCH'?'WATCH':risk==='LOW'?'WAIT':'NO DATA');
 paint('gammaRisk',risk==='HIGH'?'BULLISH':risk==='ELEVATED'?'WAIT':risk==='WATCH'?'WAIT':'WAIT');
 set('gammaSide',side);
 paint('gammaSide',side==='CALL'?'BULLISH':side==='PUT'?'BEARISH':'WAIT');
 set('gammaWindow',x.probable_window||'—');
 const c=x.confirmations, total=x.confirmation_total||5;
 set('gammaScore',c==null?'—':`${c}/${total}`);
 set('gammaTrigger',x.trigger||'Wait for live option-chain confirmation.');
 set('gammaReason',x.reason||'No squeeze condition confirmed.');
 set('gammaWarning',x.warning||'Wait for the trigger.');
}
function renderOption(o,price){
 const oc=calcOption(o,price||0);set('expiry',`Expiry ${oc.expiry}`);set('optionStatus',oc.status==='OK'?'● LIVE':'● NO DATA');set('pcrOi',fmt(o.pcr_oi_calc??oc.pcr,2));set('pcrVol',fmt(o.pcr_volume_calc??oc.pcrVol??o.volume_pcr??o.pcr_volume,2));set('ceVolume',fmt(o.call_volume_total??oc.callVol,0));set('peVolume',fmt(o.put_volume_total??oc.putVol,0));set('dayVolume',fmt(o.chain_total_volume??((oc.callVol||0)+(oc.putVol||0)),0));set('openInterest',fmt(o.chain_total_oi??((oc.callOi||0)+(oc.putOi||0)),0));set('atm',fmt(oc.atm,0));set('maxPain',fmt(oc.maxPain,0));set('support',fmt(oc.support??o.max_put_oi_support,0));set('resistance',fmt(oc.resistance??o.max_call_oi_resistance,0));set('optionView',oc.view);paint('optionView',oc.view);set('optionViewReason',o.reason||'OI positioning snapshot');$('optionView').className=biasClass(oc.view);
 const row=(r,i,type)=>`<tr><td>${i+1}</td><td>${fmt(r.strike,0)}</td><td>${fmt(type==='CE'?r.ceOi:r.peOi,0)}</td><td>${fmt(type==='CE'?r.ceLtp:r.peLtp,2)}</td><td>${fmt(type==='CE'?r.ceDoi:r.peDoi,0)}</td></tr>`;
 $('topCalls').innerHTML=oc.topCalls.map((r,i)=>row(r,i,'CE')).join('')||'<tr><td colspan="5">No call OI data</td></tr>';
 $('topPuts').innerHTML=oc.topPuts.map((r,i)=>row(r,i,'PE')).join('')||'<tr><td colspan="5">No put OI data</td></tr>';
 set('optionNote',oc.status==='OK'?`${oc.source||'Live'} expiry chain • Top 5 OI`:'Option chain unavailable — no stale signal');
 renderGamma(o.gamma_squeeze);
}
function renderParticipant(d){
 const fd=(d&&d.fii_dii&&d.fii_dii.rows)||[];
 const fii=fd.find(x=>String(x.category||'').toUpperCase().includes('FII'))||{};
 const dii=fd.find(x=>String(x.category||'').toUpperCase()==='DII')||{};
 set('fiiNet',fii.net_cr==null?'—':`${fii.net_cr>=0?'+':''}${fmt(fii.net_cr,0)} Cr`);
 set('diiNet',dii.net_cr==null?'—':`${dii.net_cr>=0?'+':''}${fmt(dii.net_cr,0)} Cr`);
 const vx=d.india_vix||{}; set('indiaVix',vx.value==null?'—':fmt(vx.value,2));
 const sent=d.sentiment||{}; set('positionSentiment',sent.bias||'—');paint('positionSentiment',sent.bias);paint('fiiNet',fii.net_cr>=0?'BULLISH':'BEARISH');paint('diiNet',dii.net_cr>=0?'BULLISH':'BEARISH');
 const score=num(sent.score); let impact='MIXED / DATA-DEPENDENT';
 if(score!=null) impact=score>=1?'Potential risk-on support':score<=-1?'Potential risk-off pressure':'Mixed positioning — watch first-hour confirmation';
 set('nextSessionImpact',impact); set('participantReason',(sent.reasons||[]).join(' • ')||sent.note||'NSE participant data unavailable');
 const hasParticipant=((d.participant_oi&&d.participant_oi.rows)||[]).length>0;const hasAny=(fd.length>0)||(vx.value!=null)||hasParticipant;set('participantStatus',d.status==='OK'?'● EOD DATA':hasAny?'● PARTIAL EOD':'● NO DATA');
 const oi=(d.participant_oi&&d.participant_oi.rows)||[];
 const rows=oi.map(r=>{const long=num(r.future_index_long),short=num(r.future_index_short);return {p:String(r.participant||'—').toUpperCase(),long,short,net:(long!=null&&short!=null?long-short:null),ceNet:(num(r.index_call_long)||0)-(num(r.index_call_short)||0),peNet:(num(r.index_put_long)||0)-(num(r.index_put_short)||0)}}).filter(x=>x.p&&x.p!=='—');
 $('participantRows').innerHTML=rows.length?rows.slice(0,8).map(x=>`<tr><td>${esc(x.p)}</td><td>${fmt(x.long,0)}</td><td>${fmt(x.short,0)}</td><td class="${x.net>=0?'bull':'bear'}">${x.net==null?'—':fmt(x.net,0)}</td><td class="${x.ceNet>=0?'bull':'bear'}">${fmt(x.ceNet,0)}</td><td class="${x.peNet>=0?'bull':'bear'}">${fmt(x.peNet,0)}</td></tr>`).join(''):'<tr><td colspan="6">NSE participant-wise OI unavailable or schema changed.</td></tr>';
}
async function loadNSEIntelligence(){try{const r=await fetch(`/api/nse-intelligence?symbol=${encodeURIComponent(symbol)}&_=${Date.now()}`,{cache:'no-store'});const d=await r.json();renderParticipant(d)}catch(e){set('participantStatus','● ERROR');set('nextSessionImpact','NSE participant feed unavailable')}}
async function loadOptions(){try{const r=await fetch(`/api/options?symbol=${encodeURIComponent(symbol)}&_=${Date.now()}`,{cache:'no-store'});const d=await r.json();if(d)renderOption(d, num($('price')?.textContent?.replace(/,/g,''))||0)}catch(e){set('optionStatus','● ERROR')}}

function renderFutures(d){const f=d?.futures||{},c=d?.combined||{};set('futureStatus',`● ${f.status||'NO DATA'}`);set('futureContract',f.contract||'—');set('futurePrice',fmt(f.price));set('futureOi',fmt(f.oi,0));set('futureVolume',fmt(f.volume,0));if(['NIFTY50','BANKNIFTY','NIFTYIT'].includes(symbol)){set('dayVolume',fmt(f.volume,0));set('openInterest',fmt(f.oi,0));}set('futureBasis',f.basis==null?'—':`${f.basis>=0?'+':''}${fmt(f.basis,2)}`);set('futureDoi',f.snapshot_oi_change==null?'WARMING':`${f.snapshot_oi_change>=0?'+':''}${fmt(f.snapshot_oi_change,0)}`);set('futureBuild',f.buildup||'NO DATA');paint('futureBuild',f.buildup);set('foCompare',c.view||'WAIT');set('foAction',c.action||'WAIT');paint('foCompare',c.view);paint('foAction',c.action);set('futureNote',f.note||f.reason||'Live futures data unavailable.')}
async function loadFutures(){try{const r=await fetch(`/api/futures?symbol=${encodeURIComponent(symbol)}&_=${Date.now()}`,{cache:'no-store'});renderFutures(await r.json())}catch(e){set('futureStatus','● ERROR')}}

function render(a){
 const x=a.analysis||{},t=a.ticker||{},o=x.option_chain||{},it=x.intraday_trend||{},ast=x.astrology||{},numx=x.numerology||{},sent=x.sentiment||{},ag=x.agreement_detail||{};
 const by={};(it.timeframes||[]).forEach(z=>by[z.timeframe]=z); const tr=x.technical?.trend||{}; const dt=x.derived_timeframes||{};
 const price=num(t.ltp??t.price??t.close??x.price); let perChange=num(t.percent_change??t.per_change??t.perChange??t.change_24h); if(perChange===null){const prev=num(t.previous_close??t.prev_close??t.close); const px=num(t.ltp??t.price); if(prev&&px&&Math.abs(px-prev)>0) perChange=((px-prev)/prev)*100;}
 set('marketSymbol',symbol==='NIFTY50'?'NIFTY 50':symbol.replace('CRUDEOIL','CRUDE OIL'));set('price',fmt(price));set('change',perChange===null?'1D change unavailable':`1D ${perChange>=0?'▲':'▼'} ${fmt(Math.abs(perChange))}%`);set('dayChange',perChange===null?'—':`${perChange>=0?'▲':'▼'} ${fmt(Math.abs(perChange))}%`);set('dayChangePct',t.change!=null?`${t.change>=0?'+':''}${fmt(t.change)}`:'—');paint('change',perChange>=0?'BULLISH':'BEARISH');paint('dayChange',perChange>=0?'BULLISH':'BEARISH');paint('dayChangePct',perChange>=0?'BULLISH':'BEARISH');set('dayHigh',fmt(t.high??x.day_high));set('dayLow',fmt(t.low??x.day_low));if(!['NIFTY50','BANKNIFTY'].includes(symbol)){set('dayVolume',fmt(t.volume,0));set('openInterest',fmt(t.oi??x.open_interest,0));}
 const decision=String(x.recommendation||x.signal||'WAIT').toUpperCase();set('decision',decision);paint('decision',decision);paint('whyDecision',decision);set('whyDecision',decision);const conf=num(x.confidence??x.overall_confidence);set('confidence',`Strength ${fmt(conf,0)}/100`);if($('confidenceBar')){$('confidenceBar').style.width=`${Math.max(0,Math.min(100,conf||0))}%`;$('confidenceBar').className=biasClass(decision)}
 set('agreementMini',`Agreement ${ag.final||x.agreement||'—'}`);set('agreementMini2',ag.final||x.agreement||'—');
 set('tf5',tr['5m']?.trend||by['5m']?.trend||dt['5m']?.trend||'UNKNOWN');set('tf15',tr['15m']?.trend||by['15m']?.trend||dt['15m']?.trend||'UNKNOWN');set('tf1h',tr['1h']?.trend||by['1h']?.trend||dt['1h']?.trend||'UNKNOWN');set('tf1d',tr['1d']?.trend||by['1d']?.trend||dt['1d']?.trend||'UNKNOWN');set('tf1w',tr['1w']?.trend||by['1w']?.trend||dt['1w']?.trend||'UNKNOWN');
 set('intra5',by['5m']?.trend||tr['5m']?.trend||dt['5m']?.trend||'UNKNOWN');set('intra15',by['15m']?.trend||tr['15m']?.trend||dt['15m']?.trend||'UNKNOWN');set('intra1h',by['1h']?.trend||tr['1h']?.trend||dt['1h']?.trend||'UNKNOWN');
 set('activityRegime','MARKET DATA');
 renderTradePlan(x,price);renderOptionTradePlan(a.option_trade||x.option_trade);renderPositionShift(a.position_shift);renderMarketShift(a.market_shift||x.market_shift);
 const fut=x.futures_intelligence||a.futures_intelligence||{}; const f=fut.futures||{}; const fc=fut.combined||{}; const ms=a.market_shift||x.market_shift||{}; const ps=a.position_shift||{}; set('foFutureBias',fc.futures_bias||((f.buildup||'').includes('LONG')?'BULLISH':(f.buildup||'').includes('SHORT')?'BEARISH':'NEUTRAL')); set('foOptionBias',fc.options_bias||o.signal||'—'); set('foMarketShift',ms.bias||'WAIT'); set('foPositionShift',ps.bias||'WAIT'); set('foDecisionView',fc.view||'WAIT'); set('foDecisionAction',fc.action||'WAIT'); paint('foFutureBias',fc.futures_bias);paint('foOptionBias',fc.options_bias||o.signal);paint('foMarketShift',ms.bias);paint('foPositionShift',ps.bias);paint('foDecisionView',fc.view);paint('foDecisionAction',fc.action); set('foDecisionStatus',fc.status||'PARTIAL'); set('foDecisionReason', ms.shift_detected ? `Market shift: ${ms.shift_type||'detected'} • ${ms.phase||'SHIFTING'}; require futures/options confirmation before CE/PE.` : (fc.view==='CONFLICT'?'Futures and options disagree → WAIT.':'Futures + options comparison updated from live snapshots.'));
 $('reasons').innerHTML=(x.reasons||[]).slice(0,6).map(r=>`<div>• ${esc(r)}</div>`).join('')||'<div>No high-quality reasons returned.</div>'; const tech=x.technical||{};set('moduleTechnical',tech.signal||'—');paint('moduleTechnical',tech.signal);set('moduleOption',o.signal||'—');paint('moduleOption',o.signal);set('moduleAstrology',ast.bias||'—');set('moduleAstrology2',ast.bias||'—');set('moduleNumerology',numx.bias||'—');set('moduleNumerology2',numx.bias||'—');set('trend',tr.overall_trend||it.overall||'—');paint('trend',tr.overall_trend||it.overall);['tf5','tf15','tf1h','tf1d','tf1w','intra5','intra15','intra1h'].forEach(id=>paint(id,$(id)?.textContent));
 $('metrics').innerHTML=[['EMA9',tr['5m']?.ema9],['EMA50',tr['5m']?.ema50],['EMA200',tr['5m']?.ema200],['RSI',tech.momentum?.rsi??x.rsi],['MACD',tech.momentum?.macd??x.macd],['ATR',x.atr??'—'],['Technical Score',tech.confidence??tech.score],['MTF Score',tr.total_score]].map(q=>`<div><small>${q[0]}</small><b>${fmt(q[1],4)}</b></div>`).join('');
 $('astroRows').innerHTML=[['Rashi Trend',ast.rashi_trend||ast.bias],['Nakshatra',ast.nakshatra_influence||ast.nakshatra],['Tithi',ast.tithi_impact||ast.tithi],['Yoga',ast.yoga],['Karana',ast.karana],['Planetary',ast.planetary_alignment],['Score',ast.score]].map(q=>`<div><span>${esc(q[0])}</span><b>${esc(q[1])}</b></div>`).join('');
 $('numRows').innerHTML=[['Life Path',numx.life_path],['Expression',numx.expression_number],['Day Vibration',numx.day_vibration],['Market Number',numx.market_number],['Score',numx.score]].map(q=>`<div><span>${esc(q[0])}</span><b>${esc(q[1])}</b></div>`).join('');
 const sb=sent.bias||sent.signal||sent.overall||'NOT CONNECTED';set('sentimentBias',sb);$('sentimentRows').innerHTML=[['Social Sentiment',sent.social_sentiment||'NOT CONNECTED'],['News Sentiment',sent.news_sentiment||'NOT CONNECTED'],['Fear/Greed',sent.fear_greed||'NOT CONNECTED'],['Overall Score',sent.score??'—']].map(q=>`<div><span>${esc(q[0])}</span><b>${esc(q[1])}</b></div>`).join('');
 renderOption(o,price);set('agreeTechnical',ag.technical||tech.signal||'—');paint('agreeTechnical',ag.technical||tech.signal);set('agreeOptions',ag.option_chain||o.signal||'—');paint('agreeOptions',ag.option_chain||o.signal);set('agreeAstrology',ag.astrology||ast.bias||'—');paint('agreeAstrology',ag.astrology||ast.bias);set('agreeNumerology',ag.numerology||numx.bias||'—');paint('agreeNumerology',ag.numerology||numx.bias);set('agreeFinal',ag.final||x.agreement||'—');paint('agreeFinal',ag.final||x.agreement);
 set('status','● KOTAK LIVE');set('dataState','● LIVE');set('updateStatus',`Updated ${new Date().toLocaleTimeString()}`);
}
async function load(){
 if(busy)return;
 busy=true;
 set('dataState','● CONNECTING');
 set('status','● KOTAK CONNECTING');
 try{
  const r=await fetch(`/api/live?symbol=${encodeURIComponent(symbol)}&_=${Date.now()}`,{cache:'no-store',headers:{'Cache-Control':'no-cache'}});
  if(!r.ok) throw new Error(`HTTP ${r.status}`);
  const d=await r.json();
  if(d && (d.ticker || d.analysis)){
    render(d); loadOptions(); loadFutures(); loadNSEIntelligence(); loadCatalysts();
    if(d.status!=='OK' && d.analysis?.status!=='OK'){
      set('status','● DATA RISK');
      set('dataState','● DATA RISK');
      set('updateStatus',d.analysis?.message||'Partial market data');
    }
  }else{
    set('status','● DATA RISK');
    set('dataState','● DATA RISK');
    set('updateStatus',d?.message||'No market data returned');
  }
 }catch(e){
  set('status','● OFFLINE');
  set('dataState','● OFFLINE');
  set('updateStatus',`Connection error: ${e.message||'API unavailable'}`);
 }finally{busy=false}
}

async function scanner(){try{const r=await fetch('/api/scanner?_='+Date.now(),{cache:'no-store'});const d=await r.json();const arr=Array.isArray(d)?d:(d.markets||[]);$('scanner').innerHTML=arr.map(x=>`<div class="scanner-row"><b>${esc(x.symbol)}</b><span>${esc(x.signal||x.recommendation||'WAIT')}</span><small>${esc(x.strength??x.confidence??'—')}</small></div>`).join('')||'No scanner data'}catch(e){$('scanner').textContent='Scanner unavailable'}}
async function trades(){try{const r=await fetch('/api/history?_='+Date.now(),{cache:'no-store'});const d=await r.json();const arr=Array.isArray(d)?d:(d.history||[]);$('trades').innerHTML=(arr||[]).slice(-8).reverse().map(x=>`<tr><td>${esc(x.symbol)}</td><td>${esc(x.side)}</td><td>${esc(fmt(x.entry))}</td><td>${esc(fmt(x.pnl))}</td><td>${esc(x.status)}</td></tr>`).join('')||'<tr><td colspan="5">No trades yet</td></tr>';$('equitySummary').textContent=arr?.length?`${arr.length} recorded trades`:'No recorded trades'}catch(e){$('equitySummary').textContent='Trade history unavailable'}}
document.querySelectorAll('.symbol').forEach(b=>b.onclick=()=>selectSymbol(b.dataset.symbol));$('refreshBtn')?.addEventListener('click',()=>{load();scanner();trades();loadOptions();loadNSEIntelligence();loadCatalysts()});load();scanner();trades();loadOptions();loadNSEIntelligence();loadCatalysts();loadPositionShift();setInterval(()=>{load();loadOptions();loadPositionShift()},15000);setInterval(()=>{scanner();loadNSEIntelligence()},60000);
