async function loadStats(){

    const response=await fetch("/stats");
    const data=await response.json();

    document.getElementById("total").innerText=data.total_trades;
    document.getElementById("wins").innerText=data.wins;
    document.getElementById("losses").innerText=data.losses;
    document.getElementById("open").innerText=data.open_trades;
    document.getElementById("rate").innerText=data.win_rate+"%";
    document.getElementById("pnl").innerText=data.net_pnl;
}

async function loadTrades(){

    const response=await fetch("/trades");
    const data=await response.json();

    const table=document.getElementById("tradeTable");

    table.innerHTML="";

    data.trades.forEach(function(trade){

        table.innerHTML+=`
        <tr>
            <td>${trade[0]}</td>
            <td>${trade[2]}</td>
            <td>${trade[3]}</td>
            <td>${trade[4]}</td>
            <td>${trade[8]}</td>
            <td>${trade[13]}</td>
        </tr>
        `;
    });

}

loadStats();
loadTrades();

setInterval(function(){

    loadStats();
    loadTrades();

},5000);
