from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel, Field


class TTSAudioResult(BaseModel):
    """Result of synthesizing text into raw audio bytes."""
    audio_bytes: bytes = Field(..., description="Raw binary content of generated audio file")
    audio_format: str = Field(default="mp3", description="Audio container/codec format: mp3 or wav")
    sample_rate: int = Field(default=44100, description="Audio sample rate in Hz (e.g. 44100 or 48000)")
    channels: int = Field(default=1, description="Number of audio channels (1=mono, 2=stereo)")
    duration: Optional[float] = Field(default=None, description="Audio duration in seconds if known")


class TTSVoiceOption(BaseModel):
    """Available voice descriptor for selection in settings."""
    id: str = Field(..., description="Provider voice identifier")
    name: str = Field(..., description="Human-readable voice display name")
    gender: Optional[str] = Field(default=None, description="Voice gender: female, male, neutral")
    language_codes: List[str] = Field(default_factory=lambda: ["id-ID"], description="Supported BCP-47 language tags")
    description: Optional[str] = Field(default=None, description="Additional voice characteristics or tone")


class TTSProvider(ABC):
    """Abstract Base Class defining the contract for Text-to-Speech audio providers."""

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        model: Optional[str] = None
    ) -> TTSAudioResult:
        """
        Synthesizes the given text into an audio clip and returns TTSAudioResult.
        """
        pass

    @abstractmethod
    async def get_available_voices(self) -> List[TTSVoiceOption]:
        """
        Returns the list of voices supported by this provider for Indonesian shorts.
        """
        pass
