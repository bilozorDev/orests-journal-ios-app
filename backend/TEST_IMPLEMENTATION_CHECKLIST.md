# Test Implementation Checklist

Priority-ordered list of tests to implement. Check off items as they're completed.

## Setup (Complete First)

- [ ] Install testing dependencies: `pip install pytest pytest-asyncio pytest-cov faker freezegun`
- [ ] Create `backend/pytest.ini` configuration file
- [ ] Enhance `backend/tests/conftest.py` with new fixtures
- [ ] Create `backend/tests/factories.py` for test data generation

## Phase 1: Critical Path - Medications (P0 - CRITICAL)

### Schema Tests (30 tests)
File: `backend/tests/schemas/test_medication_schemas.py`

- [ ] `test_medication_type_enum_all_values_valid()` - Test all 8 enum values
- [ ] `test_medication_type_invalid_value_raises_error()` - Invalid enum
- [ ] `test_medication_create_required_fields_only()` - Minimal valid medication
- [ ] `test_medication_create_with_all_fields()` - Complete medication
- [ ] `test_medication_create_scheduled_times_validation()` - Hour 0-23, minute 0-59
- [ ] `test_medication_create_invalid_hour_raises_error()` - Hour > 23
- [ ] `test_medication_create_invalid_minute_raises_error()` - Minute > 59
- [ ] `test_medication_create_interval_days_range()` - 1-30 validation
- [ ] `test_medication_create_interval_days_below_min()` - < 1 invalid
- [ ] `test_medication_create_interval_days_above_max()` - > 30 invalid
- [ ] `test_medication_create_times_per_day_validation()` - >= 1
- [ ] `test_medication_create_is_as_needed_defaults_false()` - PRN default
- [ ] `test_medication_create_timezone_valid_string()` - Valid timezone
- [ ] `test_medication_update_all_fields_optional()` - Partial updates
- [ ] `test_medication_update_single_field()` - Update one field
- [ ] `test_medication_update_scheduled_times()` - Replace schedules
- [ ] `test_medication_response_serialization()` - Model to JSON
- [ ] `test_medication_response_is_active_property()` - Computed field logic
- [ ] `test_medication_response_is_active_before_start()` - Not started
- [ ] `test_medication_response_is_active_after_end()` - Ended
- [ ] `test_medication_response_is_active_no_end_date()` - Ongoing
- [ ] `test_medication_with_schedules_includes_times()` - Nested schedules
- [ ] `test_medication_with_schedules_includes_photos()` - Nested photos
- [ ] `test_medication_photo_response_fields()` - Photo schema
- [ ] `test_scheduled_time_create_validation()` - Schedule schema
- [ ] `test_scheduled_time_response_fields()` - Schedule response
- [ ] `test_dose_create_defaults_given_at_to_now()` - Default timestamp
- [ ] `test_dose_response_fields()` - Dose schema
- [ ] `test_dose_detail_response_formatted_user_name()` - User name formatting
- [ ] `test_all_dose_detail_includes_medication_info()` - Joined data

### Endpoint Tests (40 tests)
File: `backend/tests/api/test_medications.py`

**POST /medications - Create (12 tests)**
- [ ] `test_create_medication_minimal_success()` - Required fields only
- [ ] `test_create_medication_with_all_fields_success()` - Complete medication
- [ ] `test_create_medication_with_scheduled_times()` - With reminders
- [ ] `test_create_medication_prn_without_interval()` - As-needed medication
- [ ] `test_create_medication_scheduled_with_interval()` - Regular schedule
- [ ] `test_create_medication_invalid_medication_type_422()` - Bad enum
- [ ] `test_create_medication_invalid_interval_range_422()` - Out of range
- [ ] `test_create_medication_invalid_timezone_422()` - Invalid timezone
- [ ] `test_create_medication_not_family_member_403()` - No access
- [ ] `test_create_medication_pet_not_found_404()` - Invalid pet_id
- [ ] `test_create_medication_missing_org_id_422()` - No org_id param
- [ ] `test_create_medication_no_auth_401()` - No token

**GET /medications?org_id= - List (8 tests)**
- [ ] `test_list_medications_active_only()` - Excludes archived
- [ ] `test_list_medications_include_archived()` - With archived flag
- [ ] `test_list_medications_filtered_by_pet()` - Pet filter
- [ ] `test_list_medications_empty_list()` - No medications
- [ ] `test_list_medications_cache_hit()` - Returns cached
- [ ] `test_list_medications_cache_miss()` - Queries DB
- [ ] `test_list_medications_not_family_member_403()` - No access
- [ ] `test_list_medications_no_auth_401()` - No token

