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

## Current Status

**Milestone 1: Project Skeleton Initialized.**
The foundational directory structure, configuration templates, Docker Compose specifications, type definitions, and healthcheck endpoints are established. Feature workflows (video upload, transcription, TTS, scene search, timeline composition) will be introduced in subsequent milestones according to the PRD roadmap.
