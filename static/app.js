const state = {
  symbol: "BTCUSD",
  busy: false,
  timer: null,
  lastAnalysis: null,
};

const $ = (id) => document.getElementById(id);

function text(id, value) {
  const el = $(id);
  if (el) el.textContent = value ?? "—";
}

async function fetchJSON(url, timeoutMs = 15000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      cache: "no-store",
      signal: controller.signal,
    });
    const body = await response.text();
    let data;
    try { data = JSON.parse(body); }
    catch { throw new Error(`HTTP ${response.status}: ${body.slice(0, 160)}`); }

    if (!response.ok) throw new Error(data.detail || data.message || `HTTP ${response.status}`);
    return data;
  } finally {
    clearTimeout(timer);
  }
}

function signalText(x) {
  if (x === undefined || x === null || x === "") return "—";
  return String(x);
}

function renderAnalysis(payload) {
  const a = payload.analysis || {};
  state.lastAnalysis = a;

  if (a.status === "ERROR" || a.status === "NO DATA") {
    text("decision", a.status);
    text("confidence", a.message || "Analysis data unavailable");
    text("action", "Action: WAIT");
    $("reasons").innerHTML = `<li>${escapeHtml(a.message || "Delta data unavailable")}</li>`;
    return;
  }

  const technical = a.technical || {};
  const astrology = a.astrology || {};
  const numerology = a.numerology || {};
  const agreement = a.agreement || {};
  const optionChain = a.option_chain || {};

  text("decision", a.recommendation || a.action || "WAIT");
  text("confidence", `Overall Confidence: ${a.overall_confidence ?? "—"}`);
  text("action", `Action: ${a.recommendation || a.action || "WAIT"}`);

  text("technical", technical.signal || "NEUTRAL");
  text("technicalConf", `Confidence: ${technical.confidence ?? "—"}`);
  text("astrology", astrology.bias || "NEUTRAL");
  text("astrologyScore", `Score: ${astrology.score ?? "—"}`);
  text("numerology", numerology.bias || "NEUTRAL");
  text("numerologyScore", `Score: ${numerology.score ?? "—"}`);

  const trend = technical.trend || {};
  const mtf = ["5m","15m","1h","1d","1w","1mo"];
  $("mtf").innerHTML = mtf.map(tf => {
    const x = trend[tf] || {};
    return `<div class="tf"><b>${tf}</b><span>${escapeHtml(signalText(x.trend))}</span><small>score ${escapeHtml(signalText(x.score))}</small></div>`;
  }).join("");

  text("agreeTechnical", technical.signal || "—");
  text("agreeAstrology", astrology.bias || "—");
  text("agreeNumerology", numerology.bias || "—");
  text("agreeOptionChain", optionChain.signal || "—");
  text("agreeFinal", typeof agreement === "string" ? agreement : (agreement.final || agreement.status || a.recommendation || "—"));

  renderMarketTrend(technical.trend || {});
  renderOptionChain(optionChain);

  text("ema9", trend["5m"]?.ema9 ?? technical.ema9 ?? "—");
  text("ema50", trend["5m"]?.ema50 ?? technical.ema50 ?? "—");
  text("ema200", trend["5m"]?.ema200 ?? technical.ema200 ?? "—");

  const reasons = Array.isArray(a.reasons)
    ? a.reasons
    : Array.isArray(technical.reasons) ? technical.reasons : [];

  $("reasons").innerHTML = reasons.length
    ? reasons.slice(0, 20).map(r => `<li>${escapeHtml(String(r))}</li>`).join("")
    : "<li>No reasons returned by analysis engine.</li>";
}


function renderMarketTrend(trend) {
  const keys = ["5m", "15m", "1h", "1d", "1w", "1mo"];
  const rows = keys.map(tf => ({ tf, ...(trend[tf] || {}) }));
  const available = rows.filter(x => x.trend && x.trend !== "UNKNOWN");
  const total = available.reduce((n, x) => n + (Number(x.score) || 0), 0);
  const avg = available.length ? total / available.length : 0;
  let overall = "SIDEWAYS";
  if (avg >= 40) overall = "STRONG_BULL";
  else if (avg >= 15) overall = "BULL";
  else if (avg <= -40) overall = "STRONG_BEAR";
  else if (avg <= -15) overall = "BEAR";

  text("marketTrendOverall", overall);
  text("marketTrendScore", `Score: ${total}`);
  const box = $("marketTrendTable");
  if (!box) return;
  box.innerHTML = rows.map(x => `
    <div class="trend-row">
      <b>${escapeHtml(x.tf)}</b>
      <strong class="trend-${escapeHtml(String(x.trend || "UNKNOWN").toLowerCase().replaceAll("_", "-"))}">${escapeHtml(x.trend || "UNKNOWN")}</strong>
      <span>Score: ${escapeHtml(String(x.score ?? "—"))}</span>
    </div>`).join("");
}

