const APP_VERSION='INDIA-3.0';
let symbol='NIFTY50';
let selectedDisplayName='NIFTY 50';
let requestGeneration=0;
let equitySearchTimer=null;
let equitySearchSeq=0;
let equitySearchController=null;
const $=id=>document.getElementById(id);
const esc=v=>String(v??'—').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;');
const num=v=>{const n=Number(v);return Number.isFinite(n)?n:null};
const fmt=(v,d=2)=>{const n=num(v);return n===null?'—':n.toLocaleString('en-IN',{maximumFractionDigits:d})};
function set(id,v){if($(id))$(id).textContent=v??'—'}
function paint(id,v){const el=$(id);if(!el)return;const s=String(v||'').toUpperCase();el.classList.remove('bull','bear','wait');if(s.includes('BULL')||s.includes('BUY'))el.classList.add('bull');else if(s.includes('BEAR')||s.includes('SELL'))el.classList.add('bear');else if(s.includes('WAIT')||s.includes('SIDEWAYS')||s.includes('NEUTRAL'))el.classList.add('wait')}
function isCurrent(gen, expected){return gen===requestGeneration && (!expected || String(expected).toUpperCase()===String(symbol).toUpperCase())}
async function getJson(url,options={}){const r=await fetch(url,{cache:'no-store',...options});let d;try{d=await r.json()}catch{throw new Error(`HTTP ${r.status}`)};if(!r.ok)throw new Error(d?.error||`HTTP ${r.status}`);return d}

function selectSymbol(s,name){
 symbol=String(s).toUpperCase();
 selectedDisplayName=name||symbol;
 requestGeneration++;
 document.querySelectorAll('.symbol').forEach(b=>b.classList.toggle('active',b.dataset.symbol===symbol));
 set('marketSymbol',selectedDisplayName); set('dataState','● QUOTE LOADING');
 clearDataForSwitch();
 const gen=requestGeneration;
 loadQuote(gen,symbol);
 loadFull(gen,symbol);
 loadOptions(gen,symbol);
 loadFutures(gen,symbol);
 loadNse(gen,symbol);
 loadShift(gen,symbol);
 loadCatalysts(gen,symbol);
}
function clearDataForSwitch(){
 ['decision','confidence','tf5','tf15','tf1h','tf1d','tf1w','moduleTechnical','moduleOption','moduleAstrology','moduleNumerology','sentimentBias','futureContract','futurePrice','futureOi','futureVolume','futureBasis','futureDoi','futureBuild','foCompare','foAction','pcrOi','pcrVol','ceVolume','peVolume','atm','maxPain','support','resistance','optionView','shiftBias','shiftPhase','shiftStrength','shiftAction','marketShiftBias','marketShiftPhase','marketShiftStrength','marketShiftAction','marketShift5Score','marketShift15Score','marketShiftDelta','marketShiftType'].forEach(id=>set(id,'—'));
 if($('astroRows'))$('astroRows').innerHTML='<div>Loading astrology…</div>';
 if($('numRows'))$('numRows').innerHTML='<div>Loading numerology…</div>';
 if($('sentimentRows'))$('sentimentRows').innerHTML='<div>Loading sentiment…</div>';
 if($('topCalls'))$('topCalls').innerHTML='<tr><td colspan="5">Loading…</td></tr>';
 if($('topPuts'))$('topPuts').innerHTML='<tr><td colspan="5">Loading…</td></tr>';
}

function renderQuote(d,gen,expected){
 if(!isCurrent(gen,expected)||!d)return;
 const t=d.ticker||{}; const x=d.analysis||{};
 const price=t.ltp??t.price??t.close??x.price;
 if(price!=null)set('price',fmt(price));
 const ch=t.percent_change??t.per_change;
 const change=t.change;
 if(ch!=null)set('change',`${num(ch)>=0?'▲':'▼'} ${fmt(Math.abs(ch))}%`);
 else if(change!=null)set('change',`${num(change)>=0?'▲':'▼'} ${fmt(Math.abs(change))}`);
 set('dayChange',ch==null?'—':`${num(ch)>=0?'▲':'▼'} ${fmt(Math.abs(ch))}%`);
 set('dayChangePct',change==null?'—':fmt(change));
 set('dayHigh',fmt(t.high)); set('dayLow',fmt(t.low));
 set('dataState',d.status==='OK'?'● QUOTE LIVE':'● QUOTE RETRY');
}

