// NAKSHATRA AI v4.0 - Dashboard V2
let currentSymbol = "BTCUSD";
let equityChart = null;

const $ = (id) => document.getElementById(id);

function text(v, fallback = "—") {
  return v === undefined || v === null || v === "" ? fallback : String(v);
}

function scoreText(v) {
  return v === undefined || v === null ? "—" : `${v}%`;
}

function tone(value) {
  const s = String(value || "").toUpperCase();
  if (s.includes("BUY") || s.includes("BULL")) return "green";
  if (s.includes("SELL") || s.includes("BEAR")) return "red";
  if (s.includes("NO AGREEMENT") || s.includes("MIXED") || s.includes("NEUTRAL")) return "yellow";
  return "blue";
}

function paint(el, value) {
  el.textContent = text(value);
  el.className = "value " + tone(value);
}

function setSymbol(symbol) {
  currentSymbol = symbol;
  $("btcBtn").classList.toggle("active", symbol === "BTCUSD");
  $("ethBtn").classList.toggle("active", symbol === "ETHUSD");
  refreshDashboard();
}

async function getJSON(url) {
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`${url} -> HTTP ${res.status}`);
  return await res.json();
}

async function loadAnalysis() {
  const data = await getJSON(`/analysis/${currentSymbol}`);

  $("price").textContent = data.price !== undefined
    ? Number(data.price).toLocaleString("en-IN", {maximumFractionDigits: 2})
    : "—";

  $("symbolTime").textContent =
    `${text(data.symbol, currentSymbol)} • ${text(data.time)}`;

  const agreement = data.agreement;
  const recommendation = data.recommendation || agreement || "—";

  $("decision").textContent = recommendation;
  $("decision").className = "big " + tone(recommendation);
  $("overallConfidence").textContent =
    data.overall_confidence !== undefined ? `${data.overall_confidence}%` : "—";

  // The current decision engine is designed to avoid automatic BUY/SELL
  // when analyses do not agree. This is a dashboard display guard only.
  const finalAgreement = String(agreement || "").toUpperCase();
  let action = "WAIT / MANUAL REVIEW";
  if (finalAgreement === "FULL AGREEMENT") {
    const signals = [
      data.technical_signal,
      data.astrology_signal,
      data.numerology_signal
    ].map(x => String(x || "").toUpperCase());

    if (signals.every(x => x.includes("BUY") || x === "BULLISH")) action = "BUY";
    else if (signals.every(x => x.includes("SELL") || x === "BEARISH")) action = "SELL";
  }
  $("action").textContent = action;
  $("action").className = tone(action);

  const technical = data.technical || {};
  const astrology = data.astrology || {};
  const numerology = data.numerology || {};
  const trend = technical.trend || {};

  paint($("technicalSignal"), technical.signal);
  $("technicalScore").textContent = scoreText(technical.confidence);

  paint($("astroBias"), astrology.bias);
  $("astroScore").textContent = scoreText(astrology.score);

  paint($("numBias"), numerology.bias);
  $("numScore").textContent = scoreText(numerology.score);

  $("agreementTechnical").textContent = text(data.technical_signal || technical.signal);
  $("agreementAstro").textContent = text(data.astrology_signal || astrology.bias);
  $("agreementNum").textContent = text(data.numerology_signal || numerology.bias);
  $("agreementFinal").textContent = text(agreement || recommendation);
  $("agreementFinal").className = tone(agreement || recommendation);

  const tfBox = $("timeframes");
  tfBox.innerHTML = "";
  ["5m", "15m", "1h", "1d"].forEach(tf => {
    const x = trend[tf] || {};
    const pct = Math.max(0, Math.min(100, Math.abs(Number(x.score || 0)) * 2));
    tfBox.innerHTML += `
      <div class="tf">
        <div class="name">${tf}</div>
        <div class="trend ${tone(x.trend)}">${text(x.trend)}</div>
        <div class="score">Score: ${text(x.score, "0")}</div>
        <div class="bar"><i style="width:${pct}%"></i></div>
      </div>`;
  });

  const five = trend["5m"] || {};
  $("ema9").textContent = text(five.ema9);
  $("ema50").textContent = text(five.ema50);
  $("ema200").textContent = text(five.ema200);

  const reasons = [
    ...(technical.reasons || []),
    ...(astrology.reasons || []),
    ...(numerology.reasons || [])
  ];

  const uniqueReasons = [...new Set(reasons)].slice(0, 12);
  $("reasons").innerHTML = uniqueReasons.length
    ? uniqueReasons.map(r => `<div class="reason">• ${escapeHTML(r)}</div>`).join("")
    : `<div class="small">No reasons returned.</div>`;
}

function escapeHTML(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function loadStats() {
  const data = await getJSON("/stats");
  $("totalTrades").textContent = data.total_trades ?? 0;
  $("wins").textContent = data.wins ?? 0;
  $("losses").textContent = data.losses ?? 0;
  $("openTrades").textContent = data.open_trades ?? 0;
  $("winRate").textContent = `${data.win_rate ?? 0}%`;
  $("netPnl").textContent = `₹${data.net_pnl ?? 0}`;
}

async function loadHistory() {
  const history = await getJSON("/api/history");
  const table = $("tradeTable");
  table.innerHTML = "";

  const labels = [];
  const values = [];

  history.forEach((t, i) => {
    table.innerHTML += `<tr>
      <td>${i + 1}</td>
      <td>${escapeHTML(t.symbol)}</td>
      <td>${escapeHTML(t.side)}</td>
      <td>${escapeHTML(t.entry)}</td>
      <td>${escapeHTML(t.exit)}</td>
      <td>${escapeHTML(t.pnl)}</td>
      <td>${escapeHTML(t.status)}</td>
    </tr>`;
    labels.push(t.symbol);
    values.push(Number(t.pnl) || 0);
  });

  drawChart(labels, values);
}

function drawChart(labels, values) {
  const ctx = $("equityChart");
  if (equityChart) equityChart.destroy();

  equityChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [{
        label: "P&L",
        data: values,
        tension: 0.25
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { labels: { color: "#dce7f8" } } },
      scales: {
        x: { ticks: { color: "#8fa0b9" } },
        y: { ticks: { color: "#8fa0b9" } }
      }
    }
  });
}

async function loadScanner() {
  const data = await getJSON("/api/scanner");
  const box = $("scannerSignals");
  box.innerHTML = "";

  data.forEach(s => {
    const signal = s.signal || "WAIT";
    box.innerHTML += `
      <div class="scanner-card">
        <div><b>${escapeHTML(s.symbol)}</b></div>
        <div class="${tone(signal)}" style="font-size:20px;font-weight:bold">${escapeHTML(signal)}</div>
        <div class="small">Strength: ${escapeHTML(s.strength ?? "—")}</div>
      </div>`;
  });
}

async function refreshDashboard() {
  try {
    await Promise.all([
      loadAnalysis(),
      loadStats(),
      loadHistory(),
      loadScanner()
    ]);
    $("lastUpdate").textContent =
      "🟢 Updated " + new Date().toLocaleTimeString();
  } catch (e) {
    console.error(e);
    $("lastUpdate").textContent = "🔴 Update error";
  }
}

refreshDashboard();
setInterval(refreshDashboard, 10000);
