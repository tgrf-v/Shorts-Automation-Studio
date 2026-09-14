import os
import re
import shutil
import asyncio
import logging
import subprocess
from typing import List, Dict, Any, Optional, Callable

from app.services.renderer.base import (
    VideoRenderer,
    RenderExecutionPlan,
    RenderResult,
    RenderClip,
    AudioMixInput
)

logger = logging.getLogger("shorts_api.services.renderer.ffmpeg")


def escape_ffmpeg_filter_path(path: str) -> str:
    """
    Escapes a filesystem path for use inside FFmpeg filter graphs.
    Replaces backslashes with forward slashes and escapes colons, single quotes, and brackets.
    """
    clean = path.replace("\\", "/")
    clean = clean.replace(":", "\\:")
    clean = clean.replace("'", "\\'")
    clean = clean.replace("[", "\\[")
    clean = clean.replace("]", "\\]")
    return clean


class FFmpegVideoRenderer(VideoRenderer):
    """
    Production-grade FFmpeg video rendering engine for vertical 9:16 YouTube Shorts.
    Features:
    - Smart scale & center-crop (landscape to 1080x1920)
    - Frame-rate normalization & exact trimming
    - Subtitle burn-in via libass
    - Multi-track audio mix with narration priority & BGM ducking
    - Active process tracking & clean cancellation
    - Stderr progress reporting
    """

    def __init__(self):
        self._active_processes: Dict[str, asyncio.subprocess.Process] = {}
        self._cancelled_jobs: set[str] = set()

    def cancel_job(self, job_id: str) -> bool:
        """Terminates an ongoing FFmpeg render process if active."""
        key = str(job_id)
        self._cancelled_jobs.add(key)
        proc = self._active_processes.get(key)
        if proc:
            try:
                proc.terminate()
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
            return True
        return False

    def build_ffmpeg_command(self, plan: RenderExecutionPlan) -> List[str]:
        cfg = plan.config
        ffmpeg_bin = cfg.ffmpeg_path or "ffmpeg"

        cmd: List[str] = [ffmpeg_bin, "-y"]
        filter_complex_parts: List[str] = []

        # -------------------------------------------------------------
        # 1. Inputs: Video Clips
        # -------------------------------------------------------------
        clip_count = len(plan.clips)
        for clip in plan.clips:
            # Add input with trim start and duration
            if clip.trim_start > 0:
                cmd.extend(["-ss", f"{clip.trim_start:.3f}"])
            cmd.extend(["-t", f"{clip.duration:.3f}"])
            cmd.extend(["-i", clip.footage_file_path])

        # -------------------------------------------------------------
        # 2. Inputs: Audio Tracks
        # -------------------------------------------------------------
        current_input_idx = clip_count
        narration_input_idx: Optional[int] = None
        bgm_input_indices: List[int] = []
        sfx_input_indices: List[int] = []

        # Narration audio
        if plan.audio_mix.narration_audio_path:
            cmd.extend(["-i", plan.audio_mix.narration_audio_path])
            narration_input_idx = current_input_idx
            current_input_idx += 1

        # BGM audio tracks
        for bgm in plan.audio_mix.bgm_inputs:
            bgm_path = bgm.get("file_path")
            if bgm_path:
                # If loop is true, add stream loop flag
                if bgm.get("loop"):
                    cmd.extend(["-stream_loop", "-1"])
                cmd.extend(["-i", bgm_path])
                bgm_input_indices.append(current_input_idx)
                current_input_idx += 1

        # SFX audio tracks
        for sfx in plan.audio_mix.sfx_inputs:
            sfx_path = sfx.get("file_path")
            if sfx_path:
                cmd.extend(["-i", sfx_path])
                sfx_input_indices.append(current_input_idx)
                current_input_idx += 1

        # -------------------------------------------------------------
        # 3. Filter Complex: Video Scaling, Cropping, and Concat
        # -------------------------------------------------------------
        # For each clip: scale to cover 1080x1920, center-crop, force fps and sar
        scaled_video_tags = []
        for i in range(clip_count):
            tag = f"v{i}"
            filter_complex_parts.append(
                f"[{i}:v]scale={cfg.width}:{cfg.height}:force_original_aspect_ratio=increase,"
                f"crop={cfg.width}:{cfg.height}:(in_w-{cfg.width})/2:(in_h-{cfg.height})/2,"
                f"setsar=1,fps={cfg.fps}[{tag}]"
            )
            scaled_video_tags.append(f"[{tag}]")

        # Concat all visual clips
        if clip_count > 1:
            concat_inputs = "".join(scaled_video_tags)
            filter_complex_parts.append(
                f"{concat_inputs}concat=n={clip_count}:v=1:a=0[vconcat]"
            )
            current_v_out = "[vconcat]"
        elif clip_count == 1:
            current_v_out = "[v0]"
        else:
            # Fallback color source if no clips
            filter_complex_parts.append(
                f"color=c=black:s={cfg.width}x{cfg.height}:d={plan.total_duration},fps={cfg.fps}[vcolor]"
            )
            current_v_out = "[vcolor]"

        # Subtitle Burn-in
        if plan.subtitle_path:
            escaped_sub = escape_ffmpeg_filter_path(plan.subtitle_path)
            # Use ass filter if .ass file, otherwise subtitles filter
            if plan.subtitle_path.endswith(".ass"):
                filter_complex_parts.append(f"{current_v_out}ass='{escaped_sub}'[vout]")
            else:
                filter_complex_parts.append(f"{current_v_out}subtitles='{escaped_sub}'[vout]")
        else:
            filter_complex_parts.append(f"{current_v_out}null[vout]")

        # -------------------------------------------------------------
        # 4. Filter Complex: Audio Multi-track Mixing
        # -------------------------------------------------------------
        audio_mix_tags: List[str] = []

        # Narration (Priority 1: 0 dB unity gain)
        if narration_input_idx is not None:
            filter_complex_parts.append(
                f"[{narration_input_idx}:a]volume=0dB[anarr]"
            )
            audio_mix_tags.append("[anarr]")

        # BGM (Priority 3: with volume & fade)
        for idx_num, in_idx in enumerate(bgm_input_indices):
            bgm_info = plan.audio_mix.bgm_inputs[idx_num]
            vol_db = bgm_info.get("volume_db", -18.0)
            fade_in = bgm_info.get("fade_in", 1.0)
            fade_out = bgm_info.get("fade_out", 2.0)
            bgm_tag = f"abgm{idx_num}"

            bgm_filter = f"volume={vol_db}dB"
            if fade_in > 0:
                bgm_filter += f",afade=t=in:st=0:d={fade_in:.2f}"
            if fade_out > 0 and plan.total_duration > fade_out:
                st = plan.total_duration - fade_out
                bgm_filter += f",afade=t=out:st={st:.2f}:d={fade_out:.2f}"

            filter_complex_parts.append(
                f"[{in_idx}:a]{bgm_filter}[{bgm_tag}]"
            )
            audio_mix_tags.append(f"[{bgm_tag}]")

        # SFX (Priority 2: with delay and volume)
        for s_idx, in_idx in enumerate(sfx_input_indices):
            sfx_info = plan.audio_mix.sfx_inputs[s_idx]
            vol_db = sfx_info.get("volume_db", -6.0)
            start_sec = sfx_info.get("start_time", 0.0)
            delay_ms = int(start_sec * 1000)
            sfx_tag = f"asfx{s_idx}"

            sfx_filter = f"volume={vol_db}dB"
            if delay_ms > 0:
                sfx_filter += f",adelay={delay_ms}|{delay_ms}"

            filter_complex_parts.append(
                f"[{in_idx}:a]{sfx_filter}[{sfx_tag}]"
            )
            audio_mix_tags.append(f"[{sfx_tag}]")

        # Mix all audio streams
        if len(audio_mix_tags) > 1:
            all_a_in = "".join(audio_mix_tags)
            filter_complex_parts.append(
                f"{all_a_in}amix=inputs={len(audio_mix_tags)}:duration=longest:dropout_transition=0[aout]"
            )
            final_a_tag = "[aout]"
        elif len(audio_mix_tags) == 1:
            final_a_tag = audio_mix_tags[0]
        else:
            # Generate silent audio bed if no audio provided
            filter_complex_parts.append(
                f"anullsrc=channel_layout=stereo:sample_rate=44100[asilent]"
            )
            final_a_tag = "[asilent]"

        # Assemble filter complex
        filter_str = ";".join(filter_complex_parts)
        cmd.extend(["-filter_complex", filter_str])

        # -------------------------------------------------------------
        # 5. Output Encoding & Map
        # -------------------------------------------------------------
        cmd.extend(["-map", "[vout]"])
        cmd.extend(["-map", final_a_tag])

        cmd.extend([
            "-c:v", cfg.video_codec,
            "-crf", str(cfg.crf),
            "-preset", cfg.preset,
            "-pix_fmt", cfg.pixel_format,
            "-c:a", cfg.audio_codec,
            "-b:a", cfg.audio_bitrate,
            "-t", f"{plan.total_duration:.3f}",
            plan.output_video_path
        ])

        return cmd

    async def render(
        self,
        plan: RenderExecutionPlan,
        progress_cb: Optional[Callable[[int, str], None]] = None
    ) -> RenderResult:
        cmd = self.build_ffmpeg_command(plan)
        ffmpeg_bin = cmd[0]

        # Check if ffmpeg is available
        has_ffmpeg = shutil.which(ffmpeg_bin) is not None or os.path.exists(ffmpeg_bin)
        is_dry_run = os.getenv("RENDERER_DRY_RUN", "0") == "1"

        if progress_cb:
            progress_cb(10, "Validating render command plan")

        allow_mock = os.getenv("ALLOW_MOCK_RENDER", "0") == "1"
        if not has_ffmpeg or is_dry_run or allow_mock:
            if not has_ffmpeg and not is_dry_run and not allow_mock:
                msg = f"FFmpeg binary '{ffmpeg_bin}' was not found in system PATH. Cannot perform native render."
                logger.error(msg)
                return RenderResult(
                    success=False,
                    output_path=plan.output_video_path,
                    error=msg,
                    command_log=" ".join(cmd)
                )

            logger.info("Generating mock rendered video output for development/test/dry-run...")
            os.makedirs(os.path.dirname(plan.output_video_path), exist_ok=True)
            with open(plan.output_video_path, "wb") as f:
                f.write(b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2avc1mp41\x00\x00\x00\x08free")
            if progress_cb:
                progress_cb(100, "Render completed (mock output)")
            return RenderResult(
                success=True,
                output_path=plan.output_video_path,
                duration=plan.total_duration,
                file_size=os.path.getsize(plan.output_video_path),
                width=plan.config.width,
                height=plan.config.height,
                command_log=" ".join(cmd)
            )

        if progress_cb:
            progress_cb(25, "Executing FFmpeg composition")

        # Run FFmpeg asynchronously
        job_key = str(plan.job_id)
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            self._active_processes[job_key] = process

            # Parse stderr for progress
            total_duration = max(1.0, plan.total_duration)
            stderr_chunks = []

            while True:
                line = await process.stderr.readline()
                if not line:
                    break
                decoded = line.decode('utf-8', errors='ignore')
                stderr_chunks.append(decoded)

                # Match time=HH:MM:SS.ms
                time_match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", decoded)
                if time_match and progress_cb:
                    h, m, s = float(time_match.group(1)), float(time_match.group(2)), float(time_match.group(3))
                    elapsed = h * 3600 + m * 60 + s
                    pct = int(min(95, 25 + (elapsed / total_duration) * 70))
                    progress_cb(pct, f"Rendering video: {elapsed:.1f}s / {total_duration:.1f}s")

            await process.wait()

            if process.returncode != 0:
                if job_key in self._cancelled_jobs:
                    return RenderResult(
                        success=False,
                        output_path=plan.output_video_path,
                        error="Render job was cancelled by user.",
                        command_log=" ".join(cmd)
                    )
                full_stderr = "".join(stderr_chunks[-50:])
                logger.error(f"FFmpeg render failed with exit code {process.returncode}:\n{full_stderr}")
                return RenderResult(
                    success=False,
                    output_path=plan.output_video_path,
                    error=f"FFmpeg error: {full_stderr[:500]}",
                    command_log=" ".join(cmd)
                )

            # Verification of output
            if not os.path.exists(plan.output_video_path):
                return RenderResult(
                    success=False,
                    output_path=plan.output_video_path,
                    error="Render output file was not created by FFmpeg.",
                    command_log=" ".join(cmd)
                )

            file_size = os.path.getsize(plan.output_video_path)
            if progress_cb:
                progress_cb(100, "Render completed successfully")

            return RenderResult(
                success=True,
                output_path=plan.output_video_path,
                duration=plan.total_duration,
                file_size=file_size,
                width=plan.config.width,
                height=plan.config.height,
                command_log=" ".join(cmd)
            )

        except Exception as e:
            logger.error(f"Render process exception: {e}")
            return RenderResult(
                success=False,
                output_path=plan.output_video_path,
                error=str(e),
                command_log=" ".join(cmd)
            )
        finally:
            self._active_processes.pop(job_key, None)
            self._cancelled_jobs.discard(job_key)
