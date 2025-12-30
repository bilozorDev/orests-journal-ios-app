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
make start                              # Start Postgres + Redis (Docker)
make migrate                            # Run database migrations
make run                                # Start dev server at localhost:8000
```

### Backend Makefile Commands
| Command | Description |
|---------|-------------|
| `make start` | Start Postgres + Redis containers |
| `make stop` | Stop containers (keeps data) |
| `make reset-db` | Fast reset - truncate all tables, clear Redis |
| `make nuke-db` | Full reset - destroy volumes, recreate, run migrations |
| `make migrate` | Run Alembic migrations |
| `make run` | Start FastAPI dev server |
| `make celery` | Start Celery worker |
| `make celery-beat` | Start Celery beat scheduler |

### Switch Database Environment
```bash
cd backend
cp .env.local .env   # Use local Postgres (Docker)
cp .env.neon .env    # Use Neon cloud database
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
- Most endpoints require `family_id` query param for family context
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
| Foods | 1 hr | `foods:{family_id}` |

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

## UI Testing

### Running UI Tests
UI tests require:
1. **Backend running** - The tests authenticate via the backend `/auth/test-login` endpoint
2. **Simulator** - Tests run on iOS Simulator (not physical device)

**Preferred Simulator**: iPhone 16 Pro (iOS 18.6) - UUID: `D718C840-01E8-489A-9322-2DC4B9CF8D63`

### Run All UI Tests
```bash
# Using xcodebuild (run from project root)
xcodebuild test \
  -project "Orest's Journal.xcodeproj" \
  -scheme "Orest's Journal" \
  -destination 'platform=iOS Simulator,id=D718C840-01E8-489A-9322-2DC4B9CF8D63' \
  -parallel-testing-enabled NO
```

### Run Specific Test Class
```bash
xcodebuild test \
  -project "Orest's Journal.xcodeproj" \
  -scheme "Orest's Journal" \
  -destination 'platform=iOS Simulator,id=D718C840-01E8-489A-9322-2DC4B9CF8D63' \
  -only-testing:"Orest's JournalUITests/FamilyMemberManagementTests"
```

### Run Single Test Method
```bash
xcodebuild test \
  -project "Orest's Journal.xcodeproj" \
  -scheme "Orest's Journal" \
  -destination 'platform=iOS Simulator,id=D718C840-01E8-489A-9322-2DC4B9CF8D63' \
  -only-testing:"Orest's JournalUITests/CreateFamilyFlowTests/testCreateFamilyAndAddPet"
```

### Using XcodeBuildMCP (Claude Code)
```
# Run all tests on simulator
test_sim({ projectPath: 'Orest\'s Journal.xcodeproj', scheme: 'Orest\'s Journal', simulatorId: 'D718C840-01E8-489A-9322-2DC4B9CF8D63' })
```

### Test Structure
- **BaseUITest.swift** - Base class with auth helpers, multi-user setup, cleanup
- **Tests/**
  - `CreateFamilyFlowTests.swift` - Create family flow
  - `AddPetFlowTests.swift` - Add pet flow
  - `FamilyMemberManagementTests.swift` - Join family, change roles, remove members
  - `PetManagementTests.swift` - Add/edit/delete pets
  - `EndToEndFlowTests.swift` - Full user journeys

### Test Data Cleanup
Tests automatically clean up created users via `/auth/test-cleanup/{test_user_id}` in teardown.

### API Base URL
Tests use ngrok URL configured in `BaseUITest.apiBaseURL`. Update this when ngrok URL changes.

## API Documentation
When backend is running: `http://localhost:8000/docs` (Swagger) or `/redoc`
