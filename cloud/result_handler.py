"""
POST /result
Called by the RPi once after motors finish.
Sends an IOTA reward (if eligible) and pushes a LINE result message.
"""
import json
import os

from shared import db, iota, line_bot

_CATEGORY_ZH = {
    "metal_can":           "金屬罐",
    "plastic_bottle":      "塑膠瓶",
    "paper":               "紙類",
    "glass":               "玻璃",
    "general_waste":       "一般垃圾",
    "unknown":             "無法辨識",
    "multiple_categories": "多種類別混合",
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
        try:
            amount_mist = int(os.environ["IOTA_REWARD_AMOUNT_MIST"])
            tx          = iota.send_reward(wallet_address, amount_mist)
            tx_digest    = tx["digest"]
            explorer_url = tx["explorer_url"]

            line_bot.push(line_user_id, (
                f"♻️ 分類成功！\n"
                f"類別：{cat_zh}\n"
                f"信心度：{confidence:.0%}\n\n"
                f"🎉 已發放 3 IOTA 獎勵至您的錢包。\n\n"
                f"🔗 鏈上驗證（可截圖給助教）：\n{explorer_url}"
            ))
        except Exception as exc:
            print(f"[ERROR] IOTA send_reward: {exc}")
            try:
                line_bot.push(line_user_id, (
                    f"♻️ 分類成功，但獎勵發送失敗，請聯繫管理員。\n"
                    f"類別：{cat_zh}｜信心度：{confidence:.0%}\n"
                    f"錯誤：{exc}"
                ))
            except Exception as line_exc:
                print(f"[ERROR] LINE push failed: {line_exc}")

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
    return _resp(200, {"ok": True})


def _resp(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }
