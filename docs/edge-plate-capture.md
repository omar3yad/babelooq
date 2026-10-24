# نظام كاميرات الجراج والتعرف الآلي على اللوحات (Edge Plate Capture & ANPR)

> **الحالة:** وثيقة معمارية وتفصيلية رسمية محققة 100% من الكود الفعلي المطبق.  
> **حالة النشر والتشغيل:** الكود مكتمل بالكامل، ومدمج في الفرع الرئيسي `main`، وتم تطبيق الهجرات (`b8e4d2c71f05` و `c9f5e1a82d06`).  
> **مسار النظام:** `/srv/pgms-babelooq/app` (FastAPI + Jinja2 + SQLAlchemy Async + PostgreSQL).  
> **مسار وكيل الجراج:** `edge_agent/` (Python 3.10+ مع PyTorch و Ultralytics YOLOv8 على جهاز PC محلي مزود بـ GPU).

---

## 1. الغرض والمعمارية العامة (Architecture Overview)

الهدف من النظام هو قراءة وتوثيق لوحات السيارات المصرية تلقائياً عند الدخول والخروج دون تعطيل حركة المرور:

1. عند مسح كارت الدخول في بوابة 1، تُحفظ الجلسة فوراً في قاعدة البيانات وتفتح البوابة للسائق في جزء من الثانية (< 200ms).
2. في الخلفية، يُرسل السيرفر إشارة فورية عبر WebSocket لحاسوب الجراج المحلي (Edge PC).
3. يسحب الـ Edge PC لقطة فورية من كاميرا Hikvision IP عبر الشبكة المحلية (LAN).
4. يُشغل الـ Edge PC موديلات الذكاء الاصطناعي (YOLOv8 Plate Detection + Egyptian Character OCR) مع الترتيب من اليمين لليسار.
5. تُرسل النتيجة وصورة السيارة المضغوطة (WebP/JPEG) إلى السيرفر لتخزينها وعرضها فوراً على شاشة المشغل، مع إمكانية التعديل اليدوي في أي وقت.
6. عند بوابة الخروج (بوابة 2)، يتم التقاط صورة خروج تأكيدية تلقائية (`exit-image`) بدون تشغيل الـ OCR للتوثيق والرقابة الإدارية.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 شبكة جراج باب اللوق المحلية                              │
│                                                                                        │
│  ┌───────────────────────────────┐                  ┌───────────────────────────────┐  │
│  │   كاميرا دخول 1 (Hikvision)   │                  │   كاميرا خروج 2 (Hikvision)   │  │
│  │   Channel 201 (ISAPI HTTP)    │                  │   Channel 101 (ISAPI HTTP)    │  │
│  └───────────────┬───────────────┘                  └───────────────┬───────────────┘  │
│                  │                                                  │                  │
│                  └─────────────────────────┬────────────────────────┘                  │
│                                            │ LAN (HTTP Digest Auth)                    │
│                                            ▼                                           │
│                       ┌──────────────────────────────────────────┐                     │
│                       │    Garage Edge PC (NVIDIA GPU / CUDA)    │                     │
│                       │    - agent.py (WebSocket Client)         │                     │
│                       │    - camera.py (Snapshot Pooling)        │                     │
│                       │    - recognizer.py (YOLO Detection + OCR)│                     │
│                       │    - settings.py (Edge Configuration)    │                     │
│                       └────────────────────┬─────────────────────┘                     │
└────────────────────────────────────────────┼───────────────────────────────────────────┘
                                             │
                        اتصال WebSocket صادر │ Outbound WSS: /ws/edge
                        (يتجاوز الـ NAT)     │ (Bearer Token Secured)
                                             ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              سيرفر التطبيق السحابي (VPS)                               │
│                                                                                        │
│  ┌───────────────────────────────┐                  ┌───────────────────────────────┐  │
│  │      Gunicorn Worker A        │                  │      Gunicorn Worker B        │  │
│  │      (يستقبل طلب المشغل)      │                  │      (يحمل اتصال الـ WS)      │  │
│  └───────────────┬───────────────┘                  └───────────────▲───────────────┘  │
│                  │                                                  │                  │
│                  │ NOTIFY pgms_edge_trigger                         │ LISTEN           │
│                  └─────────────────────────┬────────────────────────┘                  │
│                                            ▼                                           │
│                       ┌──────────────────────────────────────────┐                     │
│                       │   PostgreSQL LISTEN/NOTIFY (EventBus)    │                     │
│                       │   - pgms_edge_trigger                    │                     │
│                       │   - pgms_edge_result                     │                     │
│                       │   - pgms_edge_presence                   │                     │
│                       └──────────────────────────────────────────┘                     │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. تفاصيل ومكونات وكيل الجراج (`edge_agent/`)

