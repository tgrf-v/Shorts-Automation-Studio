# Product Requirements Document (PRD)

## Shorts Automation Studio

**Status:** Draft v1.0
**Jenis produk:** Web application untuk otomatisasi produksi YouTube Shorts
**Target pengguna awal:** Creator individu / small creator team
**Platform utama:** Web desktop
**Arsitektur:** Next.js + FastAPI + Python workers + FFmpeg
**Prinsip utama:** automate repetitive work, retain human control over creative decisions

---

# 1. Ringkasan Produk

Shorts Automation Studio adalah aplikasi web untuk mengotomatisasi proses produksi YouTube Shorts berbasis **video referensi yang telah terbukti menarik/viral**.

Workflow utama pengguna:

> menemukan Shorts referensi berbahasa Inggris → memasukkan video ke aplikasi → sistem menganalisis struktur video → membuat/adaptasi narasi Bahasa Indonesia → menghasilkan TTS → mendeteksi scene dan kebutuhan footage → mencari footage yang sama/mirip → pengguna memilih footage → sistem menyusun video → menghasilkan caption, BGM, dan SFX → pengguna melakukan review → export final Shorts.

Produk ini **bukan video generator generik** dan bukan pengganti CapCut secara penuh.

Fokus produk adalah menghilangkan pekerjaan yang berulang dari workflow creator:

* transkripsi
* adaptasi script
* pembuatan voice-over
* scene segmentation
* pencarian footage
* penyusunan timeline
* caption
* audio mixing
* rendering

Creative decision yang penting tetap berada di tangan pengguna.

---

# 2. Problem Statement

Workflow produksi saat ini membutuhkan banyak aktivitas manual berulang:

1. Menemukan video referensi.
2. Menonton dan memahami struktur video.
3. Mencari ulang footage yang sama atau mirip.
4. Menerjemahkan/adaptasi narasi.
5. Generate TTS.
6. Menyesuaikan footage dengan durasi narasi.
7. Membuat caption.
8. Menambahkan BGM/SFX.
9. Menyusun semuanya dalam editor.
10. Export.

Masalah utama bukan ketidakmampuan teknis pengguna, melainkan **waktu dan repetisi**.

Creator dapat memahami dan melakukan seluruh proses tersebut, tetapi proses manual tersebut menghabiskan banyak waktu, terutama ketika produksi dilakukan berulang kali.

Produk harus mengubah workflow tersebut menjadi:

> **Reference → Analyze → Adapt → Find → Select → Compose → Review → Export**

---

# 3. Product Vision

Membangun tool yang memungkinkan creator mengubah sebuah Shorts referensi menjadi **draft Shorts versi sendiri** dengan intervensi manual seminimal mungkin.

Target ideal jangka panjang:

> User memasukkan satu video referensi, sistem memahami struktur visual dan narasinya, menemukan footage yang paling relevan, membuat versi Bahasa Indonesia, kemudian menghasilkan draft Shorts yang siap direview.

---

# 4. Product Philosophy

## 4.1 Reference-first

Video referensi adalah sumber utama struktur konten.

Sistem tidak dimulai dari:

> "Buat video tentang topik X."

Sistem dimulai dari:

> "Analisis video ini dan bantu saya membuat versi baru dengan struktur yang serupa."

## 4.2 Similarity-first

Dalam pencarian footage, prioritas utama adalah:

**kemiripan visual**, bukan hanya kemiripan teks.

Target:

1. exact/same footage
2. footage dari event/source yang sama
3. footage sangat mirip
4. footage relevan secara konteks
5. fallback berdasarkan semantic text search

## 4.3 Human-in-the-loop

Sistem tidak dipaksa mengambil keputusan yang tidak pasti.

Contoh:

> Exact footage tidak ditemukan.

Sistem harus memberikan beberapa kandidat dan membiarkan pengguna memilih.

## 4.4 Automation over complexity

Jangan membangun video editor generik seperti CapCut.

Bangun editor yang:

* opinionated
* sederhana
* khusus Shorts
* cepat
* mengutamakan otomatisasi

---

# 5. Target User

## Primary User

Creator YouTube Shorts yang:

* membuat konten berbasis narration/voice-over
* menggunakan footage dari berbagai sumber
* sering menggunakan video viral sebagai reference
* membutuhkan Bahasa Indonesia
* melakukan editing berulang
* ingin mempercepat produksi

## Secondary User

Small team:

* researcher
* script writer
* editor
* content manager

---

# 6. User Goals

User harus dapat:

1. Memasukkan video referensi.
2. Melihat transcript.
3. Mendapatkan script Bahasa Indonesia.
4. Mengedit script.
5. Menghasilkan voice-over.
6. Melihat scene dan keyframe.
7. Mencari footage yang sama/mirip.
8. Memilih footage.
9. Mengatur urutan footage.
10. Menghasilkan caption.
11. Menambahkan BGM/SFX.
12. Generate preview.
13. Export MP4.

---

# 7. Non-Goals

Produk tidak bertujuan menjadi:

