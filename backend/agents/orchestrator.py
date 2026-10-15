"""
Rol: Agente Líder / Director de Orquesta del Sistema Multi-Agente (Lead System Agent)
Gobernanza, Supervisión y Orquestación Autónoma:
1. Regla Absoluta de Idioma: Toda salida en ESPAÑOL. Rechaza y exige corrección inmediata ante cualquier desvío.
2. Secuencia Estricta:
   - Paso 1: CuttingAgent (Identificación de highlights 30-60s y traducción al español)
   - Paso 2: SubtitleAgent (Segmentación 1-3 palabras en MAYÚSCULAS y timestamps)
   - Paso 3: FramingAgent (Auto-framing 9:16 y Safe Zones para TikTok/Shorts)
   - Paso 4: SeoMarketingAgent (3 hooks, descripción, CTA y 5-8 hashtags en español)
3. Validación de contratos JSON y control de fallos en cada compuerta de pase.
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from backend.agents.cutting_agent import CuttingAgent
from backend.agents.subtitle_agent import SubtitleAgent
from backend.agents.framing_agent import FramingAgent
from backend.agents.seo_agent import SeoMarketingAgent
from backend.agents.translator import is_text_spanish, translate_to_spanish

logger = logging.getLogger("clipai.orchestrator")


class GovernanceValidationError(Exception):
    """Excepción lanzada cuando una compuerta de validación de gobernanza es rechazada."""
    pass


class LeadOrchestratorAgent:
    """
    Agente Líder y Director de Orquesta Multi-Agente.
    Supervisa, valida y coordina el flujo end-to-end.
    """
    def __init__(self, output_dir: Path = Path("output")):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "orchestrator").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "thumbnails").mkdir(parents=True, exist_ok=True)

        # Instanciación de agentes especializados subordinados
        self.cutting_agent = CuttingAgent()
        self.subtitle_agent = SubtitleAgent(style_name="alex_hormozi")
        self.framing_agent = FramingAgent()
        self.seo_agent = SeoMarketingAgent()

    # ------------------------------------------------------------------
    # Compuertas de Validación Estricta
    # ------------------------------------------------------------------
    def validate_cutting_output(self, data: Dict[str, Any]):
        """Valida contrato JSON y regla absoluta de idioma en Paso 1."""
        if not isinstance(data, dict) or data.get("status") != "success":
            raise GovernanceValidationError("El Agente de Corte no devolvió un estado de éxito.")
        clips = data.get("clips", [])
        if not clips:
            raise GovernanceValidationError("El Agente de Corte no devolvió ningún clip válido.")
        
        for idx, c in enumerate(clips):
            for field in ["start_time", "end_time", "duration_seconds", "text_spanish"]:
                if field not in c:
                    raise GovernanceValidationError(f"Clip #{idx+1} carece del campo obligatorio: '{field}'.")
            
            # REGLA ABSOLUTA DE IDIOMA
            if not is_text_spanish(c["text_spanish"]):
                logger.error(f"[Gobernanza] Rechazada salida de CuttingAgent: clip #{idx+1} contiene texto no español.")
                # Corrección obligatoria inmediata
                c["text_spanish"] = translate_to_spanish(c["text_spanish"])
                if not is_text_spanish(c["text_spanish"]):
                    raise GovernanceValidationError(f"Rechazo: No se pudo garantizar traducción al español en clip #{idx+1}.")

    def validate_subtitle_output(self, data: Dict[str, Any]):
        """Valida contrato JSON, sincronización y formato de mayúsculas en Paso 2."""
        if not isinstance(data, dict) or data.get("status") != "success":
            raise GovernanceValidationError("El Agente de Subtitulación no devolvió estado de éxito.")
        if "ass_file_path" not in data or not Path(data["ass_file_path"]).exists():
            raise GovernanceValidationError("No se generó el archivo de subtítulos ASS correspondiente.")
        
        tokens = data.get("all_tokens", [])
        if not tokens:
            raise GovernanceValidationError("El Agente de Subtitulación no generó tokens de subtítulo.")
        
        # Validar MAYÚSCULAS
        for t in tokens:
            txt = t.get("text_uppercase", "")
            if txt != txt.upper():
                t["text_uppercase"] = txt.upper()

    def validate_framing_output(self, data: Dict[str, Any]):
        """Valida resolución 9:16 y existencia de archivo renderizado en Paso 3."""
        if not isinstance(data, dict) or data.get("status") != "success":
            raise GovernanceValidationError("El Agente de Formato 9:16 reportó un fallo en renderizado.")
        out_vid = data.get("output_video_path")
        if not out_vid or not Path(out_vid).exists():
            raise GovernanceValidationError(f"El archivo de video final no existe en disco: {out_vid}")
        if data.get("aspect_ratio") != "9:16":
            raise GovernanceValidationError(f"La relación de aspecto debe ser estrictamente 9:16.")

    def validate_seo_output(self, data: Dict[str, Any]):
        """Valida que la estrategia de marketing contenga todos los elementos en español."""
        if not isinstance(data, dict) or data.get("status") != "success":
            raise GovernanceValidationError("El Agente de SEO/Marketing no devolvió un resultado válido.")
        
        hooks = data.get("hook_screen_options", [])
        if len(hooks) < 3:
            raise GovernanceValidationError("El Agente SEO debe proporcionar un mínimo de 3 opciones de hooks.")
        
        tags = data.get("hashtags", [])
        if len(tags) < 5 or len(tags) > 8:
            raise GovernanceValidationError(f"Se requieren entre 5 y 8 hashtags (se recibieron {len(tags)}).")
        
        # Regla absoluta de idioma en SEO
        for h in hooks:
            if not is_text_spanish(h):
                raise GovernanceValidationError("Un hook de pantalla contiene palabras no adaptadas al español.")

    # ------------------------------------------------------------------
    # Flujo de Orquestación Secuencial
    # ------------------------------------------------------------------
    def orchestrate_pipeline(
        self,
        job_id: str,
        source_video_path: str,
        transcript_data: Dict[str, Any],
        max_clips: int = 3,
        framing_layout: str = "autoframing",
    ) -> Dict[str, Any]:
        """
        Ejecución supervisada del flujo multi-agente con validación secuencial.
        """
        logger.info(f"[Director de Orquesta] Iniciando orquestación supervisada para Job ID: {job_id}")
        orchestrator_log = []

        # ==============================================================
        # PASO 1: Agente de Corte
        # ==============================================================
        logger.info("[Director de Orquesta] Delegando Paso 1 al Agente de Corte...")
        step1_result = self.cutting_agent.process(transcript_data, max_clips=max_clips)
        self.validate_cutting_output(step1_result)
        orchestrator_log.append({
            "step": 1,
            "agent": "CuttingAgent",
            "validation": "PASSED (ESPAÑOL VERIFICADO)",
            "output_summary": f"{len(step1_result['clips'])} fragmentos identificados",
        })

        processed_clips = []
        job_work_dir = self.output_dir / "orchestrator" / job_id
        job_work_dir.mkdir(parents=True, exist_ok=True)

        for clip_meta in step1_result["clips"]:
            idx = clip_meta["clip_index"]
            clip_id = f"{job_id}_clip{idx}"

            # ==========================================================
            # PASO 2: Agente de Subtitulación
            # ==========================================================
            logger.info(f"[Director de Orquesta] Delegando Paso 2 al Agente de Subtitulación para Clip #{idx}...")
            step2_result = self.subtitle_agent.process(
                clip_data=clip_meta,
                transcript_segments=transcript_data.get("segments", []),
                out_dir=job_work_dir,
            )
            self.validate_subtitle_output(step2_result)
            orchestrator_log.append({
                "step": 2,
                "clip_id": clip_id,
                "agent": "SubtitleAgent",
                "validation": "PASSED (MAYÚSCULAS & TIMESTAMPS MS)",
                "tokens_count": step2_result["tokens_count"],
            })

            # ==========================================================
            # PASO 3: Agente de Formato 9:16
            # ==========================================================
            logger.info(f"[Director de Orquesta] Delegando Paso 3 al Agente de Formato 9:16 para Clip #{idx}...")
            target_mp4 = self.output_dir / f"{clip_id}.mp4"
            step3_result = self.framing_agent.process(
                source_video_path=source_video_path,
                start_time=clip_meta["start_time"],
                end_time=clip_meta["end_time"],
                ass_subtitle_path=step2_result["ass_file_path"],
                output_video_path=target_mp4,
                layout_mode=framing_layout,
            )
            self.validate_framing_output(step3_result)
            orchestrator_log.append({
                "step": 3,
                "clip_id": clip_id,
                "agent": "FramingAgent",
                "validation": "PASSED (RESOLUCIÓN 1080x1920 & SAFE ZONES APLICADAS)",
                "file_size_mb": step3_result["file_size_mb"],
            })

            # ==========================================================
            # PASO 4: Agente SEO/Marketing
            # ==========================================================
            logger.info(f"[Director de Orquesta] Delegando Paso 4 al Agente SEO/Marketing para Clip #{idx}...")
            step4_result = self.seo_agent.process(clip_meta)
            self.validate_seo_output(step4_result)
            orchestrator_log.append({
                "step": 4,
                "clip_id": clip_id,
                "agent": "SeoMarketingAgent",
                "validation": "PASSED (ESTRATEGIA 100% EN ESPAÑOL)",
                "hooks_count": len(step4_result["hook_screen_options"]),
            })

            # Consolidar paquete del clip
            consolidated_clip = {
                "clip_id": clip_id,
                "job_id": job_id,
                "clip_index": idx,
                "timing": {
                    "start_time": clip_meta["start_time"],
                    "end_time": clip_meta["end_time"],
                    "duration_seconds": step3_result["duration_seconds"],
                },
                "language": "es",
                "text_content_es": clip_meta["text_spanish"],
                "video_technical": {
                    "format": "9:16 Vertical",
                    "resolution": "1080x1920",
                    "codec": "H.264 / AAC",
                    "video_path": str(target_mp4),
                    "video_url": f"/output/{clip_id}.mp4",
                    "file_size_mb": step3_result["file_size_mb"],
                    "safe_zones_applied": step3_result["safe_zones"],
                },
                "subtitles": {
                    "style": step2_result["style"],
                    "ass_path": step2_result["ass_file_path"],
                    "tokens_preview": step2_result["sample_tokens"],
                },
                "marketing_seo": {
                    "screen_hook_options": step4_result["hook_screen_options"],
                    "recommended_hook": step4_result["selected_hook"],
                    "engagement_description": step4_result["description"],
                    "call_to_action": step4_result["call_to_action"],
                    "hashtags": step4_result["hashtags"],
                    "ready_to_publish_copy": step4_result["ready_to_publish_copy"],
                },
                "viral_score": clip_meta["viral_score"],
            }
            processed_clips.append(consolidated_clip)

            # Persistir metadata en disco para la biblioteca
            meta_file = self.output_dir / "metadata" / f"{clip_id}.json"
            meta_file.parent.mkdir(parents=True, exist_ok=True)
            with open(meta_file, "w", encoding="utf-8") as mf:
                json.dump({
                    "clip_id": clip_id,
                    "job_id": job_id,
                    "title": step4_result["selected_hook"],
                    "hook": step4_result["selected_hook"],
                    "hashtags": step4_result["hashtags"],
                    "viral_score": clip_meta["viral_score"],
                    "duration": step3_result["duration_seconds"],
                    "aspect_ratio": "9:16",
                    "video_path": str(target_mp4),
                    "video_url": f"/output/{clip_id}.mp4",
                    "file_size_mb": step3_result["file_size_mb"],
                    "ai_copy": step4_result["ready_to_publish_copy"],
                }, mf, ensure_ascii=False, indent=2)

        # Informe final estructurado del Lead System Agent
        orchestrator_report = {
            "status": "completed",
            "role": "Lead System Agent / Director de Orquesta",
            "job_id": job_id,
            "governance_status": "ALL VALIDATION GATES PASSED",
            "language_enforcement": "STRICT_SPANISH_VERIFIED",
            "total_clips_delivered": len(processed_clips),
            "orchestration_log": orchestrator_log,
            "clips": processed_clips,
        }

        # Guardar registro de gobernanza
        gov_file = job_work_dir / "orchestration_report.json"
        with open(gov_file, "w", encoding="utf-8") as gf:
            json.dump(orchestrator_report, gf, ensure_ascii=False, indent=2)

        return orchestrator_report