function renderRows(id,rows){
 const el=$(id); if(!el)return;
 if(!rows || !rows.length){el.innerHTML='<div><span>STATUS</span><b>NO DATA</b></div>';return}
 el.innerHTML=rows.map(([k,v])=>`<div><span>${esc(k)}</span><b>${esc(v)}</b></div>`).join('');
}
function renderAstrology(a){
 a=a||{};set('moduleAstrology',a.bias||'—');paint('moduleAstrology',a.bias);
 renderRows('astroRows',[
  ['Bias',a.bias||'—'],['Score',a.score==null?'—':`${a.score}/100`],['Moon',a.moon?.reason||a.moon?.phase||'—'],['Nakshatra',a.nakshatra?.reason||a.nakshatra?.name||'—'],['Tithi',a.tithi?.reason||a.tithi?.name||'—'],['Rahu Kaal',a.rahu?.active?'ACTIVE':'CLEAR']
 ]);
}
function renderNumerology(n){
 n=n||{};set('moduleNumerology',n.bias||'—');paint('moduleNumerology',n.bias);
 renderRows('numRows',[["Bias",n.bias||'—'],['Score',n.score==null?'—':`${n.score}/100`],['Life Path',n.life_path??'—'],['Universal Day',n.universal_day??'—'],['Symbol Number',n.symbol_number??'—'],['Reason',(n.reasons||[]).join(' • ')||'—']]);
}
function renderSentiment(s){
 s=s||{};set('sentimentBias',s.bias||'—');paint('sentimentBias',s.bias);
 renderRows('sentimentRows',[["Bias",s.bias||'—'],['Score',s.score==null?'—':s.score],['Fear & Greed',s.fear_greed||'—'],['Source',s.source||'—'],['Reason',(s.reasons||[]).join(' • ')||s.note||'—']]);
}
function renderTop5(o){
 const calls=(o.top_call_oi||[]).slice(0,5), puts=(o.top_put_oi||[]).slice(0,5);
 if($('topCalls'))$('topCalls').innerHTML=calls.length?calls.map((r,i)=>`<tr><td>${i+1}</td><td>${esc(fmt(r.strike,0))}</td><td>${esc(fmt(r.oi,0))}</td><td>${esc(fmt(r.ltp,2))}</td><td>${esc(fmt(r.oi_change,0))}</td></tr>`).join(''):'<tr><td colspan="5">No call OI data</td></tr>';
 if($('topPuts'))$('topPuts').innerHTML=puts.length?puts.map((r,i)=>`<tr><td>${i+1}</td><td>${esc(fmt(r.strike,0))}</td><td>${esc(fmt(r.oi,0))}</td><td>${esc(fmt(r.ltp,2))}</td><td>${esc(fmt(r.oi_change,0))}</td></tr>`).join(''):'<tr><td colspan="5">No put OI data</td></tr>';
}
function renderOption(o,gen,expected){
 if(!isCurrent(gen,expected)||!o)return;
 set('expiry',o.expiry?`Expiry ${o.expiry}`:'Expiry —');set('optionStatus',o.status==='OK'?'● LIVE':`● ${o.status||'NO DATA'}`);
 set('pcrOi',fmt(o.pcr_oi_calc??o.pcr,2));set('pcrVol',fmt(o.pcr_volume_calc??o.volume_pcr,2));set('ceVolume',fmt(o.call_volume,0));set('peVolume',fmt(o.put_volume,0));set('atm',fmt(o.atm_strike,0));set('maxPain',fmt(o.max_pain,0));set('support',fmt(o.max_put_oi_support,0));set('resistance',fmt(o.max_call_oi_resistance,0));set('optionView',o.signal||'SIDEWAYS');set('optionViewReason',o.reason||'NSE option-chain data');set('optionNote',o.status==='OK'?`${o.source||'NSE'} • ${o.row_count||0} rows`:'Option chain unavailable');renderTop5(o);
 const g=o.gamma_squeeze||{};set('gammaStatus',g.status||'—');set('gammaRisk',g.bias||g.setup||'WAIT');set('gammaSide',g.action||'—');set('gammaWindow',g.watch_window||g.phase||'—');set('gammaScore',g.strength==null?'—':`${g.strength}/100`);set('gammaTrigger',g.trigger||'Wait for live option-chain confirmation.');set('gammaReason',g.reason||g.message||'No squeeze condition confirmed.');
}
function renderFutures(d,gen,expected){
 if(!isCurrent(gen,expected)||!d)return;
 const f=d.futures||{},c=d.combined||{};set('futureStatus',`● ${f.status||'NO DATA'}`);set('futureContract',f.contract||f.trading_symbol||'—');set('futurePrice',fmt(f.price));set('futureOi',fmt(f.oi,0));set('futureVolume',fmt(f.volume,0));set('futureBasis',f.basis==null?'—':fmt(f.basis,2));set('futureDoi',f.snapshot_oi_change==null?'WARMING':fmt(f.snapshot_oi_change,0));set('futureBuild',f.buildup||'NO DATA');set('futureNote',f.note||f.reason||'Kotak Neo futures data unavailable.');set('foCompare',c.view||'WAIT');set('foAction',c.action||'WAIT');set('foFutureBias',c.futures_bias||'—');set('foOptionBias',c.options_bias||'—');paint('foCompare',c.view);paint('foAction',c.action);
 set('foDecisionView',c.view||'WAIT');set('foDecisionAction',c.action||'WAIT');set('foDecisionStatus',c.status||f.status||'—');
}
function renderNse(d,gen,expected){
 if(!isCurrent(gen,expected)||!d)return;
 const rows=d.fii_dii?.rows||[];const fii=rows.find(x=>String(x.category||'').toUpperCase().includes('FII'))||{};const dii=rows.find(x=>String(x.category||'').toUpperCase()==='DII')||{};
 set('fiiNet',fii.net_cr==null?'—':`${fii.net_cr>=0?'+':''}${fmt(fii.net_cr,0)} Cr`);set('diiNet',dii.net_cr==null?'—':`${dii.net_cr>=0?'+':''}${fmt(dii.net_cr,0)} Cr`);set('indiaVix',fmt(d.india_vix?.value,2));set('positionSentiment',d.sentiment?.bias||'—');set('participantStatus',d.status==='OK'?'● EOD DATA':`● ${d.status||'NO DATA'}`);set('participantReason',d.sentiment?.note||d.disclaimer||'NSE participant data is EOD, not live order flow.');
 renderSentiment(d.sentiment||{});
 const prows=d.participant_oi?.rows||[];if($('participantRows'))$('participantRows').innerHTML=prows.slice(0,10).map(r=>`<tr><td>${esc(r.participant||'—')}</td><td>${esc(fmt(r.future_index_long,0))}</td><td>${esc(fmt(r.future_index_short,0))}</td><td>${esc(fmt((r.future_index_long??0)-(r.future_index_short??0),0))}</td><td>${esc(fmt((r.index_call_long??0)-(r.index_call_short??0),0))}</td><td>${esc(fmt((r.index_put_long??0)-(r.index_put_short??0),0))}</td></tr>`).join('')||'<tr><td colspan="6">No participant data</td></tr>';
}
function renderPositionShift(x,gen,expected){if(!isCurrent(gen,expected)||!x)return;set('shiftStatus',`● ${x.status||'NO DATA'}`);set('shiftBias',x.bias||'WAIT');set('shiftPhase',x.phase||'—');set('shiftStrength',`${x.strength||0}/100`);set('shiftAction',x.action||'WAIT');const w=x.windows||{};set('shift1m',w['1m']?.score==null?'—':w['1m'].score);set('shift3m',w['3m']?.score==null?'—':w['3m'].score);set('shift5m',w['5m']?.score==null?'—':w['5m'].score);set('shift15m',w['15m']?.score==null?'—':w['15m'].score);set('shiftNote',x.note||x.message||'Collecting snapshots…')}
function renderMarketShift(x,gen,expected){if(!isCurrent(gen,expected)||!x)return;set('marketShiftStatus',`● ${x.status||'NO DATA'}`);set('marketShiftBias',x.bias||'WAIT');set('marketShiftPhase',x.phase||'—');set('marketShiftStrength',`${x.strength??0}/100`);set('marketShiftAction',x.action||'WAIT');set('marketShift5Score',x.score_5m==null?'—':x.score_5m);set('marketShift15Score',x.confirm_15m?.score==null?'—':Math.round(x.confirm_15m.score));set('marketShiftDelta',x.score_change==null?'—':Math.round(x.score_change));set('marketShiftType',x.shift_type||'—');set('marketShiftReason',(x.current_5m?.reasons||[]).join(' • ')||x.error||'Waiting for valid 5M data.');set('marketShiftNote',x.note||'No new regime shift detected.')}
function renderCore(a,gen,expected){
 if(!isCurrent(gen,expected)||!a||a.status!=='OK')return;
 const t=a.ticker||{},x=a.analysis||{};renderQuote(a,gen,expected);
 const price=t.ltp??t.price??t.close??x.price;const decision=String(x.recommendation||x.signal||'WAIT').toUpperCase();set('decision',decision);paint('decision',decision);const conf=num(x.confidence??x.overall_confidence);set('confidence',conf==null?'Strength —':`Strength ${fmt(conf,0)}/100`);if($('confidenceBar'))$('confidenceBar').style.width=`${Math.max(0,Math.min(100,conf||0))}%`;
 const tr=x.derived_timeframes||{};set('tf5',tr['5m']?.trend||'UNKNOWN');set('tf15',tr['15m']?.trend||'UNKNOWN');set('tf1h',tr['1h']?.trend||'UNKNOWN');set('tf1d',tr['1d']?.trend||'UNKNOWN');set('tf1w',tr['1w']?.trend||'UNKNOWN');set('intra5',x.intraday_trend?.timeframes?.find(z=>z.timeframe==='5m')?.trend||tr['5m']?.trend||'UNKNOWN');set('intra15',x.intraday_trend?.timeframes?.find(z=>z.timeframe==='15m')?.trend||tr['15m']?.trend||'UNKNOWN');set('intra1h',x.intraday_trend?.timeframes?.find(z=>z.timeframe==='1h')?.trend||tr['1h']?.trend||'UNKNOWN');
 set('agreementMini',x.agreement||'—');set('agreementMini2',x.agreement||'—');set('whyDecision',decision);const mom=x.technical?.momentum||{};if($('metrics'))$('metrics').innerHTML=[["Signal",x.technical?.signal||x.signal||'—'],["Confidence",x.technical?.confidence==null?'—':`${fmt(x.technical.confidence,0)}/100`],["RSI",mom.rsi==null?'—':fmt(mom.rsi,2)],["EMA9",mom.ema9==null?'—':fmt(mom.ema9,2)],["EMA21",mom.ema21==null?'—':fmt(mom.ema21,2)],["RVOL",mom.rvol==null?'—':fmt(mom.rvol,2)]].map(r=>`<div><small>${esc(r[0])}</small><b>${esc(r[1])}</b></div>`).join('');set('moduleTechnical',x.technical?.signal||x.signal||'—');set('moduleOption',x.option_chain?.signal||'—');set('moduleAstrology',x.astrology?.bias||'—');set('moduleAstrology2',x.astrology?.bias||'—');set('moduleNumerology',x.numerology?.bias||'—');set('moduleNumerology2',x.numerology?.bias||'—');set('agreeTechnical',x.technical?.signal||'—');set('agreeOptions',x.option_chain?.signal||'—');set('agreeAstrology',x.astrology?.bias||'—');set('agreeNumerology',x.numerology?.bias||'—');set('agreeFinal',x.agreement||decision);
 renderAstrology(x.astrology);renderNumerology(x.numerology);renderSentiment(x.sentiment);renderTradePlan(x);renderOptionTradePlan(a.option_trade||x.option_trade);renderPositionShift(a.position_shift,gen,expected);renderMarketShift(a.market_shift||x.market_shift,gen,expected);renderFutures(x.futures_intelligence||a.futures_intelligence,gen,expected);set('foMarketShift',(a.market_shift||x.market_shift)?.bias||'WAIT');set('foPositionShift',a.position_shift?.bias||'WAIT');set('foDecisionReason',((a.market_shift||x.market_shift)?.note)||'Futures + options + market-shift confirmation required.');if(x.option_chain)renderOption(x.option_chain,gen,expected);else loadOptions(gen,expected);
 const reasons=x.reasons||x.reason||[];if($('reasons'))$('reasons').innerHTML=(Array.isArray(reasons)?reasons:[String(reasons)]).slice(0,8).map(r=>`<div>${esc(r)}</div>`).join('')||'<div>Waiting for complete market data.</div>';
}
function renderTradePlan(x){const p=x.trade_plan||{};const side=String(p.side||x.recommendation||x.signal||'WAIT').toUpperCase();if(p.entry_zone){set('entryZone',p.entry_zone);set('stopLoss',fmt(p.stop_loss));set('tp1',fmt(p.target1));set('tp2',fmt(p.target2));set('tp3',fmt(p.target3));set('rr',p.risk_reward||'—')}else{['entryZone','stopLoss','tp1','tp2','tp3','rr'].forEach(id=>set(id,'—'))}set('riskState',side==='BUY'||side==='SELL'?side:'WAIT');paint('riskState',side)}
function renderOptionTradePlan(p){p=p||{};set('optionBuy',p.status==='READY'?`${p.action||'BUY'} • ${p.contract||''}`:'WAIT • NO OPTION BUY');set('optionLtp',p.ltp==null?'—':fmt(p.ltp));set('optionExpiry',p.expiry||'—');paint('optionBuy',p.status==='READY'?'BUY':'WAIT')}