يتكون مجلد `edge_agent/` من 4 ملفات رئيسية تمثل المحرك التنفيذي في الجراج:

### أ. ملف الإعدادات (`edge_agent/settings.py`)
فئة `EdgeSettings` المعتمدة على `pydantic_settings.BaseSettings`:
- تقرأ كافة الإعدادات تلقائياً ببادئة `EDGE_*` من ملف `edge_agent/.env`.
- أهم المتغيرات:
  - `SERVER_URL`: رابط الاتصال بالسيرفر (`wss://babelooq.garage4u.io/ws/edge`).
  - `API_TOKEN`: التوكن السري المشفر (32 محرفاً كحد أدنى) لمصادقة الـ WebSocket.
  - `NODE_ID`: معرّف الجهاز (افتراضياً: `garage-edge-1`).
  - `CAMERAS`: قاموس يعين لكل بوابة رابط لقطة الكاميرا المباشر ISAPI:
    - بوابة 1: `http://192.168.1.100/ISAPI/Streaming/channels/201/picture`
    - بوابة 2: `http://192.168.1.100/ISAPI/Streaming/channels/101/picture`
  - `CAMERA_AUTH`: نوع المصادقة (`digest` لكاميرات هيكفيجن).
  - `CAMERA_USERNAME` و `CAMERA_PASSWORD`: بيانات الدخول لكاميرات المراقبة.
  - `SNAPSHOT_TIMEOUT_S`: أقصى مهلة لسحب لقطة الكاميرا (افتراضياً: `1.0` ثانية).
  - `DETECTOR_WEIGHTS`: مسار موديل كشف مكان اللوحة (`E:/AISystem/Models/plate_detection/best.pt`).
  - `OCR_WEIGHTS`: مسار موديل قراءة الحروف والأرقام (`E:/AISystem/Models/plate_recognition/best.pt`).
  - `USE_GPU`: تفعيل تسريع الرسوميات (`True` لاستخدام CUDA).
  - `MIN_DETECTION_CONFIDENCE`: الحد الأدنى لثقة كشف اللوحة (`0.25`).
  - `IMAGE_FORMAT`: صيغة إرسال الصورة (`webp` أو `jpeg`).
  - `SAVE_LOCAL_DATASET`: تفعيل الحفظ التلقائي لبيانات التدريب المستمر (`True`).
  - `DATASET_DIR`: مجلد أرشفة بيانات التدريب (`E:/AISystem/saved_gate_images/babelooq_edge`).

### ب. عميل الكاميرات المجمع (`edge_agent/camera.py`)
- فئة `SnapshotCamera`:
  - تستخدم عميلاً غير متزامن واحد `httpx.AsyncClient` يعيد استخدام اتصالات الـ TCP و Keep-Alive ومصادقة Digest Auth المكتملة مسبقاً، بحيث تصبح عملية سحب اللقطة في رحلة شبكة واحدة (Single round-trip) بدون إعادة المصافحة.
  - تتأكد من أن الـ `content-type` المستلم هو `image/*`.
  - تطبق مهلة محددة (`timeout_s <= 1.0s`) وترمي `CameraError` الصريح في حال التأخر أو عدم الاستجابة.

### ج. محرك الذكاء الاصطناعي والتعرف الضوئي (`edge_agent/recognizer.py`)
- فئة `EgyptianPlateRecognizer`:
  - **التهيئة والتسخين (Warmup):** دالة `warmup()` لتشغيل كيرنل الـ CUDA فور تشغيل التطبيق وتفادي أي بطء مع أول سيارة تدخل الجراج.
  - **كشف اللوحة (Localization):** تمرير الصورة لموديل YOLO المكتشف، واستخراج مربع الإحاطة ذو أعلى ثقة وقص صورة اللوحة بدقة (`best_plate_crop`).
  - **قراءة الرموز (OCR):** تمرير قصاصة اللوحة لموديل `plate_recognition/best.pt` لاستخراج الرموز.
  - **الترتيب العربي من اليمين إلى اليسار (Arabic RTL Sorting):** فرز الرموز تنازلياً حسب الإحداثي السيني `X` (`chars.sort(key=lambda x: x[0], reverse=True)`) لضمان أن تظهر الأحرف العربية أولاً متبوعة بالأرقام.
  - **الثقة المركبة (Composite Confidence):** ضرب ثقة كشف اللوحة في متوسط ثقة قراءة الحروف للحصول على ثقة نهائية دقيقة.
  - **ضغط الصورة:** ضغط وتصغير الصورة إلى عرض أقصى 1024 بكسل بصيغة WebP (جودة 75%) أو JPEG (جودة 80%) لتخفيض حجم حزمة الشبكة.

