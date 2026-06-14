"""
Raspberry Pi touchscreen kiosk (replaces physical GPIO button).

States:
  waiting    QR code shown, background thread polls GET /check every 2s
  registered "開始偵測" touch button shown (user places item then taps)
  detecting  animated dots while VLM runs
  result     success or fail card shown for 6s, then back to waiting
  error      error message for 8s, then back to waiting

Run on Pi:
  python kiosk.py

Dev mode (windowed 800x480):
  python kiosk.py --windowed
"""

import argparse
import json
import re
import sys
import threading
import time
from pathlib import Path

import requests
import tkinter as tk
from tkinter import font as tkfont

from config import API_BASE, MACHINE_ID

# ── Optional imports (graceful degradation on dev machine) ───────────────────
try:
    import qrcode
    from PIL import Image, ImageTk
    _QR_AVAILABLE = True
except ImportError:
    _QR_AVAILABLE = False
    print("[WARN] qrcode/Pillow not available; QR display disabled", file=sys.stderr)

try:
    from vlm import describe_image, get_api_key
    from openai import OpenAI
    _VLM_AVAILABLE = True
except ImportError:
    _VLM_AVAILABLE = False
    print("[WARN] vlm module not available", file=sys.stderr)

try:
    from detection import detect_object_detailed
    _DETECTION_AVAILABLE = True
except ImportError:
    _DETECTION_AVAILABLE = False
    print("[WARN] detection module not available", file=sys.stderr)

try:
    from servo_control import Category, RecycleBin
    _recycle_bin = RecycleBin()
    _SERVO_AVAILABLE = True
except Exception as _e:
    _recycle_bin = None
    _SERVO_AVAILABLE = False
    print(f"[WARN] RecycleBin unavailable: {_e}", file=sys.stderr)

# ── Constants ─────────────────────────────────────────────────────────────────
LIFF_ID          = "2010382965-397QCX0y"
LIFF_URL         = f"https://liff.line.me/{LIFF_ID}?machine_id={MACHINE_ID}"
POLL_INTERVAL_S     = 2
RESULT_HOLD_MS      = 6000
ERROR_HOLD_MS       = 8000
REGISTERED_TIMEOUT_MS = 60_000   # reset if user doesn't press Start within 60s

# Colors — matches LIFF palette
BG            = "#F7F9FC"
CARD_BG       = "#FFFFFF"
ACCENT        = "#1E3A5F"
ACCENT_BTN    = "#2C5282"
ACCENT_BTN_HL = "#1A3A6E"
MUTED         = "#64748B"
BORDER        = "#D1D9E6"
SUCCESS_BG    = "#F0F7F4"
SUCCESS_TEXT  = "#14563C"
SUCCESS_CHIP  = "#D1FAE5"
ERROR_TEXT    = "#B91C1C"
ERROR_BG      = "#FEF2F2"
ERROR_CHIP    = "#FEE2E2"
REWARD_GREEN  = "#15803D"

CATEGORY_MAP_SERVO = {
    "metal_can":           "METAL",
    "plastic_bottle":      "PLASTIC",
    "paper":               "PAPER",
    "glass":               "OTHER",
    "general_waste":       "OTHER",
    "unknown":             "OTHER",
    "multiple_categories": "OTHER",
}

CATEGORY_ZH = {
    "metal_can":           "金屬罐",
    "plastic_bottle":      "塑膠瓶",
    "paper":               "紙類",
    "glass":               "玻璃",
    "general_waste":       "一般垃圾",
    "unknown":             "無法辨識",
    "multiple_categories": "多種類別混合",
}


# ── API helpers ───────────────────────────────────────────────────────────────

def api_check() -> dict:
    resp = requests.get(f"{API_BASE}/check", params={"machine_id": MACHINE_ID}, timeout=5)
    resp.raise_for_status()
    return resp.json()


def api_send_result(session_id: str, result: dict) -> None:
    payload = {"session_id": session_id, "machine_id": MACHINE_ID, **result}
    resp = requests.post(f"{API_BASE}/result", json=payload, timeout=90)
    resp.raise_for_status()
    print(f"[RESULT] cloud acknowledged: {resp.json()}")


def run_vlm(image_path: str) -> dict:
    client = OpenAI(api_key=get_api_key())
    raw = describe_image(client, Path(image_path))
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if not match:
        raise ValueError(f"VLM returned non-JSON output: {raw!r}")
    return json.loads(match.group())


# ── Kiosk application ─────────────────────────────────────────────────────────

