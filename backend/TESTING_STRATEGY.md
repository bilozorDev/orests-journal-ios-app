# FastAPI Backend Testing Strategy

## Executive Summary

This document outlines a comprehensive testing strategy for the Orest's Journal FastAPI backend to prevent breaking changes to the iOS app and ensure API reliability.

**Current Status**:
- **Test Coverage**: ~15% (5 test files covering 3 out of 12 endpoints)
- **Testing Gaps**: Critical features like medications, notifications, health events, foods, feedings, doses, dashboard, and auth endpoints are untested
- **Risk Level**: HIGH - Recent medication and notification changes are completely untested

---

## 1. Current Test Coverage Analysis

### Existing Tests

| Test File | Lines | Coverage |
|-----------|-------|----------|
| `conftest.py` | 143 | Fixtures and test helpers |
| `test_families.py` | 743 | Family management endpoints |
| `test_pets.py` | 333 | Pet CRUD operations |
| `test_pet_schemas.py` | 166 | Pet schema validation |

**Well-Tested Areas:**
- ✅ Family management (update family, member roles, brute force protection)
- ✅ Pet CRUD (create, update, get with date_of_birth)
- ✅ Pet schema validation (date parsing, optional fields)

### Critical Gaps

| Endpoint/Area | Status | Priority | Risk |
|---------------|--------|----------|------|
| Medications API | ❌ No tests | **P0 - CRITICAL** | Breaking changes to medication schema will crash iOS app |
| Notifications API | ❌ No tests | **P0 - CRITICAL** | Device token registration failures block all push notifications |
| Medication Doses API | ❌ No tests | **P1 - HIGH** | Dose recording is core feature |
| Health Events API | ❌ No tests | **P1 - HIGH** | Recently refactored, needs regression prevention |
| Foods/Feedings API | ❌ No tests | **P1 - HIGH** | Core daily-use features |
| Dashboard API | ❌ No tests | **P1 - HIGH** | Main app view, caching logic untested |
| Auth Endpoints | ❌ No tests | **P1 - HIGH** | Sign in with Apple integration |
| Uploads/Storage | ❌ No tests | **P2 - MEDIUM** | Photo uploads to R2 |
| `family_notifications` service | ❌ No tests | **P0 - CRITICAL** | Notification filtering logic untested |
| Schema validators | ⚠️ Partial | **P1 - HIGH** | Only Pet schemas tested |

---

## 2. Testing Architecture

### Test Pyramid

```
       ┌─────────────────┐
       │  E2E (Manual)   │  <- UI Tests (existing iOS XCUITest suite)
       └─────────────────┘
      ┌───────────────────┐
      │ Integration Tests │  <- API endpoint tests (200 tests needed)
      └───────────────────┘
     ┌─────────────────────┐
     │    Unit Tests       │  <- Services, schemas, utils (150 tests needed)
     └─────────────────────┘
    ┌───────────────────────┐
    │  Schema Validation    │  <- Contract tests (50 tests needed)
    └───────────────────────┘
```

### Test Types

1. **Schema Validation Tests** - Prevent breaking changes to API contracts
2. **Integration Tests** - Test endpoints with mocked database
3. **Unit Tests** - Test services, business logic, utilities
4. **Database Model Tests** - Validate constraints, relationships, migrations
5. **Contract Tests** - Ensure iOS app compatibility

---

## 3. Testing Standards & Conventions

### File Organization

```
backend/tests/
├── conftest.py                      # Shared fixtures
├── schemas/
│   ├── test_medication_schemas.py   # Pydantic validation tests
│   ├── test_notification_schemas.py
│   └── test_health_schemas.py
├── api/
│   ├── test_medications.py          # Endpoint integration tests
│   ├── test_notifications.py
│   ├── test_doses.py
│   ├── test_health.py
│   ├── test_foods.py
│   ├── test_feedings.py
│   ├── test_dashboard.py
│   └── test_auth.py
├── services/
│   ├── test_family_notifications.py # Service unit tests
│   ├── test_apns.py
│   └── test_storage.py
├── models/
│   ├── test_medication_models.py    # Database model tests
│   └── test_notification_models.py
└── contract/
    └── test_ios_compatibility.py    # iOS app contract tests
```

### Naming Conventions