### د. العميل الرئيسي وإدارة الاتصال (`edge_agent/agent.py`)
- فئة `EdgeAgent`:
  - تدير الاتصال بالـ WebSocket مع السيرفر عبر حلقة دائمة `run_forever()`.
  - في حال انقطاع الاتصال تطبق خوارزمية التراجع الأسي العشوائي (Exponential Backoff with Jitter) لإعادة الاتصال التلقائي.
  - مصافحة الدخول `HELLO` / `HELLO_ACK`.
  - **أقفال البوابات (`_gate_locks`):** قفل غير متزامن `asyncio.Lock` لكل بوابة لمنع تداخل عمليات التصوير لنفس الحارة.
  - **طابور النتائج المؤقتة (`_outbox`):** إذا انقطع الاتصال أثناء إرسال نتيجة، تُحفظ النتيجة في طابور محلي بحد أقصى 120 ثانية لتُرسل فور عودة الاتصال (`_flush_outbox()`).
  - **الأرشفة والتدريب المستمر (`_save_training_data`):** حفظ صورة السيارة وصورة اللوحة المقصوصة وتدوين تفاصيلها في ملف `dataset_index.csv`.

---

## 3. تفاصيل بروتوكول الـ WebSocket (`/ws/edge`) وحزم البيانات

نقطة النهاية: `wss://<DOMAIN>/ws/edge`  
الترويسات الإجبارية: `Authorization: Bearer <EDGE_API_TOKEN>`

### أ. حزمة المصافحة (Handshake: `HELLO` & `HELLO_ACK`)
- **من العميل إلى السيرفر:**
  ```json
  {
    "event": "HELLO",
    "node_id": "garage-edge-1",
    "gates": [1, 2],
    "version": "1.0.0"
  }
  ```
- **من السيرفر إلى العميل:**
  ```json
  {
    "event": "HELLO_ACK",
    "conn_id": "8f9a2b3c4d5e6f7a..."
  }
  ```

### ب. حزمة أمر التصوير (`TRIGGER_CAPTURE`)
- **من السيرفر إلى العميل:**
  ```json
  {
    "event": "TRIGGER_CAPTURE",
    "session_id": 1052,
    "card_uid": "CARD-0042",
    "gate_id": 1,
    "timeout_ms": 3500,
    "capture_type": "entry",
    "skip_ocr": false
  }
  ```

### ج. حزمة نتيجة المعالجة (`CAPTURE_RESULT`)
- **من العميل إلى السيرفر:**
  ```json
  {
    "event": "CAPTURE_RESULT",
    "session_id": 1052,
    "gate_id": 1,
    "capture_type": "entry",
    "status": "SUCCESS",
    "plate_number": "س ر ج 5 1 2 4",
    "confidence": 0.884,
    "image_webp_b64": "UklGRuAAAABXRUJQVlA4...",
    "timings_ms": {
      "snapshot": 285.4,
      "analyse": 465.1,
      "total": 750.5
    }
  }
  ```
- *ملاحظة في حالة عدم وجود لوحة أو خطأ:* تكون قيمة `status` إما `"NO_PLATE"` أو `"ERROR"` مع تضمين حقل `"error": "وصف الخطأ"`.

### د. حزمة إقرار الاستلام (`RESULT_ACK`)
- **من السيرفر إلى العميل:**
  ```json
  {
    "event": "RESULT_ACK",
    "session_id": 1052,
    "accepted": true,
    "reason": null
  }
  ```

### هـ. حزم نبضات الاتصال (Heartbeat: `PING` & `PONG`)
- يرسل الـ Edge أو السيرفر `{"event": "PING"}` ويتم الرد بـ `{"event": "PONG"}` للحفاظ على الاتصال نشطاً ومنع الـ Timeouts عبر البروكسي.

---

## 4. مسارات حفظ وأرشفة الصور

### أ. مسار السيرفر الرئيسي (Server Media Storage)
- **المجلد الأساسي:** `/srv/pgms-babelooq/app/media/plates/`
- **هيكل المسار الداخلي:**
  `media/plates/YYYY/MM/DD/{session_id}_{suffix}_{uuid8}.webp` (أو `.jpg`)
  - صورة الدخول: `media/plates/2026/10/24/1052_a1b2c3d4.webp`
  - صورة الخروج: `media/plates/2026/10/24/1052_exit_e5f6a7b8.jpg`
