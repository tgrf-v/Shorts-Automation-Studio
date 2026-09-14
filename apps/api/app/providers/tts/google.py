import base64
import logging
from typing import List, Optional
import httpx

from app.core.config import settings
from app.providers.tts.base import TTSProvider, TTSAudioResult, TTSVoiceOption

logger = logging.getLogger("shorts_api.tts.google")


class GoogleTTSProvider(TTSProvider):
    """
    Google Cloud Text-to-Speech provider using official REST endpoints.
    Synthesizes natural Indonesian speech using Standard and WaveNet neural voices.
    """

    SYNTHESIZE_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"

    DEFAULT_VOICES: List[TTSVoiceOption] = [
        TTSVoiceOption(
            id="id-ID-Standard-A",
            name="id-ID-Standard-A (Wanita)",
            gender="female",
            language_codes=["id-ID"],
            description="Suara wanita standar jernih"
        ),
        TTSVoiceOption(
            id="id-ID-Standard-B",
            name="id-ID-Standard-B (Pria)",
            gender="male",
            language_codes=["id-ID"],
            description="Suara pria standar mantap"
        ),
        TTSVoiceOption(
            id="id-ID-Standard-C",
            name="id-ID-Standard-C (Pria)",
            gender="male",
            language_codes=["id-ID"],
            description="Suara pria nada tinggi & energik"
        ),
        TTSVoiceOption(
            id="id-ID-Standard-D",
            name="id-ID-Standard-D (Wanita)",
            gender="female",
            language_codes=["id-ID"],
            description="Suara wanita lembut dan natural"
        ),
        TTSVoiceOption(
            id="id-ID-Wavenet-A",
            name="id-ID-Wavenet-A (Wanita - Deep Neural)",
            gender="female",
            language_codes=["id-ID"],
            description="Suara neural wanita ekspresif untuk video shorts"
        ),
        TTSVoiceOption(
            id="id-ID-Wavenet-B",
            name="id-ID-Wavenet-B (Pria - Deep Neural)",
            gender="male",
            language_codes=["id-ID"],
            description="Suara neural pria berwibawa & jelas"
        ),
        TTSVoiceOption(
            id="id-ID-Wavenet-C",
            name="id-ID-Wavenet-C (Pria - Deep Neural)",
            gender="male",
            language_codes=["id-ID"],
            description="Suara neural pria santai dan informatif"
        ),
        TTSVoiceOption(
            id="id-ID-Wavenet-D",
            name="id-ID-Wavenet-D (Wanita - Deep Neural)",
            gender="female",
            language_codes=["id-ID"],
            description="Suara neural wanita antusias & ceria"
        ),
    ]

    def __init__(self, api_key: Optional[str] = None):
        # Allow specific GOOGLE_TTS_API_KEY, or fallback to GEMINI_API_KEY
        self.api_key = api_key or settings.GOOGLE_TTS_API_KEY or settings.GEMINI_API_KEY
        if not self.api_key:
            logger.warning("Neither GOOGLE_TTS_API_KEY nor GEMINI_API_KEY is configured.")

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        model: Optional[str] = None
    ) -> TTSAudioResult:
        if not self.api_key:
            raise ValueError(
                "Google TTS API key is not configured. "
                "Please set GOOGLE_TTS_API_KEY in your .env file or choose 'mock' provider."
            )

        chosen_voice = voice or settings.TTS_VOICE or "id-ID-Standard-A"
        language_code = "id-ID"

        payload = {
            "input": {"text": text},
            "voice": {
                "languageCode": language_code,
                "name": chosen_voice
            },
            "audioConfig": {
                "audioEncoding": "MP3",
                "sampleRateHertz": 44100,
                "speakingRate": 1.0,
                "pitch": 0.0
            }
        }

        url = f"{self.SYNTHESIZE_URL}?key={self.api_key}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code == 200:
                    data = response.json()
                    audio_b64 = data.get("audioContent", "")
                    if not audio_b64:
                        raise ValueError("Google TTS returned empty audioContent.")
                    audio_bytes = base64.b64decode(audio_b64)
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
                        error_detail = err_json.get("error", {}).get("message", error_detail)
                    except Exception:
                        pass

                    if response.status_code in (401, 403):
                        raise RuntimeError(
                            f"Google Cloud TTS authentication failed ({response.status_code}): {error_detail}. "
                            "Ensure the Cloud Text-to-Speech API is enabled in your Google Cloud Console, "
                            "or switch TTS_PROVIDER to 'mock' for local offline testing."
                        )
                    elif response.status_code == 429:
                        raise RuntimeError(f"Google Cloud TTS quota or rate limit exceeded: {error_detail}")
                    else:
                        raise RuntimeError(f"Google Cloud TTS error ({response.status_code}): {error_detail}")

            except httpx.RequestError as exc:
                raise RuntimeError(f"Failed to connect to Google Cloud TTS: {exc}") from exc

    async def get_available_voices(self) -> List[TTSVoiceOption]:
        return self.DEFAULT_VOICES
