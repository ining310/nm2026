// ── config (replace before deploying) ──────────────────────────────────────
const LIFF_ID  = "2010382965-397QCX0y";
const API_BASE = "https://wsmw87jtx4.execute-api.ap-northeast-1.amazonaws.com/Prod";
// ─────────────────────────────────────────────────────────────────────────────

// ── Demo wallets (pre-funded devnet addresses) ────────────────────────────────
const DEMO_WALLETS = [
  "0x43cd396a1525b4f2f92c5f533c5a4340f574cce93afe26851552d7189441022f",
  "0x2d688b5ba7418daf47e74361213832066f5fba740d50ff95321ade12cd6a9929",
  "0xe35bad3d30e2e0a295f558569593d462f24e0a58aa16c4809dea445873baf6cd",
  "0xffbe22613a79d77427d1425225c597cef6a42a75ad18b718e70753e4cc672d83",
];

function selectDemo(index) {
  document.getElementById("wallet").value = DEMO_WALLETS[index];
  document.querySelectorAll(".demo-btn").forEach((b, i) => {
    b.classList.toggle("active", i === index);
  });
}
// ─────────────────────────────────────────────────────────────────────────────

const btn = document.getElementById("payBtn");
const msg = document.getElementById("msg");
let lineUserId = null;

// SVG icon snippets reused in status messages
const ICON_OK = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none"
  stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="20 6 9 17 4 12"/></svg>`;

const ICON_ERR = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none"
  stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="10"/>
  <line x1="12" y1="8" x2="12" y2="12"/>
  <line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;

// ── LIFF init ─────────────────────────────────────────────────────────────────
liff.init({ liffId: LIFF_ID })
  .then(() => {
    if (!liff.isLoggedIn()) {
      liff.login({ redirectUri: location.href });
      return;
    }
    return liff.getProfile();
  })
  .then((profile) => {
    if (!profile) return;
    lineUserId = profile.userId;
    return fetch(`${API_BASE}/wallet?line_user_id=${encodeURIComponent(lineUserId)}`);
  })
  .then((resp) => resp && resp.json())
  .then((data) => {
    if (data && data.wallet_address) {
      document.getElementById("wallet").value = data.wallet_address;
    }
  })
  .catch((err) => {
    setMsg(ICON_ERR, `LIFF 初始化失敗：${err.message}`, "error");
    btn.disabled = true;
  });

// ── pay ───────────────────────────────────────────────────────────────────────
async function pay() {
  const walletAddr = document.getElementById("wallet").value.trim();

  if (!walletAddr.match(/^0x[0-9a-fA-F]{64}$/)) {
    setMsg(ICON_ERR, "錢包地址格式不正確（需為 0x + 64 位十六進位）", "error");
    return;
  }
  if (!lineUserId) {
    setMsg(ICON_ERR, "尚未取得 LINE 使用者資訊，請重新整理頁面。", "error");
    return;
  }

  // Show spinner in button
  btn.disabled = true;
  btn.innerHTML = `<span class="spin"></span> 處理中…`;
  clearMsg();

  const params    = new URLSearchParams(location.search);
  const machineId = params.get("machine_id") || "machine_001";
  const sessionId = crypto.randomUUID();

  try {
    const resp = await fetch(`${API_BASE}/pay`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({
        session_id:     sessionId,
        machine_id:     machineId,
        line_user_id:   lineUserId,
        wallet_address: walletAddr,
      }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${resp.status}`);
    }

    setMsg(ICON_OK, "已登記！請將垃圾放上偵測平台，再按下機台按鈕。", "success");
    // Keep button disabled — one session per scan
    btn.innerHTML = `
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="20 6 9 17 4 12"/>
      </svg>
      已確認`;

  } catch (err) {
    setMsg(ICON_ERR, `登記失敗：${err.message}`, "error");
    btn.disabled = false;
    btn.innerHTML = `
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <line x1="5" y1="12" x2="19" y2="12"/>
        <polyline points="12 5 19 12 12 19"/>
      </svg>
      確認付款`;
  }
}

function setMsg(iconHtml, text, state) {
  msg.innerHTML = `${iconHtml}<span>${text}</span>`;
  msg.className = state; // "success" | "error" | ""
}

function clearMsg() {
  msg.innerHTML = "";
  msg.className = "hidden";
}