```python
# Test class names describe the feature/endpoint
class TestCreateMedication:
class TestMedicationSchemaValidation:
class TestFamilyNotificationService:

# Test method names describe scenario + expected outcome
def test_create_medication_with_photos_success():
def test_create_medication_without_pet_access_returns_403():
def test_medication_type_invalid_value_raises_422():
def test_notification_preferences_default_all_enabled():
```

### Test Structure (AAA Pattern)

```python
@pytest.mark.asyncio
async def test_create_medication_with_scheduled_times(
    client: AsyncClient,
    mock_db_session: AsyncMock,
    auth_headers: dict,
    test_user_id: str,
    test_family_id: str,
):
    """Admin can create medication with scheduled reminder times."""
    # ARRANGE - Setup test data and mocks
    mock_pet = create_mock_pet(family_id=test_family_id)
    mock_membership = create_mock_membership(
        user_id=test_user_id,
        family_id=test_family_id,
        role="admin"
    )

    # Setup database query mocks
    membership_result = MagicMock()
    membership_result.scalar_one_or_none.return_value = mock_membership
    mock_db_session.execute = AsyncMock(return_value=membership_result)

    # ACT - Execute the operation
    response = await client.post(
        f"/api/v1/medications?family_id={test_family_id}",
        json={
            "pet_id": str(mock_pet.id),
            "name": "Prednisone",
            "medication_type": "pill",
            "dosage": "5mg",
            "start_date": "2024-01-01T00:00:00Z",
            "times_per_day": 2,
            "scheduled_times": [
                {"hour": 8, "minute": 0},
                {"hour": 20, "minute": 0}
            ]
        },
        headers=auth_headers,
    )

    # ASSERT - Verify results
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Prednisone"
    assert data["medication_type"] == "pill"
    assert len(data["scheduled_times"]) == 2
    mock_db_session.commit.assert_called()
```

---

## 4. Priority Test Suites (Next 2 Weeks)

### Week 1: Critical Path (P0)

#### 1. Medication Schema Tests (`tests/schemas/test_medication_schemas.py`)
**Why**: Recent changes to medication models/schemas are untested. Breaking changes will crash iOS app.

```python
# Required tests (30 tests):
- MedicationType enum validation (8 types)
- MedicationCreate with all field combinations
- MedicationUpdate partial updates
- MedicationResponse serialization with photos
- ScheduledTimeCreate hour/minute validation (0-23, 0-59)
- MedicationPhotoResponse ordering
- is_active property calculation logic
- Timezone string validation
- interval_days range validation (1-30)
- times_per_day validation
```

#### 2. Notification Schema Tests (`tests/schemas/test_notification_schemas.py`)
**Why**: Device token registration is critical for push notifications.

```python
# Required tests (20 tests):
- DeviceTokenCreate validation
- DeviceTokenResponse serialization
- NotificationPreferencesUpdate partial updates (13 boolean fields)
- NotificationPreferencesResponse defaults (all True)
- ScheduleSetRequest validation
```

#### 3. Medications Endpoint Tests (`tests/api/test_medications.py`)
**Why**: Core feature, recently modified, completely untested.

```python
# Required tests (40 tests):
- POST /medications - Create with photos, schedules, validation errors
- GET /medications?family_id= - List active/archived, pagination
- GET /medications/{id} - Get with schedules and photos
- PATCH /medications/{id} - Update fields, schedules
- DELETE /medications/{id} - Archive medication
- POST /medications/{id}/photos - Upload photo
- DELETE /medications/{id}/photos/{photo_id} - Remove photo
- Authorization tests (403 when not family member)
- Validation tests (invalid medication_type, invalid timezone)
- Cache invalidation tests
```

#### 4. Notifications Endpoint Tests (`tests/api/test_notifications.py`)
**Why**: Push notifications are critical for medication reminders and family updates.

```python
# Required tests (25 tests):
- POST /device-token - Register new token
- POST /device-token - Reactivate existing token
- DELETE /device-token - Unregister token
- GET /device-tokens - List active tokens
- POST /test - Send test notification (success, no devices, APNs not configured)
- GET /preferences - Default preferences
- PATCH /preferences - Update preferences (partial, full)
```

#### 5. Family Notifications Service Tests (`tests/services/test_family_notifications.py`)
**Why**: Notification filtering logic is complex and untested.

```python
# Required tests (15 tests):
- get_other_family_member_tokens - excludes triggering user
- get_all_family_member_tokens - includes all members
- get_filtered_family_member_tokens - respects preferences
- get_filtered_family_member_tokens - handles missing preferences (defaults)
- get_filtered_family_member_tokens - unknown notification type fallback
- Empty family handling
- Inactive tokens excluded
```

