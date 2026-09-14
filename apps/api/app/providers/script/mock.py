import logging
from typing import List
from app.providers.script.base import (
    ScriptGenerationProvider,
    ScriptGenerationContext,
    GeneratedScriptPayload,
    GeneratedSceneSegment,
)

logger = logging.getLogger("shorts_api.providers.script.mock")


class MockScriptProvider(ScriptGenerationProvider):
    """Deterministic script generation provider for testing and offline environments."""

    async def generate_script(self, context: ScriptGenerationContext) -> GeneratedScriptPayload:
        logger.info(
            f"Using MockScriptProvider for project '{context.project_name}' with {len(context.scenes)} scenes"
        )

        # Deterministic phrase mappings for engaging Indonesian Shorts narration
        hook_templates = [
            "Pernah nggak kamu kepikiran tentang hal luar biasa ini?",
            "Ternyata ada rahasia besar yang baru saja terungkap!",
            "Jangan skip dulu, fakta ini bakal bikin kamu tercengang!",
            "Para peneliti baru saja menemukan fakta yang sangat mengejutkan!"
        ]

        body_templates = [
            "Di kedalaman yang belum pernah terjamah, fenomena alam ini terus berlangsung secara alami.",
            "Proses ini terjadi dengan kecepatan luar biasa dan menggunakan energi yang sangat masif.",
            "Setiap detailnya memperlihatkan betapa rumit dan canggihnya struktur yang sedang bekerja ini.",
            "Tidak banyak orang tahu bahwa hal ini memiliki dampak langsung terhadap kehidupan kita sehari-hari."
        ]

        conclusion_templates = [
            "Penemuan ini benar-benar mengubah cara pandang sains modern selamanya!",
            "Kira-kira menurut kamu, apa yang bakal terjadi selanjutnya? Tulis di kolom komentar ya!",
            "Gimana menurutmu? Jangan lupa like dan subscribe untuk fakta menarik berikutnya!",
            "Fakta ini membuktikan bahwa masih banyak misteri dunia yang belum terpecahkan."
        ]

        segments: List[GeneratedSceneSegment] = []

        if not context.scenes:
            # Fallback if no scenes are present
            default_text = "Fakta mengejutkan tentang hal ini baru saja terungkap dan mengubah segalanya!"
            segments.append(
                GeneratedSceneSegment(
                    scene_id="default_scene",
                    sequence=1,
                    adapted_text=default_text
                )
            )
        else:
            num_scenes = len(context.scenes)
            for idx, sc in enumerate(context.scenes):
                seq = sc.sequence

                # Build natural adapted Indonesian text for this scene
                if idx == 0:
                    # Hook
                    template = hook_templates[idx % len(hook_templates)]
                    if sc.source_dialogue and len(sc.source_dialogue.strip()) > 5:
                        adapted = f"{template} {sc.source_dialogue.strip()}"
                    else:
                        adapted = template
                elif idx == num_scenes - 1:
                    # Payoff / Conclusion
                    template = conclusion_templates[idx % len(conclusion_templates)]
                    adapted = template
                else:
                    # Body information
                    template = body_templates[(idx - 1) % len(body_templates)]
                    if sc.source_dialogue and len(sc.source_dialogue.strip()) > 5:
                        adapted = f"{template} Terkait hal ini: {sc.source_dialogue.strip()}."
                    else:
                        adapted = template

                # Respect custom instructions if any
                if context.instructions and "pendek" in context.instructions.lower():
                    words = adapted.split()
                    if len(words) > 8:
                        adapted = " ".join(words[:8]) + "..."

                segments.append(
                    GeneratedSceneSegment(
                        scene_id=sc.scene_id,
                        sequence=seq,
                        adapted_text=adapted
                    )
                )

        # Build full combined script
        full_script = " ".join(seg.adapted_text for seg in segments)

        # Generate catchy YouTube Shorts title
        clean_title = context.project_name.strip()
        title = f"Fakta Menarik: {clean_title} Yang Bikin Tercengang!"

        return GeneratedScriptPayload(
            title=title,
            full_script=full_script,
            segments=segments
        )