async function loadQuote(gen,expected){try{const d=await getJson(`/api/quote?symbol=${encodeURIComponent(expected)}&_=${Date.now()}`);renderQuote(d,gen,expected)}catch(e){if(isCurrent(gen,expected))set('dataState','● QUOTE RETRY')}}
async function loadFull(gen,expected){try{const d=await getJson(`/api/live?symbol=${encodeURIComponent(expected)}&_=${Date.now()}`);if(!isCurrent(gen,expected))return;if(d.status==='OK')renderCore(d,gen,expected);else set('dataState','● ANALYSIS REFRESHING • QUOTE LIVE')}catch(e){if(isCurrent(gen,expected))set('dataState','● LAST QUOTE • ANALYSIS RETRY')}}
async function loadOptions(gen,expected){if(String(expected).startsWith('EQ_'))return;try{const d=await getJson(`/api/options?symbol=${encodeURIComponent(expected)}&_=${Date.now()}`);renderOption(d,gen,expected)}catch(e){if(isCurrent(gen,expected))set('optionStatus','● RETRY')}}
async function loadFutures(gen,expected){if(!['NIFTY50','BANKNIFTY','NIFTYIT'].includes(String(expected).toUpperCase()))return;try{const d=await getJson(`/api/futures?symbol=${encodeURIComponent(expected)}&_=${Date.now()}`);renderFutures(d,gen,expected)}catch(e){if(isCurrent(gen,expected))set('futureStatus','● RETRY')}}
async function loadNse(gen,expected){if(String(expected).startsWith('EQ_'))return;try{const d=await getJson(`/api/nse-intelligence?symbol=${encodeURIComponent(expected)}&_=${Date.now()}`);renderNse(d,gen,expected)}catch(e){}}
async function loadShift(gen,expected){if(String(expected).startsWith('EQ_')){renderPositionShift({status:'NOT_REQUIRED',bias:'WAIT',strength:0,phase:'CASH EQUITY',action:'TECHNICAL ONLY',note:'Position shift is not applicable to cash equity.'},gen,expected);renderMarketShift({status:'NOT_REQUIRED',bias:'WAIT',strength:0,phase:'CASH EQUITY',action:'TECHNICAL ONLY',note:'Market-shift is reserved for index derivatives.'},gen,expected);return;}try{const [p,m]=await Promise.all([getJson(`/api/position-shift?symbol=${encodeURIComponent(expected)}&_=${Date.now()}`),getJson(`/api/market-shift?symbol=${encodeURIComponent(expected)}&_=${Date.now()}`)]);renderPositionShift(p,gen,expected);renderMarketShift(m,gen,expected)}catch(e){}}
async function loadCatalysts(gen,expected){try{const d=await getJson(`/api/catalysts?symbol=${encodeURIComponent(expected)}&_=${Date.now()}`);if(!isCurrent(gen,expected))return;set('eventRisk',d.items?.length?'NORMAL':'NO DATA');set('eventDisclaimer',d.note||'Verified catalyst feed only.');if($('catalyst'))$('catalyst').innerHTML=(d.items||[]).slice(0,8).map(x=>`<div class="catalyst-row"><strong>${esc(x.title)}</strong><small>${esc(x.effect||'Confirm with live market data.')}</small></div>`).join('')||'<div class="catalyst-row">No verified catalyst available.</div>'}catch(e){}}

