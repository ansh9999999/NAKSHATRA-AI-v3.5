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
  text("agreeFinal", typeof agreement === "string" ? agreement : (agreement.final || agreement.status || "—"));

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