function renderOptionChain(o) {
  const status = String(o.status || "NO DATA");
  text("ocSignal", o.signal || "NEUTRAL");
  text("ocConfidence", status === "OK" ? `Confidence: ${o.confidence ?? "—"}%` : status);
  text("ocExpiry", o.expiry || "—");
  text("ocPcr", o.pcr ?? "—");
  text("ocVolumePcr", o.volume_pcr ?? "—");
  text("ocCallOi", o.call_oi ?? "—");
  text("ocPutOi", o.put_oi ?? "—");
  text("ocCallVol", o.call_volume ?? "—");
  text("ocPutVol", o.put_volume ?? "—");
  text("ocSupport", o.max_put_oi_support ?? "—");
  text("ocResistance", o.max_call_oi_resistance ?? "—");
  text("ocMaxPain", o.max_pain ?? "—");
  text("ocAtm", o.atm_strike ?? "—");
  const note = $("ocNote");
  if (note) note.textContent = status === "OK" ? (o.reason || "Live Delta option-chain data") : (o.reason || "Option-chain data unavailable");

  const calls = Array.isArray(o.top_call_oi) ? o.top_call_oi : [];
  const puts = Array.isArray(o.top_put_oi) ? o.top_put_oi : [];
  const top = $("ocTopOi");
  if (top) {
    top.innerHTML = `
      <div class="oc-side"><b>Top CALL OI</b>${calls.map(r => `<div><span>${escapeHtml(String(r.strike))}</span><span>${escapeHtml(String(r.oi))}</span></div>`).join("") || "<div>—</div>"}</div>
      <div class="oc-side"><b>Top PUT OI</b>${puts.map(r => `<div><span>${escapeHtml(String(r.strike))}</span><span>${escapeHtml(String(r.oi))}</span></div>`).join("") || "<div>—</div>"}</div>`;
  }
}

function renderMarket(payload) {
  const ticker = payload.ticker;
  if (!ticker) {
    text("livePrice", "Price unavailable");
    text("liveMeta", "Ticker API did not return data");
    return;
  }

  const price = ticker.price ?? ticker.close ?? ticker.mark_price;
  text("livePrice", price !== undefined ? Number(price).toLocaleString() : "—");
  text("liveMeta", `${payload.symbol} • Mark ${ticker.mark_price ?? "—"} • Volume ${ticker.volume ?? "—"}`);
}

async function loadLive() {
  if (state.busy) return;
  state.busy = true;
  text("updateStatus", "🟡 Updating...");

  try {
    const data = await fetchJSON(`/api/live?symbol=${encodeURIComponent(state.symbol)}`);
    renderMarket(data);
    renderAnalysis(data);
    text("updateStatus", `🟢 Updated ${new Date().toLocaleTimeString()}`);
    $("brokerStatus").textContent = "🟢 Broker Online";
  } catch (err) {
    console.error(err);
    text("updateStatus", "🔴 Data Error");
    text("livePrice", "Data unavailable");
    text("liveMeta", err.name === "AbortError" ? "Request timeout" : err.message);
    text("decision", "WAIT");
    text("confidence", "Overall Confidence: —");
    text("action", "Action: Data unavailable");
    $("reasons").innerHTML = `<li>${escapeHtml(err.message)}</li>`;
    $("brokerStatus").textContent = "🟠 Broker/API Issue";
  } finally {
    state.busy = false;
  }
}

async function loadScanner() {
  try {
    const data = await fetchJSON("/api/scanner");
    $("scanner").innerHTML = data.map(x =>
      `<div class="scanner-row"><b>${escapeHtml(x.symbol)}</b><span>${escapeHtml(x.signal)}</span><small>${escapeHtml(String(x.strength ?? "—"))}%</small></div>`
    ).join("");
  } catch (err) {
    $("scanner").textContent = `Scanner error: ${err.message}`;
  }
}

async function loadStatsAndTrades() {
  try {
    const [stats, trades] = await Promise.all([
      fetchJSON("/stats"),
      fetchJSON("/api/history"),
    ]);

    const rows = Array.isArray(trades) ? trades : [];
    $("trades").innerHTML = rows.length
      ? rows.slice(-20).reverse().map((t, i) =>
        `<tr>
          <td>${i + 1}</td>
          <td>${escapeHtml(t.symbol)}</td>
          <td>${escapeHtml(t.side)}</td>
          <td>${escapeHtml(String(t.entry ?? "—"))}</td>
          <td>${escapeHtml(String(t.exit ?? "—"))}</td>
          <td>${escapeHtml(String(t.pnl ?? "—"))}</td>
          <td>${escapeHtml(t.status)}</td>
        </tr>`).join("")
      : `<tr><td colspan="7">No trades yet</td></tr>`;

    drawEquity(rows);
  } catch (err) {
    $("trades").innerHTML = `<tr><td colspan="7">${escapeHtml(err.message)}</td></tr>`;
  }
}