### Week 2: High Priority (P1)

#### 6. Doses Endpoint Tests (`tests/api/test_doses.py`)
```python
# Required tests (20 tests):
- POST /doses - Record dose
- GET /doses/medication/{id} - List doses with user names
- PATCH /doses/{id} - Update dose
- DELETE /doses/{id} - Delete dose
- GET /doses/all - List all doses for family (pagination)
- Authorization tests
- "You" formatting for current user
```

#### 7. Health Events Tests (`tests/api/test_health.py`)
```python
# Required tests (30 tests):
- POST /health - Create event with photos
- GET /health - List events (pagination, category filter)
- PATCH /health/{id} - Update event
- DELETE /health/{id} - Delete event
- Smart Search integration tests
- Category management
- Photo ordering
```

#### 8. Foods & Feedings Tests (`tests/api/test_foods.py`, `test_feedings.py`)
```python
# Required tests (25 tests):
- CRUD operations
- Calorie calculations
- Cache behavior (foods have 1hr TTL)
- Pagination
```

#### 9. Dashboard Tests (`tests/api/test_dashboard.py`)
```python
# Required tests (15 tests):
- GET /dashboard - Returns all pet data
- Cache hit/miss scenarios
- Data aggregation correctness
- Recent activity filtering
```

#### 10. Auth Tests (`tests/api/test_auth.py`)
```python
# Required tests (20 tests):
- Sign in with Apple flow
- JWT token validation
- Test login endpoint
- Token refresh
- Test cleanup endpoint
```

---

## 5. Contract Testing (iOS Compatibility)

### Purpose
Prevent breaking changes that crash the iOS app by validating:
1. Response schemas match iOS Codable structs
2. snake_case JSON keys (APIClient auto-converts)
3. Optional fields remain optional
4. Date formats are ISO8601
5. Enum values match iOS enums

### Implementation (`tests/contract/test_ios_compatibility.py`)

```python
"""Contract tests to ensure iOS app compatibility."""
import pytest
from datetime import datetime
from app.schemas.medication import MedicationType, MedicationResponse

class TestMedicationContract:
    """Verify medication API contracts don't break iOS app."""

    def test_medication_type_enum_values_match_ios(self):
        """iOS MedicationType enum must match backend."""
        # iOS Swift enum:
        # enum MedicationType: String, Codable {
        #     case drops, pill, inhaler, shot, liquid, tablet, capsule, topical
        # }
        expected_values = {
            "drops", "pill", "inhaler", "shot",
            "liquid", "tablet", "capsule", "topical"
        }
        actual_values = {e.value for e in MedicationType}
        assert actual_values == expected_values, \
            "MedicationType enum mismatch will crash iOS app"

    def test_medication_response_has_required_fields(self):
        """iOS Medication struct requires these fields."""
        # Must not make required fields optional
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            MedicationResponse(
                # Missing required fields
                id=None,  # MUST be present
                pet_id=None,  # MUST be present
            )

    def test_medication_response_json_uses_snake_case(self):
        """iOS APIClient expects snake_case JSON keys."""
        from uuid import uuid4

        med = MedicationResponse(
            id=uuid4(),
            pet_id=uuid4(),
            name="Test",
            medication_type=MedicationType.PILL,
            start_date=datetime.utcnow(),
            times_per_day=1,
            created_at=datetime.utcnow(),
        )

        json_dict = med.model_dump(mode='json')

        # Verify snake_case keys (not camelCase)
        assert "pet_id" in json_dict
        assert "medication_type" in json_dict
        assert "times_per_day" in json_dict
        assert "created_at" in json_dict

        # Verify NO camelCase keys
        assert "petId" not in json_dict
        assert "medicationType" not in json_dict
```

### Contract Test Coverage

Create contract tests for:
- ✅ Medication schemas (MedicationType, MedicationResponse, MedicationCreate)
- ✅ Notification schemas (DeviceTokenResponse, NotificationPreferencesResponse)
- ✅ Pet schemas (PetResponse, PetCreate)
- ✅ Health schemas (HealthEventResponse, HealthCategoryResponse)
- ✅ Dose schemas (DoseDetailResponse, AllDoseDetailResponse)

---

## 6. Database Model Tests

