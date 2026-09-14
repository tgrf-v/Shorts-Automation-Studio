import os
import json
import wave
import shutil
import asyncio
import logging
import tempfile
import subprocess
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

logger = logging.getLogger("shorts_api.services.audio_processor")


class AudioTechnicalInfo(BaseModel):
    duration: float = Field(default=0.0, description="Exact audio duration in seconds")
    sample_rate: int = Field(default=44100, description="Sample rate in Hz")
    channels: int = Field(default=1, description="Audio channels (1=mono, 2=stereo)")
    codec: Optional[str] = Field(default="mp3", description="Audio codec name")
    format_name: Optional[str] = Field(default="mp3", description="Audio container format")
    size_bytes: int = Field(default=0, description="File size in bytes")


class AudioProcessorService:
    """
    Audio processing service using FFmpeg and FFprobe with standard library fallbacks
    for duration measurement, format standardization, and segment concatenation.
    """

    @staticmethod
    def _inspect_via_wave_fallback(file_path: str) -> Optional[AudioTechnicalInfo]:
        """Inspects WAV audio using Python standard library wave module."""
        try:
            with wave.open(file_path, 'rb') as wf:
                channels = wf.getnchannels()
                sample_rate = wf.getframerate()
                n_frames = wf.getnframes()
                duration = round(n_frames / float(sample_rate), 3) if sample_rate > 0 else 0.0
                file_size = os.path.getsize(file_path)
                return AudioTechnicalInfo(
                    duration=duration,
                    sample_rate=sample_rate,
                    channels=channels,
                    codec="pcm_s16le",
                    format_name="wav",
                    size_bytes=file_size
                )
        except Exception:
            return None

    @classmethod
    async def inspect_audio(cls, file_path: str) -> AudioTechnicalInfo:
        """
        Inspects technical audio metadata (duration, sample rate, channels, codec).
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file does not exist: {file_path}")

        file_size = os.path.getsize(file_path)
        loop = asyncio.get_running_loop()

        def _run_ffprobe() -> AudioTechnicalInfo:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                file_path
            ]
            try:
                res = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True,
                    timeout=15
                )
                data = json.loads(res.stdout)
                streams = data.get("streams", [])
                format_info = data.get("format", {})

                audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

                duration = 0.0
                if "duration" in format_info:
                    try:
                        duration = round(float(format_info["duration"]), 3)
                    except (ValueError, TypeError):
                        duration = 0.0

                sample_rate = 44100
                channels = 1
                codec = "mp3"
                if audio_stream:
                    if not duration and "duration" in audio_stream:
                        try:
                            duration = round(float(audio_stream["duration"]), 3)
                        except (ValueError, TypeError):
                            pass
                    try:
                        sample_rate = int(audio_stream.get("sample_rate", 44100))
                    except (ValueError, TypeError):
                        sample_rate = 44100
                    try:
                        channels = int(audio_stream.get("channels", 1))
                    except (ValueError, TypeError):
                        channels = 1
                    codec = audio_stream.get("codec_name", "mp3")

                return AudioTechnicalInfo(
                    duration=duration,
                    sample_rate=sample_rate,
                    channels=channels,
                    codec=codec,
                    format_name=format_info.get("format_name", "mp3"),
                    size_bytes=file_size
                )
            except Exception as exc:
                logger.warning(f"FFprobe failed on {file_path} ({exc}), checking fallback...")
                # Try wave fallback if WAV
                wave_info = cls._inspect_via_wave_fallback(file_path)
                if wave_info:
                    return wave_info

                # Fallback: estimate from file size assuming standard MP3 128kbps (16000 bytes/sec)
                est_sec = round(file_size / 16000.0, 2)
                return AudioTechnicalInfo(
                    duration=max(est_sec, 1.0),
                    sample_rate=44100,
                    channels=1,
                    codec="unknown",
                    format_name=os.path.splitext(file_path)[1].lstrip("."),
                    size_bytes=file_size
                )

        return await loop.run_in_executor(None, _run_ffprobe)

    @classmethod
    async def concatenate_segments(
        cls,
        segment_paths: List[str],
        output_path: str,
        output_format: str = "mp3"
    ) -> AudioTechnicalInfo:
        """
        Concatenates multiple audio segment files into a single master narration audio file.
        Standardizes to 44.1kHz mono output.
        """
        if not segment_paths:
            raise ValueError("Cannot concatenate empty list of audio segments.")

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        loop = asyncio.get_running_loop()

        # Single segment fast-path
        if len(segment_paths) == 1:
            def _single_copy():
                shutil.copyfile(segment_paths[0], output_path)
            await loop.run_in_executor(None, _single_copy)
            return await cls.inspect_audio(output_path)

        # Multiple segments: Concat Demuxer
        def _run_concat():
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f_list:
                concat_list_file = f_list.name
                for p in segment_paths:
                    # FFmpeg concat demuxer requires forward slashes on Windows
                    clean_p = os.path.abspath(p).replace("\\", "/")
                    f_list.write(f"file '{clean_p}'\n")

            try:
                # Concat and re-encode to clean mono 44.1kHz
                codec_args = ["-c:a", "libmp3lame", "-q:a", "2"] if output_format == "mp3" else ["-c:a", "pcm_s16le"]
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", concat_list_file,
                    *codec_args,
                    "-ar", "44100",
                    "-ac", "1",
                    output_path
                ]
                subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True,
                    timeout=120
                )
                logger.info(f"FFmpeg successfully concatenated {len(segment_paths)} segments to {output_path}")
            except Exception as ffmpeg_exc:
                logger.warning(f"FFmpeg concat failed ({ffmpeg_exc}), attempting python wave concat fallback...")
                # Fallback: if segments are WAV, concatenate with wave module
                try:
                    cls._concatenate_wav_fallback(segment_paths, output_path)
                except Exception as fb_exc:
                    raise RuntimeError(f"Audio concatenation failed: {ffmpeg_exc}; Fallback failed: {fb_exc}") from ffmpeg_exc
            finally:
                if os.path.exists(concat_list_file):
                    try:
                        os.unlink(concat_list_file)
                    except Exception:
                        pass

        await loop.run_in_executor(None, _run_concat)
        return await cls.inspect_audio(output_path)

    @staticmethod
    def _concatenate_wav_fallback(segment_paths: List[str], output_path: str) -> None:
        """Pure Python fallback for concatenating WAV audio files."""
        frames = []
        sample_rate = 44100
        channels = 1
        sampwidth = 2

        for p in segment_paths:
            with wave.open(p, 'rb') as w_in:
                sample_rate = w_in.getframerate()
                channels = w_in.getnchannels()
                sampwidth = w_in.getsampwidth()
                frames.append(w_in.readframes(w_in.getnframes()))

        with wave.open(output_path, 'wb') as w_out:
            w_out.setnchannels(channels)
            w_out.setsampwidth(sampwidth)
            w_out.setframerate(sample_rate)
            for f in frames:
                w_out.writeframes(f)


audio_processor = AudioProcessorService()
