# Milestone 11 — End-to-End Testing & Production Hardening

## Overview

Milestone 11 validates the complete, integrated production pipeline of **Shorts Automation Studio** from Reference Video ingestion through final 1080×1920 vertical Shorts video rendering. Rather than introducing new production features, M11 rigorously verifies that Milestones 1 through 10 operate together as a cohesive, resilient, and resource-safe system.

---

## 1. Pipeline Architecture & Timing Source of Truth

The end-to-end flow connects all previous milestones:

```text
Reference Video (M1, M2)
       ↓
Reference Video Analysis (M3: Transcript + Scenes + Keyframes + Visual Descriptions)
       ↓
Indonesian Script Adaptation (M4: Scene-aligned segments, WPM/duration target)
       ↓
TTS Audio Generation (M5: Master narration audio + AudioSegment timestamps)
       ↓  ◄─────── [PRIMARY TIMING ANCHOR: AudioSegments from M5]
Visual Footage Search & Selection (M6: Visual query generation + Multimodal similarity)
       ↓
Production Timeline (M7: Unified shot plan, exact duration, trim offsets, transition)
       ↓
       ├── Captions & Subtitle Track (M8: ASS burn-in, readability bounded by AudioSegments)
       └── BGM & SFX Timeline (M9: Audio layers, volume offset, fade, ducking)
                   ↓
             FFmpeg Renderer (M10: Smart crop/scale 9:16, concat, libass burn-in, audio mix)
                   ↓
             Final Vertical 1080×1920 Shorts Video (.mp4)
```

### Critical Architectural Principle: M5 Primary Timing Anchor
* **Master Clock**: The narration audio segments generated in **Milestone 5 (`AudioSegment`)** remain the immutable timing reference for the video timeline.
* **Production Timeline (M7)** directly consumes `AudioSegment.duration`, `AudioSegment.start_time`, and `AudioSegment.end_time`.
* **Captions (M8)** segments are strictly bounded within their parent `AudioSegment` duration to guarantee subtitle synchronicity with speech.
* **BGM & SFX Layers (M9)** cannot exceed the production timeline duration; ducking attenuates BGM automatically during active narration windows.

---

## 2. Hardening & Safety Controls

### 2.1 Stale Dependency Rejection
Rendering is blocked with explicit, actionable error messages whenever an upstream artifact is modified after downstream planning:
1. **Script Drift**: If `active_script.updated_at > production_timeline.created_at`, render is rejected (`"Active Indonesian script (vX) was updated after the production timeline (vY) was created. Please regenerate the production timeline."`).
2. **TTS Drift**: If `active_tts.updated_at > production_timeline.created_at`, render is rejected (`"Active TTS narration (vX) was updated after the production timeline (vY) was created. Please regenerate the production timeline."`).
3. **Duration Drift**: If `abs(tts_generation.duration - production_timeline.duration) > 0.5s`, render is rejected (`"Timeline duration (X.Xs) does not match TTS narration duration (Y.Ys)."`).
4. **Missing Footage**: If any scene on the timeline lacks an approved footage candidate, render is blocked (`"Scene X has no selected footage candidate."`).
5. **Caption Track Drift**: If `caption_track.updated_at < tts_generation.updated_at`, render issues a warning or blocks rendering if total duration drifts by >0.5s.
6. **Audio Timeline Drift**: If `audio_timeline.updated_at < production_timeline.updated_at` or audio layers extend beyond timeline duration.

### 2.2 Concurrency Safeguards
* Each project permits strictly **one active render job** at a time (`PENDING`, `VALIDATING`, `PREPARING`, `RENDERING`).
* Attempting to initiate a duplicate render job while another is active raises an explicit error:
  `"A render job (<job_id>) is already in progress for this project. Please wait for it to complete or cancel it."`

### 2.3 Process Cancellation & Resource Safety
* `FFmpegVideoRenderer` maintains an internal dictionary `_active_processes` tracking active OS-level subprocesses.
* Cancellation triggers graceful `proc.terminate()` followed by `proc.kill()` if unresponsive, tracking `_cancelled_jobs` so exit codes caused by cancellation cleanly return `"Render job was cancelled by user."`.
* Temporary `.ass` subtitle files and intermediate mock artifacts are safely pruned on job cancellation and job failure. Finalized video exports (`output_path`) are never inadvertently unlinked.

