"""
Smoke-test for the three Lambda endpoints.

Usage (against a running sam local or deployed API):
    export API_BASE=https://xxxxx.execute-api.ap-northeast-1.amazonaws.com/Prod
    python cloud/scripts/test_endpoints.py

Or for local sam:
    sam local start-api --template cloud/template.yaml   (in a separate terminal)
    python cloud/scripts/test_endpoints.py               (uses localhost:3000 by default)

Note: The /result test will attempt a real IOTA transaction if
IOTA_MACHINE_PRIVATE_KEY_HEX is set in the Lambda environment.
Set reward_eligible=False to skip the IOTA transfer during testing.
"""
import json
import os
import sys
import uuid
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env")

API_BASE   = os.environ.get("API_BASE", "http://localhost:3000")
MACHINE_ID = "machine_001"
SESSION_ID = str(uuid.uuid4())

print(f"API : {API_BASE}")
print(f"SID : {SESSION_ID}")
print()


def check(label: str, condition: bool, detail: str = ""):
    if condition:
        print(f"  ✅ {label}")
    else:
        print(f"  ❌ {label}" + (f" — {detail}" if detail else ""))
        sys.exit(1)


# ── 1. GET /check before /pay ─────────────────────────────────────────────────
print("1. GET /check (before /pay) — expect 'waiting'")
r = requests.get(f"{API_BASE}/check", params={"machine_id": MACHINE_ID}, timeout=10)
check(f"HTTP 200", r.status_code == 200, str(r.status_code))
check("status == waiting", r.json()["status"] == "waiting", str(r.json()))
print()

# ── 2. POST /pay ──────────────────────────────────────────────────────────────
print("2. POST /pay")
r = requests.post(f"{API_BASE}/pay", json={
    "session_id":     SESSION_ID,
    "machine_id":     MACHINE_ID,
    "line_user_id":   "U_TEST_USER",   # replace with a real LINE userId to test push
    "wallet_address": "0x" + "01" * 32,   # dummy address for testing
}, timeout=10)
check(f"HTTP 200", r.status_code == 200, str(r.status_code))
check("ok == True", r.json().get("ok") is True, str(r.json()))
print()

# ── 3. GET /check after /pay ──────────────────────────────────────────────────
print("3. GET /check (after /pay) — expect 'paid'")
r = requests.get(f"{API_BASE}/check", params={"machine_id": MACHINE_ID}, timeout=10)
check(f"HTTP 200", r.status_code == 200, str(r.status_code))
check("status == paid", r.json()["status"] == "paid", str(r.json()))
check("session_id matches", r.json()["session_id"] == SESSION_ID, str(r.json()))
print()

# ── 4. POST /result (no reward, safe for testing) ─────────────────────────────
print("4. POST /result (reward_eligible=False — skips IOTA tx)")
r = requests.post(f"{API_BASE}/result", json={
    "session_id":        SESSION_ID,
    "machine_id":        MACHINE_ID,
    "predicted_category": "other",
    "target_bin":        "Bin D",
    "confidence":        0.35,
    "recyclable":        False,
    "single_category":   False,
    "reward_eligible":   False,
    "reason":            "Low confidence test",
}, timeout=15)
check(f"HTTP 200", r.status_code == 200, str(r.status_code))
check("ok == True", r.json().get("ok") is True, str(r.json()))
print()

print("All smoke tests passed!")
print()
print("To test the reward path (real IOTA tx), manually POST /result with")
print('reward_eligible=True and a real wallet_address set in the /pay call.')
