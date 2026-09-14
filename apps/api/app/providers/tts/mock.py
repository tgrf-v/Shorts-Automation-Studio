import io
import math
import struct
import wave
import logging
from typing import List, Optional
from app.providers.tts.base import TTSProvider, TTSAudioResult, TTSVoiceOption

logger = logging.getLogger("shorts_api.tts.mock")


class MockTTSProvider(TTSProvider):
    """
    Deterministic Mock TTS provider for local development, CI/CD, and tests.
    Generates valid, non-empty 44.1kHz 16-bit mono WAV audio files with predictable
    duration calculated from words and speaking rate (~150 words/minute = 2.5 wps).
    Zero external dependencies or API keys required.
    """

    AVAILABLE_VOICES: List[TTSVoiceOption] = [
        TTSVoiceOption(
            id="mock-id-female",
            name="Siti (Mock Wanita - Naratif)",
            gender="female",
            language_codes=["id-ID"],
            description="Suara wanita hangat untuk narasi YouTube Shorts"
        ),
        TTSVoiceOption(
            id="mock-id-male",
            name="Budi (Mock Pria - Informatif)",
            gender="male",
            language_codes=["id-ID"],
            description="Suara pria lugas dan profesional"
        ),
    ]

    def _estimate_duration(self, text: str) -> float:
        """Estimates duration in seconds based on word count (150 WPM = 2.5 words/sec)."""
        words = [w for w in text.split() if w.strip()]
        count = max(len(words), 1)
        # 150 words/minute -> 2.5 words/second
        duration = round(count / 2.5, 2)
        return max(duration, 1.2)  # Minimum 1.2s for audible audio clip

    def _generate_wav_bytes(self, duration: float, sample_rate: int = 44100, freq: float = 440.0) -> bytes:
        """
        Synthesizes a clean, gentle synthetic audio WAV with fade-in and fade-out
        to prevent clipping or audio pop artifacts.
        """
        num_samples = int(duration * sample_rate)
        fade_samples = min(int(sample_rate * 0.05), num_samples // 4)
        frames = bytearray()

        for i in range(num_samples):
            # Compute smooth fade-in and fade-out envelope
            fade = 1.0
            if i < fade_samples and fade_samples > 0:
                fade = i / fade_samples
            elif i > (num_samples - fade_samples) and fade_samples > 0:
                fade = (num_samples - i) / fade_samples

            # Gentle, pleasant harmonic chime (440Hz with soft 880Hz overtone)
            val = 0.15 * math.sin(2.0 * math.pi * freq * i / sample_rate) + \
                  0.05 * math.sin(2.0 * math.pi * (freq * 2) * i / sample_rate)
            sample = int(32767.0 * fade * val)
            sample = max(-32768, min(32767, sample))
            frames.extend(struct.pack('<h', sample))

        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1)       # Mono
            wf.setsampwidth(2)       # 16-bit PCM
            wf.setframerate(sample_rate)
            wf.writeframes(frames)

        return buf.getvalue()

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        model: Optional[str] = None
    ) -> TTSAudioResult:
        logger.info(f"MockTTS synthesizing text ({len(text)} chars) with voice='{voice}'")
        duration = self._estimate_duration(text)

        # Tone frequency variation depending on voice: female (520Hz) vs male (330Hz)
        freq = 520.0 if voice and "female" in voice.lower() else 330.0
        sample_rate = 44100
        audio_bytes = self._generate_wav_bytes(duration=duration, sample_rate=sample_rate, freq=freq)

        return TTSAudioResult(
            audio_bytes=audio_bytes,
            audio_format="wav",
            sample_rate=sample_rate,
            channels=1,
            duration=duration
        )

    async def get_available_voices(self) -> List[TTSVoiceOption]:
        return self.AVAILABLE_VOICES
