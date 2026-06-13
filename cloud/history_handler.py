"""
GET /history?wallet_address=0x...&line_user_id=Uxxxx
Returns all recycling sessions for a wallet address, newest first.
"""
import json

from shared import db


def handler(event, context):
    params = event.get("queryStringParameters") or {}
    wallet_address = params.get("wallet_address", "").strip()
    line_user_id   = params.get("line_user_id", "").strip()

    if not wallet_address:
        return _resp(400, {"ok": False, "error": "Missing wallet_address"})

    sessions = db.get_history_by_wallet(wallet_address, line_user_id)
    return _resp(200, {"ok": True, "sessions": sessions})


def _resp(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type":                "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }
