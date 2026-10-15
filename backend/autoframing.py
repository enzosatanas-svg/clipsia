"""
Módulo de Auto-Framing y Seguimiento Facial con MediaPipe
- Detecta rostros en video usando MediaPipe FaceDetector
- Sigue al personaje que habla y calcula las coordenadas óptimas para encuadre 9:16
- Aplica suavizado exponencial (EMA) para movimientos de cámara fluidos y cinemáticos
- Genera expresiones nativas de FFmpeg para recorte dinámico en tiempo real
"""
import os
import logging
import urllib.request
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

import cv2
import numpy as np

logger = logging.getLogger("clipai.autoframing")

MODELS_DIR = Path(__file__).resolve().parent / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
MODEL_PATH = MODELS_DIR / "blaze_face_short_range.tflite"
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite"

_detector_instance = None


def ensure_model_file() -> Path:
    """Verifica que el modelo de MediaPipe exista en disco o lo descarga."""
    if not MODEL_PATH.exists() or MODEL_PATH.stat().st_size < 1000:
        logger.info(f"Descargando modelo MediaPipe FaceDetector en {MODEL_PATH}...")
        try:
            urllib.request.urlretrieve(MODEL_URL, str(MODEL_PATH))
            logger.info("Modelo MediaPipe descargado exitosamente.")
        except Exception as e:
            logger.error(f"Error descargando modelo MediaPipe: {e}")
            raise
    return MODEL_PATH


def get_detector():
    """Inicializa o retorna la instancia en caché de MediaPipe FaceDetector."""
    global _detector_instance
    if _detector_instance is not None:
        return _detector_instance

    try:
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision

        model_p = ensure_model_file()
        base_options = python.BaseOptions(model_asset_path=str(model_p))
        options = vision.FaceDetectorOptions(
            base_options=base_options,
            min_detection_confidence=0.4,
        )
        _detector_instance = vision.FaceDetector.create_from_options(options)
        return _detector_instance
    except Exception as e:
        logger.error(f"No se pudo inicializar MediaPipe FaceDetector: {e}")
        return None


def detect_face_center_x(image_bgr: np.ndarray, detector) -> Optional[float]:
    """
    Detecta el rostro más prominente en una imagen y retorna su centro X normalizado (0.0 a 1.0).
    """
    if detector is None:
        return None

    try:
        import mediapipe as mp
        h, w = image_bgr.shape[:2]
        if h == 0 or w == 0:
            return None

        # Convertir BGR a RGB
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)

        result = detector.detect(mp_image)
        if not result or not result.detections:
            return None

        # Si hay múltiples rostros, seleccionar el de mayor área (personaje principal/hablante)
        best_area = -1.0
        best_center_x = 0.5

        for det in result.detections:
            bb = det.bounding_box
            area = bb.width * bb.height
            if area > best_area:
                best_area = area
                center_px = bb.origin_x + (bb.width / 2.0)
                best_center_x = max(0.0, min(1.0, center_px / float(w)))

        return best_center_x
    except Exception as e:
        logger.debug(f"Error en detección facial: {e}")
        return None


def smooth_trajectory(raw_points: List[Tuple[float, float]], alpha: float = 0.25) -> List[Tuple[float, float]]:
    """
    Aplica suavizado exponencial (EMA) para que el movimiento de la cámara sea fluido y cinematográfico.
    """
    if not raw_points:
        return []

    smoothed = []
    current_val = raw_points[0][1]

    for t, val in raw_points:
        # Suavizado exponencial
        current_val = alpha * val + (1.0 - alpha) * current_val
        smoothed.append((t, current_val))

    return smoothed


def build_ffmpeg_crop_expression(keyframes: List[Tuple[float, float]], in_w_scaled: int, crop_w: int = 1080) -> str:
    """
    Construye una expresión de FFmpeg optimizada para paneo dinámico o estático según el movimiento.
    """
    max_x = max(0, in_w_scaled - crop_w)
    if not keyframes:
        return f"{max_x // 2}"

    if len(keyframes) == 1:
        val = int(round(max(0, min(max_x, keyframes[0][1]))))
        return f"{val}"

    # Calcular variación total
    x_vals = [kf[1] for kf in keyframes]
    spread = max(x_vals) - min(x_vals)

    # Si el movimiento es despreciable (< 50 píxeles), usar una posición fija estable
    if spread < 50:
        avg_val = int(round(max(0, min(max_x, sum(x_vals) / len(x_vals)))))
        return f"{avg_val}"

    # Si hay muchas muestras, submuestrear a puntos clave cada ~1.0 - 1.5s para no sobrecargar el filtro
    kfs = [keyframes[0]]
    last_t = keyframes[0][0]
    for kf in keyframes[1:-1]:
        if (kf[0] - last_t) >= 1.0:
            kfs.append(kf)
            last_t = kf[0]
    kfs.append(keyframes[-1])

    # Construir expresión if-else anidada con interpolación lineal lerp
    expr = f"{round(max(0, min(max_x, kfs[-1][1])), 1)}"
    for i in range(len(kfs) - 2, -1, -1):
        t0, x0 = kfs[i]
        t1, x1 = kfs[i + 1]
        x0_clamped = max(0, min(max_x, x0))
        x1_clamped = max(0, min(max_x, x1))
        dt = max(0.01, t1 - t0)
        curr = f"({x0_clamped:.1f}+({x1_clamped - x0_clamped:.1f})*(t-{t0:.2f})/{dt:.2f})"
        expr = f"if(lte(t,{t1:.2f}),{curr},{expr})"

    return f"min(max(0,{expr}),in_w-{crop_w})"


def analyze_speaker_framing(
    video_path: str,
    start_sec: float,
    end_sec: float,
    target_w: int = 1080,
    target_h: int = 1920,
    sample_fps: float = 3.0,
) -> Dict[str, Any]:
    """
    Analiza el video con MediaPipe para rastrear la cara del personaje que habla
    y calcula el filtro de encuadre 9:16 perfecto.
    """
    v_path = Path(video_path)
    if not v_path.exists():
        logger.warning(f"Video {video_path} no encontrado para autoframing. Usando recorte centrado.")
        return {
            "success": False,
            "crop_expr": f"(in_w-{target_w})/2",
            "video_filter": f"scale=-2:{target_h},crop={target_w}:{target_h}[composed]",
            "faces_detected": 0,
        }

    detector = get_detector()
    if detector is None:
        logger.warning("MediaPipe no disponible. Fallback a recorte centrado.")
        return {
            "success": False,
            "crop_expr": f"(in_w-{target_w})/2",
            "video_filter": f"scale=-2:{target_h},crop={target_w}:{target_h}[composed]",
            "faces_detected": 0,
        }

    cap = cv2.VideoCapture(str(v_path))
    if not cap.isOpened():
        logger.warning(f"No se pudo abrir {video_path} con OpenCV. Fallback a centrado.")
        return {
            "success": False,
            "crop_expr": f"(in_w-{target_w})/2",
            "video_filter": f"scale=-2:{target_h},crop={target_w}:{target_h}[composed]",
            "faces_detected": 0,
        }

    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1920
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 1080
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    # Dimensiones escaladas manteniendo proporción original ajustada a target_h = 1920
    scaled_w = round(orig_w * (float(target_h) / float(orig_h)))
    max_crop_x = max(0, scaled_w - target_w)

    duration = max(0.5, end_sec - start_sec)
    step_sec = 1.0 / max(1.0, sample_fps)

    raw_centers: List[Tuple[float, float]] = []
    current_time = start_sec
    last_known_cx = 0.5
    faces_detected_count = 0

    try:
        while current_time <= end_sec:
            rel_t = current_time - start_sec
            frame_num = int(current_time * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()
            if not ret or frame is None:
                current_time += step_sec
                continue

            cx = detect_face_center_x(frame, detector)
            if cx is not None:
                last_known_cx = cx
                faces_detected_count += 1
                raw_centers.append((rel_t, cx))
            else:
                # Mantener la última posición detectada para evitar saltos bruscos
                raw_centers.append((rel_t, last_known_cx))

            current_time += step_sec
    finally:
        cap.release()

    if not raw_centers:
        raw_centers = [(0.0, 0.5), (duration, 0.5)]

    # Convertir centros normalizados (0.0 - 1.0) a píxeles de recorte crop_x
    # crop_x = (cx * scaled_w) - (target_w / 2)
    pixel_points = []
    for t, cx in raw_centers:
        face_x_px = cx * scaled_w
        crop_x = face_x_px - (target_w / 2.0)
        clamped_x = max(0.0, min(float(max_crop_x), crop_x))
        pixel_points.append((t, clamped_x))

    # Suavizar trayectoria para movimiento fluido estilo cámara cinematográfica
    smoothed_points = smooth_trajectory(pixel_points, alpha=0.3)

    # Construir expresión de FFmpeg
    crop_expr = build_ffmpeg_crop_expression(smoothed_points, in_w_scaled=scaled_w, crop_w=target_w)

    # Construir filtro de FFmpeg
    video_filter = f"scale=-2:{target_h},crop={target_w}:{target_h}:x='{crop_expr}':y=0[composed]"

    logger.info(
        f"MediaPipe Auto-Framing completado: {faces_detected_count} caras detectadas en {len(raw_centers)} muestras. "
        f"Filtro: {video_filter}"
    )

    return {
        "success": True,
        "crop_expr": crop_expr,
        "video_filter": video_filter,
        "faces_detected": faces_detected_count,
        "samples_count": len(raw_centers),
    }
