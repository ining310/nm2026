from pathlib import Path
import time

import cv2
import numpy as np
from PIL import Image
from hailo_platform import (
    ConfigureParams,
    FormatType,
    HEF,
    HailoStreamInterface,
    InferVStreams,
    InputVStreamParams,
    OutputVStreamParams,
    VDevice,
)
from picamera2 import Picamera2

COCO_LABELS = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train",
    "truck", "boat", "traffic light", "fire hydrant", "stop sign",
    "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep",
    "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella",
    "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard",
    "sports ball", "kite", "baseball bat", "baseball glove", "skateboard",
    "surfboard", "tennis racket", "bottle", "wine glass", "cup", "fork",
    "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
    "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
    "couch", "potted plant", "bed", "dining table", "toilet", "tv",
    "laptop", "mouse", "remote", "keyboard", "cell phone", "microwave",
    "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase",
    "scissors", "teddy bear", "hair drier", "toothbrush",
]

HEF_PATH = "/usr/share/hailo-models/yolov8s_h8.hef"
DEFAULT_SAVE_PATH = Path(__file__).parent / "captured.jpg"
SCORE_THRESHOLD = 0.4


def capture_image(save_path=None, warmup_seconds=2.0):
    """
    Open the camera, capture one frame, and save it as an image file.

    Returns:
        tuple[Path, np.ndarray]: Saved file path and the captured RGB frame.
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

    frame = np.array(Image.open(save_path).convert("RGB"))
    return save_path, frame


def _parse_detections(raw_output, confidence_threshold=SCORE_THRESHOLD):
    detections = []

    for _, raw_data in raw_output.items():
        batch = raw_data[0]
        for class_id, class_dets in enumerate(batch):
            if len(class_dets) == 0:
                continue

            label = (
                COCO_LABELS[class_id]
                if class_id < len(COCO_LABELS)
                else f"#{class_id}"
            )
            for det in class_dets:
                y_min, x_min, y_max, x_max, score = det[:5]
                if score < confidence_threshold:
                    continue

                detections.append(
                    {
                        "label": label,
                        "confidence": float(score),
                        "box": (float(x_min), float(y_min), float(x_max), float(y_max)),
                    }
                )

    detections.sort(key=lambda item: item["confidence"], reverse=True)
    return detections


def _run_hailo_detection(frame, confidence_threshold=SCORE_THRESHOLD):
    hef = HEF(HEF_PATH)
    input_info = hef.get_input_vstream_infos()[0]
    model_h, model_w = input_info.shape[0], input_info.shape[1]

    resized = cv2.resize(frame, (model_w, model_h))
    input_data = resized[np.newaxis, ...]

    with VDevice() as device:
        configure_params = ConfigureParams.create_from_hef(
            hef, interface=HailoStreamInterface.PCIe
        )
        network_group = device.configure(hef, configure_params)[0]

        input_params = InputVStreamParams.make(
            network_group, format_type=FormatType.UINT8
        )
        output_params = OutputVStreamParams.make(
            network_group, format_type=FormatType.FLOAT32
        )

        with network_group.activate():
            with InferVStreams(network_group, input_params, output_params) as pipeline:
                raw_output = pipeline.infer({input_info.name: input_data})

    return _parse_detections(raw_output, confidence_threshold)


def detect_object(save_path=None, confidence_threshold=SCORE_THRESHOLD, warmup_seconds=2.0):
    """
    Capture an image, save it, detect objects, and return the top label.

    Returns:
        str | None: The most confident detected object label, or None.
    """
    result = detect_object_detailed(
        save_path=save_path,
        confidence_threshold=confidence_threshold,
        warmup_seconds=warmup_seconds,
    )
    return result["object"]


def detect_object_detailed(
    save_path=None,
    confidence_threshold=SCORE_THRESHOLD,
    warmup_seconds=2.0,
):
    """
    Capture an image, save it, and return full detection details.
    """
    image_path, frame = capture_image(save_path=save_path, warmup_seconds=warmup_seconds)
    detections = _run_hailo_detection(frame, confidence_threshold)

    if not detections:
        return {
            "object": None,
            "confidence": None,
            "image_path": str(image_path),
            "detections": [],
        }

    top = detections[0]
    return {
        "object": top["label"],
        "confidence": top["confidence"],
        "image_path": str(image_path),
        "detections": detections,
    }


if __name__ == "__main__":
    result = detect_object_detailed()

    print(f"Saved image to: {result['image_path']}")
    if result["object"] is None:
        print("No object detected.")
    else:
        print(f"Detected: {result['object']} ({result['confidence']:.2f})")
        for item in result["detections"]:
            print(f"  - {item['label']}: {item['confidence']:.2f}")
