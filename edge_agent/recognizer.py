"""Plate recognition.

`PlateRecognizer` is the only contract the agent depends on. `YoloOcrRecognizer`
is a working default (Ultralytics YOLO locates the plate, EasyOCR reads it); if
the garage already has its own trained pipeline, wrap it in a class with the
same two methods and pass it to the agent instead.
"""
import io
import re
from dataclasses import dataclass
from typing import Protocol

from PIL import Image


@dataclass(frozen=True)
class Recognition:
    plate_text: str | None
    confidence: float
    bbox: tuple[int, int, int, int] | None = None


class PlateRecognizer(Protocol):
    def warmup(self) -> None: ...

    def recognize(self, image: Image.Image) -> Recognition: ...


class YoloOcrRecognizer:
    _LETTER = re.compile(r"[ء-ي]")
    _DIGIT = re.compile(r"[0-9٠-٩]")
    # Header band printed on Egyptian plates; not part of the registration.
    _IGNORED = ("مصر", "EGYPT")

    def __init__(
        self,
        weights: str,
        ocr_langs: list[str],
        use_gpu: bool,
        min_confidence: float,
    ) -> None:
        # Heavy imports kept local so the rest of the agent stays importable
        # (and testable) without the ML stack installed.
        import easyocr
        from ultralytics import YOLO

        self._detector = YOLO(weights)
        self._device = 0 if use_gpu else "cpu"
        self._reader = easyocr.Reader(ocr_langs, gpu=use_gpu, verbose=False)
        self._min_confidence = min_confidence

    def warmup(self) -> None:
        # The first inference allocates buffers/compiles kernels (~seconds);
        # pay that at boot, not on the first car.
        self.recognize(Image.new("RGB", (640, 480)))

    def recognize(self, image: Image.Image) -> Recognition:
        import numpy as np

        frame = np.asarray(image)
        result = self._detector.predict(
            frame, conf=self._min_confidence, device=self._device, verbose=False
        )[0]
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            return Recognition(None, 0.0)

        best = int(boxes.conf.argmax())
        det_conf = float(boxes.conf[best])
        x1, y1, x2, y2 = (int(v) for v in boxes.xyxy[best].tolist())
        bbox = (max(x1, 0), max(y1, 0), x2, y2)
        crop = frame[bbox[1]:y2, bbox[0]:x2]
        if crop.size == 0:
            return Recognition(None, 0.0)

        text, ocr_conf = self._assemble(self._reader.readtext(crop, detail=1, paragraph=False))
        if not text:
            return Recognition(None, det_conf, bbox)
        return Recognition(text, round(det_conf * ocr_conf, 3), bbox)

    def _assemble(self, fragments: list) -> tuple[str | None, float]:
        """Egyptian layout: letters on the right, digits on the left. Fragments
        are visited right-to-left; output is "ب ن ر 1234"-style (the server
        normalises Arabic-Indic digits)."""
        letters: list[str] = []
        digits: list[str] = []
        confidences: list[float] = []
        for box, text, conf in sorted(fragments, key=lambda f: -max(p[0] for p in f[0])):
            if any(word in text for word in self._IGNORED):
                continue
            found_letters = self._LETTER.findall(text)
            found_digits = self._DIGIT.findall(text)
            if found_letters or found_digits:
                letters.extend(found_letters)
                digits.extend(found_digits)
                confidences.append(float(conf))
        if not confidences:
            return None, 0.0
        plate = " ".join(letters)
        if digits:
            plate = f"{plate} {''.join(digits)}".strip()
        return plate, sum(confidences) / len(confidences)


def decode_image(data: bytes) -> Image.Image:
    image = Image.open(io.BytesIO(data))
    image.load()
    return image.convert("RGB")


def encode_webp(image: Image.Image, max_width: int, quality: int) -> bytes:
    if image.width > max_width:
        height = round(image.height * max_width / image.width)
        image = image.resize((max_width, height), Image.Resampling.BILINEAR)
    buffer = io.BytesIO()
    # method=3: noticeably faster than the default 4 for a negligible size cost.
    image.save(buffer, format="WEBP", quality=quality, method=3)
    return buffer.getvalue()
