"""Egyptian Plate recognition using trained YOLO models.

Implements the PlateRecognizer protocol required by Babelooq edge_agent.
Uses plate_detection/best.pt for plate localization and
plate_recognition/best.pt for Egyptian character/digit OCR.
"""
import io
import re
from dataclasses import dataclass
from typing import Protocol, Any
import numpy as np
import torch
from PIL import Image


@dataclass(frozen=True)
class Recognition:
    plate_text: str | None
    confidence: float | None = None
    bbox: tuple[int, int, int, int] | None = None
    plate_crop: np.ndarray | None = None


class PlateRecognizer(Protocol):
    def warmup(self) -> None: ...
    def recognize(self, image: Image.Image) -> Recognition: ...


class EgyptianPlateRecognizer:
    def __init__(
        self,
        detector_weights: str,
        ocr_weights: str,
        use_gpu: bool = True,
        min_confidence: float = 0.25,
    ) -> None:
        from ultralytics import YOLO

        self.device = "cuda" if (use_gpu and torch.cuda.is_available()) else "cpu"
        self._min_confidence = min_confidence

        self._detector = YOLO(detector_weights).to(self.device)
        self._ocr = YOLO(ocr_weights).to(self.device)

    def warmup(self) -> None:
        """Warup CUDA kernels so the first real car is not delayed."""
        dummy = Image.new("RGB", (640, 480))
        self.recognize(dummy)

    def recognize(self, image: Image.Image) -> Recognition:
        frame = np.asarray(image)
        # Convert RGB to BGR for OpenCV-trained YOLO if needed, but RGB is fine
        results = self._detector(frame, conf=self._min_confidence, verbose=False)
        
        best_plate_crop = None
        best_det_conf = 0.0
        best_bbox = None

        for r in results:
            if r.boxes and len(r.boxes) > 0:
                for box in r.boxes:
                    conf = float(box.conf[0])
                    if conf > best_det_conf:
                        best_det_conf = conf
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        # ensure within bounds
                        h, w = frame.shape[:2]
                        x1, y1 = max(0, x1), max(0, y1)
                        x2, y2 = min(w, x2), min(h, y2)
                        if x2 > x1 and y2 > y1:
                            best_bbox = (x1, y1, x2, y2)
                            best_plate_crop = frame[y1:y2, x1:x2]

        if best_plate_crop is None or best_plate_crop.size == 0:
            return Recognition(plate_text=None, confidence=0.0)

        # Run Egyptian OCR model on the plate crop
        ocr_results = self._ocr(best_plate_crop, verbose=False)
        chars = []
        char_confs = []

        for ocr_res in ocr_results:
            if ocr_res.boxes is not None and len(ocr_res.boxes) > 0:
                for box in ocr_res.boxes:
                    coords = box.data.tolist()[0]  # [x1, y1, x2, y2, conf, cls_id]
                    char_confs.append(float(coords[4]))
                    chars.append(coords)

        if not chars:
            return Recognition(
                plate_text=None,
                confidence=round(best_det_conf, 3),
                bbox=best_bbox,
                plate_crop=best_plate_crop
            )

        # Sort characters right-to-left for Arabic plates (descending X coordinate)
        chars.sort(key=lambda x: x[0], reverse=True)

        names = ocr_results[0].names
        plate_tokens = []
        for c in chars:
            cls_id = int(c[5])
            char_name = str(names.get(cls_id, ""))
            if char_name:
                plate_tokens.append(char_name)

        plate_text = " ".join(plate_tokens).strip()
        avg_ocr_conf = sum(char_confs) / len(char_confs) if char_confs else 0.5
        composite_conf = round(best_det_conf * avg_ocr_conf, 3)

        return Recognition(
            plate_text=plate_text if plate_text else None,
            confidence=composite_conf,
            bbox=best_bbox,
            plate_crop=best_plate_crop
        )


def decode_image(data: bytes) -> Image.Image:
    image = Image.open(io.BytesIO(data))
    image.load()
    return image.convert("RGB")


def encode_webp(image: Image.Image, max_width: int, quality: int) -> bytes:
    if image.width > max_width:
        height = round(image.height * max_width / image.width)
        image = image.resize((max_width, height), Image.Resampling.BILINEAR)
    buffer = io.BytesIO()
    image.save(buffer, format="WEBP", quality=quality, method=3)
    return buffer.getvalue()


def encode_jpeg(image: Image.Image, max_width: int, quality: int = 80) -> bytes:
    """Encodes as JPEG for maximum compatibility."""
    if image.width > max_width:
        height = round(image.height * max_width / image.width)
        image = image.resize((max_width, height), Image.Resampling.BILINEAR)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=True)
    return buffer.getvalue()