### Purpose
Validate SQLAlchemy models, relationships, and constraints.

### Example (`tests/models/test_medication_models.py`)

```python
"""Tests for medication database models."""
import pytest
from sqlalchemy import select
from app.models.medication import PetMedication, PetMedicationPhoto, MedicationType

@pytest.mark.asyncio
async def test_medication_photo_cascade_delete(db_session, test_pet):
    """Deleting medication should cascade delete photos."""
    # Create medication with photos
    med = PetMedication(
        pet_id=test_pet.id,
        name="Test Med",
        medication_type=MedicationType.PILL,
        start_date=datetime.utcnow(),
    )
    db_session.add(med)
    await db_session.commit()
    await db_session.refresh(med)

    # Add photos
    photo1 = PetMedicationPhoto(
        medication_id=med.id,
        photo_url="https://example.com/1.jpg",
        sort_order=0
    )
    photo2 = PetMedicationPhoto(
        medication_id=med.id,
        photo_url="https://example.com/2.jpg",
        sort_order=1
    )
    db_session.add_all([photo1, photo2])
    await db_session.commit()

    # Delete medication
    await db_session.delete(med)
    await db_session.commit()

    # Verify photos were cascade deleted
    photos = await db_session.execute(
        select(PetMedicationPhoto).where(
            PetMedicationPhoto.medication_id == med.id
        )
    )
    assert photos.scalar_one_or_none() is None

@pytest.mark.asyncio
async def test_medication_photos_ordered_by_sort_order(db_session, test_medication):
    """Photos should be ordered by sort_order."""
    # Add photos out of order
    photo2 = PetMedicationPhoto(medication_id=test_medication.id, photo_url="2.jpg", sort_order=2)
    photo0 = PetMedicationPhoto(medication_id=test_medication.id, photo_url="0.jpg", sort_order=0)
    photo1 = PetMedicationPhoto(medication_id=test_medication.id, photo_url="1.jpg", sort_order=1)

    db_session.add_all([photo2, photo0, photo1])
    await db_session.commit()

    # Query medication with photos
    result = await db_session.execute(
        select(PetMedication)
        .where(PetMedication.id == test_medication.id)
        .options(selectinload(PetMedication.photos))
    )
    med = result.scalar_one()

    # Verify photos are ordered
    assert len(med.photos) == 3
    assert med.photos[0].photo_url == "0.jpg"
    assert med.photos[1].photo_url == "1.jpg"
    assert med.photos[2].photo_url == "2.jpg"
```

### Model Test Coverage

Test for each model:
- Cascade deletes (medication -> photos, doses, schedules)
- Relationship loading (selectinload, joinedload)
- Unique constraints (user_id + device_token)
- Default values (is_active=True, platform="ios")
- Nullable/non-nullable fields
- Foreign key constraints
- Ordering (photos by sort_order)

---

## 7. Test Fixtures & Helpers

### Enhanced `conftest.py`

```python
"""Enhanced fixtures for comprehensive testing."""
import pytest
from datetime import datetime, date
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

# Medication fixtures
@pytest.fixture
def create_mock_medication():
    """Factory fixture to create mock medications."""
    def _create(
        medication_id: str = None,
        pet_id: str = None,
        name: str = "Test Medication",
        medication_type: str = "pill",
        dosage: str = "5mg",
        start_date: datetime = None,
        times_per_day: int = 1,
        reminders_enabled: bool = False,
    ):
        med = MagicMock()
        med.id = medication_id or str(uuid4())
        med.pet_id = pet_id or str(uuid4())
        med.name = name
        med.medication_type = medication_type
        med.dosage = dosage
        med.start_date = start_date or datetime.utcnow()
        med.end_date = None
        med.times_per_day = times_per_day
        med.reminders_enabled = reminders_enabled
        med.is_archived = False
        med.created_at = datetime.utcnow()
        med.photos = []
        med.schedules = []
        return med
    return _create

# Notification fixtures
@pytest.fixture
def create_mock_device_token():
    """Factory fixture to create mock device tokens."""
    def _create(
        user_id: str,
        device_token: str = "mock-device-token-12345",
        is_active: bool = True,
    ):
        token = MagicMock()
        token.id = str(uuid4())
        token.user_id = user_id
        token.device_token = device_token
        token.is_active = is_active
        token.platform = "ios"
        token.created_at = datetime.utcnow()
        return token
    return _create

@pytest.fixture
def create_mock_notification_preferences():
    """Factory fixture to create mock notification preferences."""
    def _create(user_id: str, **overrides):
        prefs = MagicMock()
        prefs.user_id = user_id

        # Defaults (all enabled)
        defaults = {
            "family_member_joined": True,
            "family_role_changed": True,
            "family_member_left": True,
            "family_member_left_promoted": True,
            "family_account_deleted": True,
            "family_account_deleted_promoted": True,
            "pet_added": True,
            "pet_updated": True,
            "pet_deleted": True,
            "medication_created": True,
            "medication_updated": True,
            "medication_archived": True,
        }

        # Apply overrides
        for key, value in {**defaults, **overrides}.items():
            setattr(prefs, key, value)

        return prefs
    return _create

# Mock APNs service
@pytest.fixture
def mock_apns_service():
    """Mock APNS service for testing notifications."""
    mock = MagicMock()
    mock.is_configured = True
    mock.send_to_multiple = AsyncMock(return_value=1)  # 1 device sent
    return mock
```

