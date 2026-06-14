"""
Raspberry Pi main loop.

Flow:
  1. GPIO interrupt fires when the physical button is pressed.
  2. GET /check — verify a LIFF session is registered ("paid" state); ignore if not.
  3. Capture image with the Pi camera.
  4. Run VLM classification (GPT-4V via vlm.py).
  5. RecycleBin.dispose() — rotate turntable, open/close gate, return to idle.
  6. POST /result to cloud with classification output — Lambda handles IOTA reward + LINE push.
"""
import json
import re
import sys
import time

import requests

try:
    import RPi.GPIO as GPIO
    _GPIO_AVAILABLE = True
except ImportError:
    # Allow importing on non-Pi machines for development
    _GPIO_AVAILABLE = False
    print("[WARN] RPi.GPIO not available; button interrupt disabled", file=sys.stderr)

from config import API_BASE, BUTTON_DEBOUNCE_MS, BUTTON_PIN, MACHINE_ID
from detection import detect_object_detailed
from vlm import describe_image, get_api_key
from servo_control import Category, RecycleBin

from openai import OpenAI
from pathlib import Path

# ── VLM category → servo Category mapping ────────────────────────────────────
CATEGORY_MAP: dict[str, Category] = {
    "metal_can":           Category.METAL,
    "plastic_bottle":      Category.PLASTIC,
    "paper":               Category.PAPER,
    "glass":               Category.OTHER,
    "general_waste":       Category.OTHER,
    "unknown":             Category.OTHER,
    "multiple_categories": Category.OTHER,
}

# ── Servo initialisation ──────────────────────────────────────────────────────
try:
    recycle_bin = RecycleBin()
    _SERVO_AVAILABLE = True
except Exception as _servo_err:
    recycle_bin = None
    _SERVO_AVAILABLE = False
    print(f"[WARN] RecycleBin init failed: {_servo_err}", file=sys.stderr)

# ── GPIO setup ────────────────────────────────────────────────────────────────
if _GPIO_AVAILABLE:
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Re-entry guard — ignore button presses while processing
_processing = False


# ── helpers ───────────────────────────────────────────────────────────────────

def check_payment() -> dict:
    """GET /check — return {"status": "paid"|"waiting", "session_id": ...}.
    "paid" means a user has registered via LIFF and is waiting for detection.
    """
    resp = requests.get(
        f"{API_BASE}/check",
        params={"machine_id": MACHINE_ID},
        timeout=5,
    )
    resp.raise_for_status()
    return resp.json()


def run_vlm(image_path: str) -> dict:
    """Call GPT-4V to classify the garbage image. Returns the result dict."""
    client = OpenAI(api_key=get_api_key())
    raw    = describe_image(client, Path(image_path))
    # Extract JSON block in case the model wraps it in extra text
    match  = re.search(r'\{.*\}', raw, re.DOTALL)
    if not match:
        raise ValueError(f"VLM returned non-JSON output: {raw!r}")
    return json.loads(match.group())


def send_result(session_id: str, result: dict) -> None:
    """POST /result once and return; do not poll for a response."""
    payload = {"session_id": session_id, "machine_id": MACHINE_ID, **result}
    # Timeout 90s: Lambda itself can take ~60s waiting for IOTA tx confirmation
    resp = requests.post(f"{API_BASE}/result", json=payload, timeout=90)
    resp.raise_for_status()
    print(f"[RESULT] cloud acknowledged: {resp.json()}")


# ── button callback ───────────────────────────────────────────────────────────

def on_button_press(channel=None) -> None:
    global _processing
    if _processing:
        print("[BTN] already processing — ignoring press")
        return
    _processing = True

    try:
        # ── Step 1: registration check ───────────────────────────────────────
        status_data = check_payment()
        if status_data.get("status") != "paid":
            print("[BTN] no registered session — ignoring press")
            return

        session_id = status_data["session_id"]
        print(f"[BTN] session {session_id} confirmed → starting detection")

        # ── Step 2: capture + Hailo detection ────────────────────────────────
        hailo = detect_object_detailed()
        image_path = hailo["image_path"]
        if hailo["object"] is not None:
            print(f"[AI] Hailo top hit: {hailo['object']} ({hailo['confidence']:.2f})")
        else:
            print("[AI] Hailo: no object detected — proceeding to VLM")

        # ── Step 3: VLM classification ────────────────────────────────────────
        result = run_vlm(image_path)
        print(f"[VLM] classification: {result}")

        # ── Step 4: motor control ─────────────────────────────────────────────
        category = CATEGORY_MAP.get(result.get("predicted_category", "unknown"), Category.OTHER)
        if _SERVO_AVAILABLE:
            recycle_bin.dispose(category)
        else:
            print(f"[MOTOR] servo unavailable — would dispose {category.name}")

        # ── Step 5: report to cloud ───────────────────────────────────────────
        send_result(session_id, result)

    except Exception as exc:
        print(f"[ERROR] on_button_press: {exc}", file=sys.stderr)
    finally:
        _processing = False


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"[MAIN] machine={MACHINE_ID}  api={API_BASE}")

    if _GPIO_AVAILABLE:
        GPIO.add_event_detect(
            BUTTON_PIN,
            GPIO.FALLING,
            callback=on_button_press,
            bouncetime=BUTTON_DEBOUNCE_MS,
        )
        print(f"[MAIN] waiting for button press on GPIO {BUTTON_PIN} …")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[MAIN] shutting down")
        finally:
            GPIO.cleanup()
            if _SERVO_AVAILABLE:
                recycle_bin.cleanup()
    else:
        # Development mode: simulate a single button press
        print("[MAIN] GPIO unavailable — simulating one button press")
        on_button_press()


if __name__ == "__main__":
    main()
