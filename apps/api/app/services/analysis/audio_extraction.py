import os
import asyncio
import logging
import tempfile
import subprocess
from typing import Optional

logger = logging.getLogger("shorts_api.services.audio_extraction")


class AudioExtractionService:
    """Service to safely extract 16kHz mono PCM WAV audio for transcription."""

    @staticmethod
    async def extract_audio(video_path: str) -> str:
        """
        Extracts audio from video_path to a temporary 16kHz mono WAV file.
        Caller is responsible for unlinking the temporary file when finished.
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found at: {video_path}")

        temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_wav_path = temp_wav.name
        temp_wav.close()

        loop = asyncio.get_running_loop()

        def _run_ffmpeg():
            cmd = [
                "ffmpeg",
                "-y",
                "-i", video_path,
                "-vn",
                "-acodec", "pcm_s16le",
                "-ar", "16000",
                "-ac", "1",
                temp_wav_path
            ]
            try:
                res = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True,
                    timeout=120
                )
                logger.info(f"Audio extracted successfully to: {temp_wav_path}")
                return temp_wav_path
            except subprocess.SubprocessError as exc:
                if os.path.exists(temp_wav_path):
                    os.unlink(temp_wav_path)
                logger.error(f"FFmpeg audio extraction failed: {exc}")
                raise RuntimeError(f"Audio extraction failed: {exc}") from exc

        return await loop.run_in_executor(None, _run_ffmpeg)

    @staticmethod
    def cleanup_file(file_path: Optional[str]) -> None:
        """Safely removes temporary audio file."""
        if file_path and os.path.exists(file_path):
            try:
                os.unlink(file_path)
                logger.info(f"Cleaned up temporary audio file: {file_path}")
            except Exception as exc:
                logger.warning(f"Failed to clean up temporary audio file {file_path}: {exc}")


audio_extraction_service = AudioExtractionService()
