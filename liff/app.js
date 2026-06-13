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

// ── Tab switching ─────────────────────────────────────────────────────────────
function switchTab(name) {
  document.getElementById("tab-pay").style.display     = (name === "pay")     ? "" : "none";
  document.getElementById("tab-history").style.display = (name === "history") ? "" : "none";

  document.getElementById("tab-btn-pay").classList.toggle("active",     name === "pay");
  document.getElementById("tab-btn-history").classList.toggle("active", name === "history");

  if (name === "history") loadHistory();
}

// ── History: load ─────────────────────────────────────────────────────────────
async function loadHistory() {
  const walletAddr = document.getElementById("wallet").value.trim();
  if (!walletAddr) {
    document.getElementById("balance-amount").textContent = "—";
    document.getElementById("balance-address-text").textContent = "";
    document.getElementById("sessions-list").innerHTML =
      '<p class="empty-msg">請先在「投遞」頁面填入錢包地址</p>';
    return;
  }

  document.getElementById("balance-amount").textContent = "…";
  document.getElementById("balance-address-text").textContent = "";
  document.getElementById("sessions-list").innerHTML = '<p class="empty-msg">載入中…</p>';

  const uid = lineUserId || "";
  const [histData, balData] = await Promise.all([
    fetch(`${API_BASE}/history?wallet_address=${encodeURIComponent(walletAddr)}&line_user_id=${encodeURIComponent(uid)}`)
      .then((r) => r.json()).catch(() => null),
    fetch(`${API_BASE}/balance?wallet_address=${encodeURIComponent(walletAddr)}`)
      .then((r) => r.json()).catch(() => null),
  ]);

  const sessions = histData ? (histData.sessions || []) : [];
  renderBalance(balData, walletAddr, sessions);
  renderSessions(histData ? sessions : null);
}

// ── History: render balance ───────────────────────────────────────────────────
function renderBalance(data, walletAddr, sessions = []) {
  const amountEl  = document.getElementById("balance-amount");
  const addrText  = document.getElementById("balance-address-text");
  const linkEl    = document.getElementById("balance-link");
  const statsEl   = document.getElementById("balance-stats");

  amountEl.textContent = (data && data.ok) ? data.balance_iota.toFixed(1) : "—";
  addrText.textContent = walletAddr;
  linkEl.href = `https://explorer.iota.org/address/${walletAddr}?network=devnet`;

  // Stats
  const total    = sessions.length;
  const rewarded = sessions.filter((s) => s.rewarded).length;
  const rate     = total > 0 ? Math.round((rewarded / total) * 100) : 0;

  if (total === 0) {
    statsEl.innerHTML = "";
    return;
  }
  statsEl.innerHTML = `
    <div class="balance-stat">
      <span class="balance-stat-value">${total}</span>
      <span class="balance-stat-label">次投遞</span>
    </div>
    <div class="balance-stat">
      <span class="balance-stat-value">${rewarded}</span>
      <span class="balance-stat-label">次獲獎</span>
    </div>
    <div class="balance-stat">
      <span class="balance-stat-value">${rate}%</span>
      <span class="balance-stat-label">成功率</span>
    </div>`;
}

// ── History: render session list ──────────────────────────────────────────────
function renderSessions(sessions) {
  const el = document.getElementById("sessions-list");

  if (sessions === null) {
    el.innerHTML = '<p class="empty-msg">載入失敗，請稍後再試</p>';
    return;
  }
  if (sessions.length === 0) {
    el.innerHTML = '<p class="empty-msg">尚無投遞記錄</p>';
    return;
  }

  el.innerHTML = sessions.map((s) => sessionRowHTML(s)).join("");
}

// ── History: single row ───────────────────────────────────────────────────────
function sessionRowHTML(s) {
  const isPending  = s.status === "paid";
  const isRewarded = s.rewarded;

  // Icon
  let iconColor, iconSVG;
  if (isPending) {
    iconColor = "gray";
    iconSVG = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none"
      stroke="#8FA3BC" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`;
  } else if (isRewarded) {
    iconColor = "green";
    iconSVG = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none"
      stroke="#15643C" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <polyline points="1 4 1 10 7 10"/>
      <polyline points="23 20 23 14 17 14"/>
      <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4-4.64 4.36A9 9 0 0 1 3.51 15"/></svg>`;
  } else {
    iconColor = "red";
    iconSVG = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none"
      stroke="#B91C1C" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="12" cy="12" r="10"/>
      <line x1="15" y1="9" x2="9" y2="15"/>
      <line x1="9" y1="9" x2="15" y2="15"/></svg>`;
  }

  // Title
  const title = isPending ? "等待偵測中"
    : (s.category_zh || s.predicted_category || "無法辨識");

  // "我" chip
  const mineChip = s.is_mine ? `<span class="chip-mine">我</span>` : "";

  // Meta left: date + confidence
  let metaLeft = fmtDate(s.created_at);
  if (!isPending && s.confidence > 0) {
    metaLeft += `　信心度 ${Math.round(s.confidence * 100)}%`;
  }

  // Reward right (same line as meta)
  let rewardRight = "";
  if (!isPending) {
    if (isRewarded) {
      const linkHTML = s.iota_explorer_url
        ? `<a class="explorer-link" href="${escHtml(s.iota_explorer_url)}" target="_blank" rel="noopener">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
              <polyline points="15 3 21 3 21 9"/>
              <line x1="10" y1="14" x2="21" y2="3"/>
            </svg>
          </a>` : "";
      rewardRight = `<span class="reward-green">+3 IOTA${linkHTML}</span>`;
    } else {
      rewardRight = `<span class="reward-gray">未獲獎勵</span>`;
    }
  }

  return `
    <div class="session-row">
      <div class="session-icon ${iconColor}">${iconSVG}</div>
      <div class="session-body">
        <div class="session-top">
          <span class="session-title">${escHtml(title)}</span>
          ${mineChip}
        </div>
        <div class="session-meta">
          <span class="meta-left">${metaLeft}</span>
          ${rewardRight}
        </div>
      </div>
    </div>`;
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function fmtDate(ts) {
  if (!ts) return "";
  return new Date(ts * 1000).toLocaleString("zh-TW", {
    timeZone: "Asia/Taipei",
    month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit",
    hour12: false,
  });
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

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

    btn.innerHTML = `
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="20 6 9 17 4 12"/>
      </svg>
      已登記`;

    // Next-step callout: guide user to press the physical machine button
    msg.className = "";
    msg.innerHTML = `
      <div class="next-step">
        <div class="next-step-icon">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
               stroke="#15643C" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
        </div>
        <div class="next-step-body">
          <div class="next-step-done">登記成功</div>
          <div class="next-step-action">
            放上物品後，按下
            <span class="press-icon">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                   stroke="#1A5C42" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="5" y="2" width="14" height="20" rx="3"/>
                <line x1="12" y1="6" x2="12" y2="10"/>
              </svg>
            </span>
            機台上的按鈕
          </div>
        </div>
      </div>`;

  } catch (err) {
    setMsg(ICON_ERR, `登記失敗：${err.message}`, "error");
    btn.disabled = false;
    btn.innerHTML = `
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <line x1="5" y1="12" x2="19" y2="12"/>
        <polyline points="12 5 19 12 12 19"/>
      </svg>
      確認投遞`;
  }
}

function setMsg(iconHtml, text, state) {
  msg.innerHTML = `${iconHtml}<span>${text}</span>`;
  msg.className = state;
}

function clearMsg() {
  msg.innerHTML = "";
  msg.className = "hidden";
}
