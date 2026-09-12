# Infrastructure: Docker

This directory contains Docker configurations and guidelines for Shorts Automation Studio.

## Services Architecture

- **web**: Next.js App Router frontend on port 3000.
- **api**: FastAPI application on port 8000.
- **postgres**: PostgreSQL 16 relational database on port 5432.
- **redis**: Redis 7 cache and job queue broker on port 6379.
- **qdrant**: Qdrant vector database on port 6333.
- **worker**: Python background worker equipped with FFmpeg and FFprobe.

## Usage

Start all services:
```bash
docker compose up --build
```

Stop services:
```bash
docker compose down
```