**GET /medications/{id} - Get Single (6 tests)**
- [ ] `test_get_medication_with_schedules_and_photos()` - Complete data
- [ ] `test_get_medication_without_schedules()` - No reminders
- [ ] `test_get_medication_not_found_404()` - Invalid ID
- [ ] `test_get_medication_not_family_member_403()` - No access
- [ ] `test_get_medication_invalid_uuid_422()` - Malformed ID
- [ ] `test_get_medication_no_auth_401()` - No token

**PATCH /medications/{id} - Update (8 tests)**
- [ ] `test_update_medication_name_success()` - Update single field
- [ ] `test_update_medication_multiple_fields()` - Update several
- [ ] `test_update_medication_scheduled_times()` - Update reminders
- [ ] `test_update_medication_clear_end_date()` - Set to null
- [ ] `test_update_medication_cache_invalidated()` - Cache cleared
- [ ] `test_update_medication_not_found_404()` - Invalid ID
- [ ] `test_update_medication_not_family_member_403()` - No access
- [ ] `test_update_medication_no_auth_401()` - No token

**DELETE /medications/{id} - Archive (6 tests)**
- [ ] `test_archive_medication_success()` - Soft delete
- [ ] `test_archive_medication_already_archived()` - Idempotent
- [ ] `test_archive_medication_cache_invalidated()` - Cache cleared
- [ ] `test_archive_medication_not_found_404()` - Invalid ID
- [ ] `test_archive_medication_not_family_member_403()` - No access
- [ ] `test_archive_medication_no_auth_401()` - No token

## Phase 2: Critical Path - Notifications (P0 - CRITICAL)

### Schema Tests (20 tests)
File: `backend/tests/schemas/test_notification_schemas.py`

- [ ] `test_device_token_create_required_fields()` - Token required
- [ ] `test_device_token_create_optional_device_name()` - Name optional
- [ ] `test_device_token_response_all_fields()` - Complete response
- [ ] `test_device_token_delete_validation()` - Delete schema
- [ ] `test_notification_preferences_update_all_optional()` - Partial updates
- [ ] `test_notification_preferences_update_single_field()` - One field
- [ ] `test_notification_preferences_update_all_fields()` - All fields
- [ ] `test_notification_preferences_response_defaults()` - All True
- [ ] `test_notification_preferences_family_fields()` - 6 family prefs
- [ ] `test_notification_preferences_pet_fields()` - 3 pet prefs
- [ ] `test_notification_preferences_medication_fields()` - 3 medication prefs
- [ ] `test_schedule_set_request_validation()` - Schedule list
- [ ] `test_schedule_response_format()` - Schedule response
- [ ] `test_notification_log_response_fields()` - Log schema
- [ ] `test_notification_log_response_recipient_count()` - Count field
- [ ] `test_notification_preferences_boolean_validation()` - Only bool
- [ ] `test_device_token_platform_default_ios()` - Platform field
- [ ] `test_device_token_is_active_default_true()` - Active field
- [ ] `test_notification_type_validation()` - Type enum
- [ ] `test_scheduled_time_validation()` - Time format

### Endpoint Tests (25 tests)
File: `backend/tests/api/test_notifications.py`

**POST /device-token - Register (8 tests)**
- [ ] `test_register_device_token_new_success()` - New token
- [ ] `test_register_device_token_reactivate_existing()` - Existing token
- [ ] `test_register_device_token_update_device_name()` - Update name
- [ ] `test_register_device_token_with_device_name()` - Include name
- [ ] `test_register_device_token_without_device_name()` - Omit name
- [ ] `test_register_device_token_duplicate_idempotent()` - Same token
- [ ] `test_register_device_token_missing_token_422()` - No token
- [ ] `test_register_device_token_no_auth_401()` - No auth

**DELETE /device-token - Unregister (4 tests)**
- [ ] `test_unregister_device_token_success()` - Mark inactive
- [ ] `test_unregister_device_token_not_found_success()` - Idempotent
- [ ] `test_unregister_device_token_already_inactive()` - Already inactive
- [ ] `test_unregister_device_token_no_auth_401()` - No auth

**GET /device-tokens - List (3 tests)**
- [ ] `test_list_device_tokens_success()` - Active only
- [ ] `test_list_device_tokens_empty()` - No tokens
- [ ] `test_list_device_tokens_no_auth_401()` - No auth

**POST /test - Test Notification (5 tests)**
- [ ] `test_send_test_notification_success()` - Send to devices
- [ ] `test_send_test_notification_custom_message()` - Custom text
- [ ] `test_send_test_notification_no_devices_404()` - No registered
- [ ] `test_send_test_notification_apns_not_configured_503()` - APNs down
- [ ] `test_send_test_notification_no_auth_401()` - No auth

**GET /preferences - Get Preferences (2 tests)**
- [ ] `test_get_notification_preferences_exists()` - Has prefs
- [ ] `test_get_notification_preferences_defaults()` - No prefs

**PATCH /preferences - Update Preferences (3 tests)**
- [ ] `test_update_notification_preferences_create_new()` - Upsert
- [ ] `test_update_notification_preferences_partial_update()` - Some fields
- [ ] `test_update_notification_preferences_all_fields()` - All fields

### Service Tests (15 tests)
File: `backend/tests/services/test_family_notifications.py`

- [ ] `test_get_other_family_member_tokens_excludes_user()` - Exclude sender
- [ ] `test_get_other_family_member_tokens_includes_others()` - Include family
- [ ] `test_get_other_family_member_tokens_empty_family()` - No members
- [ ] `test_get_other_family_member_tokens_only_active()` - Active only
- [ ] `test_get_all_family_member_tokens_includes_all()` - All members
- [ ] `test_get_all_family_member_tokens_empty()` - Empty family
- [ ] `test_get_filtered_tokens_respects_preferences()` - Filter by pref
- [ ] `test_get_filtered_tokens_disabled_pref_excluded()` - Disabled user
- [ ] `test_get_filtered_tokens_no_prefs_included()` - Default enabled
- [ ] `test_get_filtered_tokens_unknown_type_fallback()` - Unknown type
- [ ] `test_get_filtered_tokens_multiple_devices_per_user()` - Multi device
- [ ] `test_get_filtered_tokens_inactive_excluded()` - Inactive tokens
- [ ] `test_notification_type_to_pref_mapping()` - Correct mapping
- [ ] `test_notification_type_to_pref_all_types()` - All 12 types
- [ ] `test_family_notification_service_integration()` - Full flow

## Phase 3: Contract Tests (P0 - CRITICAL)

File: `backend/tests/contract/test_ios_compatibility.py`

### Medication Contracts (10 tests)
- [ ] `test_medication_type_enum_matches_ios()` - Enum values
- [ ] `test_medication_response_required_fields()` - Required fields
- [ ] `test_medication_response_snake_case_keys()` - JSON format
- [ ] `test_medication_create_accepts_iso8601_dates()` - Date parsing
- [ ] `test_medication_response_date_format_iso8601()` - Date output
- [ ] `test_medication_photo_response_snake_case()` - Photo format
- [ ] `test_scheduled_time_response_snake_case()` - Schedule format
- [ ] `test_dose_response_given_by_is_uuid()` - UUID format
- [ ] `test_medication_optional_fields_nullable()` - Nullable fields
- [ ] `test_medication_is_active_computed_property()` - Derived field

### Notification Contracts (5 tests)
- [ ] `test_device_token_response_snake_case()` - JSON format
- [ ] `test_notification_preferences_boolean_types()` - Bool not int
- [ ] `test_notification_preferences_all_fields_present()` - Complete
- [ ] `test_notification_log_datetime_iso8601()` - Date format
- [ ] `test_test_notification_response_format()` - Test endpoint

## Phase 4: High Priority - Doses (P1)

File: `backend/tests/api/test_doses.py`

### Endpoint Tests (20 tests)
- [ ] `test_record_dose_success()` - Create dose
- [ ] `test_record_dose_with_notes()` - Include notes
- [ ] `test_record_dose_custom_timestamp()` - Past time
- [ ] `test_record_dose_defaults_to_now()` - Default time
- [ ] `test_record_dose_cache_invalidated()` - Cache cleared
- [ ] `test_record_dose_medication_not_found_404()` - Invalid med
- [ ] `test_record_dose_not_family_member_403()` - No access
- [ ] `test_list_doses_for_medication()` - Get list
- [ ] `test_list_doses_user_name_formatting()` - "You" for current
- [ ] `test_list_doses_pagination()` - Limit works
- [ ] `test_list_doses_ordered_desc()` - Newest first
- [ ] `test_list_doses_empty()` - No doses
- [ ] `test_update_dose_timestamp()` - Edit time
- [ ] `test_update_dose_notes()` - Edit notes
- [ ] `test_update_dose_not_found_404()` - Invalid dose
- [ ] `test_delete_dose_success()` - Remove dose
- [ ] `test_delete_dose_not_found_404()` - Invalid dose
- [ ] `test_list_all_doses_org()` - All pets
- [ ] `test_list_all_doses_pagination()` - Pagination
- [ ] `test_list_all_doses_includes_pet_info()` - Pet data

