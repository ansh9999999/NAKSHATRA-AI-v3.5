// ======================================
// NAKSHATRA AI Dashboard v2.0
// static/app.js
// ======================================

let equityChart = null;

// =======================
// Dashboard Stats
// =======================
async function loadStats() {

    const response = await fetch("/stats");
    const data = await response.json();

    document.getElementById("totalTrades").textContent =
        data.total_trades;

    document.getElementById("wins").textContent =
        data.wins;

    document.getElementById("losses").textContent =
        data.losses;

    document.getElementById("openTrades").textContent =
        data.open_trades;

    document.getElementById("winRate").textContent =
        data.win_rate + "%";

    document.getElementById("netPnl").textContent =
        "₹" + data.net_pnl;

}

// =======================
// Trade History
// =======================
async function loadHistory() {

    const response = await fetch("/api/history");
    const history = await response.json();

    const table =
        document.getElementById("tradeTable");

    table.innerHTML = "";

    const labels = [];
    const pnl = [];

    history.forEach((trade, index) => {

        table.innerHTML += `
        <tr>
            <td>${index + 1}</td>
            <td>${trade.symbol}</td>
            <td>${trade.side}</td>
            <td>${trade.entry}</td>
            <td>${trade.exit}</td>
            <td>${trade.pnl}</td>
            <td>${trade.status}</td>
        </tr>
        `;

        labels.push(trade.symbol);
        pnl.push(trade.pnl);

    });

    drawChart(labels, pnl);

}

// =======================
// Scanner
// =======================
async function loadScanner() {

    const response =
        await fetch("/api/scanner");

    const data =
        await response.json();

    const scanner =
        document.getElementById("scannerSignals");

    scanner.innerHTML = "";

    data.forEach((item) => {

        scanner.innerHTML += `
        <div class="scanner-card">

            <h3>${item.symbol}</h3>

            <h2>${item.signal}</h2>

            <p>${item.strength}</p>

        </div>
        `;

    });

}

// =======================
// Equity Chart
// =======================
function drawChart(labels, values) {

    const ctx =
        document.getElementById("equityChart");

    if (equityChart) {
        equityChart.destroy();
    }

    equityChart = new Chart(ctx, {

        type: "line",

        data: {

            labels: labels,

            datasets: [

                {
                    label: "PnL",

                    data: values,

                    tension: 0.3,

                    fill: false

                }

            ]

        },

        options: {

            responsive: true,

            maintainAspectRatio: false

        }

    });

}

// =======================
// Refresh Dashboard
// =======================
async function refreshDashboard() {

    try {

        await loadStats();

        await loadHistory();

        await loadScanner();

    }

    catch (error) {

        console.error(
            "Dashboard Error:",
            error
        );

    }

}

// =======================
// Auto Refresh
// =======================

refreshDashboard();

setInterval(
    refreshDashboard,
    10000
);