async function loadScanner(){try{const d=await getJson(`/api/scanner?_=${Date.now()}`);if(!$('scanner'))return;$('scanner').innerHTML=(d.rows||[]).map(r=>`<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #ffffff0a"><span><b>${esc(r.symbol)}</b></span><span>${fmt(r.price)} ${r.change_pct==null?'':`(${fmt(r.change_pct,2)}%)`}</span></div>`).join('')||'No scanner data';}catch(e){if($('scanner'))$('scanner').textContent='Scanner retrying…'}}

async function searchEquitiesUI(q){
 const box=$('equityResults');if(!box)return;q=String(q||'').trim();const seq=++equitySearchSeq;if(equitySearchController)equitySearchController.abort();if(q.length<2){box.style.display='none';box.innerHTML='';return;}equitySearchController=new AbortController();box.style.display='block';box.innerHTML='<div class="equity-result"><small>Searching…</small></div>';
 try{const d=await getJson(`/api/equity-search?q=${encodeURIComponent(q)}&limit=12&_=${Date.now()}`,{signal:equitySearchController.signal});if(seq!==equitySearchSeq)return;const current=String($('equitySearch')?.value||'').trim();if(current!==q)return;const rows=d?.results||[];box.innerHTML=rows.length?rows.map((r,i)=>`<div class="equity-result" data-i="${i}"><span><b>${esc(r.trading_symbol||r.symbol||'—')}</b><small>${esc(r.name||'')}</small></span><span class="equity-exchange">${esc(r.exchange||r.segment||'')}</span></div>`).join(''):'<div class="equity-result"><small>No matching equity found.</small></div>';
   box.querySelectorAll('.equity-result[data-i]').forEach(el=>el.addEventListener('click',async()=>{const r=rows[Number(el.dataset.i)];if(!r)return;const trading=String(r.trading_symbol||'').toUpperCase();try{const reg=await getJson(`/api/equity-register?symbol=${encodeURIComponent(trading)}&_=${Date.now()}`);const nextSymbol=String(reg?.symbol||r.symbol||'').toUpperCase();if(!nextSymbol)throw new Error('No registered symbol');localStorage.setItem('nak_equity_trading',trading);localStorage.setItem('nak_equity_name',r.name||trading);symbol=nextSymbol;selectedDisplayName=r.name||trading;requestGeneration++;document.querySelectorAll('.symbol').forEach(b=>b.classList.remove('active'));set('marketSymbol',selectedDisplayName);set('dataState','● QUOTE LOADING');box.style.display='none';if($('equitySearch'))$('equitySearch').value='';equitySearchSeq++;if(equitySearchController)equitySearchController.abort();const gen=requestGeneration;loadQuote(gen,symbol);loadFull(gen,symbol);loadNse(gen,symbol);loadCatalysts(gen,symbol);}catch(e){box.innerHTML='<div class="equity-result"><small>Selection failed — retry once.</small></div>'}}));
 }catch(e){if(e?.name==='AbortError')return;if(seq!==equitySearchSeq)return;box.innerHTML='<div class="equity-result"><small>Search unavailable. Check Kotak Neo connection.</small></div>'}
}

