# Backend Testing Summary

## Quick Reference

**Current Test Coverage**: ~15% (5 test files, ~50 tests)
**Target Coverage**: 70% overall, 90% for critical paths
**Tests Needed**: ~400 total
**Estimated Effort**: 2 weeks for core coverage

---

## What's Tested ✅

| Area | Test File | Tests | Coverage |
|------|-----------|-------|----------|
| Family Management | `test_families.py` | ~25 | Good |
| Pet CRUD | `test_pets.py` | ~15 | Good |
| Pet Schemas | `test_pet_schemas.py` | ~10 | Good |

**Well-tested scenarios**:
- Family update/role changes
- Brute force protection
- Pet date_of_birth handling
- Pet schema validation

---

## What's NOT Tested ❌

### Critical Gaps (P0 - Will Break iOS App)

1. **Medications** - 0% coverage
   - Recently modified models/schemas
   - Core feature with complex logic
   - iOS app crashes if schemas change

2. **Notifications** - 0% coverage
   - Device token registration
   - Push notification preferences
   - Family notification filtering service
   - APNs integration

3. **API Contracts** - 0% coverage
   - No tests ensuring iOS compatibility
   - Enum value changes will crash app
   - snake_case JSON format unchecked

### High Priority Gaps (P1)

4. **Doses** - 0% coverage
   - Medication dose tracking
   - User name formatting ("You" vs full name)

5. **Health Events** - 0% coverage
   - Recently refactored
   - Smart Search LLM integration
   - Photo management

6. **Foods & Feedings** - 0% coverage
   - Daily-use features
   - Calorie calculations
   - Cache behavior (1hr TTL)

7. **Dashboard** - 0% coverage
   - Main app view
   - Complex data aggregation
   - Caching logic

8. **Auth** - 0% coverage
   - Sign in with Apple
   - JWT validation
   - Test login/cleanup endpoints

---

## Getting Started (5 Minutes)

### 1. Install Dependencies

```bash
cd backend
pip install pytest pytest-asyncio pytest-cov faker freezegun
```

### 2. Run Existing Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=app --cov-report=term-missing

# Run specific test file
pytest tests/test_families.py -v
```

### 3. Run Example Tests (Just Created)

```bash
# Medication schema tests
pytest tests/schemas/test_medication_schemas.py -v

# iOS compatibility contract tests
pytest tests/contract/test_ios_compatibility.py -v
```

---

## Next Steps (Recommended Order)

### This Week: Critical Path (P0)

**Day 1-2**: Setup
- [ ] Review existing test files (`test_families.py`, `test_pets.py`)
- [ ] Run existing tests and ensure they pass
- [ ] Review `TESTING_STRATEGY.md` (comprehensive guide)

**Day 3-4**: Medication Tests
- [ ] Complete `test_medication_schemas.py` (30 tests) - **STARTED**
- [ ] Create `test_medications.py` (40 endpoint tests)
- [ ] Create `test_family_notifications.py` (15 service tests)

**Day 5-7**: Notification Tests
- [ ] Create `test_notification_schemas.py` (20 tests)
- [ ] Create `test_notifications.py` (25 endpoint tests)
- [ ] Complete contract tests - **STARTED** (`test_ios_compatibility.py`)

### Next Week: High Priority (P1)

**Day 1-2**: Doses & Health
- [ ] Create `test_doses.py` (20 tests)
- [ ] Create `test_health.py` (30 tests)

**Day 3-4**: Foods, Feedings, Dashboard
- [ ] Create `test_foods.py` (12 tests)
- [ ] Create `test_feedings.py` (13 tests)
- [ ] Create `test_dashboard.py` (15 tests)

**Day 5**: Auth & Models
- [ ] Create `test_auth.py` (20 tests)
- [ ] Create `test_medication_models.py` (20 tests)

---

## Key Files Created for You

1. **TESTING_STRATEGY.md** - Comprehensive testing guide
   - Testing architecture
   - Best practices
   - Code examples
   - CI/CD integration
   - 15 sections covering everything

2. **TEST_IMPLEMENTATION_CHECKLIST.md** - Detailed task list
   - 400+ specific tests to write
   - Checkboxes to track progress
   - Organized by priority
   - Quick commands reference

3. **pytest.ini** - Pytest configuration
   - Coverage settings
   - Test markers
   - HTML report generation
   - Warning filters

4. **tests/schemas/test_medication_schemas.py** - Example schema tests
   - 30+ medication schema tests
   - Demonstrates testing patterns
   - Ready to run

5. **tests/contract/test_ios_compatibility.py** - iOS contract tests
   - Prevents breaking changes to iOS app
   - Validates enum values, JSON format, field types
   - Critical safety net

---

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_families.py

# Run specific test class
pytest tests/test_families.py::TestUpdateFamily

# Run specific test method
pytest tests/test_families.py::TestUpdateFamily::test_update_family_name_success

# Run tests matching pattern
pytest -k "medication"

# Run tests with specific marker
pytest -m "contract"
```

### Coverage Commands

```bash
# Coverage report in terminal
pytest --cov=app --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=app --cov-report=html
open htmlcov/index.html

# Coverage for specific module
pytest --cov=app.api.endpoints.medications

# Fail if coverage below threshold
pytest --cov=app --cov-fail-under=70
```

