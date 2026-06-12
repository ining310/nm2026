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

    # ── persist session ───────────────────────────────────────────────────────
    try:
        db.create_session(session_id, machine_id, line_user_id, wallet_address)
    except Exception as exc:
        # ConditionalCheckFailedException means duplicate session_id
        print(f"[ERROR] /pay db.create_session: {exc}")
        return _resp(409, {"ok": False, "error": "Session already exists"})

    # ── notify user ───────────────────────────────────────────────────────────
    try:
        line_bot.push(
            line_user_id,
            "✅ 付款確認！\n\n"
            "請將垃圾放上偵測平台，\n"
            "再按下機台上的按鈕開始偵測。",
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