---

## 8. CI/CD Integration

### GitHub Actions Workflow (`.github/workflows/backend-tests.yml`)

```yaml
name: Backend Tests

on:
  push:
    branches: [main, feature/*, develop]
    paths:
      - 'backend/**'
  pull_request:
    branches: [main]
    paths:
      - 'backend/**'

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python 3.11
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Cache dependencies
        uses: actions/cache@v3
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('backend/requirements.txt') }}

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov httpx

      - name: Run tests with coverage
        env:
          DATABASE_URL: postgresql+asyncpg://test:test@localhost:5432/test
          REDIS_URL: redis://localhost:6379
          JWT_SECRET_KEY: test-secret-key
        run: |
          cd backend
          pytest --cov=app --cov-report=xml --cov-report=term -v

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./backend/coverage.xml
          flags: backend

      - name: Check coverage threshold
        run: |
          cd backend
          coverage report --fail-under=70
```

### Pre-commit Hook (`.git/hooks/pre-commit`)

```bash
#!/bin/bash
# Run tests before allowing commit

cd backend
pytest tests/ -v --tb=short

if [ $? -ne 0 ]; then
    echo "❌ Tests failed. Commit aborted."
    exit 1
fi

echo "✅ Tests passed. Proceeding with commit."
```

### Coverage Requirements

- **Minimum overall coverage**: 70%
- **Critical paths coverage**: 90%
  - Medication endpoints
  - Notification endpoints
  - Auth endpoints
  - Family management
- **Schema validation coverage**: 100%

---

## 9. Testing Dependencies

### Update `requirements.txt`

```txt
# Existing dependencies...

# Testing (add these)
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
pytest-mock>=3.11.0
faker>=19.0.0  # For generating test data
freezegun>=1.2.0  # For mocking datetime
```

### Create `pytest.ini`

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
addopts =
    -v
    --strict-markers
    --tb=short
    --cov=app
    --cov-report=term-missing
    --cov-report=html
markers =
    unit: Unit tests for services and utilities
    integration: Integration tests for API endpoints
    contract: Contract tests for iOS compatibility
    slow: Slow-running tests

# Ignore warnings from third-party libraries
filterwarnings =
    ignore::DeprecationWarning
```

---

## 10. Test Data Management

### Factories for Test Data

```python
# tests/factories.py
"""Test data factories using Faker."""
from datetime import datetime, timedelta
from faker import Faker
from uuid import uuid4

fake = Faker()

class MedicationFactory:
    @staticmethod
    def create_valid_payload(**overrides):
        """Create valid medication creation payload."""
        defaults = {
            "pet_id": str(uuid4()),
            "name": fake.word().title(),
            "medication_type": "pill",
            "dosage": f"{fake.random_int(1, 20)}mg",
            "start_date": datetime.utcnow().isoformat() + "Z",
            "times_per_day": 1,
            "reminders_enabled": False,
        }
        return {**defaults, **overrides}

    @staticmethod
    def create_with_schedules(**overrides):
        """Create medication with scheduled times."""
        payload = MedicationFactory.create_valid_payload(**overrides)
        payload["scheduled_times"] = [
            {"hour": 8, "minute": 0},
            {"hour": 20, "minute": 0}
        ]
        return payload
```

---

## 11. Implementation Roadmap

### Phase 1: Foundation (Week 1, Days 1-2)
- [ ] Setup pytest configuration (`pytest.ini`)
- [ ] Add testing dependencies to `requirements.txt`
- [ ] Enhance `conftest.py` with medication/notification fixtures
- [ ] Create test data factories (`tests/factories.py`)

### Phase 2: Critical Schemas (Week 1, Days 3-4)
- [ ] `test_medication_schemas.py` (30 tests)
- [ ] `test_notification_schemas.py` (20 tests)
- [ ] Contract tests for iOS compatibility (15 tests)

### Phase 3: Critical Endpoints (Week 1, Days 5-7)
- [ ] `test_medications.py` (40 tests)
- [ ] `test_notifications.py` (25 tests)
- [ ] `test_family_notifications.py` service (15 tests)

### Phase 4: Core Features (Week 2, Days 1-3)
- [ ] `test_doses.py` (20 tests)
- [ ] `test_health.py` (30 tests)
- [ ] `test_foods.py` + `test_feedings.py` (25 tests)

### Phase 5: Supporting Features (Week 2, Days 4-5)
- [ ] `test_dashboard.py` (15 tests)
- [ ] `test_auth.py` (20 tests)
- [ ] `test_uploads.py` (10 tests)

### Phase 6: Model & Service Tests (Week 2, Days 6-7)
- [ ] `test_medication_models.py` (20 tests)
- [ ] `test_notification_models.py` (15 tests)
- [ ] `test_apns.py` service (10 tests)
- [ ] `test_storage.py` service (10 tests)

### Phase 7: CI/CD Integration (Week 3, Day 1)
- [ ] GitHub Actions workflow
- [ ] Coverage reporting setup
- [ ] Pre-commit hooks

---

## 12. Best Practices & Guidelines

### Do's ✅

1. **Test behavior, not implementation**
   - Test "user can create medication with photos" not "medication object has photos list"

2. **Use descriptive test names**
   ```python
   # Good
   def test_create_medication_without_family_membership_returns_403():

   # Bad
   def test_medication_error():
   ```

3. **Keep tests isolated**
   - Each test should run independently
   - Use fixtures, not shared state
   - Clean up in teardown

4. **Test edge cases**
   - Null values, empty strings, boundary values
   - Invalid enums, malformed UUIDs
   - Race conditions, concurrent access

5. **Mock external services**
   - Mock APNs service (don't send real push notifications)
   - Mock S3/R2 storage (don't upload real files)
   - Mock OpenAI API (don't make real API calls)

6. **Test error messages**
   ```python
   assert response.status_code == 400
   assert "interval_days must be between 1 and 30" in response.json()["detail"]
   ```

7. **Use parametrize for similar tests**
   ```python
   @pytest.mark.parametrize("medication_type", [
       "drops", "pill", "inhaler", "shot", "liquid", "tablet", "capsule", "topical"
   ])
   def test_medication_type_valid(medication_type):
       ...
   ```

### Don'ts ❌

1. **Don't test third-party libraries**
   - Don't test that SQLAlchemy works
   - Don't test that FastAPI validates UUIDs

2. **Don't use real database in unit tests**
   - Use mocks for database in endpoint tests
   - Use test database only for integration tests

3. **Don't share state between tests**
   ```python
   # Bad
   shared_medication = None

   def test_create():
       global shared_medication
       shared_medication = create_medication()

   def test_update():
       update_medication(shared_medication)  # Depends on test_create
   ```

4. **Don't make tests too complex**
   - If test is hard to understand, refactor into helper
   - One assertion concept per test

5. **Don't skip cleanup**
   - Always invalidate caches in tests
   - Always rollback database changes

---

## 13. Measuring Success

### Key Metrics

1. **Test Coverage**: Target 70% overall, 90% for critical paths
2. **Test Count**: Target 400+ tests total
3. **Build Time**: Keep under 5 minutes for full suite
4. **Flakiness**: 0 flaky tests (tests should pass 100% of time)

### Coverage Targets by Module

| Module | Target Coverage | Current | Priority |
|--------|----------------|---------|----------|
| `app/api/endpoints/medications.py` | 90% | 0% | P0 |
| `app/api/endpoints/notifications.py` | 90% | 0% | P0 |
| `app/services/family_notifications.py` | 95% | 0% | P0 |
| `app/api/endpoints/doses.py` | 85% | 0% | P1 |
| `app/api/endpoints/health.py` | 85% | 0% | P1 |
| `app/api/endpoints/families.py` | 90% | ~70% | P1 |
| `app/schemas/medication.py` | 100% | 0% | P0 |
| `app/schemas/notification.py` | 100% | 0% | P0 |
| `app/models/medication.py` | 100% | 0% | P1 |
| `app/models/notification.py` | 100% | 0% | P1 |

### Weekly Reports

Run weekly coverage reports:
```bash
cd backend
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

