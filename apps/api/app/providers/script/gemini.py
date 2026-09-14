import os
import json
import re
import logging
from typing import Optional, List
import httpx
from app.core.config import settings
from app.providers.script.base import (
    ScriptGenerationProvider,
    ScriptGenerationContext,
    GeneratedScriptPayload,
    GeneratedSceneSegment,
)

logger = logging.getLogger("shorts_api.providers.script.gemini")


class GeminiScriptProvider(ScriptGenerationProvider):
    """Google Gemini script adaptation provider with structured JSON output and robust error handling."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = (api_key if api_key is not None else settings.GEMINI_API_KEY) or ""
        self.model = model or settings.SCRIPT_MODEL or "gemini-2.5-flash"

    def _get_api_url(self, model_name: str) -> str:
        clean_model = model_name.removeprefix("models/")
        return f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:generateContent"

    def _build_prompt(self, context: ScriptGenerationContext) -> str:
        prompt_lines = [
            f"Project Name: {context.project_name}",
            f"Original Reference Full Transcript:\n\"{context.source_transcript_full}\"\n",
            "Scenes to adapt (maintain strict 1-to-1 mapping with scene_id):"
        ]

        for sc in context.scenes:
            dialogue_str = f"\"{sc.source_dialogue}\"" if sc.source_dialogue else "None (Visual only scene)"
            visual_str = sc.visual_description or "Visual action sequence"
            prompt_lines.append(
                f"- Scene ID: {sc.scene_id} | Sequence: {sc.sequence} | Duration: {sc.duration:.1f}s | "
                f"Visual: {visual_str} | Original Narration: {dialogue_str}"
            )

        if context.instructions:
            prompt_lines.append(f"\nCreator's Custom Instructions:\n{context.instructions}")

        return "\n".join(prompt_lines)

    async def _execute_generate_request(
        self,
        client: httpx.AsyncClient,
        model_name: str,
        payload: dict
    ) -> dict:
        url = self._get_api_url(model_name)
        # Pass API key securely via header instead of exposing in URL query string
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        response = await client.post(url, json=payload, headers=headers)

        # If model returned 404 indicating deprecation/redirect for new projects, fallback to gemini-3.6-flash
        if response.status_code == 404 and model_name != "gemini-3.6-flash":
            error_body = response.text
            if "gemini-3.6-flash" in error_body or "no longer available" in error_body:
                logger.info(f"Model '{model_name}' redirected upstream. Retrying with 'gemini-3.6-flash'...")
                fallback_url = self._get_api_url("gemini-3.6-flash")
                response = await client.post(fallback_url, json=payload, headers=headers)

        if response.status_code != 200:
            self._handle_http_error(response)

        return response.json()

    def _handle_http_error(self, response: httpx.Response) -> None:
        status_code = response.status_code
        err_msg = ""
        try:
            err_data = response.json()
            if "error" in err_data and "message" in err_data["error"]:
                err_msg = err_data["error"]["message"]
        except Exception:
            err_msg = response.text[:200]

        # Sanitize any accidental key leak in error message
        if self.api_key and self.api_key in err_msg:
            err_msg = err_msg.replace(self.api_key, "[REDACTED_API_KEY]")

        logger.error(f"Gemini API returned HTTP {status_code}: {err_msg}")

        if status_code in (401, 403):
            raise ValueError("Invalid Google Gemini API key or unauthorized request. Please verify GEMINI_API_KEY.")
        elif status_code == 404:
            raise ValueError(f"Configured Gemini model '{self.model}' was not found: {err_msg}")
        elif status_code == 429:
            raise RuntimeError("Google Gemini API quota exceeded or rate-limited. Please wait or check your API quota.")
        elif status_code in (500, 503):
            raise RuntimeError("Google Gemini service is temporarily unavailable. Please retry in a moment.")
        else:
            raise RuntimeError(f"Gemini API request failed ({status_code}): {err_msg}")

    async def generate_script(self, context: ScriptGenerationContext) -> GeneratedScriptPayload:
        if not self.api_key or len(self.api_key.strip()) < 5:
            raise ValueError("GEMINI_API_KEY is not configured. Please set GEMINI_API_KEY in your environment.")

        system_instruction = (
            "You are an expert YouTube Shorts scriptwriter adapting viral English reference videos into natural, engaging Bahasa Indonesia.\n"
            "CRITICAL ADAPTATION RULES:\n"
            "1. Natural Conversational Indonesian: Do NOT translate word-for-word literally. Use natural spoken Indonesian suitable for fast-paced YouTube Shorts.\n"
            "2. Punchy Hook: Scene 1 MUST be a compelling hook (2-3 seconds) that grabs curiosity immediately.\n"
            "3. Pacing: Target ~150 words per minute speaking speed that matches the duration of each scene.\n"
            "4. Factual Integrity: Preserve the core facts and narrative flow of the original without hallucinating unsupported claims.\n"
            "5. Scene Alignment: Maintain exact mapping to the provided 'scene_id' for each scene.\n\n"
            "STRICT JSON OUTPUT FORMAT:\n"
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
            "contents": [
                {
                    "parts": [
                        {"text": f"System Guidelines:\n{system_instruction}\n\nTask Input:\n{user_content}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.4,
                "responseMimeType": "application/json"
            }
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            try:
                data = await self._execute_generate_request(client, self.model, payload)
                candidates = data.get("candidates", [])
                if not candidates or "content" not in candidates[0]:
                    raise RuntimeError("Gemini returned an empty response with no candidates.")

                text_content = candidates[0]["content"]["parts"][0]["text"]

                # Safe JSON parsing with regex recovery if needed
                clean_json = re.sub(r"^```(?:json)?\s*|\s*```$", "", text_content.strip(), flags=re.MULTILINE)
                try:
                    parsed = json.loads(clean_json)
                except json.JSONDecodeError:
                    # Attempt to locate JSON substring
                    json_match = re.search(r"\{.*\}", clean_json, re.DOTALL)
                    if json_match:
                        parsed = json.loads(json_match.group(0))
                    else:
                        raise ValueError("Gemini response did not contain valid JSON.")

                raw_segments = parsed.get("segments", [])
                segments: List[GeneratedSceneSegment] = []
                for s_data in raw_segments:
                    segments.append(
                        GeneratedSceneSegment(
                            scene_id=str(s_data.get("scene_id", "")),
                            sequence=int(s_data.get("sequence", len(segments) + 1)),
                            adapted_text=str(s_data.get("adapted_text", "")).strip()
                        )
                    )

                full_script = str(parsed.get("full_script", "")).strip()
                if not full_script:
                    full_script = " ".join(s.adapted_text for s in segments)

                title = str(parsed.get("title", "")).strip() or f"Shorts: {context.project_name}"

                return GeneratedScriptPayload(
                    title=title,
                    full_script=full_script,
                    segments=segments
                )

            except httpx.TimeoutException:
                logger.error("Gemini API request timed out after 45s.")
                raise RuntimeError("Google Gemini API request timed out. Please try again.")
            except httpx.RequestError as req_err:
                logger.error(f"Gemini connection error: {req_err}")
                raise RuntimeError("Failed to connect to Google Gemini API. Please check network connectivity.")
            except (ValueError, RuntimeError):
                raise
            except Exception as exc:
                logger.error(f"Unexpected error during Gemini script generation: {exc}", exc_info=True)
                raise RuntimeError(f"Gemini script generation failed: {exc}") from exc