* full-featured video editor
* animation software
* professional NLE
* AI text-to-video generator
* automatic YouTube uploader pada MVP
* universal downloader semua platform
* sistem yang menjamin copyright clearance
* sistem yang menjamin sebuah video akan viral

Sistem juga tidak boleh menjanjikan:

> "Video ini pasti viral."

Sistem hanya mengoptimalkan proses produksi berdasarkan reference yang dipilih pengguna.

---

# 8. Product Roadmap

## V1 — Automated Shorts Editor

Fokus pada otomatisasi editing.

### Fitur

* project management
* upload reference
* transcript
* scene detection
* script adaptation
* TTS
* caption
* manual footage assignment
* timeline composition
* BGM/SFX
* preview
* rendering
* export

---

## V2 — Visual Footage Finder

Menambahkan:

* keyframe extraction
* visual similarity search
* image search
* source discovery
* candidate ranking
* source URL
* exact-match detection
* similar-footage detection

---

## V3 — Reference Recreation Engine

Integrasi penuh:

```text
Reference
    ↓
Analysis
    ↓
Script
    ↓
Voice
    ↓
Visual Search
    ↓
Footage Selection
    ↓
Timeline Reconstruction
    ↓
Audio
    ↓
Caption
    ↓
Render
```

Sistem dapat menghasilkan draft hampir otomatis.

---

# 9. User Journey

## Step 1 — Create Project

User klik:

**New Project**

Masukkan:

* project name
* reference video

---

## Step 2 — Analyze

Sistem:

* membaca metadata
* mengekstrak audio
* melakukan transcription
* mendeteksi scene
* menentukan keyframe
* mengidentifikasi visual content
* menganalisis pacing

Status:

```text
Uploading
Analyzing
Transcribing
Detecting scenes
Analyzing visuals
Completed
```

---

## Step 3 — Script

Sistem menampilkan:

### Original script

Bahasa asli video.

### Indonesian script

Versi Bahasa Indonesia.

User dapat mengedit.

Kontrol:

* regenerate
* shorten
* rewrite
* preserve meaning
* preserve tone
* preserve pacing

---

# 10. Script Adaptation Requirements

Adaptasi bukan terjemahan literal.

Sistem harus:

* mempertahankan informasi utama
* mempertahankan hook
* mempertahankan urutan informasi
* mempertahankan pacing
* menghasilkan Bahasa Indonesia natural
* menyesuaikan panjang script dengan durasi target voice-over

Contoh:

```text
Original:
Scientists recently discovered...

Adapted:
Para ilmuwan baru-baru ini menemukan...
```

Namun sistem harus lebih memprioritaskan:

**meaning + pacing**

daripada:

**literal translation**

---

# 11. Voice Generation

Provider abstraction harus digunakan.

Interface:

```text
TTSProvider
├── ElevenLabsProvider
└── GoogleTTSProvider
```

Jangan mengikat business logic langsung ke satu provider.

Configuration:

* provider
* voice
* language
* speed
* stability
* style jika tersedia

Output:

```text
voice.wav
```

Sistem menyimpan:

* provider
* voice ID
* generation timestamp
* script version
* audio duration

---

# 12. Scene Detection

Reference video dibagi menjadi scene.

Contoh:

```text
Scene 1
00:00–00:03

Scene 2
00:03–00:07

Scene 3
00:07–00:12
```

Setiap scene memiliki:

```text
scene_id
start_time
end_time
duration
thumbnail
keyframes
visual_description
transcript_segment
```

---

# 13. Keyframe Extraction

Setiap scene menghasilkan beberapa kandidat frame.

Contoh:

```text
Scene 3

Frame A
Frame B
Frame C
Frame D
```

Sistem memilih frame terbaik berdasarkan:

* sharpness
* object visibility
* uniqueness
* visual information
* low transition likelihood

Frame yang blur atau terlalu banyak overlay harus diberi skor lebih rendah.

---

# 14. Visual Footage Search

## Tujuan

Menemukan video yang:

1. sama dengan reference
2. berasal dari source/event yang sama
3. sangat mirip
4. relevan secara visual

---

# 15. Visual Search Architecture

Search dilakukan secara bertingkat.

```text
Reference Scene
      ↓
Keyframes
      ↓
Visual Embedding
      ↓
Candidate Search
      ↓
Similarity Ranking
```

Search adapter harus modular.

Contoh:

```text
SearchProvider
├── WebImageSearch
├── WebVideoSearch
├── YouTubeSearch
├── TikTokSearch
├── InstagramSearch
├── DouyinSearch
└── Future providers
```

Provider yang tidak memiliki API resmi atau akses stabil tidak boleh menjadi dependency wajib sistem.

---

# 16. Footage Search Strategy

Sistem melakukan beberapa tipe pencarian.

## Level 1 — Exact Visual Match

Target:

> footage yang kemungkinan merupakan video yang sama.

Teknik:

* multiple keyframes
* perceptual hashing
* image embeddings
* sequence similarity
* OCR jika text pada frame membantu
* visual feature comparison

---

## Level 2 — Same Event / Same Source

Target:

> video berbeda tetapi merekam kejadian yang sama.

Signal:

* visual similarity
* object similarity
* environment
* people
* location
* timestamp clues
* textual metadata

---

## Level 3 — Similar Footage

Target:

> video berbeda tetapi visualnya sangat mirip.

Contoh:

Reference:

> seseorang merekam anjing mengejar mobil.

Candidate:

> video anjing mengejar kendaraan dari angle berbeda.

---

## Level 4 — Semantic Fallback

Jika visual search gagal:

```text
visual scene description
        ↓
text search
        ↓
candidate videos
```

---

# 17. Candidate Scoring

Setiap kandidat diberi score.

Contoh model awal:

```text
Visual similarity       40%
Object similarity       20%
Scene/context           15%
Motion similarity       15%
Text/metadata           10%
```

Total:

```text
0–100
```

Label:

```text
90–100   Very likely same
80–89    Highly similar
70–79    Similar
50–69    Related
<50      Weak match
```

Bobot harus configurable.

Jangan hard-code seluruh algoritma ke UI.

---

# 18. Footage Search UI

Setiap scene memiliki panel:

```text
Scene 03
00:08 – 00:13

Reference
[ thumbnail ]

Search results

[ Candidate 1 ]
Similarity: 94%
Platform: TikTok
[Open source]

[ Candidate 2 ]
Similarity: 88%
Platform: Instagram
[Open source]

[ Candidate 3 ]
Similarity: 81%
Platform: Douyin
[Open source]

[Upload footage manually]
```

User dapat:

* open source
* copy URL
* upload downloaded video
* reject
* select candidate

---

# 19. Important Footage Principle

Sistem **tidak wajib mengunduh footage dari platform**.

Responsibility aplikasi:

> discover and rank.

Responsibility user:

> download/import footage.

Hal tersebut menghindari ketergantungan terhadap downloader platform tertentu.

---

# 20. Manual Footage Upload

User harus dapat memasukkan:

* MP4
* MOV
* WebM

Setiap footage disimpan sebagai asset project.

Metadata:

```text
asset_id
filename
source_url
source_platform
duration
width
height
fps
codec
created_at
```

---

# 21. Footage Matching to Timeline

Setiap scene memiliki satu asset utama.

Example:

```text
Scene 1 → asset_001
Scene 2 → asset_014
Scene 3 → asset_003
```

Sistem otomatis menyesuaikan:

* trim
* crop
* scale
* aspect ratio
* duration

Default output:

**1080 × 1920**

---

# 22. Timeline Engine

Timeline menggunakan scene-based representation.

```text
Timeline
├── Scene 1
├── Scene 2
├── Scene 3
├── Scene 4
└── Scene 5
```

Setiap scene:

```text
source_asset
start
end
duration
crop
scale
position
transition
```

Jangan membuat arbitrary timeline editor pada V1.

---

# 23. Video Composition

Video composition dilakukan oleh FFmpeg.

Pipeline:

```text
Input videos
      ↓
Normalize
      ↓
Trim
      ↓
Scale
      ↓
Crop 9:16
      ↓
Concatenate
      ↓
Voice overlay
      ↓
BGM
      ↓
SFX
      ↓
Caption
      ↓
Encode
      ↓
Final MP4
```

---

# 24. Caption Engine

Caption berasal dari transcript voice-over.

Caption harus mempunyai timestamps.

Contoh:

```text
00:00.00 – 00:00.45
PARA

00:00.45 – 00:01.10
ILMUWAN

00:01.10 – 00:02.00
BARU-BARU INI
```

---

# 25. Caption Styles

V1 menyediakan template, bukan editor caption penuh.

Contoh preset:

```text
Style A
Bold centered

Style B
Bold lower-center

Style C
Keyword highlight

Style D
Minimal
```

Configuration:

* font
* size
* position
* max words per line
* line count
* background
* outline
* highlight keywords

---

# 26. Caption Timing

Caption harus mengikuti voice-over aktual.

Source of truth:

**generated audio**

bukan durasi original reference.

Jika script berubah:

```text
script changed
    ↓
regenerate TTS
    ↓
regenerate timestamps
    ↓
regenerate captions
```

---

# 27. BGM

User memilih:

* track
* volume
* fade in
* fade out
* loop behavior

Default BGM volume:

```text
10–15%
```

Namun harus configurable.

---

# 28. SFX

V1:

* manual selection
* predefined library
* scene-based placement

V2:

AI dapat menyarankan:

```text
Hook → impact
Transition → whoosh
Reveal → hit
Action → corresponding SFX
```

SFX harus optional.

---

# 29. Audio Mixing

Hierarchy default:

```text
Voice        100%
BGM          10–15%
SFX          contextual
```

Audio processing:

* volume normalization
* ducking BGM during voice
* fade in/out
* limiter

---

# 30. Render System

Rendering harus berjalan sebagai background job.

User tidak boleh menunggu HTTP request terbuka selama rendering.

Flow:

```text
POST /render
      ↓
Create RenderJob
      ↓
Redis Queue
      ↓
Worker
      ↓
FFmpeg
      ↓
Upload result
      ↓
Update status
```

Status:

```text
queued
processing
completed
failed
cancelled
```

---

# 31. Preview

Preview harus dapat menampilkan:

* video
* caption
* audio
* scene boundaries
* selected footage

Preview tidak harus menggunakan final-quality rendering.

Gunakan lower-resolution/proxy rendering untuk kecepatan.

---

# 32. Export

Output utama:

```text
MP4
H.264
AAC
1080x1920
9:16
```

Preset:

### Draft

720×1280

### Standard

1080×1920

### High

1080×1920 high bitrate

---

# 33. Project Model

Satu project terdiri dari:

```text
Project
├── Reference
├── Transcript
├── Script
├── Voice
├── Scenes
├── Assets
├── Timeline
├── Caption settings
├── Audio settings
├── Render jobs
└── Outputs
```

---

# 34. Database Core Entities

## projects

```text
id
name
status
reference_asset_id
created_at
updated_at
```

## media_assets

```text
id
project_id
type
filename
storage_path
source_url
source_platform
mime_type
duration
width
height
fps
size
metadata
created_at
```

## transcripts

```text
id
project_id
language
provider
content
segments
version
created_at
```

## scripts

```text
id
project_id
source_language
target_language
content
version
created_at
```

## scenes

```text
id
project_id
sequence
start_time
end_time
duration
description
transcript_segment
created_at
```

## keyframes

```text
id
scene_id
timestamp
image_path
quality_score
embedding_reference
```

## footage_candidates

```text
id
scene_id
source_url
platform
thumbnail_url
title
similarity_score
match_type
metadata
status
```

## timeline_clips

```text
id
project_id
scene_id
media_asset_id
source_start
source_end
timeline_start
timeline_end
crop_data
position_data
scale
```

## tts_generations

```text
id
project_id
script_id
provider
voice_id
audio_asset_id
duration
metadata
created_at
```

## captions

```text
id
project_id
source_audio_id
style
configuration
segments
```

## audio_tracks

```text
id
project_id
type
media_asset_id
volume
start_time
end_time
fade_in
fade_out
```

## render_jobs

```text
id
project_id
status
progress
preset
output_asset_id
error
started_at
completed_at
```

---

# 35. API Architecture

FastAPI menjadi orchestration layer.

Contoh:

```text
POST   /projects
GET    /projects
GET    /projects/{id}

POST   /projects/{id}/reference
POST   /projects/{id}/analyze

GET    /projects/{id}/transcript
POST   /projects/{id}/script/generate
PUT    /projects/{id}/script

POST   /projects/{id}/tts
GET    /projects/{id}/scenes

POST   /scenes/{id}/search
GET    /scenes/{id}/candidates

POST   /projects/{id}/assets
POST   /projects/{id}/timeline

POST   /projects/{id}/captions
POST   /projects/{id}/render

GET    /render-jobs/{id}
GET    /projects/{id}/outputs
```

API harus versioned:

```text
/api/v1
```

---

# 36. Frontend Pages

## Dashboard

Menampilkan:

* recent projects
* processing projects
* completed projects
* create project

---

## New Project

Input:

```text
Project name
Reference video
```

---

## Project Overview

Menampilkan:

```text
Reference
Analysis status
Script status
Voice status
Footage status
Render status
```

---

## Script Workspace

Layout:

```text
Original              Indonesian
[ transcript ]         [ editable ]
```

Actions:

* regenerate
* save
* generate voice

---

## Scene Workspace

List:

```text
Scene 1
Scene 2
Scene 3
...
```

Setiap scene:

```text
Reference frame
Description
Transcript
Selected footage
Search candidates
```

---

## Editor Workspace

Simplified scene timeline:

```text
[Scene 1][Scene 2][Scene 3][Scene 4]
```

Panel:

```text
Video
Caption
Audio
```

---

## Render Page

Menampilkan:

```text
Preparing
Rendering
Encoding
Completed
```

---

## Output Page

Menampilkan:

* video preview
* duration
* resolution
* file size
* download

---

# 37. UI/UX Principles

Design:

* dark/light neutral workspace
* editor-focused
* minimal distraction
* responsive
* desktop-first

Primary navigation:

```text
Dashboard
Projects
Assets
Settings
```

Project navigation:

```text
Overview
Script
Scenes
Editor
Render
```

---

# 38. Background Jobs

Jenis job:

```text
AnalyzeVideoJob
TranscribeAudioJob
DetectScenesJob
ExtractKeyframesJob
GenerateScriptJob
GenerateTTSJob
GenerateCaptionJob
SearchFootageJob
DownloadAssetJob [optional]
GeneratePreviewJob
RenderVideoJob
```

Semua job harus:

* retryable
* observable
* idempotent jika memungkinkan
* menyimpan status
* menyimpan error

---

# 39. Queue Architecture

Gunakan Redis.

Queue dapat dipisahkan:

```text
default
ai
video
search
render
```

Contoh:

```text
video/render
```

dipisahkan dari:

```text
ai
```

agar render video berat tidak menghambat task AI ringan.

---

# 40. Worker Architecture

Gunakan Python workers.