Generate coverage badge:
```bash
coverage-badge -o coverage.svg
```

---

## 14. Preventing Breaking Changes - Critical Checklist

Before deploying ANY change that affects the API:

- [ ] **Run full test suite** - `pytest tests/ -v`
- [ ] **Check contract tests** - Verify iOS compatibility tests pass
- [ ] **Review schema changes** - Any field removed? Type changed? Required field added?
- [ ] **Test with iOS app** - Manual smoke test on physical device
- [ ] **Check API versioning** - Breaking change? Needs new version endpoint?
- [ ] **Update documentation** - API docs reflect changes?
- [ ] **Migration tested** - Alembic migration runs without errors?
- [ ] **Cache invalidation** - Caches properly cleared for changed data?

### Schema Change Guidelines

**Safe changes** (non-breaking):
- ✅ Adding optional fields
- ✅ Adding new enum values (append only)
- ✅ Relaxing validations (e.g., increase max_length)
- ✅ Adding new endpoints

**Breaking changes** (requires careful coordination):
- ⚠️ Removing fields
- ⚠️ Renaming fields
- ⚠️ Changing field types
- ⚠️ Making optional fields required
- ⚠️ Removing enum values
- ⚠️ Changing validation rules (stricter)

For breaking changes:
1. Create new endpoint version (`/api/v2/...`)
2. Maintain old endpoint for 2 releases
3. Coordinate iOS app update deployment
4. Deprecation notice in API docs

---

## 15. Resources & References

### Documentation
- [pytest docs](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Pydantic Testing](https://docs.pydantic.dev/latest/concepts/testing/)

### Example Test Files
- `backend/tests/test_families.py` - Excellent example of comprehensive endpoint tests
- `backend/tests/test_pet_schemas.py` - Schema validation testing patterns

### Internal References
- iOS app test suite: `/Orest's Journal/Orest's JournalUITests/`
- API documentation: `http://localhost:8000/docs` (when running)
- Alembic migrations: `backend/alembic/versions/`

---

## Appendix A: Quick Start

```bash
# 1. Install dependencies
cd backend
pip install pytest pytest-asyncio pytest-cov httpx

# 2. Create pytest.ini (copy from section 9)
cat > pytest.ini << 'EOF'
[pytest]
testpaths = tests
...
EOF

# 3. Run existing tests
pytest tests/ -v

# 4. Run with coverage
pytest tests/ --cov=app --cov-report=term-missing

# 5. Run specific test file
pytest tests/test_medications.py -v

# 6. Run tests matching pattern
pytest tests/ -k "medication" -v

# 7. Run with verbose output
pytest tests/ -vv --tb=long
```

---

## Appendix B: Test Template

```python
"""
Tests for [FEATURE] endpoints/schemas/services.

[Brief description of what this test file covers]
"""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.conftest import (
    TEST_FAMILY_ID,
    TEST_USER_ID,
    create_mock_membership,
    create_mock_pet,
)


class Test[FeatureName]:
    """Tests for [specific feature/endpoint]."""

    @pytest.mark.asyncio
    async def test_[scenario]_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """[Description of what this test verifies]."""
        # ARRANGE
        # ... setup test data

        # ACT
        response = await client.post(
            "/api/v1/endpoint",
            json={},
            headers=auth_headers,
        )

        # ASSERT
        assert response.status_code == 200
        data = response.json()
        assert data["field"] == "expected_value"

    @pytest.mark.asyncio
    async def test_[scenario]_validation_error(self, client: AsyncClient):
        """[Description of validation error scenario]."""
        # Test 422 validation error
        ...

    @pytest.mark.asyncio
    async def test_[scenario]_unauthorized(self, client: AsyncClient):
        """[Description of authorization failure scenario]."""
        # Test 401/403 authorization error
        ...
```

---

**Document Version**: 1.0
**Last Updated**: 2024-12-27
**Author**: Claude Code (Sonnet 4.5)
**Review Status**: Draft - Pending Review
