// Dashboard Data Loader

let chart = null;

async function loadDashboard() {

    try {

        // Stats
        const statsResponse = await fetch("/api/stats");
        const stats = await statsResponse.json();

        document.getElementById("totalTrades").innerText = stats.total_trades ?? 0;
        document.getElementById("wins").innerText = stats.wins ?? 0;
        document.getElementById("losses").innerText = stats.losses ?? 0;
        document.getElementById("openTrades").innerText = stats.open_trades ?? 0;
        document.getElementById("winRate").innerText = (stats.win_rate ?? 0) + "%";
        document.getElementById("netPnl").innerText = "₹ " + (stats.net_pnl ?? 0);

        // Trade History
        const historyResponse = await fetch("/api/history");
        const history = await historyResponse.json();

        let table = "";

        history.forEach((trade) => {

            table += `
            <tr>
                <td>${trade.id}</td>
                <td>${trade.symbol}</td>
                <td>${trade.signal}</td>
                <td>${trade.entry}</td>
                <td>${trade.exit ?? "-"}</td>
                <td>${trade.pnl}</td>
                <td>${trade.result}</td>
            </tr>
            `;

        });

        document.getElementById("tradeTable").innerHTML = table;

        // Scanner
        const scannerResponse = await fetch("/api/scanner");
        const scanner = await scannerResponse.json();

        let scanHTML = "";

        scanner.forEach((s) => {

            scanHTML += `
            <p>
                ${s.symbol}
                |
                ${s.signal}
                |
                Confidence ${s.confidence}%
            </p>
            `;

        });

        document.getElementById("scannerSignals").innerHTML =
            scanHTML || "No Signals";

        // Equity Chart
        const pnlData = history.map(x => x.pnl);
        const labels = history.map(x => x.id);

        if (chart !== null) {
            chart.destroy();
        }

        chart = new Chart(document.getElementById("equityChart"), {

            type: "line",

            data: {

                labels: labels,

                datasets: [{

                    label: "Equity",

                    data: pnlData,

                    borderWidth: 3,

                    fill: false

                }]

            },

            options: {

                responsive: true,

                maintainAspectRatio: false

            }

        });

    }

    catch (err) {

        console.log(err);

    }

}

loadDashboard();

setInterval(loadDashboard, 10000);
