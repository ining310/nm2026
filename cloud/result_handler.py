"""
POST /result
Called by the RPi once after motors finish.
Sends an IOTA reward (if eligible) and pushes a LINE result message.
"""
import json
import os

from shared import db, iota, line_bot

_CATEGORY_ZH = {
    "plastic": "塑膠",
    "metal":   "金屬",
    "paper":   "紙類",
    "other":   "其他",
}


def handler(event, context):
    # ── parse body ────────────────────────────────────────────────────────────
    try:
        body           = json.loads(event.get("body") or "{}")
        session_id     = body["session_id"]
        category       = body["predicted_category"]
        confidence     = float(body["confidence"])
        reward_eligible = bool(body.get("reward_eligible", False))
        reason         = body.get("reason", "")
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        return _resp(400, {"ok": False, "error": f"Bad request: {exc}"})

    # ── fetch session ─────────────────────────────────────────────────────────
    session = db.get_session(session_id)
    if not session:
        return _resp(404, {"ok": False, "error": "Session not found"})

    line_user_id   = session["user_line_id"]
    wallet_address = session["user_wallet_address"]
    cat_zh         = _CATEGORY_ZH.get(category, category)

    tx_digest    = None
    explorer_url = None

    # ── reward path ───────────────────────────────────────────────────────────
    if reward_eligible:
        # 1. LINE 先通知（不等 IOTA）
        try:
            line_bot.push(line_user_id, (
                f"♻️ 分類成功！\n"
                f"類別：{cat_zh}\n"
                f"信心度：{confidence:.0%}\n\n"
                f"🎉 正在發放 3 IOTA 獎勵至您的錢包，請稍候…"
            ))
        except Exception as line_exc:
            print(f"[ERROR] LINE push (pre-IOTA) failed: {line_exc}")

        # 2. IOTA 送金
        try:
            amount_mist = int(os.environ["IOTA_REWARD_AMOUNT_MIST"])
            tx           = iota.send_reward(wallet_address, amount_mist)
            tx_digest    = tx["digest"]
            explorer_url = tx["explorer_url"]

            line_bot.push(line_user_id, f"🔗 {explorer_url}")
        except Exception as exc:
            print(f"[ERROR] IOTA send_reward: {exc}")
            try:
                line_bot.push(line_user_id, (
                    f"獎勵發送失敗，請聯繫管理員。\n錯誤：{exc}"
                ))
            except Exception as line_exc:
                print(f"[ERROR] LINE push (IOTA error) failed: {line_exc}")

    # ── no-reward path ────────────────────────────────────────────────────────
    else:
        try:
            line_bot.push(line_user_id, (
                f"❌ 無法明確分類\n"
                f"類別：{cat_zh}\n"
                f"信心度：{confidence:.0%}\n"
                f"原因：{reason}\n\n"
                f"本次無獎勵。請確認物品類別後再試。"
            ))
        except Exception as exc:
            print(f"[ERROR] LINE push failed: {exc}")

    # ── persist result ────────────────────────────────────────────────────────
    db.update_result(session_id, body, tx_digest, explorer_url)
    return _resp(200, {
        "ok":               True,
        "rewarded":         reward_eligible and tx_digest is not None,
        "iota_tx_digest":   tx_digest,
        "iota_explorer_url": explorer_url,
    })


def _resp(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }
