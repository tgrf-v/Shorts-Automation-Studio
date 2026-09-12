import os
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.core.config import settings

logger = logging.getLogger("shorts_api.services.transcription")


class TranscriptSegment(BaseModel):
    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")
    text: str = Field(..., description="Transcribed text segment")


class STTResult(BaseModel):
    language: str = Field(default="en", description="Detected language code")
    text: str = Field(..., description="Full combined transcript text")
    segments: List[TranscriptSegment] = Field(default_factory=list, description="Timestamped segments")
    provider: str = Field(default="faster_whisper", description="STT provider used")


class STTProvider(ABC):
    """Abstract Base Class defining the contract for speech-to-text providers."""

    @abstractmethod
    async def transcribe(self, audio_path: str) -> STTResult:
        """Transcribes an audio file into structured text and timestamped segments."""
        pass


class FasterWhisperSTTProvider(STTProvider):
    """Local STT provider powered by faster-whisper on CPU/GPU."""

    def __init__(self, model_size: Optional[str] = None):
        self.model_size = model_size or settings.WHISPER_MODEL
        self._model = None

    def _get_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            # Run on CPU with int8 quantization for lightweight and fast execution
            logger.info(f"Loading faster-whisper model '{self.model_size}' (device=cpu, compute_type=int8)...")
            self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
        return self._model

    async def transcribe(self, audio_path: str) -> STTResult:
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        loop = asyncio.get_running_loop()

        def _do_transcribe() -> STTResult:
            try:
                model = self._get_model()
                segments_iter, info = model.transcribe(
                    audio_path,
                    beam_size=5,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=500)
                )

                segments: List[TranscriptSegment] = []
                full_text_parts: List[str] = []

                for seg in segments_iter:
                    seg_text = seg.text.strip()
                    if seg_text:
                        segments.append(
                            TranscriptSegment(
                                start=round(float(seg.start), 3),
                                end=round(float(seg.end), 3),
                                text=seg_text
                            )
                        )
                        full_text_parts.append(seg_text)

                detected_lang = info.language if info and info.language else "en"
                full_text = " ".join(full_text_parts)

                logger.info(
                    f"Transcription complete: {len(segments)} segments, language='{detected_lang}'"
                )

                return STTResult(
                    language=detected_lang,
                    text=full_text,
                    segments=segments,
                    provider="faster_whisper"
                )
            except Exception as exc:
                logger.error(f"faster-whisper transcription error: {exc}")
                raise RuntimeError(f"Transcription failed: {exc}") from exc

        return await loop.run_in_executor(None, _do_transcribe)


class MockSTTProvider(STTProvider):
    """Deterministic mock provider for automated tests and offline environments."""

    async def transcribe(self, audio_path: str) -> STTResult:
        logger.info(f"Using MockSTTProvider for audio: {audio_path}")
        segments = [
            TranscriptSegment(
                start=0.0,
                end=2.5,
                text="Scientists recently made an astonishing discovery."
            ),
            TranscriptSegment(
                start=2.5,
                end=5.0,
                text="Deep beneath the ocean floor, new ecosystems thrive."
            ),
            TranscriptSegment(
                start=5.0,
                end=8.0,
                text="This finding completely changes how we understand biology on Earth."
            )
        ]
        return STTResult(
            language="en",
            text=" ".join(s.text for s in segments),
            segments=segments,
            provider="mock"
        )


def get_stt_provider() -> STTProvider:
    provider_name = settings.STT_PROVIDER.lower()
    if provider_name == "faster_whisper":
        try:
            return FasterWhisperSTTProvider()
        except ImportError:
            logger.warning("faster-whisper is not installed. Falling back to MockSTTProvider.")
            return MockSTTProvider()
    elif provider_name == "mock":
        return MockSTTProvider()
    else:
        logger.warning(f"Unknown STT_PROVIDER '{provider_name}'. Falling back to MockSTTProvider.")
        return MockSTTProvider()
