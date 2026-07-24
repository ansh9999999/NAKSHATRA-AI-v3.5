// ===============================
// NAKSHATRA AI Dashboard v2.0
// static/app.js
// ===============================

let equityChart = null;

async function loadStats() {

    const response = await fetch("/stats");
    const data = await response.json();

    document.getElementById("totalTrades").innerText =
        data.total_trades;

    document.getElementById("wins").innerText =
        data.wins;

    document.getElementById("losses").innerText =
        data.losses;

    document.getElementById("openTrades").innerText =
        data.open_trades;

    document.getElementById("winRate").innerText =
        data.win_rate + "%";

    document.getElementById("netPnl").innerText =
        data.net_pnl;
}


async function loadHistory() {

    const response = await fetch("/api/history");
    const history = await response.json();

    const table =
        document.getElementById("tradeTable");

    table.innerHTML = "";

    let labels = [];
    let pnl = [];

    history.forEach((trade) => {

        table.innerHTML += `
        <tr>
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


async function loadScanner() {

    const response =
        await fetch("/api/scanner");

    const data =
        await response.json();

    const scanner =
        document.getElementById("scanner");

    scanner.innerHTML = "";

    data.forEach((item)=>{

        scanner.innerHTML += `
        <div class="scanner-card">

            <h3>${item.symbol}</h3>

            <h2>${item.signal}</h2>

            <p>${item.strength}</p>

        </div>
        `;

    });

}


function drawChart(labels,data){

    const ctx =
    document.getElementById("equityChart");

    if(equityChart){
        equityChart.destroy();
    }

    equityChart =
    new Chart(ctx,{

        type:"line",

        data:{

            labels:labels,

            datasets:[{

                label:"PnL",

                data:data

            }]
        }

    });

}


async function refreshDashboard(){

    await loadStats();

    await loadHistory();

    await loadScanner();

}


refreshDashboard();

setInterval(refreshDashboard,10000);
