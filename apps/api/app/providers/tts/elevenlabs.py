import logging
from typing import List, Optional
import httpx

from app.core.config import settings
from app.providers.tts.base import TTSProvider, TTSAudioResult, TTSVoiceOption

logger = logging.getLogger("shorts_api.tts.elevenlabs")


class ElevenLabsProvider(TTSProvider):
    """
    ElevenLabs TTS provider for ultra-realistic multilingual voice narration.
    """

    BASE_URL = "https://api.elevenlabs.io/v1"

    DEFAULT_VOICES: List[TTSVoiceOption] = [
        TTSVoiceOption(
            id="21m00Tcm4TlvDq8ikWAM",
            name="Rachel (Calm & Narrative)",
            gender="female",
            language_codes=["id-ID", "en-US"],
            description="Suara tenang dan jernih, cocok untuk narasi santai"
        ),
        TTSVoiceOption(
            id="AZnzlk1XvdvUeBnXmlld",
            name="Domi (Strong & Engaging)",
            gender="female",
            language_codes=["id-ID", "en-US"],
            description="Suara berenergi tinggi untuk hook Shorts yang memikat"
        ),
        TTSVoiceOption(
            id="ErXwobaYiN019PkySvjV",
            name="Antoni (Warm Storyteller)",
            gender="male",
            language_codes=["id-ID", "en-US"],
            description="Suara pria hangat dan mendalam untuk fakta/edukasi"
        ),
        TTSVoiceOption(
            id="VR6AewLTigWG4xSOukaG",
            name="Arnold (Crisp & Articulate)",
            gender="male",
            language_codes=["id-ID", "en-US"],
            description="Suara pria tegas dan terartikulasi dengan baik"
        ),
    ]

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.ELEVENLABS_API_KEY
        if not self.api_key:
            logger.warning("ELEVENLABS_API_KEY is not configured.")

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        model: Optional[str] = None
    ) -> TTSAudioResult:
        if not self.api_key:
            raise ValueError(
                "ElevenLabs API key is not configured. "
                "Please set ELEVENLABS_API_KEY in your .env file or choose 'mock' or 'google' provider."
            )

        voice_id = voice or settings.ELEVENLABS_VOICE_ID or "21m00Tcm4TlvDq8ikWAM"
        model_id = model or settings.TTS_MODEL or "eleven_multilingual_v2"

        url = f"{self.BASE_URL}/text-to-speech/{voice_id}"

        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg"
        }

        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "use_speaker_boost": True
            }
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                if response.status_code == 200:
                    audio_bytes = response.content
                    return TTSAudioResult(
                        audio_bytes=audio_bytes,
                        audio_format="mp3",
                        sample_rate=44100,
                        channels=1,
                        duration=None
                    )
                else:
                    error_detail = response.text
                    try:
                        err_json = response.json()
                        error_detail = err_json.get("detail", {}).get("message", error_detail)
                    except Exception:
                        pass

                    if response.status_code in (401, 403):
                        raise RuntimeError(f"ElevenLabs authentication failed ({response.status_code}): {error_detail}")
                    elif response.status_code == 429:
                        raise RuntimeError(f"ElevenLabs rate limit or quota exceeded: {error_detail}")
                    else:
                        raise RuntimeError(f"ElevenLabs API error ({response.status_code}): {error_detail}")

            except httpx.RequestError as exc:
                raise RuntimeError(f"Failed to connect to ElevenLabs API: {exc}") from exc

    async def get_available_voices(self) -> List[TTSVoiceOption]:
        if not self.api_key:
            return self.DEFAULT_VOICES

        url = f"{self.BASE_URL}/voices"
        headers = {"xi-api-key": self.api_key}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    voices_list = data.get("voices", [])
                    res = []
                    for v in voices_list:
                        res.append(
                            TTSVoiceOption(
                                id=v.get("voice_id", ""),
                                name=v.get("name", "Unnamed"),
                                gender=v.get("labels", {}).get("gender"),
                                language_codes=["id-ID", "multilingual"],
                                description=v.get("labels", {}).get("description")
                            )
                        )
                    if res:
                        return res
        except Exception as exc:
            logger.warning(f"Could not fetch dynamic ElevenLabs voices: {exc}")

        return self.DEFAULT_VOICES
