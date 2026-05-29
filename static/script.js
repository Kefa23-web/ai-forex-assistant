async function getSignal(){

    let pair =
    document.getElementById("pair").value;

    document.getElementById(
    "result"
    ).innerHTML = `

    <div class="loading">
        AI analyzing market...
    </div>

    `;

    let response = await fetch("/signal",{

        method:"POST",

        headers:{
            "Content-Type":"application/json"
        },

        body:JSON.stringify({
            pair:pair
        })
    });

    let data = await response.json();

    let signalClass = "";

    if(data.signal === "BUY"){
        signalClass = "buy";
    }

    else if(data.signal === "SELL"){
        signalClass = "sell";
    }

    else{
        signalClass = "wait";
    }

    document.getElementById(
    "result"
    ).innerHTML = `

    <div>

        <div class="signal ${signalClass}">
            ${data.signal}
        </div>

        <div class="price">
            ${data.price}
        </div>

        <div class="explanation">
            ${data.explanation}
        </div>

    </div>

    `;
}