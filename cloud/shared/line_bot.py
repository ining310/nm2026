"""LINE Messaging API — push message to a user."""
import os

import requests


def push(user_id: str, text: str) -> None:
    """Send a plain-text push message to a LINE user."""
    token = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
    resp = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {token}",
        },
        json={
            "to":       user_id,
            "messages": [{"type": "text", "text": text}],
        },
        timeout=10,
    )
    resp.raise_for_status()
