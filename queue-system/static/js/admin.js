// admin.js - admin dashboard interactions
async function loadAdmin() {
  try {
    const [statsRes, waitingRes, allRes] = await Promise.all([
      fetch("/api/stats"),
      fetch("/api/tokens?served=0"),
      fetch("/api/tokens")
    ]);
    const stats = await statsRes.json();
    const waiting = await waitingRes.json();
    const all = await allRes.json();

    document.getElementById("aTotal").innerText = stats.total;
    document.getElementById("aWaiting").innerText = stats.waiting;
    document.getElementById("aServed").innerText = stats.served;

    // waiting table
    const waitDiv = document.getElementById("waitingTable");
    waitDiv.innerHTML = "<div class='row header'><div class='col'>Token</div><div class='col'>Category</div><div class='col'>Name</div><div class='col'>Issued</div><div style='width:170px'>Action</div></div>";
    waiting.forEach(t => {
      const row = document.createElement("div");
      row.className = "row";
      row.innerHTML = `
        <div class="col">${t.token_number}</div>
        <div class="col">${t.category}</div>
        <div class="col">${t.name || "-"}</div>
        <div class="col">${new Date(t.issued_at).toLocaleTimeString()}</div>
        <div style="width:170px">
          <button class="btn" onclick="serveToken(${t.id})">Serve</button>
        </div>
      `;
      waitDiv.appendChild(row);
    });

    // all tokens table
    const allDiv = document.getElementById("allTable");
    allDiv.innerHTML = "<div class='row header'><div class='col'>Token</div><div class='col'>Category</div><div class='col'>Name</div><div class='col'>Issued</div><div class='col'>Served</div></div>";
    all.forEach(t => {
      const row = document.createElement("div");
      row.className = "row";
      row.innerHTML = `
        <div class="col">${t.token_number}</div>
        <div class="col">${t.category}</div>
        <div class="col">${t.name || "-"}</div>
        <div class="col">${new Date(t.issued_at).toLocaleTimeString()}</div>
        <div class="col">${t.served ? "Yes (" + (t.counter || "-") + ")" : "No"}</div>
      `;
      allDiv.appendChild(row);
    });

  } catch (e) {
    console.error("admin load error", e);
  }
}

async function serveToken(id) {
  const counter = document.getElementById("counterInput").value || "";
  try {
    const res = await fetch("/api/serve_token", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({id, counter})
    });
    const data = await res.json();
    if (data.success) {
      loadAdmin();
    } else {
      alert(data.error || "Failed to serve");
    }
  } catch (e) {
    console.error(e);
    alert("Error serving token");
  }
}

document.getElementById("serveNextBtn").addEventListener("click", async () => {
  const counter = document.getElementById("counterInput").value || "";
  try {
    const res = await fetch("/api/serve_next", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({counter})
    });
    const data = await res.json();
    if (data.success) {
      loadAdmin();
      alert("Served: " + (data.token ? data.token.token_number : ""));
    } else {
      alert(data.error || "No tokens to serve");
    }
  } catch (e) {
    console.error(e);
    alert("Error while serving next");
  }
});

loadAdmin();
setInterval(loadAdmin, 5000);
