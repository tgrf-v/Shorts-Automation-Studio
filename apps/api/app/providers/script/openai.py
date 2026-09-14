import os
import json
import re
import logging
from typing import Optional
import httpx
from app.core.config import settings
from app.providers.script.base import (
    ScriptGenerationProvider,
    ScriptGenerationContext,
    GeneratedScriptPayload,
    GeneratedSceneSegment,
)

logger = logging.getLogger("shorts_api.providers.script.openai")


class OpenAIScriptProvider(ScriptGenerationProvider):
    """OpenAI script adaptation provider with JSON Mode support."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.SCRIPT_MODEL or "gpt-4o-mini"
        self.api_url = "https://api.openai.com/v1/chat/completions"

    def _build_prompt(self, context: ScriptGenerationContext) -> str:
        prompt_lines = [
            f"Project: {context.project_name}",
            f"Original Reference Full Transcript:\n\"{context.source_transcript_full}\"\n",
            "Scenes to adapt (preserve exact scene_id mapping):"
        ]

        for sc in context.scenes:
            dialogue_str = f"\"{sc.source_dialogue}\"" if sc.source_dialogue else "None (Visual only)"
            visual_str = sc.visual_description or "Visual elements in action"
            prompt_lines.append(
                f"- Scene ID: {sc.scene_id} | Sequence: {sc.sequence} | Duration: {sc.duration:.1f}s | "
                f"Visual: {visual_str} | Original Narration: {dialogue_str}"
            )

        if context.instructions:
            prompt_lines.append(f"\nUser Specific Instructions:\n{context.instructions}")

        return "\n".join(prompt_lines)

    async def generate_script(self, context: ScriptGenerationContext) -> GeneratedScriptPayload:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured.")

        system_instruction = (
            "You are an expert YouTube Shorts scriptwriter adapting viral English reference videos into natural, engaging Bahasa Indonesia.\n"
            "ADAPTATION RULES:\n"
            "1. Do NOT translate word-for-word literally. Rephrase naturally into conversational Indonesian suitable for YouTube Shorts.\n"
            "2. Scene 1 MUST be a punchy hook (2-3 seconds) that grabs curiosity.\n"
            "3. Keep sentences short, fast-paced, and active. Avoid formal or stiff academic vocabulary.\n"
            "4. Preserve core factual meaning without hallucinating or making up unverified claims.\n"
            "5. Pacing: Aim for around 150 words per minute speaking speed matching the timing of each scene.\n"
            "6. Alignment: Return each scene's narration mapped to its exact 'scene_id'.\n\n"
            "OUTPUT FORMAT: Strictly return valid JSON adhering to:\n"
            "{\n"
            "  \"title\": \"Judul Menarik YouTube Shorts\",\n"
            "  \"full_script\": \"Narasi lengkap dari awal sampai akhir dalam Bahasa Indonesia.\",\n"
            "  \"segments\": [\n"
            "    {\n"
            "      \"scene_id\": \"<exact scene_id string>\",\n"
            "      \"adapted_text\": \"Narasi Bahasa Indonesia untuk scene ini.\"\n"
            "    }\n"
            "  ]\n"
            "}"
        )

        user_content = self._build_prompt(context)

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_content}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.4
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            try:
                response = await client.post(self.api_url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                text_content = data["choices"][0]["message"]["content"]

                clean_json = re.sub(r"^```(?:json)?\s*|\s*```$", "", text_content.strip(), flags=re.MULTILINE)
                parsed = json.loads(clean_json)

                raw_segments = parsed.get("segments", [])
                segments: list[GeneratedSceneSegment] = []
                for s_data in raw_segments:
                    segments.append(
                        GeneratedSceneSegment(
                            scene_id=str(s_data.get("scene_id", "")),
                            sequence=int(s_data.get("sequence", len(segments) + 1)),
                            adapted_text=str(s_data.get("adapted_text", "")).strip()
                        )
                    )

                full_script = parsed.get("full_script", " ".join(s.adapted_text for s in segments))
                title = parsed.get("title", f"Shorts: {context.project_name}")

                return GeneratedScriptPayload(
                    title=title,
                    full_script=full_script,
                    segments=segments
                )

            except Exception as exc:
                logger.error(f"OpenAI API script generation error: {exc}", exc_info=True)
                raise RuntimeError(f"OpenAI script generation failed: {exc}") from exc
