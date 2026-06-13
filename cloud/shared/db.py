"""DynamoDB helpers for recycling-sessions table."""
import json
import os
import time

import boto3
from boto3.dynamodb.conditions import Key

_table = None


def _get_table():
    global _table
    if _table is None:
        _table = boto3.resource("dynamodb").Table(os.environ["DYNAMODB_TABLE"])
    return _table


_profiles_table = None


def _get_profiles_table():
    global _profiles_table
    if _profiles_table is None:
        _profiles_table = boto3.resource("dynamodb").Table(os.environ["PROFILES_TABLE"])
    return _profiles_table


def create_session(
    session_id: str,
    machine_id: str,
    line_user_id: str,
    wallet_address: str,
) -> None:
    """Write a new session with status='paid'."""
    _get_table().put_item(
        Item={
            "session_id":           session_id,
            "machine_id":           machine_id,
            "status":               "paid",
            "user_line_id":         line_user_id,
            "user_wallet_address":  wallet_address,
            "created_at":           int(time.time()),
            "updated_at":           int(time.time()),
        },
        # Prevent overwriting an existing session with the same ID
        ConditionExpression="attribute_not_exists(session_id)",
    )


def get_paid_session(machine_id: str) -> dict | None:
    """Return the most recently created 'paid' session for a machine, or None."""
    resp = _get_table().query(
        IndexName="machine_id-status-index",
        KeyConditionExpression=(
            Key("machine_id").eq(machine_id) & Key("status").eq("paid")
        ),
    )
    items = resp.get("Items", [])
    if not items:
        return None
    return max(items, key=lambda s: int(s.get("created_at", 0)))



def count_today(line_user_id: str) -> int:
    """Return the number of sessions created today (UTC) for this LINE user."""
    import datetime
    today_start = int(
        datetime.datetime.now(datetime.timezone.utc)
        .replace(hour=0, minute=0, second=0, microsecond=0)
        .timestamp()
    )
    resp = _get_table().query(
        IndexName="user_line_id-created_at-index",
        KeyConditionExpression=(
            Key("user_line_id").eq(line_user_id)
            & Key("created_at").gte(today_start)
        ),
        Select="COUNT",
    )
    return resp["Count"]



def get_wallet(line_user_id: str) -> str | None:
    """Return the stored wallet address for a LINE user, or None."""
    resp = _get_profiles_table().get_item(Key={"line_user_id": line_user_id})
    item = resp.get("Item")
    return item["wallet_address"] if item else None


def save_wallet(line_user_id: str, wallet_address: str) -> None:
    """Upsert the wallet address for a LINE user."""
    _get_profiles_table().put_item(Item={
        "line_user_id":    line_user_id,
        "wallet_address":  wallet_address,
        "updated_at":      int(time.time()),
    })


def get_session(session_id: str) -> dict | None:
    """Fetch a session by primary key."""
    resp = _get_table().get_item(Key={"session_id": session_id})
    return resp.get("Item")


def update_result(
    session_id: str,
    result: dict,
    tx_digest: str | None,
    explorer_url: str | None,
) -> None:
    """Mark session as done and store classification + IOTA result."""
    _get_table().update_item(
        Key={"session_id": session_id},
        UpdateExpression=(
            "SET #s = :done, classification_result = :r, "
            "iota_tx_digest = :tx, iota_explorer_url = :url, updated_at = :ts"
        ),
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":done": "done",
            ":r":    json.dumps(result, ensure_ascii=False),
            ":tx":   tx_digest    or "N/A",
            ":url":  explorer_url or "N/A",
            ":ts":   int(time.time()),
        },
    )
