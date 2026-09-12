# Shorts Automation Studio

Shorts Automation Studio is a web application designed to automate the repetitive production workflow of YouTube Shorts based on proven, viral reference videos, while keeping creative decisions under creator control.

---

## Architecture Overview

The system uses a hybrid micro-service monorepo architecture:

- **Next.js (Web Frontend)**: Located in `apps/web`. Provides a fast desktop-first web interface built with React, TypeScript, App Router, and Tailwind CSS.
- **FastAPI (API Gateway & Core Logic)**: Located in `apps/api`. Handles project management, orchestration, validation, and coordinates background workers using clean layered architecture (routes, schemas, services, repositories, providers).
- **PostgreSQL (Database)**: Stores relational models including projects, media assets, transcripts, script adaptations, scenes, and render job metadata.
- **Redis (Cache & Job Queue)**: Provides asynchronous task queues for offloading CPU-intensive or long-running tasks from HTTP request cycles.
- **Qdrant (Vector Database)**: Dedicated vector engine for indexing and querying keyframe image embeddings during visual footage search.
- **FFmpeg & Python Workers**: Located in `workers/`. Containers equipped with FFmpeg and FFprobe to perform media operations (metadata extraction, audio trimming, aspect ratio scaling, captions burn-in, and video composition).

---

## Repository Structure

```text
shorts-automation/
├── apps/
│   ├── web/                    # Next.js web application
│   └── api/                    # FastAPI backend service
├── workers/
│   ├── video/                  # FFmpeg and video composition worker
│   ├── ai/                     # LLM / Transcription / TTS worker
│   └── search/                 # Visual similarity & search worker
├── packages/
│   ├── shared-types/           # Shared TypeScript interfaces
│   └── shared-config/          # Shared linting & tsconfig definitions
├── infrastructure/
│   ├── docker/                 # Docker guidelines and configurations
│   └── caddy/                  # Caddy reverse proxy configuration
├── scripts/
│   └── verify.ps1              # Service connectivity verification script
├── docs/
│   └── PRD.md                  # Complete Product Requirements Document
├── docker-compose.yml          # Multi-service development setup
├── .env.example                # Environment variables template
├── .gitignore                  # Git ignore rules
└── README.md                   # Project documentation
```

---

## Requirements

- **Docker & Docker Compose** (recommended for full multi-service environment)
- **Node.js** v20+ and **npm** v10+ (for local web development)
- **Python** 3.11+ (for local API and worker development)
- **FFmpeg** 6+ (for local media execution outside Docker)

---

## Getting Started

### 1. Configure Environment Variables

Copy the example environment configuration:
```bash
cp .env.example .env
```
Update any API keys or configuration options as needed.

### 2. Start Services with Docker Compose

Run all services using Docker Compose:
```bash
docker compose up --build
```

### 3. Accessing Services

Once started, the services are accessible at:

| Service | Address | Description |
| :--- | :--- | :--- |
| Frontend Web | http://localhost:3000 | Next.js user interface |
| FastAPI Backend | http://localhost:8000 | Core REST API |
| API Docs (Swagger) | http://localhost:8000/docs | Interactive API documentation |
| API Healthcheck | http://localhost:8000/health | Service liveness endpoint |
| PostgreSQL | localhost:5432 | Relational database |
| Redis | localhost:6379 | Task queue & cache broker |
| Qdrant Console | http://localhost:6333/dashboard | Vector database web UI |

---

## Local Development (Without Docker)

You can also run services independently on your host machine:

### Frontend
```bash
cd apps/web
npm install
npm run dev
```

### Backend
```bash
cd apps/api
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Workers
```bash
cd workers
pip install -r requirements.txt
python video/main.py
```

---

## Milestone 3: Reference Video Analysis

Milestone 3 implements reference video analysis, transforming uploaded Shorts videos into structured analysis data for subsequent production milestones.

### Pipeline Workflow
1. **Audio Extraction**: FFmpeg extracts audio from reference video to a temporary 16kHz mono PCM WAV file.
2. **Speech-to-Text (STT)**: Transcribes spoken dialogue with high-precision timestamps (`start`, `end`, `text`) using `faster-whisper`.
3. **Scene Cut Detection**: Identifies visual scene boundaries via FFmpeg visual cut filter (`select='gt(scene,0.3)'`).
4. **Transcript Alignment**: Associates overlapping spoken transcript segments with each scene.
5. **Keyframe Extraction**: Extracts 3 distributed keyframes per scene (at 20%, 50%, and 80% of scene duration) and computes a Laplacian variance sharpness quality score.
6. **Scene Visual Description**: Uses multimodal Google Gemini Vision (with heuristic fallback) to generate structured descriptions (main subject, actions, objects, environment).
7. **Persistence & Presentation**: Stores structured results in PostgreSQL (`transcripts`, `scenes`, `keyframes`, `analysis_jobs`) and provides an interactive Next.js workspace with live progress polling and keyframe modal preview.

### Running Analysis Tests
```bash
cd apps/api
python -m pytest tests -v
```

### Environment Variables
- `STT_PROVIDER`: Speech-to-text provider (`faster_whisper` or `mock`, default: `faster_whisper`).
- `WHISPER_MODEL`: Model size for Whisper (`tiny`, `base`, `small`, default: `tiny`).
- `KEYFRAMES_PER_SCENE`: Number of keyframe captures per scene (default: `3`).
- `ANALYSIS_MAX_DURATION_SECONDS`: Maximum reference duration in seconds (default: `180`).
- `GEMINI_API_KEY`: Google Gemini API key for visual scene descriptions.

### Known Limitations
- Visual footage search, Indonesian script adaptation, TTS voice synthesis, caption burn-in, and timeline rendering are **not implemented yet** (scheduled for subsequent milestones).

---

## Current Status

- **Milestone 1**: Project Skeleton & Micro-Service Architecture Initialized.
- **Milestone 2**: Project Management, Media Asset Upload, and Technical Metadata Extraction.
- **Milestone 3**: Reference Video Analysis (Audio Extraction, Faster-Whisper Transcription, Scene Cut Detection, Keyframe Scoring, Gemini Scene Descriptions, and Next.js Workspace).