function drawEquity(rows) {
  const canvas = $("equityChart");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const w = canvas.width = canvas.clientWidth * devicePixelRatio;
  const h = canvas.height = 180 * devicePixelRatio;
  ctx.clearRect(0, 0, w, h);

  if (!rows.length) {
    ctx.fillText("No closed trade data", 12 * devicePixelRatio, 30 * devicePixelRatio);
    return;
  }

  let equity = 0;
  const points = rows.map(r => {
    equity += Number(r.pnl || 0);
    return equity;
  });

  const min = Math.min(...points, 0);
  const max = Math.max(...points, 0);
  const range = max - min || 1;
  const pad = 20 * devicePixelRatio;

  ctx.beginPath();
  points.forEach((v, i) => {
    const x = pad + i * ((w - pad * 2) / Math.max(points.length - 1, 1));
    const y = h - pad - ((v - min) / range) * (h - pad * 2);
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

document.querySelectorAll(".symbol").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".symbol").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    state.symbol = btn.dataset.symbol;
    loadLive();
  });
});

async function refreshAll() {
  await Promise.allSettled([
    loadLive(),
    loadScanner(),
    loadStatsAndTrades(),
  ]);
}

refreshAll();
setInterval(refreshAll, 10000);


// ------------------------------------------------------------
// Historical Backtest / Validation
// ------------------------------------------------------------
const validationToggle = $("validationToggle");
const validationPanel = $("validationPanel");
const runBacktestBtn = $("runBacktest");

if (validationToggle && validationPanel) {
  validationToggle.addEventListener("click", () => {
    validationPanel.hidden = !validationPanel.hidden;
    if (!validationPanel.hidden) {
      validationPanel.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  });
}

function drawValidationEquity(points) {
  const canvas = $("backtestChart");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth || 320;
  const h = 190;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);

  if (!points || !points.length) {
    ctx.fillText("No validation trades", 12, 28);
    return;
  }

  const values = points.map(p => Number(p.value) || 0);
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 0);
  const range = max - min || 1;
  const pad = 18;

  ctx.beginPath();
  values.forEach((v, i) => {
    const x = pad + i * ((w - pad * 2) / Math.max(values.length - 1, 1));
    const y = h - pad - ((v - min) / range) * (h - pad * 2);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

function renderBacktest(data) {
  const rows = Array.isArray(data.summary) ? data.summary : [];
  const first = rows[0] || {};

  text("btTrades", first.trades ?? "0");
  text("btWinRate", first.win_rate_pct !== undefined ? `${first.win_rate_pct}%` : "—");
  text("btAvgReturn", first.avg_return_pct !== undefined ? `${first.avg_return_pct}%` : "—");

  $("backtestTable").innerHTML = rows.length
    ? rows.map(r => `<tr>
        <td>${escapeHtml(String(r.horizon * 5))}m</td>
        <td>${escapeHtml(String(r.trades))}</td>
        <td>${escapeHtml(String(r.wins))}</td>
        <td>${escapeHtml(String(r.losses))}</td>
        <td>${escapeHtml(String(r.win_rate_pct))}%</td>
        <td>${escapeHtml(String(r.avg_return_pct))}%</td>
      </tr>`).join("")
    : `<tr><td colspan="6">No BUY/SELL validation signals found</td></tr>`;

  $("backtestNote").textContent = data.note || "";
  $("backtestResults").hidden = false;
  drawValidationEquity(data.equity_curve || []);
}

if (runBacktestBtn) {
  runBacktestBtn.addEventListener("click", async () => {
    const fileInput = $("backtestFile");
    const status = $("backtestStatus");
    const file = fileInput?.files?.[0];

    if (!file) {
      status.textContent = "Please select a historical 5m CSV first.";
      return;
    }

    const form = new FormData();
    form.append("file", file);
    form.append("symbol", $("backtestSymbol")?.value || "BTCUSD");

    const horizon = $("backtestHorizon")?.value || "3";
    // Keep the selected horizon as the primary metric and also test
    // the standard 30m/60m horizons for comparison.
    const horizons = [...new Set([Number(horizon), 6, 12])];
    form.append("horizons", horizons.join(","));

    runBacktestBtn.disabled = true;
    status.textContent = "Running validation… this can take a little while.";
    $("backtestResults").hidden = true;

    try {
      const response = await fetch("/api/backtest", {
        method: "POST",
        body: form,
        cache: "no-store",
      });
      const data = await response.json();

      if (!response.ok || data.status !== "OK") {
        throw new Error(data.message || `HTTP ${response.status}`);
      }

      status.textContent = `Validation complete • ${data.rows} evaluated rows`;
      renderBacktest(data);
    } catch (err) {
      console.error(err);
      status.textContent = `Validation error: ${err.message}`;
      $("backtestResults").hidden = true;
    } finally {
      runBacktestBtn.disabled = false;
    }
  });
}