## Phase 5: High Priority - Health Events (P1)

File: `backend/tests/api/test_health.py`

### Endpoint Tests (30 tests)
- [ ] `test_create_health_event_success()` - Basic create
- [ ] `test_create_health_event_with_photos()` - With images
- [ ] `test_create_health_event_with_category()` - Categorized
- [ ] `test_create_health_event_with_notes()` - With notes
- [ ] `test_create_health_event_custom_timestamp()` - Past event
- [ ] `test_list_health_events_pagination()` - Paging works
- [ ] `test_list_health_events_category_filter()` - Filter by cat
- [ ] `test_list_health_events_date_range_filter()` - Date filter
- [ ] `test_list_health_events_ordered_desc()` - Newest first
- [ ] `test_get_health_event_with_photos()` - Include photos
- [ ] `test_get_health_event_photo_ordering()` - sort_order
- [ ] `test_update_health_event_title()` - Edit title
- [ ] `test_update_health_event_add_photos()` - Add images
- [ ] `test_update_health_event_remove_photos()` - Remove images
- [ ] `test_delete_health_event_success()` - Delete event
- [ ] `test_delete_health_event_cascade_photos()` - Photos deleted
- [ ] `test_create_category_success()` - New category
- [ ] `test_list_categories_for_org()` - Get categories
- [ ] `test_update_category_name()` - Edit category
- [ ] `test_delete_category_success()` - Remove category
- [ ] `test_delete_category_with_events_fails()` - Has events
- [ ] `test_smart_search_llm_parsing()` - AI search
- [ ] `test_smart_search_date_extraction()` - Date parsing
- [ ] `test_smart_search_multi_pet()` - Multiple pets
- [ ] `test_health_event_cache_invalidation()` - Cache cleared
- [ ] `test_health_event_not_family_member_403()` - No access
- [ ] `test_health_event_pet_not_found_404()` - Invalid pet
- [ ] `test_health_photo_upload_success()` - Upload photo
- [ ] `test_health_photo_delete_success()` - Delete photo
- [ ] `test_health_photo_reorder_success()` - Change order

## Phase 6: Foods & Feedings (P1)

### Foods Tests (12 tests)
File: `backend/tests/api/test_foods.py`

- [ ] `test_create_food_success()` - Create food
- [ ] `test_list_foods_for_org()` - Get org foods
- [ ] `test_list_foods_cache_hit()` - 1hr cache
- [ ] `test_update_food_calories()` - Edit nutrition
- [ ] `test_delete_food_success()` - Delete food
- [ ] `test_delete_food_with_feedings_fails()` - Has feedings
- [ ] `test_food_validation_name_required()` - Name required
- [ ] `test_food_validation_calories_positive()` - Calories > 0
- [ ] `test_food_not_family_member_403()` - No access
- [ ] `test_food_not_found_404()` - Invalid ID
- [ ] `test_food_cache_invalidation()` - Cache cleared
- [ ] `test_food_duplicate_name_allowed()` - Same name OK

### Feedings Tests (13 tests)
File: `backend/tests/api/test_feedings.py`

- [ ] `test_record_feeding_success()` - Create feeding
- [ ] `test_record_feeding_with_custom_amount()` - Amount field
- [ ] `test_list_feedings_for_pet()` - Get pet feedings
- [ ] `test_list_feedings_date_range()` - Filter dates
- [ ] `test_list_feedings_pagination()` - Limit works
- [ ] `test_update_feeding_amount()` - Edit amount
- [ ] `test_delete_feeding_success()` - Delete feeding
- [ ] `test_feeding_calorie_calculation()` - Auto calculate
- [ ] `test_feeding_cache_invalidation()` - Cache cleared
- [ ] `test_calorie_goal_get()` - Get goal
- [ ] `test_calorie_goal_set()` - Set goal
- [ ] `test_calorie_goal_update()` - Update goal
- [ ] `test_feeding_not_family_member_403()` - No access

## Phase 7: Dashboard & Auth (P1)

### Dashboard Tests (15 tests)
File: `backend/tests/api/test_dashboard.py`

- [ ] `test_get_dashboard_complete_data()` - All sections
- [ ] `test_get_dashboard_recent_medications()` - Med section
- [ ] `test_get_dashboard_recent_feedings()` - Food section
- [ ] `test_get_dashboard_recent_health()` - Health section
- [ ] `test_get_dashboard_cache_hit()` - Returns cached
- [ ] `test_get_dashboard_cache_miss()` - Queries DB
- [ ] `test_get_dashboard_cache_ttl()` - Cache expiry
- [ ] `test_get_dashboard_empty_pet()` - No data
- [ ] `test_get_dashboard_aggregation()` - Correct counts
- [ ] `test_get_dashboard_date_filtering()` - Recent only
- [ ] `test_get_dashboard_not_family_member_403()` - No access
- [ ] `test_get_dashboard_pet_not_found_404()` - Invalid pet
- [ ] `test_dashboard_medication_status()` - Active/archived
- [ ] `test_dashboard_calorie_tracking()` - Goal vs actual
- [ ] `test_dashboard_performance()` - Response time

### Auth Tests (20 tests)
File: `backend/tests/api/test_auth.py`

- [ ] `test_sign_in_with_apple_success()` - SIWA flow
- [ ] `test_sign_in_with_apple_new_user()` - Create user
- [ ] `test_sign_in_with_apple_existing_user()` - Return user
- [ ] `test_sign_in_with_apple_invalid_token_401()` - Bad token
- [ ] `test_jwt_token_generation()` - Create JWT
- [ ] `test_jwt_token_validation()` - Verify JWT
- [ ] `test_jwt_token_expired_401()` - Expired token
- [ ] `test_jwt_token_invalid_signature_401()` - Bad signature
- [ ] `test_get_current_user_valid_token()` - Extract user
- [ ] `test_get_current_user_no_token_401()` - No auth
- [ ] `test_get_current_user_invalid_token_401()` - Invalid
- [ ] `test_test_login_creates_user()` - Test endpoint
- [ ] `test_test_login_returns_token()` - Test token
- [ ] `test_test_cleanup_deletes_user()` - Cleanup endpoint
- [ ] `test_test_cleanup_cascade_deletes()` - Delete related
- [ ] `test_user_creation_validation()` - Email required
- [ ] `test_user_duplicate_apple_id_fails()` - Unique constraint
- [ ] `test_clerk_jwt_validation()` - Clerk integration
- [ ] `test_auth_header_format()` - Bearer token
- [ ] `test_auth_middleware_flow()` - Full auth flow

## Phase 8: Model Tests (P1)

### Medication Models (20 tests)
File: `backend/tests/models/test_medication_models.py`

- [ ] `test_medication_cascade_delete_photos()` - Photos deleted
- [ ] `test_medication_cascade_delete_doses()` - Doses deleted
- [ ] `test_medication_cascade_delete_schedules()` - Schedules deleted
- [ ] `test_medication_cascade_delete_logs()` - Logs deleted
- [ ] `test_medication_photo_ordering()` - sort_order works
- [ ] `test_medication_pet_relationship()` - FK to pet
- [ ] `test_medication_created_by_null_on_user_delete()` - SET NULL
- [ ] `test_medication_type_enum_constraint()` - Valid types only
- [ ] `test_medication_defaults()` - Default values
- [ ] `test_medication_nullable_fields()` - Null allowed
- [ ] `test_medication_schedule_unique_constraint()` - Unique times
- [ ] `test_medication_schedule_hour_range()` - 0-23
- [ ] `test_medication_schedule_minute_range()` - 0-59
- [ ] `test_medication_dose_given_by_null_on_delete()` - SET NULL
- [ ] `test_medication_dose_timestamp_default()` - Default now
- [ ] `test_medication_photo_cascade_delete()` - Delete with med
- [ ] `test_notification_log_unique_constraint()` - No duplicates
- [ ] `test_notification_log_cascade_delete()` - Delete with med
- [ ] `test_medication_timezone_default_utc()` - Default TZ
- [ ] `test_medication_is_archived_default_false()` - Default active

### Notification Models (15 tests)
File: `backend/tests/models/test_notification_models.py`

