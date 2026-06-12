"""
GET /check?machine_id=<id>
Called by the RPi immediately after the physical button is pressed.
Returns {"status": "paid", "session_id": "..."} or {"status": "waiting"}.
"""
import json

from shared import db


def handler(event, context):
    params = (event.get("queryStringParameters") or {})
    machine_id = params.get("machine_id")
    if not machine_id:
        return _resp(400, {"status": "error", "error": "machine_id is required"})

    session = db.get_paid_session(machine_id)
    if session:
        return _resp(200, {
            "status":     "paid",
            "session_id": session["session_id"],
        })
    return _resp(200, {"status": "waiting"})


def _resp(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
