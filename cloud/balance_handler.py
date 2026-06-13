"""
GET /balance?wallet_address=0x...
Returns the total IOTA balance for a wallet address via IOTA RPC.
"""
import json
import os

import requests


def handler(event, context):
    params = event.get("queryStringParameters") or {}
    wallet_address = params.get("wallet_address", "").strip()

    if not wallet_address:
        return _resp(400, {"ok": False, "error": "Missing wallet_address"})

    try:
        rpc_url = os.environ["IOTA_RPC_URL"]
        resp = requests.post(rpc_url, json={
            "jsonrpc": "2.0", "id": 1,
            "method": "iotax_getCoins",
            "params": [wallet_address, "0x2::iota::IOTA", None, None],
        }, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(data["error"])

        coins = data.get("result", {}).get("data", [])
        total_mist = sum(int(c.get("balance", 0)) for c in coins)
        balance_iota = round(total_mist / 1_000_000_000, 1)

        return _resp(200, {
            "ok":            True,
            "balance_iota":  balance_iota,
            "balance_mist":  total_mist,
        })
    except Exception as exc:
        return _resp(200, {"ok": False, "error": str(exc), "balance_iota": 0, "balance_mist": 0})


def _resp(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type":                "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }
