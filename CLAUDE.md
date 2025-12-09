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

- **Utilities** (`Orest's Journal/Utilities/`):
  - `Formatters.swift` - Shared static formatters (avoid recreating expensive instances)
    - `Formatters.shortDate` - DateFormatter with `.short` dateStyle
    - `Formatters.weight` - NumberFormatter for weight (0-1 decimal places)
  - `RoundedCorner.swift` - Custom Shape for rounding specific corners
    - `View.cornerRadius(_:corners:)` extension for selective corner rounding

### Backend (FastAPI)
- **Structure**: `backend/app/` with `api/endpoints/`, `models/`, `schemas/`, `services/`
- **Database**: Neon PostgreSQL with SQLAlchemy, migrations via Alembic
- **Cache**: Redis with cache helpers
- **Auth**: Clerk JWT + Sign in with Apple
- **File Storage**: Cloudflare R2

## Key Conventions

### iOS
- Views organized by feature domain (Auth, Pets, Medications, Feeding, Health)
- Use `@Observable` pattern for state management (AuthManager is @Observable)
- Use `NavigationStack` (not deprecated `NavigationView`)
- Use `Formatters.shortDate` / `Formatters.weight` for formatting (don't recreate formatters)
- Use `Task.sleep(for:)` instead of `DispatchQueue.main.asyncAfter`
- API responses use snake_case (auto-converted by APIClient)
- Background modes: fetch, processing, remote-notification

### Backend
- All endpoints under `/api/v1/`
- Most endpoints require `org_id` query param for family/organization context
- Pydantic schemas for request/response validation
- Async/await throughout

## Cache Management

### Cache Architecture Overview

The app uses a **three-tier caching strategy**:

1. **iOS Memory Cache** (`DataService`) - Fastest, cleared on app termination or memory pressure
2. **iOS Disk Cache** (`PersistentCacheManager`) - Persists across app launches, stored in Application Support
3. **Backend Redis Cache** - Server-side caching for expensive database queries

**Pattern**: Stale-while-revalidate - Return cached data immediately, refresh in background if stale.

### iOS Cache TTLs
| Data Type | Memory TTL | Disk Max Age | Notes |
|-----------|------------|--------------|-------|
| Pets | 5 min | 24 hr | Background refresh when stale |
| Family Members | 1 min | 24 hr | Invalidated on membership changes |
| Calorie Goals | 1 min | 24 hr | Per-pet caching |

### Backend Redis TTLs
| Data Type | TTL | Key Pattern |
|-----------|-----|-------------|
| Family Details | 5 min | `family:{family_id}` |
| Calorie Goal | 5 min | `calorie_goal:{pet_id}` |
| Foods | 1 hr | `foods:{org_id}` |

### Cache Invalidation - IMPORTANT

**When invalidating cache, you must do TWO things:**
1. **Clear the cached data** - Call `DataService.shared.invalidateFamilyCache(for:)` or similar
2. **Tell the view to refresh** - Call `NavigationManager.shared.requestTabRefresh(.family)`

Just clearing the cache is NOT enough - the view won't know to reload unless you also mark the tab as needing refresh.

Example (from NotificationManager when member joins):
```swift
DataService.shared.invalidateFamilyCache(for: familyId)
NavigationManager.shared.requestTabRefresh(.family)
```

### Cache Stampede Prevention
`DataService` uses `refreshInProgress` flags to prevent multiple concurrent background refreshes of the same data.

### Flush Redis Cache (Backend)
When debugging cache issues or after making cache-related changes:
```bash
redis-cli FLUSHALL
```

### Clear iOS Disk Cache
Delete the app from device and reinstall, or clear Application Support directory programmatically.

### Adding New Cached Data
1. Add cache key to `PersistentCacheManager.CacheKey` enum (iOS)
2. Add TTL constant and key function to `backend/app/cache/keys.py` (Backend)
3. Implement cache get/set in the data fetching method
4. Add cache invalidation in all mutation methods
5. Add `requestTabRefresh()` call where appropriate for UI updates

## API Documentation
When backend is running: `http://localhost:8000/docs` (Swagger) or `/redoc`