class KioskApp:
    def __init__(self, root: tk.Tk, windowed: bool = False):
        self.root = root
        self.root.title("Smart Recycling Bin")
        self.root.configure(bg=BG)

        if windowed:
            self.root.geometry("800x480")
        else:
            self.root.attributes("-fullscreen", True)
            self.root.bind("<Escape>", lambda _: self.root.destroy())

        # State
        self._current_session_id: str | None = None
        self._polling = True
        self._processing = False
        self._qr_image = None   # keep reference to prevent GC
        self._skip_sessions: set[str] = set()  # sessions to ignore after timeout/error

        # Fonts
        self._fonts()

        # Build all frames
        container = tk.Frame(root, bg=BG)
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames: dict[str, tk.Frame] = {}
        for name, builder in [
            ("waiting",    self._build_waiting),
            ("registered", self._build_registered),
            ("detecting",  self._build_detecting),
            ("result",     self._build_result),
            ("error",      self._build_error),
        ]:
            f = tk.Frame(container, bg=BG)
            f.grid(row=0, column=0, sticky="nsew")
            self.frames[name] = f
            builder(f)

        # Dot animation + timeout jobs (must be set before _show)
        self._dot_job = None
        self._registered_timeout_job = None

        self._show("waiting")

        # Start polling thread
        t = threading.Thread(target=self._poll_loop, daemon=True)
        t.start()

    # ── Font setup ────────────────────────────────────────────────────────────

    def _fonts(self):
        self.f_title    = tkfont.Font(family="Helvetica", size=22, weight="bold")
        self.f_subtitle = tkfont.Font(family="Helvetica", size=14)
        self.f_body     = tkfont.Font(family="Helvetica", size=13)
        self.f_small    = tkfont.Font(family="Helvetica", size=11)
        self.f_btn      = tkfont.Font(family="Helvetica", size=18, weight="bold")
        self.f_big      = tkfont.Font(family="Helvetica", size=32, weight="bold")
        self.f_chip     = tkfont.Font(family="Helvetica", size=11, weight="bold")

    # ── Frame builders ────────────────────────────────────────────────────────

    def _build_waiting(self, f: tk.Frame):
        """QR code + 'scan to register' prompt."""
        inner = tk.Frame(f, bg=BG)
        inner.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(inner, text="智慧回收箱", font=self.f_title,
                 bg=BG, fg=ACCENT).pack(pady=(0, 4))
        tk.Label(inner, text="請掃描 QR Code 登記投遞", font=self.f_subtitle,
                 bg=BG, fg=MUTED).pack(pady=(0, 20))

        # QR image from link.png (same directory as kiosk.py)
        _img_path = Path(__file__).parent / "link.png"
        try:
            if _QR_AVAILABLE:
                img = Image.open(_img_path).resize((100, 100), Image.LANCZOS)
                self._qr_image = ImageTk.PhotoImage(img)
            else:
                self._qr_image = tk.PhotoImage(file=str(_img_path))
            qr_frame = tk.Frame(inner, bg="white", padx=8, pady=8,
                                relief="flat", bd=0,
                                highlightthickness=1, highlightbackground=BORDER)
            qr_frame.pack()
            tk.Label(qr_frame, image=self._qr_image, bg="white").pack()
        except Exception as _e:
            print(f"[WARN] link.png not found or unreadable: {_e}", file=sys.stderr)
            tk.Label(inner, text=LIFF_URL, font=self.f_small,
                     bg=BG, fg=MUTED, wraplength=400).pack()

        tk.Label(inner, text=f"機台 {MACHINE_ID}", font=self.f_small,
                 bg=BG, fg=BORDER).pack(pady=(14, 0))

        # Polling status dot
        self.waiting_status = tk.Label(inner, text="", font=self.f_small,
                                       bg=BG, fg=MUTED)
        self.waiting_status.pack(pady=(6, 0))

    def _build_registered(self, f: tk.Frame):
        """'Place item then tap Start' screen."""
        inner = tk.Frame(f, bg=BG)
        inner.place(relx=0.5, rely=0.5, anchor="center")

        # Checkmark card
        card = tk.Frame(inner, bg=SUCCESS_BG, padx=28, pady=24,
                        highlightthickness=1, highlightbackground="#A7F3D0")
        card.pack(pady=(0, 24))

        tk.Label(card, text="登記成功", font=self.f_title,
                 bg=SUCCESS_BG, fg=SUCCESS_TEXT).pack()
        tk.Label(card, text="請將物品放入後，點擊下方按鈕開始偵測",
                 font=self.f_body, bg=SUCCESS_BG, fg=SUCCESS_TEXT).pack(pady=(8, 0))

        # Start button
        btn = tk.Button(
            inner,
            text="開始投遞",
            font=self.f_btn,
            bg=ACCENT_BTN,
            fg="white",
            activebackground=ACCENT_BTN_HL,
            activeforeground="white",
            relief="flat",
            padx=48,
            pady=18,
            cursor="hand2",
            command=self._on_start_pressed,
        )
        btn.pack()
        self._bind_hover(btn, ACCENT_BTN, ACCENT_BTN_HL)

    def _build_detecting(self, f: tk.Frame):
        """Animated dots while VLM + servo run."""
        inner = tk.Frame(f, bg=BG)
        inner.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(inner, text="偵測中", font=self.f_title,
                 bg=BG, fg=ACCENT).pack()
        self.detecting_dots = tk.Label(inner, text="", font=self.f_big,
                                       bg=BG, fg=ACCENT_BTN)
        self.detecting_dots.pack(pady=12)
        tk.Label(inner, text="請勿移動機台", font=self.f_small,
                 bg=BG, fg=MUTED).pack()

    def _build_result(self, f: tk.Frame):
        """Rewarded / not-rewarded result card (content set dynamically)."""
        self.result_inner = tk.Frame(f, bg=BG)
        self.result_inner.place(relx=0.5, rely=0.5, anchor="center")

    def _build_error(self, f: tk.Frame):
        """Error message (content set dynamically)."""
        inner = tk.Frame(f, bg=BG)
        inner.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(inner, text="發生錯誤", font=self.f_title,
                 bg=BG, fg=ERROR_TEXT).pack()
        self.error_label = tk.Label(inner, text="", font=self.f_body,
                                    bg=BG, fg=ERROR_TEXT, wraplength=500, justify="center")
        self.error_label.pack(pady=12)
        tk.Label(inner, text="即將重新開始…", font=self.f_small,
                 bg=BG, fg=MUTED).pack()

    # ── Frame switching ───────────────────────────────────────────────────────

    def _show(self, name: str):
        if name == "detecting":
            self._start_dots()
        else:
            self._stop_dots()
        self.frames[name].tkraise()

    # ── Polling thread ────────────────────────────────────────────────────────

    def _poll_loop(self):
        while self._polling:
            if not self._processing:
                try:
                    data = api_check()
                    if data.get("status") == "paid":
                        session_id = data["session_id"]
                        if session_id in self._skip_sessions:
                            pass  # timed-out or errored session, ignore
                        else:
                            print(f"[POLL] session {session_id} registered")
                            self.root.after(0, self._on_session_registered, session_id)
                except Exception as e:
                    print(f"[POLL] check failed: {e}", file=sys.stderr)
                    self.root.after(0, lambda: self.waiting_status.config(
                        text="連線失敗，重試中…", fg=ERROR_TEXT))
                else:
                    self.root.after(0, lambda: self.waiting_status.config(
                        text="", fg=MUTED))
            time.sleep(POLL_INTERVAL_S)

    # ── State transitions (always called from main thread via root.after) ─────

    def _on_session_registered(self, session_id: str):
        if self._processing:
            return
        self._current_session_id = session_id
        self._show("registered")
        # Cancel any previous timeout and start a fresh one
        if self._registered_timeout_job:
            self.root.after_cancel(self._registered_timeout_job)
        self._registered_timeout_job = self.root.after(
            REGISTERED_TIMEOUT_MS, self._on_registered_timeout
        )

    def _on_registered_timeout(self):
        self._registered_timeout_job = None
        if not self._processing:
            print("[KIOSK] registered timeout — resetting to waiting")
            if self._current_session_id:
                self._skip_sessions.add(self._current_session_id)
            self._reset()

    def _on_start_pressed(self):
        if self._processing or not self._current_session_id:
            return
        if self._registered_timeout_job:
            self.root.after_cancel(self._registered_timeout_job)
            self._registered_timeout_job = None
        self._processing = True
        self._show("detecting")
        t = threading.Thread(target=self._run_detection, daemon=True)
        t.start()

    def _run_detection(self):
        session_id = self._current_session_id
        try:
            # Step 1: Hailo detection + capture
            if _DETECTION_AVAILABLE:
                hailo = detect_object_detailed()
                image_path = hailo["image_path"]
            else:
                image_path = "/tmp/mock_image.jpg"
                print("[DETECT] mock image path used")

            # Step 2: VLM classification
            if _VLM_AVAILABLE:
                result = run_vlm(image_path)
            else:
                # Mock result for dev
                result = {
                    "predicted_category": "plastic_bottle",
                    "confidence": 0.88,
                    "reward_eligible": True,
                    "reason": "PET plastic bottle detected (mock)",
                }
            print(f"[VLM] {result}")

            # Step 3: servo
            if _SERVO_AVAILABLE and _recycle_bin:
                cat_key = result.get("predicted_category", "unknown")
                from servo_control import Category
                cat_map = {
                    "metal_can":    Category.METAL,
                    "plastic_bottle": Category.PLASTIC,
                    "paper":        Category.PAPER,
                }
                category = cat_map.get(cat_key, Category.OTHER)
                _recycle_bin.dispose(category)

            # Step 4: cloud
            api_send_result(session_id, result)

            self.root.after(0, self._show_result, result)

        except Exception as exc:
            print(f"[ERROR] detection: {exc}", file=sys.stderr)
            self.root.after(0, self._show_error, str(exc))

    def _show_result(self, result: dict):
        rewarded  = bool(result.get("reward_eligible", False))
        cat_key   = result.get("predicted_category", "unknown")
        cat_zh    = CATEGORY_ZH.get(cat_key, cat_key)
        conf      = float(result.get("confidence", 0))
        conf_pct  = f"{conf:.0%}"

        # Clear previous result widgets
        for w in self.result_inner.winfo_children():
            w.destroy()

        if rewarded:
            card_bg   = SUCCESS_BG
            card_hl   = "#A7F3D0"
            title_txt = "分類成功"
            title_fg  = SUCCESS_TEXT
            chip_bg   = SUCCESS_CHIP
            chip_fg   = SUCCESS_TEXT
            reward_txt = "+3 IOTA"
        else:
            card_bg   = ERROR_BG
            card_hl   = "#FECACA"
            title_txt = "無法明確分類"
            title_fg  = ERROR_TEXT
            chip_bg   = ERROR_CHIP
            chip_fg   = ERROR_TEXT
            reward_txt = "本次無獎勵"

        card = tk.Frame(self.result_inner, bg=card_bg, padx=32, pady=28,
                        highlightthickness=1, highlightbackground=card_hl)
        card.pack()

        tk.Label(card, text=title_txt, font=self.f_title,
                 bg=card_bg, fg=title_fg).pack(pady=(0, 8))

        info_row = tk.Frame(card, bg=card_bg)
        info_row.pack(pady=(0, 10))
        tk.Label(info_row, text=cat_zh, font=self.f_body,
                 bg=card_bg, fg=title_fg).pack(side="left", padx=(0, 10))
        tk.Label(info_row, text=f"信心度 {conf_pct}", font=self.f_small,
                 bg=card_bg, fg=title_fg).pack(side="left")

        chip = tk.Label(card, text=reward_txt, font=self.f_chip,
                        bg=chip_bg, fg=chip_fg, padx=12, pady=4)
        chip.pack()

        if not rewarded:
            reason = result.get("reason", "")
            if reason:
                tk.Label(card, text=reason, font=self.f_small,
                         bg=card_bg, fg=title_fg, wraplength=420,
                         justify="center").pack(pady=(10, 0))

        self._show("result")
        self.root.after(RESULT_HOLD_MS, self._reset)

    def _show_error(self, msg: str):
        if self._current_session_id:
            self._skip_sessions.add(self._current_session_id)
        self.error_label.config(text=msg)
        self._show("error")
        self.root.after(ERROR_HOLD_MS, self._reset)

    def _reset(self):
        self._current_session_id = None
        self._processing = False
        self._show("waiting")

    # ── Dot animation ─────────────────────────────────────────────────────────

    def _start_dots(self):
        self._dot_count = 0
        self._animate_dots()

    def _animate_dots(self):
        self._dot_count = (self._dot_count + 1) % 4
        self.detecting_dots.config(text="." * self._dot_count)
        self._dot_job = self.root.after(500, self._animate_dots)

    def _stop_dots(self):
        if self._dot_job:
            self.root.after_cancel(self._dot_job)
            self._dot_job = None

    # ── Hover helper ──────────────────────────────────────────────────────────

    def _bind_hover(self, widget: tk.Button, normal: str, hover: str):
        widget.bind("<Enter>", lambda _: widget.config(bg=hover))
        widget.bind("<Leave>", lambda _: widget.config(bg=normal))

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def cleanup(self):
        self._polling = False
        if _SERVO_AVAILABLE and _recycle_bin:
            _recycle_bin.cleanup()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--windowed", action="store_true",
                    help="Run in a window instead of fullscreen (dev mode)")
    args = ap.parse_args()

    root = tk.Tk()
    app = KioskApp(root, windowed=args.windowed)

    try:
        root.mainloop()
    finally:
        app.cleanup()


if __name__ == "__main__":
    main()