- **الأمان والوصول:**
  - يتم حفظ الملفات بشكل ذري (Atomic write via `.tmp` ثم `os.replace`).
  - مسار الصور لا يُفتح كملفات ثابتة عامة، بل يتم الوصول إليه عبر مسارات مصادق عليها ومحمية بالصلاحيات:
    - صورة الدخول للمشغل والإدارة: `GET /ui/operator/api/sessions/{session_id}/plate-image` أو `GET /ui/admin/sessions/{session_id}/plate-image`
    - صورة الخروج للإدارة: `GET /ui/admin/sessions/{session_id}/exit-image`

### ب. مسار جهاز الجراج لبيانات التدريب المستمر (Edge PC Training Dataset)
- **المجلد الأساسي:** `E:/AISystem/saved_gate_images/babelooq_edge/`
- **التفريعات:**
  - صور السيارات الكاملة: `gate_{gate_id}/cars/{YYYYMMDD_HHMMSS}_{session_id}_{plate}.jpg`
  - صور اللوحات المقصوصة: `gate_{gate_id}/plates/{YYYYMMDD_HHMMSS}_{session_id}_{plate}.jpg`
  - ملف الفهرس العام: `dataset_index.csv` ويحتوي على الأعمدة:
    `timestamp, session_id, gate_id, plate_text, confidence, car_image, plate_image`

---

## 5. دورة حياة وحالات قراءة اللوحة (`PlateCaptureStatus`)

تُخزن حالة التقاط اللوحة في العمود `plate_capture_status` بجدول `parking_sessions` كقيم نصية:

| الحالة (`PlateCaptureStatus`) | المعنى البرمجي والتنفيذي | السلوك في واجهة المشغل والإدارة |
|---|---|---|
| **`PENDING`** | تم فتح الجلسة بنجاح، وإرسال أمر التصوير `TRIGGER_CAPTURE`، وبانتظار النتيجة من جهاز الجراج. | يظهر مؤشر تحميل دوار (Spinner) بجانب حقل اللوحة. |
| **`SUCCESS`** | تمت قراءة اللوحة بنجاح عبر الـ OCR وتخزينها، وحفظ صورة السيارة في السيرفر. | يظهر رقم اللوحة المنسق تلقائياً وصورة السيارة المقروءة ونسبة الثقة. |
| **`NO_PLATE`** | التقطت الكاميرا صورة للسيارة بنجاح، لكن الذكاء الاصطناعي لم يعثر على لوحة أو لم يجد أحرفاً واضحة. | تظهر الصورة مع إشارة "لم يتم التعرف على اللوحة" وتُتاح للعامل كتابتها يدوياً. |
| **`FAILED`** | حدث خطأ فني أبلغ عنه الـ Edge (عطل بالكاميرا أو خطأ في الموديل). | تظهر رسالة خطأ فني وتستمر الجلسة بشكل طبيعي. |
| **`TIMEOUT`** | انتهت المهلة المحددة (4 ثوانٍ) دون استلام أي نتيجة من جهاز الجراج. | تتحول الحالة تلقائياً إلى منتهية الصلاحية دون انتظار، مع إبقاء الجلسة مفتوحة. |
| **`OFFLINE`** | عند محاولة فتح الجلسة، تبين أن جهاز الـ Edge مفصول أو لم يستجب لنبضات الحضور. | تُسجل الحالة فوراً كـ `OFFLINE` بدون أي انتظار (0 ثانية) للحفاظ على سرعة البوابة. |

### معالجة التعديل اليدوي للوحة (`plate-override`)
- إذا أخطأ الذكاء الاصطناعي في قراءة حرف أو كانت اللوحة غير واضحة، يستطيع العامل تعديل اللوحة مباشرة من شاشته.
- يُرسل طلب: `POST /ui/operator/api/sessions/{session_id}/plate-override` بحمولة `{"plate_number": "ق ط ر 9 2 5"}`.
- يقوم السيرفر بتوحيد اللوحة عبر `PlateService.normalize` وتحديثها في قاعدة البيانات فوراً.

### صورة الخروج التأكيدية (`exit-image`)
- عند مسح كارت الخروج في بوابة 2، يتم استدعاء دالة `start_exit_capture`:
  ```python
  await PlateCaptureService(db, settings).start_exit_capture(
      closed_session_id, hub, gate_id=2, card_code=card_code
  )
  ```
- يُرسل أمر `TRIGGER_CAPTURE` بنوع `capture_type: "exit"` و `skip_ocr: True`.
- يكتفي حاسوب الجراج بسحب لقطة الكاميرا وضغطها وإرسالها فوراً بدون استهلاك كارت الشاشة في الـ OCR.
- تُحفظ الصورة في مسار `exit_image_path` لتوفير إثبات مرئي قطعي ومطابقة هيئة السيارة عند خروجها في لوحة الإدارة.