- [ ] `test_device_token_user_relationship()` - FK to user
- [ ] `test_device_token_cascade_delete()` - Delete with user
- [ ] `test_device_token_defaults()` - Default values
- [ ] `test_device_token_platform_default_ios()` - Default platform
- [ ] `test_device_token_is_active_default_true()` - Default active
- [ ] `test_device_token_updated_at_auto()` - Auto timestamp
- [ ] `test_notification_preference_user_unique()` - One per user
- [ ] `test_notification_preference_cascade_delete()` - Delete with user
- [ ] `test_notification_preference_defaults_all_true()` - Defaults
- [ ] `test_notification_preference_boolean_fields()` - All bool
- [ ] `test_notification_preference_updated_at_auto()` - Auto timestamp
- [ ] `test_medication_schedule_relationship()` - FK to medication
- [ ] `test_medication_schedule_cascade_delete()` - Delete with med
- [ ] `test_notification_log_medication_relationship()` - FK to med
- [ ] `test_notification_log_recipient_count_default()` - Default 0

## Phase 9: Service Unit Tests (P2)

### APNS Service (10 tests)
File: `backend/tests/services/test_apns.py`

- [ ] `test_apns_send_single_success()` - Send one notification
- [ ] `test_apns_send_multiple_success()` - Send to multiple
- [ ] `test_apns_send_invalid_token_removes()` - Remove invalid
- [ ] `test_apns_not_configured_returns_false()` - Config check
- [ ] `test_apns_connection_error_handled()` - Network error
- [ ] `test_apns_notification_payload_format()` - Correct format
- [ ] `test_apns_badge_count()` - Badge number
- [ ] `test_apns_sound_default()` - Default sound
- [ ] `test_apns_custom_data()` - Custom payload
- [ ] `test_apns_retry_logic()` - Retry on failure

### Storage Service (10 tests)
File: `backend/tests/services/test_storage.py`

- [ ] `test_upload_file_success()` - Upload to R2
- [ ] `test_upload_file_generates_key()` - Unique key
- [ ] `test_upload_file_sets_content_type()` - MIME type
- [ ] `test_upload_file_returns_url()` - Public URL
- [ ] `test_delete_file_success()` - Delete from R2
- [ ] `test_delete_file_not_found_silent()` - Idempotent
- [ ] `test_list_files_pagination()` - List objects
- [ ] `test_storage_not_configured_raises()` - Config check
- [ ] `test_upload_file_size_limit()` - Max size
- [ ] `test_upload_file_extension_validation()` - Allowed types

## Phase 10: Uploads Endpoint (P2)

File: `backend/tests/api/test_uploads.py`

- [ ] `test_upload_pet_photo_success()` - Upload image
- [ ] `test_upload_medication_photo_success()` - Med image
- [ ] `test_upload_health_photo_success()` - Health image
- [ ] `test_upload_file_too_large_413()` - Size limit
- [ ] `test_upload_invalid_file_type_422()` - Wrong type
- [ ] `test_upload_not_family_member_403()` - No access
- [ ] `test_delete_photo_success()` - Delete image
- [ ] `test_delete_photo_not_owner_403()` - Not owner
- [ ] `test_upload_generates_unique_filename()` - No collision
- [ ] `test_upload_sets_correct_content_type()` - MIME type

---

## Progress Tracking

**Total Tests Planned**: ~400
**Tests Completed**: 0 / 400
**Coverage Target**: 70% overall, 90% critical paths
**Current Coverage**: ~15%

### By Priority
- **P0 (Critical)**: 0 / 115 tests
- **P1 (High)**: 0 / 225 tests
- **P2 (Medium)**: 0 / 60 tests

### By Type
- **Schema Tests**: 0 / 50
- **Endpoint Tests**: 0 / 250
- **Service Tests**: 0 / 40
- **Model Tests**: 0 / 35
- **Contract Tests**: 0 / 15
- **Utility Tests**: 0 / 10

---

## Quick Commands

```bash
# Run all tests
pytest tests/ -v

# Run specific priority
pytest tests/schemas/test_medication_schemas.py -v  # P0

# Run with coverage
pytest tests/ --cov=app --cov-report=term-missing

# Run only unchecked tests (example)
pytest tests/schemas/ -v

# Watch mode (requires pytest-watch)
ptw tests/ -- -v
```

---

**Last Updated**: 2024-12-27
**Completion Target**: 2 weeks (by 2025-01-10)
