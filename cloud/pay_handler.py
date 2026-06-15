"""
POST /pay
Called by the LIFF page after the user confirms payment.
Writes a session to DynamoDB and pushes a LINE message.
"""
import json

from shared import db, line_bot


def handler(event, context):
    # ── parse body ────────────────────────────────────────────────────────────
    try:
        body = json.loads(event.get("body") or "{}")
        session_id     = body["session_id"]
        machine_id     = body["machine_id"]
        line_user_id   = body["line_user_id"]
        wallet_address = body["wallet_address"]
    except (KeyError, json.JSONDecodeError) as exc:
        return _resp(400, {"ok": False, "error": f"Bad request: {exc}"})

    # ── daily limit ───────────────────────────────────────────────────────────
    DAILY_LIMIT = 500
    try:
        if db.count_today(line_user_id) >= DAILY_LIMIT:
            return _resp(429, {"ok": False, "error": f"Daily limit of {DAILY_LIMIT} recycles reached. Try again tomorrow."})
    except Exception as exc:
        print(f"[WARN] /pay count_today failed: {exc}")

    # ── persist session ───────────────────────────────────────────────────────
    try:
        db.create_session(session_id, machine_id, line_user_id, wallet_address)
    except Exception as exc:
        # ConditionalCheckFailedException means duplicate session_id
        print(f"[ERROR] /pay db.create_session: {exc}")
        return _resp(409, {"ok": False, "error": "Session already exists"})


    # ── bind wallet address to LINE user ─────────────────────────────────────
    try:
        db.save_wallet(line_user_id, wallet_address)
    except Exception as exc:
        print(f"[WARN] /pay db.save_wallet: {exc}")

    # ── notify user ───────────────────────────────────────────────────────────
    try:
        line_bot.push(
            line_user_id,
            "✅ 登記成功！\n\n"
            "請將垃圾放上偵測平台，\n"
            "再按下機台上的按鈕開始偵測。\n\n"
            "AI 判斷可回收即可獲得 3 IOTA 獎勵。",
        )
    except Exception as exc:
        # LINE push failure is non-fatal; session is already created
        print(f"[WARN] /pay LINE push failed: {exc}")

    return _resp(200, {"ok": True})


def _resp(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type":                "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }
