import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

MACHINE_ID          = os.getenv("MACHINE_ID", "machine_001")
API_BASE            = os.getenv("API_BASE", "http://localhost:3000")
BUTTON_PIN          = int(os.getenv("BUTTON_PIN", "17"))
BUTTON_DEBOUNCE_MS  = int(os.getenv("BUTTON_DEBOUNCE_MS", "300"))
