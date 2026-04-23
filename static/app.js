const urlInput = document.getElementById("url");
const manifestInput = document.getElementById("manifest");
const verifyBtn = document.getElementById("verifyBtn");
const sampleBtn = document.getElementById("sampleBtn");
const refreshBtn = document.getElementById("refreshBtn");
const resultCard = document.getElementById("resultCard");
const historyBox = document.getElementById("history");

function decisionClass(decision) {
  if (decision === "accept") return "accept";
  if (decision === "pending") return "pending";
  return "reject";
}

function renderResult(result, id = null) {
  const reasonsHtml = result.reasons.map(item => `
    <li class="${item.ok ? "ok" : "ng"}">
      <strong>${item.item}</strong>: ${item.message}
    </li>
  `).join("");

  resultCard.className = `result-card ${decisionClass(result.decision)}`;
  resultCard.innerHTML = `
    <div class="result-head">
      <span class="decision ${decisionClass(result.decision)}">${result.decision.toUpperCase()}</span>
      <span class="score">Trust Score: ${Number(result.trust_score).toFixed(3)}</span>
      ${id ? `<span class="saved-id">Saved ID: ${id}</span>` : ""}
    </div>
    <div class="meta">
      <div><strong>Fail-Closed:</strong> ${result.fail_closed ? "true" : "false"}</div>
      <div><strong>Manifest SHA-256:</strong> <code>${result.manifest_sha256}</code></div>
      <div><strong>Verified At:</strong> ${result.verified_at}</div>
    </div>
    <ul class="reason-list">${reasonsHtml}</ul>
  `;
}

async function verifyAndSave() {
  const payload = {
    url: urlInput.value,
    manifest: manifestInput.value
  };

  const res = await fetch("/api/verify", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  const data = await res.json();
  if (!data.ok) {
    alert("検証に失敗しました。");
    return;
  }

  renderResult(data.result, data.id);
  await loadHistory();
}

async function loadHistory() {
  const res = await fetch("/api/results?limit=20");
  const data = await res.json();

  if (!data.ok || !data.items.length) {
    historyBox.innerHTML = `<div class="history-empty">履歴はまだありません。</div>`;
    return;
  }

  historyBox.innerHTML = data.items.map(item => `
    <div class="history-item">
      <div class="history-top">
        <span class="decision ${decisionClass(item.decision)}">${item.decision.toUpperCase()}</span>
        <span class="score">${Number(item.trust_score).toFixed(3)}</span>
      </div>
      <div><strong>ID:</strong> ${item.id}</div>
      <div><strong>URL:</strong> ${escapeHtml(item.input_url)}</div>
      <div><strong>Time:</strong> ${item.created_at}</div>
      <div><strong>SHA-256:</strong> <code>${item.manifest_sha256}</code></div>
      <button type="button" onclick="loadDetail(${item.id})">詳細表示</button>
    </div>
  `).join("");

  await loadDetail(data.items[0].id);
}

async function loadDetail(id) {
  const res = await fetch(`/api/results/${id}`);
  const data = await res.json();
  if (!data.ok) {
    alert("詳細取得に失敗しました。");
    return;
  }
  renderResult(data.item.result, data.item.id);
  urlInput.value = data.item.input_url;
  manifestInput.value = data.item.manifest_text;
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function loadSample() {
  urlInput.value = "https://example.com/verify";
  manifestInput.value = JSON.stringify({
    url: "https://example.com/verify",
    subject: {
      type: "verification_target",
      name: "sample artifact"
    },
    evidence: [
      { type: "sha256", ok: true },
      { type: "github_actions_receipt", ok: true }
    ],
    verification_policy: {
      fail_closed: true
    }
  }, null, 2);
}

verifyBtn.addEventListener("click", verifyAndSave);
sampleBtn.addEventListener("click", loadSample);
refreshBtn.addEventListener("click", loadHistory);

loadHistory();