```text
workers/
├── video_worker
├── ai_worker
├── search_worker
└── render_worker
```

Semua worker sebaiknya mempunyai service abstraction.

---

# 41. FFmpeg Requirements

FFmpeg menjadi dependency inti.

Gunakan FFmpeg untuk:

* metadata extraction
* audio extraction
* trimming
* scaling
* crop
* concatenation
* audio mixing
* caption burn-in
* encoding
* preview rendering

Jangan membuat video-processing engine sendiri untuk operasi yang sudah ditangani FFmpeg.

---

# 42. AI Provider Architecture

Jangan mengikat aplikasi ke satu vendor.

Gunakan interfaces:

```text
LLMProvider
STTProvider
TTSProvider
EmbeddingProvider
VisionProvider
```

Implementasi dapat diganti.

Contoh:

```text
LLMProvider
├── OpenAI
├── Gemini
└── Future providers
```

---

# 43. Vision / Embedding Architecture

Visual search membutuhkan embedding.

Komponen:

```text
Keyframe
   ↓
Image embedding
   ↓
Vector database
   ↓
Nearest neighbor search
```

Technology candidate:

**Qdrant**

Embedding model candidate:

* CLIP
* SigLIP
* future stronger vision embedding model

Model harus dibungkus dalam interface sehingga dapat diganti.

---

# 44. Vector Search

Collection contoh:

```text
footage_frames
```

Payload:

```text
asset_id
scene_id
timestamp
source_url
platform
```

Query:

```text
reference_frame_embedding
```

Output:

```text
candidate_id
similarity
metadata
```

---

# 45. Search Provider Abstraction

Interface:

```python
class SearchProvider:
    async def search(
        query,
        image=None,
        limit=10
    ) -> list[SearchResult]:
        ...
```

SearchResult:

```text
title
url
thumbnail
platform
description
metadata
```

Provider failure tidak boleh menghentikan seluruh application pipeline.

Contoh:

```text
TikTok provider failed
       ↓
continue with other providers
```

---

# 46. Source Reliability

Setiap search result harus diberi:

```text
provider
retrieved_at
availability
confidence
```

Jangan mengasumsikan link akan selalu valid.

---

# 47. Copyright / Safety Boundary

Aplikasi harus memperlakukan source footage sebagai **user-provided / externally sourced content**.

Sistem tidak boleh menyatakan:

> "Footage ini bebas copyright."

Sebaliknya, UI dapat memberikan informasi:

> "Verify usage rights before publishing."

Source URL disimpan agar pengguna dapat menelusuri sumber.

Untuk MVP, aplikasi tidak perlu membuat automated copyright decision engine.

---

# 48. Storage Architecture

Development:

```text
local filesystem
```

Production:

```text
Cloudflare R2
```

Folder logical structure:

```text
projects/
  {project_id}/
    reference/
    assets/
    audio/
    scenes/
    previews/
    renders/
```

Object storage abstraction:

```text
StorageProvider
├── LocalStorage
└── S3CompatibleStorage
```

---

# 49. Authentication

MVP:

* email/password
* session/JWT
* project ownership

User hanya dapat mengakses project miliknya.

---

# 50. Security

Requirements:

* validate uploaded file types
* enforce file size limits
* sanitize filenames
* prevent path traversal
* sandbox FFmpeg processes where practical
* never execute uploaded files
* API authentication
* authorization per project
* rate limiting
* secrets via environment variables
* signed/private storage URLs

---

# 51. File Validation

Allowed:

```text
.mp4
.mov
.webm
.mp3
.wav
.jpg
.jpeg
.png
```

Metadata harus diambil menggunakan trusted media tooling, bukan hanya extension.

---

# 52. Error Handling

Setiap stage harus dapat gagal secara independen.

Example:

```text
Scene detection ✓
Script generation ✓
TTS ✓
Footage search ✗
```

Project tetap dapat dilanjutkan secara manual.

UI harus memberikan:

```text
What failed
Why
Retry
Fallback option
```

Contoh:

> Visual search unavailable. You can upload footage manually.

---

# 53. Observability

Development:

* structured logging
* job status
* processing duration
* provider errors

Production:

* error tracking
* job monitoring
* render failure logs
* API latency

Setiap job mempunyai:

```text
job_id
project_id
started_at
completed_at
duration
status
error
```

---

# 54. Configuration

Environment:

```text
APP_ENV
DATABASE_URL
REDIS_URL

OPENAI_API_KEY
GEMINI_API_KEY

ELEVENLABS_API_KEY
GOOGLE_TTS_CREDENTIALS

R2_ENDPOINT
R2_BUCKET
R2_ACCESS_KEY
R2_SECRET_KEY

QDRANT_URL
QDRANT_API_KEY
```

Tidak boleh hard-code credentials.

---

# 55. Docker Architecture

Production awal:

```text
docker-compose.yml
```

Services:

```text
frontend
api
worker
postgres
redis
qdrant
caddy
```

Optional:

```text
minio
```

untuk local S3-compatible development.

---

# 56. Development Environment

Recommended:

```text
Next.js
FastAPI
PostgreSQL
Redis
Qdrant
FFmpeg
Docker Compose
```

Antigravity menjadi development environment utama.

Semua source code harus dapat dijalankan melalui:

```text
docker compose up
```

dengan dokumentasi jelas.

---

# 57. Repository Structure

Recommended monorepo:

```text
shorts-automation/
│
├── apps/
│   ├── web/
│   └── api/
│
├── workers/
│   ├── video/
│   ├── ai/
│   └── search/
│
├── packages/
│   ├── shared-types/
│   └── shared-config/
│
├── infrastructure/
│   ├── docker/
│   └── caddy/
│
├── scripts/
│
├── docs/
│
├── docker-compose.yml
├── .env.example
└── README.md
```

TypeScript dan Python masing-masing harus mempunyai tooling standar.

---

# 58. Frontend Architecture

Next.js + TypeScript.

Gunakan:

* server/client components sesuai kebutuhan
* React Query/TanStack Query untuk API state bila dibutuhkan
* form validation
* reusable UI components
* typed API client

API types idealnya di-generate/sinkronisasi.

---

# 59. Backend Architecture

FastAPI harus menggunakan layering:

```text
api/
services/
repositories/
models/
schemas/
workers/
providers/
core/
```

Contoh:

```text
services/video_analysis.py
services/script_generation.py
services/tts.py
services/visual_search.py
services/render.py
```

Business logic tidak ditempatkan di route handler.

---

# 60. Provider Layer

Struktur:

```text
providers/
├── llm/
├── stt/
├── tts/
├── embedding/
├── search/
└── storage/
```

Setiap provider memiliki interface.

Tujuan:

> vendor bisa diganti tanpa rewrite application logic.

---

# 61. Testing Strategy

## Unit Tests

Test:

* script processing
* scene timing
* timeline calculation
* caption segmentation
* audio mixing configuration
* similarity scoring

## Integration Tests

Test:

```text
upload
→ analyze
→ script
→ TTS
→ scene
→ render
```

## End-to-end

Minimal satu golden workflow:

```text
sample reference
→ expected project state
→ expected render
```

---

# 62. Render Validation

Setiap render harus diverifikasi:

* file exists
* playable
* correct resolution
* correct aspect ratio
* expected duration
* audio exists
* video stream exists
* no corrupt output

---

# 63. Performance Targets

Target awal:

### Upload

Immediate progress feedback.

### Transcript

Asynchronous.

### Scene detection

Asynchronous.

### TTS

Asynchronous.

### Search

Asynchronous.

### Render

Asynchronous.

UI tidak boleh freeze menunggu proses berat.

---

# 64. UX Progress Model

Setiap project memiliki pipeline progress:

```text
REFERENCE
   ✓

ANALYSIS
   ✓

SCRIPT
   ✓

VOICE
   ✓

FOOTAGE
   70%

EDIT
   pending

RENDER
   pending
```

User dapat kembali ke tahap sebelumnya.

---

# 65. Versioning

Important artifacts harus versioned:

* script
* transcript
* TTS
* scene configuration
* timeline
* caption configuration
* render configuration

Contoh:

```text
Script v1
Script v2
Script v3
```

Render harus menyimpan referensi terhadap versi configuration yang digunakan.

---

# 66. Project State Machine

Project state:

```text
draft
analyzing
script_ready
voice_ready
footage_ready
editing
rendering
completed
failed
```

State jangan hanya bergantung pada UI.

Backend menjadi source of truth.

---

# 67. MVP Scope Detail

MVP wajib mempunyai:

### Project

* create
* delete
* list
* open

### Reference

* upload
* metadata
* preview

### Analysis

* audio extraction
* transcription
* scene detection
* keyframe generation

### Script

* original transcript
* Indonesian adaptation
* manual editing

### TTS

* generate
* preview
* regenerate

### Footage

* upload local footage
* assign footage to scene

### Caption

* generate
* choose preset
* preview

### Audio

* upload/select BGM
* volume

### Timeline

* scene-based composition

### Render

* preview render
* final render
* export

---

# 68. V1 Success Criteria

User dapat menghasilkan satu Shorts baru melalui:

```text
reference
→ analysis
→ Indonesian script
→ TTS
→ scene assignment
→ captions
→ BGM
→ render
```

tanpa perlu membuka video editor eksternal untuk pekerjaan dasar.

Target utama:

> mengurangi pekerjaan manual editing, bukan membuat kualitas editing otomatis sempurna.

---

# 69. V2 Success Criteria

Untuk setiap scene:

```text
reference frame
→ search
→ candidates
→ ranking
```

Sistem harus dapat menemukan setidaknya beberapa kandidat yang relevan pada sebagian besar scene yang searchable.

Tidak ada requirement bahwa exact match selalu ditemukan.

---

# 70. V3 Success Criteria

User dapat:

```text
Upload reference
→ Generate Indonesian script
→ Generate voice
→ Search footage
→ Select footage
→ Generate timeline
→ Render
```

dengan intervensi manual terutama hanya pada:

* pemilihan footage
* koreksi script
* creative review

---

# 71. Quality Metrics

Produktivitas:

```text
time_to_first_draft
```

Kualitas visual:

```text
footage_match_score
```

Kualitas AI:

```text
script_edit_distance
tts_success_rate
```

Reliability:

```text
render_success_rate
job_failure_rate
provider_failure_rate
```

User experience:

```text
manual_steps_per_video
```

---

# 72. Important Architectural Principle

Jangan membangun sistem dengan asumsi:

> semua AI selalu berhasil.

Pipeline harus mendukung:

```text
AI success
AI retry
AI fallback
manual override
```

Contoh:

```text
Visual search unavailable
       ↓
manual footage upload
```

atau:

```text
TTS provider unavailable
       ↓
switch provider
```

---

# 73. AI Prompting Requirements

Prompt AI harus disimpan terpisah dari business logic.

Contoh:

```text
prompts/
├── script_adaptation.txt
├── scene_description.txt
├── footage_query.txt
└── caption_segmentation.txt
```

Version prompt harus dapat dilacak.

---

# 74. AI Output Validation

LLM output tidak boleh langsung dianggap valid.

Gunakan schema.

Contoh scene:

```json
{
  "description": "...",
  "objects": [],
  "actions": [],
  "environment": "...",
  "search_queries": []
}
```

Backend harus melakukan schema validation.

---

# 75. Search Query Generation

Untuk satu scene, AI dapat menghasilkan beberapa query:

```text
Primary:
"man riding motorcycle at night"

Alternative:
"motorcycle rider street night"

Context:
"motorbike road accident night"
```

Query ini digunakan sebagai fallback, bukan satu-satunya search signal.

---

# 76. Multi-Frame Search

Satu scene tidak boleh bergantung pada satu frame.

Contoh:

```text
Scene 4
├── keyframe 1
├── keyframe 2
└── keyframe 3
```

Search result dapat dinilai berdasarkan agregasi:

```text
candidate similarity across frames
```

Ini membantu membedakan:

> video yang benar-benar sama

dari:

> satu frame kebetulan mirip.

---

# 77. Footage Ranking Pipeline

```text
Candidate retrieval
       ↓
Deduplication
       ↓
Frame similarity
       ↓
Sequence similarity
       ↓
Semantic similarity
       ↓
Metadata relevance
       ↓
Final ranking
```

---

# 78. Search Result Deduplication

Platform berbeda dapat mengarah ke footage yang sama.

Sistem harus mencoba mengelompokkan:

```text
TikTok A
Instagram B
Douyin C
```

sebagai:

```text
Potential same source
```

sehingga UI tidak menampilkan duplikasi berlebihan.

---

# 79. Manual Override Everywhere

User dapat mengganti:

* transcript
* script
* TTS
* scene duration
* footage
* crop
* caption style
* BGM
* SFX

Tidak ada AI decision yang irreversible.

---

# 80. Undo / Version Strategy

MVP tidak memerlukan full undo stack seperti NLE.

Cukup:

* revert scene
* regenerate
* replace asset
* restore previous script version

---

# 81. Accessibility

Minimal:

* keyboard-accessible controls
* readable contrast
* clear status labels
* descriptive buttons
* non-color-only status indicators

---

# 82. Internationalization

MVP:

```text
Indonesian
English
```

Text UI harus disimpan dalam localization layer.

---

# 83. Cost Control

AI/video processing dapat mahal.

Maka:

* proxy previews
* cache transcription
* cache embeddings
* cache search results
* jangan regenerate jika input tidak berubah
* batch operations jika memungkinkan
* background workers

TTS jangan dibuat ulang jika:

```text
same script
same voice
same settings
```

---

# 84. Caching

Cache key contoh:

```text
transcript:
hash(reference_audio)

TTS:
hash(script + voice + settings)

embedding:
hash(image)

search:
hash(query + image_embedding)
```

---

# 85. Privacy

Project media default private.

User dapat menghapus:

* source video
* generated audio
* project
* rendered video

Delete harus menghapus associated storage bila aman untuk dilakukan.

---

# 86. Auditability

Untuk setiap output final, sistem harus dapat mengetahui:

```text
reference
script version
TTS version
footage assets
caption configuration
BGM
SFX
render settings
```

Tujuannya agar output dapat direproduksi.

---

# 87. Reproducible Rendering

Render harus didasarkan pada:

```text
project configuration
+
asset versions
+
render preset
```

bukan berdasarkan state UI saat ini saja.

---

# 88. Recommended Initial Repository Milestones

## Milestone 1

Project skeleton.

```text
Next.js
FastAPI
PostgreSQRedis
Docker
```

## Milestone 2

Project + media management.

## Milestone 3

Reference analysis.

## Milestone 4

Transcript + script adaptation.

## Milestone 5

TTS.

## Milestone 6

Scene + keyframe.

## Milestone 7

Timeline.

## Milestone 8

Caption.

## Milestone 9

BGM/SFX.

## Milestone 10

Preview/render/export.

## Milestone 11

Visual search foundation.

## Milestone 12

Search provider integrations.

## Milestone 13

Automatic candidate ranking.

---

# 89. Antigravity Development Rules