function startAutoRefresh(){
 setInterval(()=>{const gen=requestGeneration,expected=symbol;loadQuote(gen,expected)},10000);
 setInterval(()=>{const gen=requestGeneration,expected=symbol;loadFull(gen,expected)},30000);
 setInterval(()=>{const gen=requestGeneration,expected=symbol;loadOptions(gen,expected);loadFutures(gen,expected)},30000);
 setInterval(()=>{const gen=requestGeneration,expected=symbol;loadNse(gen,expected)},120000);
 setInterval(loadScanner,30000);
}

document.addEventListener('DOMContentLoaded',()=>{
 document.querySelectorAll('.symbol').forEach(btn=>btn.addEventListener('click',()=>selectSymbol(btn.dataset.symbol,btn.textContent.trim())));
 const es=$('equitySearch');if(es)es.addEventListener('input',()=>{clearTimeout(equitySearchTimer);equitySearchTimer=setTimeout(()=>searchEquitiesUI(es.value),180)});
 const rb=$('refreshBtn');if(rb)rb.addEventListener('click',()=>selectSymbol(symbol,selectedDisplayName));
 const gen=requestGeneration,expected=symbol;loadQuote(gen,expected);loadFull(gen,expected);loadOptions(gen,expected);loadFutures(gen,expected);loadNse(gen,expected);loadShift(gen,expected);loadCatalysts(gen,expected);loadScanner();startAutoRefresh();
});
