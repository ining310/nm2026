"""
GET /wallet?line_user_id=Uxxxx
Returns the stored wallet address for a LINE user (or null if not found).
Called by the LIFF page to pre-fill the wallet input.
"""
import json

from shared import db


def handler(event, context):
    params = event.get("queryStringParameters") or {}
    line_user_id = params.get("line_user_id", "").strip()
    if not line_user_id:
        return _resp(400, {"ok": False, "error": "Missing line_user_id"})

    wallet_address = db.get_wallet(line_user_id)
    return _resp(200, {"ok": True, "wallet_address": wallet_address})


def _resp(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type":                "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }
