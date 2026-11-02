import os
import io
import urllib.request

import cv2
import PIL
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont
import PIL.ImageOps
import numpy as np
import streamlit as st
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from insightface.app import FaceAnalysis

# ── Upload & Video Named Constants ────────────────────────────────────────────
MAX_IMAGE_UPLOAD_MB = 10
MAX_VIDEO_UPLOAD_MB = 50
MAX_VIDEO_SAMPLED_FRAMES = 120
MAX_VIDEO_UNIQUE_FACES = 10

_MODEL_PATH = "face_landmarker.task"
_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/1/face_landmarker.task"
)

# ── Model loaders ─────────────────────────────────────────────────────────────

_INSIGHTFACE_APP = None


def get_insightface_app() -> FaceAnalysis:
    """Lazy singleton to load and cache the InsightFace model once."""
    global _INSIGHTFACE_APP
    if _INSIGHTFACE_APP is None:
        app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
        app.prepare(ctx_id=0, det_size=(640, 640))
        _INSIGHTFACE_APP = app
    return _INSIGHTFACE_APP


def _ensure_model():
    if not os.path.exists(_MODEL_PATH):
        with st.spinner("Downloading face landmarker model (one-time, ~30 MB)..."):
            urllib.request.urlretrieve(_MODEL_URL, _MODEL_PATH)


def _ensure_model_silent():
    if not os.path.exists(_MODEL_PATH):
        urllib.request.urlretrieve(_MODEL_URL, _MODEL_PATH)


def _build_detector(num_faces: int = 5):
    base_options = mp_python.BaseOptions(model_asset_path=_MODEL_PATH)
    options = mp_vision.FaceLandmarkerOptions(
        base_options=base_options,
        num_faces=num_faces,
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
    )
    return mp_vision.FaceLandmarker.create_from_options(options)


def _normalize_image(image: np.ndarray) -> np.ndarray:
    if image.dtype != np.uint8:
        image = image.astype(np.uint8)
    if image.ndim == 2:
        image = np.stack([image] * 3, axis=-1)
    elif image.shape[2] == 4:
        image = image[:, :, :3]
    return image


def image_obj_to_numpy(image_obj) -> np.ndarray:
    """Convert a Streamlit-uploaded image object or PIL Image to an RGB numpy array."""
    if isinstance(image_obj, np.ndarray):
        return _normalize_image(image_obj)
    if isinstance(image_obj, PIL.Image.Image):
        return np.array(image_obj.convert("RGB"))
    image = PIL.Image.open(image_obj).convert("RGB")
    return np.array(image)


def save_display_image(
    pil_or_array,
    dest_path: str,
    max_side: int = 1600,
    quality: int = 90,
) -> bool:
    """
    Save an image for display/reference with safe compression:
    1. Apply ImageOps.exif_transpose, convert to RGB.
    2. If the long side > max_side, resize with LANCZOS keeping aspect ratio; never upscale.
    3. Save as JPEG with the given quality, no EXIF (this removes GPS data).
    """
    if isinstance(pil_or_array, np.ndarray):
        img = PIL.Image.fromarray(_normalize_image(pil_or_array))
    elif isinstance(pil_or_array, PIL.Image.Image):
        img = pil_or_array.copy()
    else:
        img = PIL.Image.open(pil_or_array)

    # 1. Apply ImageOps.exif_transpose, convert to RGB
    img = PIL.ImageOps.exif_transpose(img)
    img = img.convert("RGB")

    # 2. If the long side > max_side, resize with LANCZOS keeping aspect ratio; never upscale
    w, h = img.size
    long_side = max(w, h)
    if max_side is not None and max_side > 0 and long_side > max_side:
        scale = max_side / float(long_side)
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))
        resample = getattr(PIL.Image, "Resampling", PIL.Image).LANCZOS
        img = img.resize((new_w, new_h), resample=resample)

    # 3. Save as JPEG with the given quality, no EXIF (strips GPS and metadata)
    dest_dir = os.path.dirname(os.path.abspath(dest_path))
    if dest_dir:
        os.makedirs(dest_dir, exist_ok=True)

    clean_img = PIL.Image.new("RGB", img.size)
    clean_img.paste(img)
    clean_img.save(dest_path, format="JPEG", quality=quality)
    return True


def validate_image_upload(uploaded_file, max_mb: int = MAX_IMAGE_UPLOAD_MB):
    """
    Validate an uploaded image file:
    1. Reject if size > max_mb.
    2. Open with Pillow and call verify(), then reopen; reject on any failure.
    3. Check the real format is JPEG/PNG regardless of file extension.
    4. Return the decoded, exif-transposed RGB PIL Image or an error message string.
    """
    if uploaded_file is None:
        return "No image file provided."

    # 1. Check size limit
    size_bytes = None
    if isinstance(uploaded_file, (str, os.PathLike)):
        try:
            size_bytes = os.path.getsize(uploaded_file)
        except OSError as e:
            return f"Cannot read image file: {e}"
    elif hasattr(uploaded_file, "size"):
        size_bytes = uploaded_file.size
    elif hasattr(uploaded_file, "getbuffer"):
        size_bytes = uploaded_file.getbuffer().nbytes
    elif hasattr(uploaded_file, "seek") and hasattr(uploaded_file, "tell"):
        pos = uploaded_file.tell()
        uploaded_file.seek(0, os.SEEK_END)
        size_bytes = uploaded_file.tell()
        uploaded_file.seek(pos)

    max_bytes = max_mb * 1024 * 1024
    if size_bytes is not None and size_bytes > max_bytes:
        mb_actual = size_bytes / (1024 * 1024)
        return (
            f"Image file size ({mb_actual:.1f} MB) exceeds maximum allowed limit of {max_mb} MB."
        )

    # 2. Open with Pillow and verify()
    try:
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)
        img = PIL.Image.open(uploaded_file)
        img.verify()
    except Exception as e:
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)
        return f"Invalid or corrupted image file: {e}"

    # 3. Reopen, check real format is JPEG/PNG, and decode
    try:
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)
        img = PIL.Image.open(uploaded_file)
        real_format = (img.format or "").upper()
        if real_format not in ("JPEG", "JPG", "PNG"):
            if hasattr(uploaded_file, "seek"):
                uploaded_file.seek(0)
            return (
                f"Unsupported image format ({real_format or 'unknown'}). "
                "Only JPEG and PNG images are allowed."
            )

        # 4. Decoded, exif-transposed RGB image
        img = PIL.ImageOps.exif_transpose(img)
        img = img.convert("RGB")
        img.load()
    except Exception as e:
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)
        return f"Failed to decode image data: {e}"

    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)

    return img


def validate_video_upload(uploaded_file, max_mb: int = MAX_VIDEO_UPLOAD_MB) -> str | None:
    """
    Validate uploaded video file size against the code limit.
    Returns None if valid, or an error message string if invalid.
    """
    if uploaded_file is None:
        return "No video file provided."

    size_bytes = None
    if isinstance(uploaded_file, (str, os.PathLike)):
        try:
            size_bytes = os.path.getsize(uploaded_file)
        except OSError as e:
            return f"Cannot read video file: {e}"
    elif hasattr(uploaded_file, "size"):
        size_bytes = uploaded_file.size
    elif hasattr(uploaded_file, "getbuffer"):
        size_bytes = uploaded_file.getbuffer().nbytes
    elif hasattr(uploaded_file, "seek") and hasattr(uploaded_file, "tell"):
        pos = uploaded_file.tell()
        uploaded_file.seek(0, os.SEEK_END)
        size_bytes = uploaded_file.tell()
        uploaded_file.seek(pos)

    max_bytes = max_mb * 1024 * 1024
    if size_bytes is not None and size_bytes > max_bytes:
        mb_actual = size_bytes / (1024 * 1024)
        return (
            f"Video file size ({mb_actual:.1f} MB) exceeds maximum allowed limit of {max_mb} MB."
        )

    return None


# ── MediaPipe face detection & bounding boxes ─────────────────────────────────

def detect_all_faces(image: np.ndarray, max_faces: int = 5):
    """
    Detect up to max_faces in an image using MediaPipe.

    Returns a list of dicts, one per detected face:
        {
            "landmarks": [x1,y1,z1, x2,y2,z2, ...],   # flattened, normalised
            "bbox": (x_min, y_min, x_max, y_max),      # pixel coords
        }
    Returns an empty list if no faces are found.
    """
    _ensure_model()
    image = _normalize_image(image)
    h, w = image.shape[:2]

    try:
        detector = _build_detector(num_faces=max_faces)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image)
        result = detector.detect(mp_image)
        detector.close()
    except Exception as e:
        st.error(f"Face detection failed: {e}")
        return []

    faces = []
    for lm_list in result.face_landmarks:
        xs = [lm.x * w for lm in lm_list]
        ys = [lm.y * h for lm in lm_list]
        padding = 0.08 * max(w, h)
        bbox = (
            max(0, int(min(xs) - padding)),
            max(0, int(min(ys) - padding)),
            min(w, int(max(xs) + padding)),
            min(h, int(max(ys) + padding)),
        )
        landmarks_flat = [coord for lm in lm_list for coord in (lm.x, lm.y, lm.z)]
        faces.append({"landmarks": landmarks_flat, "bbox": bbox})
    return faces


# Distinct colours for up to 5 faces (unselected state)
_FACE_COLORS = [
    (255, 200, 0),  # yellow
    (0, 180, 255),  # cyan
    (255, 100, 0),  # orange
    (180, 0, 255),  # purple
    (255, 0, 150),  # pink
]
_SELECTED_COLOR = (50, 220, 80)  # green
_UNSELECTED_DIM = (160, 160, 160)  # grey when another face is selected


def draw_face_boxes(
    image_numpy: np.ndarray, faces: list, selected_idx: int = None
) -> PIL.Image.Image:
    """
    Draw labelled bounding boxes around detected faces.

    - Single face: one green box labelled "Face detected"
    - Multiple faces, nothing selected: each box gets a distinct colour + number
    - Multiple faces, one selected: selected = bright green, others = grey + number
    """
    img = PIL.Image.fromarray(_normalize_image(image_numpy))
    draw = PIL.ImageDraw.Draw(img)
    n = len(faces)

    for i, face in enumerate(faces):
        x0, y0, x1, y1 = face["bbox"]
        box_w = max(1, (x1 - x0) // 200 + 2)  # line width scales with box size

        if n == 1:
            color = _SELECTED_COLOR
            label = "Face detected"
        elif selected_idx is None:
            color = _FACE_COLORS[i % len(_FACE_COLORS)]
            label = f"Face {i + 1}"
        elif i == selected_idx:
            color = _SELECTED_COLOR
            label = f"Face {i + 1} (selected)"
        else:
            color = _UNSELECTED_DIM
            label = f"Face {i + 1}"

        for offset in range(box_w):
            draw.rectangle(
                [x0 - offset, y0 - offset, x1 + offset, y1 + offset],
                outline=color,
            )

        font_size = max(12, (y1 - y0) // 8)
        text_x, text_y = x0, max(0, y0 - font_size - 4)
        draw.rectangle(
            [
                text_x,
                text_y,
                text_x + len(label) * font_size // 2 + 8,
                text_y + font_size + 4,
            ],
            fill=color,
        )
        draw.text((text_x + 4, text_y + 2), label, fill=(0, 0, 0))

    return img


# ── InsightFace ArcFace embedding extraction ──────────────────────────────────

def compute_box_iou(box1: tuple, box2: tuple) -> float:
    """Compute Intersection over Union (IoU) between two bounding boxes: (x1, y1, x2, y2)."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    inter_w = max(0, x2 - x1)
    inter_h = max(0, y2 - y1)
    inter_area = inter_w * inter_h

    area1 = max(0, box1[2] - box1[0]) * max(0, box1[3] - box1[1])
    area2 = max(0, box2[2] - box2[0]) * max(0, box2[3] - box2[1])
    union_area = area1 + area2 - inter_area

    if union_area <= 0:
        return 0.0
    return float(inter_area / union_area)


def extract_face_embedding(image_rgb: np.ndarray, bbox: tuple) -> list[float] | None:
    """
    Extract an L2-normalized 512-d ArcFace embedding for the face chosen by MediaPipe.

    Runs InsightFace on the full image and picks the face with highest IoU with bbox.
    If no reasonable overlap (IoU < 0.25), crops bbox with a small margin and runs
    InsightFace on the crop. Returns None if still no face is detected.
    """
    image_rgb = _normalize_image(image_rgb)
    img_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
    h, w = img_bgr.shape[:2]

    app = get_insightface_app()

    best_face = None
    best_iou = 0.0

    try:
        faces = app.get(img_bgr)
        for f in faces:
            iou_val = compute_box_iou(bbox, tuple(f.bbox.astype(int)))
            if iou_val > best_iou:
                best_iou = iou_val
                best_face = f
    except Exception:
        best_face = None

    # If no reasonable overlap (IoU < 0.25) or no faces detected in full image, try crop
    if best_face is None or best_iou < 0.25:
        x1, y1, x2, y2 = bbox
        bw = x2 - x1
        bh = y2 - y1
        pad_x = int(0.15 * bw)
        pad_y = int(0.15 * bh)
        cx1 = max(0, x1 - pad_x)
        cy1 = max(0, y1 - pad_y)
        cx2 = min(w, x2 + pad_x)
        cy2 = min(h, y2 + pad_y)

        crop_bgr = img_bgr[cy1:cy2, cx1:cx2]
        if crop_bgr.size > 0:
            try:
                crop_faces = app.get(crop_bgr)
                if crop_faces:
                    best_face = max(
                        crop_faces,
                        key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),
                    )
            except Exception:
                best_face = None

    if best_face is None or not hasattr(best_face, "embedding") or best_face.embedding is None:
        return None

    emb = best_face.embedding
    norm = np.linalg.norm(emb)
    if norm > 0:
        emb = emb / norm
    return [float(x) for x in emb]


# ── Legacy helpers (kept for backward compatibility) ──────────────────────────

def extract_face_mesh_landmarks(image: np.ndarray):
    """
    Extract face mesh landmarks for exactly one face.
    Shows a Streamlit error if none found. Returns None on failure.
    """
    faces = detect_all_faces(image, max_faces=1)
    if not faces:
        st.error(
            "No face detected in this image.\n\n"
            "**Tips for a better result:**\n"
            "- Ensure the face is clearly visible and not obscured\n"
            "- Use good lighting — avoid dark or back-lit photos\n"
            "- Use a front-facing photo where possible"
        )
        return None
    return faces[0]["landmarks"]


def extract_face_mesh_from_frame(frame_rgb: np.ndarray):
    """Silent version for batch/video use. Returns landmarks or None."""
    _ensure_model_silent()
    frame_rgb = _normalize_image(frame_rgb)
    try:
        detector = _build_detector(num_faces=1)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        result = detector.detect(mp_image)
        detector.close()
        if result.face_landmarks:
            lm_list = result.face_landmarks[0]
            return [coord for lm in lm_list for coord in (lm.x, lm.y, lm.z)]
        return None
    except Exception:
        return None


def _cosine_distance(a: list, b: list) -> float:
    a_arr, b_arr = np.array(a, dtype=float), np.array(b, dtype=float)
    denom = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
    if denom == 0:
        return 1.0
    return float(1.0 - np.dot(a_arr, b_arr) / denom)


# ── Video frame extraction with deduplication ─────────────────────────────────

# Video frame face deduplication threshold on cosine distance (must be tuned in Phase 4)
VIDEO_DEDUP_COSINE_DISTANCE_THRESHOLD = 0.35


def extract_unique_faces_from_video(
    video_path: str,
    frame_interval: int = 15,
    similarity_threshold: float = VIDEO_DEDUP_COSINE_DISTANCE_THRESHOLD,
    max_sampled_frames: int = MAX_VIDEO_SAMPLED_FRAMES,
    max_unique_faces: int = MAX_VIDEO_UNIQUE_FACES,
):
    """
    Extract unique face embeddings from a video file.
    Returns list of (embedding, frame_rgb) tuples — one per unique face.
    Caps the number of sampled frames and unique faces.
    """
    _ensure_model_silent()
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []

    unique_faces = []
    frame_idx = 0
    sampled_count = 0
    while True:
        ret, frame_bgr = cap.read()
        if not ret:
            break
        if frame_idx % frame_interval == 0:
            sampled_count += 1
            if max_sampled_frames is not None and sampled_count > max_sampled_frames:
                break
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            faces = detect_all_faces(frame_rgb, max_faces=1)
            if faces:
                embedding = extract_face_embedding(frame_rgb, faces[0]["bbox"])
                if embedding is not None:
                    is_duplicate = any(
                        _cosine_distance(embedding, ex_emb) < similarity_threshold
                        for ex_emb, _ in unique_faces
                    )
                    if not is_duplicate:
                        unique_faces.append((embedding, frame_rgb))
                        if max_unique_faces is not None and len(unique_faces) >= max_unique_faces:
                            break
        frame_idx += 1

    cap.release()
    return unique_faces
