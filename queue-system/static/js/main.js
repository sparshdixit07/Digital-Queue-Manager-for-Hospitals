// main.js - handles public token generation and live queue

async function fetchStatsAndQueue() {
  try {
    const [statsRes, tokensRes] = await Promise.all([
      fetch("/api/stats"),
      fetch("/api/tokens?served=0")
    ]);
    const stats = await statsRes.json();
    const waitingTokens = await tokensRes.json();

    document.getElementById("statTotal").innerText = stats.total || 0;
    document.getElementById("statWaiting").innerText = stats.waiting || 0;
    document.getElementById("statServed").innerText = stats.served || 0;

    const list = document.getElementById("queueList");
    list.innerHTML = "";
    if (waitingTokens.length === 0) {
      list.innerHTML = "<p class='muted'>No waiting tokens right now.</p>";
      return;
    }
    waitingTokens.forEach(t => {
      const el = document.createElement("div");
      el.className = "tokenCard";
      el.innerHTML = `
        <div>
          <div class="leftTok">${t.token_number}</div>
          <div class="meta">${t.category} • ${t.name || "Guest"} • ${new Date(t.issued_at).toLocaleTimeString()}</div>
        </div>
        <div style="text-align:right">
          <div class="meta">#${t.id}</div>
        </div>
      `;
      list.appendChild(el);
    });
  } catch (e) {
    console.error("Failed to fetch queue", e);
  }
}

document.getElementById("refreshBtn").addEventListener("click", fetchStatsAndQueue);

document.getElementById("tokenForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const name = document.getElementById("name").value;
  const mobile = document.getElementById("mobile").value;
  const category = document.getElementById("category").value;

  try {
    const res = await fetch("/api/generate_token", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({name, mobile, category})
    });
    const data = await res.json();
    if (data.success) {
      document.getElementById("tokenNumber").innerText = data.token;
      document.getElementById("smallInfo").innerText = `Type: ${category.toUpperCase()} • Time: ${new Date().toLocaleTimeString()}`;
      document.getElementById("result").classList.remove("hidden");
      fetchStatsAndQueue();
    } else {
      alert("Failed to create token");
    }
  } catch (err) {
    console.error(err);
    alert("Error generating token");
  }
});

document.getElementById("printBtn").addEventListener("click", () => {
  // Simple print popup
  const token = document.getElementById("tokenNumber").innerText;
  const html = `
    <div style="font-family:sans-serif;padding:20px;">
      <h2>Token: ${token}</h2>
      <p>${document.getElementById("smallInfo").innerText}</p>
    </div>`;
  const w = window.open("", "_blank");
  w.document.write(html);
  w.print();
  w.close();
});

// auto refresh every 6 seconds
fetchStatsAndQueue();
setInterval(fetchStatsAndQueue, 6000);