from pathlib import Path
import time

from picamera2 import Picamera2

DEFAULT_SAVE_PATH = Path(__file__).parent / "captured.jpg"


def capture_image(save_path=None, warmup_seconds=2.0) -> Path:
    """
    Open the camera, capture one frame, and save it as a JPEG file.

    Returns:
        Path: Saved file path.
    """
    save_path = Path(save_path) if save_path else DEFAULT_SAVE_PATH

    picam2 = Picamera2()
    config = picam2.create_preview_configuration(
        main={"size": (640, 480), "format": "RGB888"}
    )
    picam2.configure(config)
    picam2.start()

    save_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        time.sleep(warmup_seconds)

        for _ in range(3):
            picam2.capture_array()

        # capture_file() keeps correct colors on the Pi camera.
        # capture_array() can return swapped channels if saved directly.
        picam2.capture_file(str(save_path))
    finally:
        picam2.stop()
        picam2.close()

    return save_path