Antigravity harus mengikuti aturan berikut.

## Rule 1 — Jangan melakukan massive rewrite

Sebelum mengubah arsitektur besar:

* inspect existing code
* explain planned change
* identify affected files
* implement incrementally

## Rule 2 — Jangan mengarang API

Library/provider API harus diverifikasi terhadap documentation/version yang digunakan.

## Rule 3 — Small atomic changes

Satu task harus fokus pada satu feature.

## Rule 4 — Test after implementation

Feature tidak dianggap selesai sebelum:

* type checking
* lint
* unit/integration test terkait
* manual verification bila diperlukan

## Rule 5 — Preserve existing behavior

Jangan mengubah fitur yang tidak berkaitan.

## Rule 6 — Explicit dependencies

Setiap dependency baru harus dijelaskan:

```text
package
version
purpose
```

## Rule 7 — No unnecessary abstraction

Abstraction hanya dibuat ketika memang dibutuhkan.

Namun provider integrations wajib mempunyai interface karena sifatnya vendor-dependent.

---

# 90. Antigravity Task Format

Setiap prompt coding berikutnya idealnya memiliki:

```text
Context
Goal
Requirements
Constraints
Files/components involved
Acceptance criteria
Tests
Do not change
```

---

# 91. Example Development Task

```text
TASK: Implement reference video upload

Context:
This is the first media workflow of Shorts Automation Studio.

Goal:
Allow authenticated users to upload one reference video to a project.

Requirements:
- Accept mp4, mov, webm
- Validate MIME type
- Validate file size
- Store metadata
- Store file locally
- Show upload progress
- Display preview
- Persist media_assets record

Constraints:
- Do not implement cloud storage yet
- Do not implement video analysis yet
- Do not modify unrelated modules

Acceptance criteria:
- User can create project
- User can upload reference
- Media metadata is persisted
- File is accessible through authenticated route
- Invalid files are rejected
- Automated tests pass
```

---

# 92. MVP Definition of Done

MVP dianggap selesai apabila:

1. User dapat membuat project.
2. User dapat upload reference.
3. System dapat transcribe.
4. System dapat menghasilkan Indonesian script.
5. System dapat generate TTS.
6. System dapat detect scenes.
7. User dapat upload footage.
8. User dapat assign footage per scene.
9. System dapat generate caption.
10. User dapat menambahkan BGM.
11. System dapat generate preview.
12. System dapat render final MP4.
13. Final video dapat diputar.
14. Project dapat dibuka kembali tanpa kehilangan state.

---

# 93. V2 Definition of Done

V2 dianggap selesai apabila:

1. Scene menghasilkan keyframes.
2. Keyframes dapat dipakai untuk search.
3. Search provider dapat mengembalikan candidate.
4. Candidate dapat diranking.
5. Exact/similar classification tersedia.
6. Source URL tersedia.
7. User dapat memilih candidate.
8. Search failure memiliki fallback manual.

---

# 94. V3 Definition of Done

V3 dianggap selesai apabila:

```text
Reference
   ↓
Automatic analysis
   ↓
Script
   ↓
Voice
   ↓
Footage candidates
   ↓
Timeline
   ↓
Caption
   ↓
Audio
   ↓
Render
```

dapat berjalan sebagai pipeline yang terintegrasi.

---

# 95. Final Product Concept

Produk akhir bukan:

> "AI membuat video."

Produk akhir adalah:

> **"AI membantu creator merekonstruksi format sebuah Shorts referensi menjadi draft Shorts baru dengan sebanyak mungkin pekerjaan repetitif dilakukan otomatis."**

Core workflow:

```text
             VIRAL REFERENCE
                     │
                     ▼
             ┌──────────────┐
             │   ANALYZE    │
             └──────┬───────┘
                    │
       ┌────────────┴────────────┐
       ▼                         ▼
  SCRIPT ENGINE            VISUAL ENGINE
       │                         │
       ▼                         ▼
 Indonesian Script         Scene + Keyframes
       │                         │
       ▼                         ▼
      TTS                  Visual Search
       │                         │
       └────────────┬────────────┘
                    ▼
              COMPOSITION
                    │
                    ▼
          CAPTION + BGM + SFX
                    │
                    ▼
                 PREVIEW
                    │
                    ▼
               FINAL SHORT
```

---

# 96. Prioritas Utama

Urutan prioritas engineering:

**P0 — Must have**

* project
* media upload
* transcription
* script
* TTS
* scene detection
* manual footage assignment
* caption
* render

**P1 — High value**

* visual search
* candidate ranking
* multi-frame matching
* source URL

**P2 — Enhancement**

* automatic footage selection
* automatic SFX
* advanced ranking
* automatic pacing optimization

**P3 — Future**

* multi-user collaboration
* cloud rendering
* batch generation
* analytics
* YouTube publishing
* multiple language outputs

---

# 97. Guiding Principle

Setiap feature baru harus menjawab pertanyaan:

> **"Apakah ini mengurangi pekerjaan repetitif dalam workflow Shorts creator?"**

Jika tidak, feature tersebut bukan prioritas.