### 2.4 Filter Graph Escaping
* `escape_ffmpeg_filter_path`: Normalizes backslashes to forward slashes, escapes drive colons (`C\:`), special characters, and square brackets (`\[` and `\]`) to prevent FFmpeg filter graph parser injection on Windows and POSIX systems.

---

## 3. Test Suites & Verification

### 3.1 End-to-End Integration Suite (`apps/api/tests/test_end_to_end.py`)
Validates the complete chain with 9 exhaustive automated tests:
* `test_complete_pipeline_dependency_chain_and_rendering`: Seeds M1–M9 artifacts, verifies preflight checklist passing, initiates render job, and validates completion.
* `test_audio_segment_timestamps_anchor_timeline`: Asserts timeline items perfectly mirror M5 `AudioSegment` timestamps.
* `test_captions_bounded_by_audio_segments`: Confirms caption segments do not overflow their associated audio segment boundaries.
* `test_bgm_and_sfx_do_not_exceed_or_drift_timeline`: Verifies audio mix timeline conforms to total project duration.
* `test_stale_script_blocks_render`: Verifies that modifying an active script without rebuilding the timeline triggers stale dependency rejection.
* `test_stale_tts_blocks_render`: Verifies that regenerating TTS narration blocks rendering until the timeline is updated.
* `test_duration_drift_blocks_render`: Verifies that artificially induced drift >0.5s is caught by preflight validation.
* `test_missing_footage_blocks_render`: Verifies that unassigned footage triggers an error identifying the exact scene sequence.
* `test_concurrency_safeguard_disallows_duplicate_active_renders`: Verifies that simultaneous render attempts are blocked.

### 3.2 Real Native FFmpeg Smoke Test (`apps/api/tests/test_render_smoke.py`)
Executes real FFmpeg and FFprobe binaries to synthesize actual 1080×1920 MP4 files:
* `test_real_ffmpeg_smoke_render_with_subtitles_and_audio`:
  - Input: Two 1.5s test video clips, a 3.0s 44100Hz sine wave audio stream, and a generated `.ass` subtitle file.
  - Verification with `ffprobe -show_format -show_streams`:
    - Container format: `mp4` / `mov`
    - Video dimensions: exactly 1080 (width) × 1920 (height)
    - Video codec: `h264` (libx264)
    - Audio codec: `aac`
    - Duration: 3.0s (±0.5s tolerance)
    - File size: >5KB valid playable MP4
* `test_real_ffmpeg_smoke_render_without_subtitles`:
  - Validates composition pipeline when subtitles are omitted.
* `test_process_cancellation`:
  - Initiates a long render, terminates it via `renderer.cancel_job()`, and confirms subprocess termination with `"Render job was cancelled by user."`.

### 3.3 Full Regression Results
All 97 tests pass with zero errors and zero failures:
```text
apps/api/tests/test_analysis.py ....                                     [  4%]
apps/api/tests/test_audio_timeline.py ..............                     [ 18%]
apps/api/tests/test_captions.py ............                             [ 30%]
apps/api/tests/test_end_to_end.py .........                              [ 40%]
apps/api/tests/test_footage.py .............                             [ 53%]
apps/api/tests/test_projects.py ....                                     [ 57%]
apps/api/tests/test_render_smoke.py ...                                  [ 60%]
apps/api/tests/test_renderer.py ........                                 [ 69%]
apps/api/tests/test_scripts.py .........                                 [ 78%]
apps/api/tests/test_timeline.py ...........                              [ 89%]
apps/api/tests/test_tts.py ..........                                    [100%]

============================= 97 passed in 49.19s =============================
```

### 3.4 Frontend Verification
* `npx tsc --noEmit`: 0 errors
* `npm run build`: Optimized production Next.js build compiled successfully across all routes (`/projects/[id]`, `/audio`, `/captions`, `/footage`, `/render`, `/script`, `/timeline`, `/tts`).

---

## 4. Operational Runbook

### Running All Tests
```bash
# Backend pytest suite (all 97 tests)
python -m pytest apps/api/tests

# End-to-end integration tests only
python -m unittest apps/api/tests/test_end_to_end.py

# Real FFmpeg smoke render tests only
python -m unittest apps/api/tests/test_render_smoke.py

# Frontend build check
cd apps/web && npm run build
```