### Useful Flags

```bash
# Stop at first failure
pytest -x

# Show 10 slowest tests
pytest --durations=10

# Run tests in parallel (requires pytest-xdist)
pytest -n auto

# Verbose output with full tracebacks
pytest -vv --tb=long

# Quiet mode (less output)
pytest -q
```

---

## Test Patterns (Quick Reference)

### Async Endpoint Test Template

```python
@pytest.mark.asyncio
async def test_endpoint_success(
    client: AsyncClient,
    mock_db_session: AsyncMock,
    auth_headers: dict,
):
    """Description of test."""
    # ARRANGE - Setup mocks
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_data
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    # ACT - Call endpoint
    response = await client.post(
        "/api/v1/endpoint",
        json={"field": "value"},
        headers=auth_headers,
    )

    # ASSERT - Verify response
    assert response.status_code == 201
    data = response.json()
    assert data["field"] == "value"
    mock_db_session.commit.assert_called()
```

### Schema Validation Test Template

```python
def test_schema_validation():
    """Test Pydantic schema validation."""
    # Valid data
    obj = SchemaClass(field="value")
    assert obj.field == "value"

    # Invalid data
    with pytest.raises(ValidationError):
        SchemaClass(field=None)  # Required field
```

### Parametrized Test Template

```python
@pytest.mark.parametrize("value,expected", [
    ("drops", MedicationType.DROPS),
    ("pill", MedicationType.PILL),
    ("inhaler", MedicationType.INHALER),
])
def test_medication_types(value, expected):
    """Test multiple medication types."""
    result = MedicationType(value)
    assert result == expected
```

---

## Common Issues & Solutions

### Issue: Tests fail with "database not found"
**Solution**: Tests use mocked database. Check that `mock_db_session` fixture is being used.

### Issue: Tests fail with "module not found"
**Solution**: Install test dependencies: `pip install pytest pytest-asyncio httpx`

### Issue: Coverage report shows 0%
**Solution**: Run with `--cov=app` flag: `pytest --cov=app`

### Issue: Tests are slow
**Solution**:
1. Check that external services (APNs, S3) are mocked
2. Use `pytest -n auto` for parallel execution
3. Skip slow tests: `pytest -m "not slow"`

### Issue: Fixtures not found
**Solution**: Ensure `conftest.py` is in the `tests/` directory

---

## Test Markers Usage

Tests can be marked and filtered:

```python
@pytest.mark.medication  # Mark as medication test
@pytest.mark.integration  # Mark as integration test
@pytest.mark.slow  # Mark as slow test
@pytest.mark.contract  # Mark as contract test
```

Run only marked tests:
```bash
pytest -m medication  # Only medication tests
pytest -m "integration and not slow"  # Integration but not slow
pytest -m "contract or schema"  # Contract or schema tests
```

---

## CI/CD Integration (Future)

Once core tests are written, add to CI/CD:

1. **GitHub Actions** - Run tests on every push/PR
2. **Coverage Reporting** - Track coverage over time
3. **Contract Tests** - Block PRs that break iOS compatibility
4. **Pre-commit Hooks** - Run tests before committing

See `TESTING_STRATEGY.md` section 8 for GitHub Actions workflow.

---

## Resources

### Documentation
- **TESTING_STRATEGY.md** - Comprehensive testing guide (read this!)
- **TEST_IMPLEMENTATION_CHECKLIST.md** - Specific tests to write
- [pytest docs](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)

### Example Tests
- `tests/test_families.py` - Excellent endpoint test examples
- `tests/test_pet_schemas.py` - Schema validation examples
- `tests/schemas/test_medication_schemas.py` - New schema tests
- `tests/contract/test_ios_compatibility.py` - Contract tests

### Internal
- iOS app tests: `/Orest's Journal/Orest's JournalUITests/`
- API docs (when running): `http://localhost:8000/docs`
- Backend structure: `/Users/alexb/Projects/orests-journal-ios-app/backend/`

---

## Coverage Goals by Module

| Module | Target | Current | Priority |
|--------|--------|---------|----------|
| `medications.py` | 90% | 0% | P0 |
| `notifications.py` | 90% | 0% | P0 |
| `family_notifications.py` | 95% | 0% | P0 |
| `doses.py` | 85% | 0% | P1 |
| `health.py` | 85% | 0% | P1 |
| `schemas/*.py` | 100% | ~20% | P0 |
| `models/*.py` | 100% | 0% | P1 |

---

## Quick Win: Run Your First New Tests

```bash
cd /Users/alexb/Projects/orests-journal-ios-app/backend

# Install dependencies (if needed)
pip install pytest pytest-asyncio pytest-cov

# Run the new medication schema tests
pytest tests/schemas/test_medication_schemas.py -v

# Run the iOS contract tests
pytest tests/contract/test_ios_compatibility.py -v

# Run all tests with coverage
pytest tests/ --cov=app --cov-report=term-missing

# Generate HTML coverage report
pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html
```

---

**Last Updated**: 2024-12-27
**Status**: Ready to implement
**Next Action**: Review `TESTING_STRATEGY.md` and start with medication schema tests
