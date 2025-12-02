# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build Commands

### iOS App
- **Build & Run**: Use Xcode or XcodeBuildMCP tools with scheme "Orest's Journal"
- **Target Device**: Always build on "Alexanders iPhone" (physical device, not simulator)
- **Project File**: `Orest's Journal.xcodeproj`

### Backend (FastAPI)
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head                    # Run database migrations
uvicorn app.main:app --reload           # Start dev server at localhost:8000
```

## Architecture

### iOS App (SwiftUI + MVVM)
- **Entry Point**: `Orest's Journal/Orest_s_JournalApp.swift`
- **Core Managers** (singletons):
  - `AuthManager` - Sign in with Apple, JWT tokens, Keychain storage
  - `APIClient` - Network layer with automatic snake_case JSON conversion
  - `DataService` - Business logic with two-tier caching (memory + disk)
  - `NotificationManager` - Push notifications and device registration
  - `BackgroundTaskManager` - BGAppRefresh for background data sync
  - `PersistentCacheManager` - Disk cache in Application Support

- **Caching**: Stale-while-revalidate pattern, 1-min TTL (general), 5-min TTL (foods)

### Backend (FastAPI)
- **Structure**: `backend/app/` with `api/endpoints/`, `models/`, `schemas/`, `services/`
- **Database**: Neon PostgreSQL with SQLAlchemy, migrations via Alembic
- **Cache**: Redis with cache helpers
- **Auth**: Clerk JWT + Sign in with Apple
- **File Storage**: Cloudflare R2

## Key Conventions

### iOS
- Views organized by feature domain (Auth, Pets, Medications, Feeding, Health)
- Use `@Observable` pattern for state management
- API responses use snake_case (auto-converted by APIClient)
- Background modes: fetch, processing, remote-notification

### Backend
- All endpoints under `/api/v1/`
- Most endpoints require `org_id` query param for family/organization context
- Pydantic schemas for request/response validation
- Async/await throughout

## API Documentation
When backend is running: `http://localhost:8000/docs` (Swagger) or `/redoc`
