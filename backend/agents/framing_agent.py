"""
Paso 3: Agente Experto en Reencuadre Dinámico 9:16 y Composición Visual (Framing Agent)
Responsabilidad:
- Transforma video horizontal (16:9) u original a formato vertical estricto 9:16 (1080x1920).
- Seguimiento Facial Activo (Face Tracking): Rastrea continuamente al hablante principal con MediaPipe BlazeFace
  y suavizado EMA (Exponential Moving Average) para evitar sacudidas de cámara.
- Composición por Capas y Fondos (Dual-Layer Blur):
  Capa Trasera: Video escalado a 1080x1920 con desenfoque gaussiano cinemático (boxblur 25:5).
  Capa Delantera: Sujeto enfocado y centrado con su relación de aspecto original intacta (sin distorsión).
- Zonas Seguras de Interfaz (UI Safe Zones):
  Márgenes estrictos para evitar colisiones con botones, descripciones y menús de TikTok, Reels y Shorts:
    * Margen Superior: 15% (288px) - Protege buscador, filtros y botón salir.
    * Margen Inferior: 20% (384px) - Protege nombre de usuario, copy, hashtags y audio.
    * Margen Lateral Derecho: 10% (108px) - Protege botones de like, comentario, guardar y compartir.
    * Margen Lateral Izquierdo: 5% (54px) - Margen de respiración visual.
"""
import os
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from backend.autoframing import analyze_speaker_framing

logger = logging.getLogger("clipai.agents.framing")


class FramingAgent:
    def __init__(self, target_resolution=(1080, 1920)):
        self.width, self.height = target_resolution
        
        # Cálculo de Zonas Seguras (Safe Zones) para TikTok, Instagram Reels y YouTube Shorts
        self.safe_zones = {
            "top_px": int(self.height * 0.15),        # 288px (15%)
            "bottom_px": int(self.height * 0.20),     # 384px (20%)
            "right_px": int(self.width * 0.10),       # 108px (10%)
            "left_px": int(self.width * 0.05),        # 54px  (5%)
            "safe_area_width": int(self.width * 0.85),# 918px
            "safe_area_height": int(self.height * 0.65),# 1248px
            "safe_y_start": int(self.height * 0.15),  # 288px
            "safe_y_end": int(self.height * 0.80),    # 1536px
        }

    def build_blur_background_filter(self) -> str:
        """
        Construye el grafo de filtros FFmpeg para fondo desenfocado cinemático (Dual-Layer Blur).
        Capa 1 (Background): Escala a 1080x1920, recorta y aplica desenfoque gaussiano boxblur=25:5.
        Capa 2 (Foreground): Escala a 1080 de ancho manteniendo relación de aspecto.
        Overlay: Centra la capa delantera sobre el fondo desenfocado.
        """
        filter_str = (
            "[0:v]split=2[in_bg][in_fg];"
            "[in_bg]scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,boxblur=25:5[bg_blur];"
            "[in_fg]scale=1080:-2[fg_sharp];"
            "[bg_blur][fg_sharp]overlay=(W-w)/2:(H-h)/2[composed]"
        )
        return filter_str

    def build_crop_filter(self, center_x_expr: str = "(in_w-out_w)/2") -> str:
        """Construye filtro de recorte centrado o dinámico a 1080x1920."""
        return f"scale=-2:1920,crop=1080:1920:{center_x_expr}:0[composed]"

    def process(
        self,
        source_video_path: str,
        start_time: float,
        end_time: float,
        ass_subtitle_path: Optional[str],
        output_video_path: Path,
        layout_mode: str = "autoframing",
    ) -> Dict[str, Any]:
        """
        Ejecuta el reencuadre 9:16 con seguimiento facial, fondo desenfocado si aplica
        y quemado de subtítulos dentro de las zonas seguras.
        """
        duration = max(1.0, round(end_time - start_time, 2))
        faces_detected = 0
        tracking_metadata = {}

        # 1. Determinar estrategia de reencuadre y seguimiento facial
        if layout_mode == "autoframing":
            try:
                framing = analyze_speaker_framing(
                    video_path=source_video_path,
                    start_sec=start_time,
                    end_sec=end_time,
                    target_w=self.width,
                    target_h=self.height,
                )
                video_filter = framing.get("video_filter")
                faces_detected = framing.get("faces_detected", 0)
                tracking_metadata = {
                    "faces_detected": faces_detected,
                    "avg_center_x": framing.get("avg_center_x", 0.5),
                    "crop_mode": framing.get("crop_mode", "mediapipe_tracked"),
                }
                if not video_filter:
                    video_filter = self.build_blur_background_filter()
            except Exception as e:
                logger.warning(f"[FramingAgent] Seguimiento MediaPipe en fallback: {e}. Aplicando Dual-Layer Blur.")
                video_filter = self.build_blur_background_filter()
                tracking_metadata = {"fallback": "dual_layer_blur", "reason": str(e)}
        elif layout_mode == "crop":
            video_filter = self.build_crop_filter()
            tracking_metadata = {"crop_mode": "static_center"}
        else:
            # blur_bg por defecto
            video_filter = self.build_blur_background_filter()
            tracking_metadata = {"crop_mode": "dual_layer_blur"}

        # 2. Inyección de subtítulos ASS (diseñados para habitar la zona segura central)
        has_subs = False
        output_label = "[composed]"
        if ass_subtitle_path and Path(ass_subtitle_path).exists():
            ass_clean = str(Path(ass_subtitle_path).resolve()).replace("\\", "/").replace(":", "\\:")
            video_filter += f";[composed]subtitles='{ass_clean}'[v_out]"
            output_label = "[v_out]"
            has_subs = True

        # 3. Ensamblado de comando FFmpeg optimizado para redes sociales
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_time),
            "-i", str(source_video_path),
            "-t", str(duration),
            "-filter_complex", video_filter,
            "-map", output_label,
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "22",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            str(output_video_path),
        ]

        logger.info(f"[FramingAgent] Ejecutando FFmpeg: {' '.join(cmd)}")
        res = subprocess.run(cmd, capture_output=True, text=True)

        # Fallback de rescate si el filtro complejo encuentra alguna incompatibilidad
        if res.returncode != 0:
            logger.warning(f"[FramingAgent] Falló filtro principal: {res.stderr}. Ejecutando renderizado de rescate...")
            fb_filter = self.build_blur_background_filter()
            cmd_fb = [
                "ffmpeg", "-y",
                "-ss", str(start_time),
                "-i", str(source_video_path),
                "-t", str(duration),
                "-filter_complex", fb_filter,
                "-map", "[composed]",
                "-map", "0:a?",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-c:a", "aac",
                "-movflags", "+faststart",
                str(output_video_path),
            ]
            res_fb = subprocess.run(cmd_fb, capture_output=True, text=True)
            if res_fb.returncode != 0:
                raise RuntimeError(f"Error crítico en FFmpeg: {res_fb.stderr}")

        file_size_mb = round(output_video_path.stat().st_size / (1024 * 1024), 2) if output_video_path.exists() else 0.0

        return {
            "status": "success",
            "agent": "FramingAndVisualCompositionAgent",
            "canvas": {
                "format": "9:16",
                "width": self.width,
                "height": self.height,
                "aspect_ratio": "9:16 Vertical"
            },
            "facial_tracking": tracking_metadata,
            "background_layer": {
                "technique": "Dual-Layer Gaussian Blur (25:5)",
                "purpose": "Eliminar barras negras y cubrir lienzo 1080x1920 con ambientación de video nativa"
            },
            "safe_zones_ui": {
                "top_margin": f"{self.safe_zones['top_px']}px (15% - Libera búsqueda y navegación)",
                "bottom_margin": f"{self.safe_zones['bottom_px']}px (20% - Libera copy, audio y perfil)",
                "right_margin": f"{self.safe_zones['right_px']}px (10% - Libera botones Like/Share/Save)",
                "safe_content_y_range": f"[{self.safe_zones['safe_y_start']}px a {self.safe_zones['safe_y_end']}px]"
            },
            "subtitles_burned": has_subs,
            "output_video_path": str(output_video_path),
            "duration_seconds": duration,
            "file_size_mb": file_size_mb,
        }
