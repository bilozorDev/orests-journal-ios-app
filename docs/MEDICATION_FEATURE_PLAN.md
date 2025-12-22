# Medication Creation & Editing Implementation Plan

## Overview
Implement medication scheduling functionality for pets, allowing users to create and edit medications with flexible scheduling (every N days or as-needed), reminders, and photo attachments.

---

## Requirements Summary

### Core Fields
- **Pet selector** - shown when family has multiple pets
- **Medication name** - required
- **Medication type** - dropdown (DROPS, PILL, INHALER, SHOT, LIQUID, TABLET, CAPSULE, TOPICAL)
- **Dosage** - free text, optional
- **Photos** - up to 3, optional
- **Notes** - optional

### Interval Types
1. **Every N days** (default):
   - N: 1-30 (stepper, default 1)
   - Start date (required)
   - "Has end date" toggle (off by default) → end date picker
   - "Setup reminders" toggle → times per day (1-8) with time pickers

2. **As needed (PRN)**:
   - Start date only (when prescribed)
   - No end date, no reminders

### Family Scope
- All family members receive scheduled reminders
- CRUD notifications sent to other family members (not creator)
- Pet selector shown when family has multiple pets

### Notifications
**CRUD Notifications** (always sent to other family members):
- `medication_created` - when medication is added
- `medication_updated` - when medication is edited
- `medication_archived` - when medication is archived/deleted

**Scheduled Reminders** (existing infrastructure):
- Controlled per-medication by `reminders_enabled` field
- Sent to ALL family members (including creator)

**Notification Preferences** (new section in iOS):
- Add "Medication Updates" toggle group alongside "Family Updates" and "Pet Updates"
- Controls CRUD notifications only (not scheduled reminders)

---

## Implementation Steps

### Phase 1: Backend Schema Updates

**File: `backend/app/models/medication.py`**
- Add `dosage: String` field (nullable)
- Add `interval_days: Integer` field (1-30, nullable for PRN)
- Add `is_as_needed: Boolean` field (default False)

**File: `backend/app/models/medication.py`** (new model)
- Create `PetMedicationPhoto` model:
  ```python
  class PetMedicationPhoto(Base):
      id: UUID
      medication_id: UUID (FK)
      photo_url: String
      sort_order: Integer
      created_at: DateTime
  ```

**File: `backend/app/schemas/medication.py`**
- Update `MedicationCreate` with new fields
- Update `MedicationUpdate` with new fields
- Update `MedicationResponse` with new fields
- Add `MedicationPhotoResponse` schema

**File: `backend/alembic/versions/` (new migration)**
- Add `dosage`, `interval_days`, `is_as_needed` columns to `pet_medications`
- Create `pet_medication_photos` table

### Phase 2: Backend Endpoints

**File: `backend/app/api/endpoints/medications.py`**
- Update `POST /medications` to handle new fields
- Update `PATCH /medications/{id}` to handle new fields
- Validate `interval_days` is 1-30 or null
- Validate `times_per_day` is 1-8
- Clear scheduled times when switching to as-needed

**File: `backend/app/api/endpoints/medications.py`** (new endpoints)
- `POST /medications/{id}/photos` - upload photo (multipart)
- `DELETE /medications/{id}/photos/{photo_id}` - delete photo
- Follow pattern from `health.py` photo endpoints

### Phase 2b: Backend Notifications

**File: `backend/app/models/notification.py`**
- Add to `NotificationPreference` model:
  - `medication_created: Boolean` (default True)
  - `medication_updated: Boolean` (default True)
  - `medication_archived: Boolean` (default True)

**File: `backend/app/services/family_notifications.py`**
- Add to `NOTIFICATION_TYPE_TO_PREF` mapping:
  - `"medication_created": "medication_created"`
  - `"medication_updated": "medication_updated"`
  - `"medication_archived": "medication_archived"`
- Add `notify_family_medication_change(db, medication, user_id, notification_type)` function:
  - Uses `get_filtered_family_member_tokens()` to respect preferences
  - Excludes the user who made the change
  - Sends notification with pet name, medication name

**File: `backend/app/api/endpoints/medications.py`** (add notification calls)
- After `POST /medications`: call `notify_family_medication_change(..., "medication_created")`
- After `PATCH /medications/{id}`: call `notify_family_medication_change(..., "medication_updated")`
- After `DELETE /medications/{id}`: call `notify_family_medication_change(..., "medication_archived")`

**File: `backend/alembic/versions/` (new migration)**
- Add notification preference columns to `notification_preferences` table

### Phase 3: iOS Models

**File: `Orest's Journal/Models/Medication.swift`** (new)
```swift
struct Medication: Codable, Identifiable {
    let id: UUID
    let petId: UUID
    let name: String
    let medicationType: MedicationType
    let dosage: String?
    let intervalDays: Int?
    let isAsNeeded: Bool
    let startDate: Date
    let endDate: Date?
    let timesPerDay: Int?
    let remindersEnabled: Bool
    let timezone: String?
    let notes: String?
    let isArchived: Bool
    let createdBy: UUID
    let createdAt: Date
    var scheduledTimes: [ScheduledTime]?
    var photos: [MedicationPhoto]?
}

enum MedicationType: String, Codable, CaseIterable {
    case drops, pill, inhaler, shot, liquid, tablet, capsule, topical
}

struct ScheduledTime: Codable, Identifiable {
    let id: UUID
    let scheduledHour: Int
    let scheduledMinute: Int
}

struct MedicationPhoto: Codable, Identifiable {
    let id: UUID
    let photoUrl: String
    let sortOrder: Int
}
```

### Phase 4: iOS API Client

**File: `Orest's Journal/APIClient.swift`**
- `getMedications(orgId:petId:activeOnly:)` - list medications
- `getMedication(id:)` - get single medication with schedules
- `createMedication(_:)` - create new medication
- `updateMedication(id:_:)` - update medication
- `deleteMedication(id:)` - archive/delete medication
- `uploadMedicationPhoto(medicationId:imageData:mimeType:)` - upload photo
- `deleteMedicationPhoto(medicationId:photoId:)` - delete photo

### Phase 5: iOS DataService

**File: `Orest's Journal/DataService.swift`**
- Add medication caching (5-min TTL like health events)
- `getMedications(for petId:)` - with stale-while-revalidate
- `createMedication(_:)` - invalidate cache after
- `updateMedication(_:)` - invalidate cache after
- `deleteMedication(_:)` - invalidate cache after
- `invalidateMedicationCache(for petId:)`

### Phase 6: iOS Views

**File: `Orest's Journal/Views/Medications/AddMedicationView.swift`** (new)

Form sections:
1. **Pet Selection** (if multiple pets)
   - Picker with pet names

2. **Basic Info**
   - Name (TextField, required)
   - Type (Picker with MedicationType cases)
   - Dosage (TextField, optional, placeholder: "e.g., 2 tablets, 5ml")

3. **Schedule Type** (Segmented Picker)
   - "Scheduled" / "As Needed"

4. **Schedule Details** (if Scheduled)
   - Interval stepper: "Every [N] day(s)" (1-30)
   - Start date picker
   - "Has end date" toggle → end date picker
   - "Setup reminders" toggle → reminder section

5. **Reminders** (if enabled)
   - Times per day stepper (+/-, 1-8)
   - Time pickers for each time

6. **Start Date** (if As Needed)
   - Single date picker

7. **Photos**
   - Photo grid (reuse pattern from AddHealthEventView)
   - PhotosPicker, max 3

8. **Notes**
   - TextEditor, optional

**File: `Orest's Journal/Views/Medications/MedicationsListView.swift`** (new)
- List of medications for selected pet
- Grouped: Active / Archived
- Tap to view/edit
- Swipe to archive

**File: `Orest's Journal/Views/Medications/MedicationDetailView.swift`** (new)
- View medication details
- Edit button → AddMedicationView in edit mode

### Phase 7: Navigation Integration

**File: `Orest's Journal/ContentView.swift`**
- Replace `PlaceholderView` with `MedicationsListView` for medication tab

**File: `Orest's Journal/NavigationManager.swift`**
- Implement `medication_reminder` notification handling
- Navigate to medication detail on notification tap

---

## Validation Rules

| Field | Rule |
|-------|------|
| Name | Required, non-empty after trim |
| Interval days | 1-30 (when scheduled) |
| Times per day | 1-8 (when reminders enabled) |
| End date | Must be >= start date |
| Scheduled times count | Must match times_per_day |
| Photos | Max 3 |

---

## Edge Cases Handled

### Schedule & Reminders
1. **Switching schedule type**: Clear reminder times when changing to "as needed"
2. **Times per day change**: Add/remove time pickers dynamically
3. **No notification permission**: Show alert when enabling reminders, prompt to settings
4. **Timezone handling**: Store timezone with medication, reminders fire at original local time

### Data & Validation
5. **Duplicate medication name**: Show inline warning "A medication named 'X' already exists for this pet" but allow save
6. **Edit with existing photos**: Support add/delete, preserve existing sort order
7. **Archived medications**: Show in separate section, view-only (no schedule editing)

### Family & Multi-user
8. **Family context**: Pet selector shown only when multiple pets
9. **Race condition (concurrent edits)**: Last write wins (no optimistic locking)
10. **Medication archived while editing**: Save fails, show "Medication not found" error
11. **Stale notification tapped**: Handle gracefully - show error if medication deleted

### Notifications
12. **CRUD notifications**: Always sent to other family members (respects preferences)
13. **Scheduled reminders**: Sent to ALL family members (controlled per-medication)
14. **User leaves family**: Device tokens automatically filtered out by family membership query
15. **Multiple devices**: User receives notification on all their registered devices

---

## Files to Modify/Create

### Backend (modify)
- `backend/app/models/medication.py` - add dosage, interval_days, is_as_needed fields
- `backend/app/models/notification.py` - add medication preference fields
- `backend/app/schemas/medication.py` - update schemas with new fields
- `backend/app/schemas/notification.py` - add medication preference fields
- `backend/app/api/endpoints/medications.py` - new fields, photo endpoints, notification calls
- `backend/app/services/family_notifications.py` - add medication notification function

### Backend (create)
- `backend/alembic/versions/XXX_add_medication_fields.py` - schema changes + preferences

### iOS (create)
- `Orest's Journal/Models/Medication.swift`
- `Orest's Journal/Views/Medications/AddMedicationView.swift`
- `Orest's Journal/Views/Medications/MedicationsListView.swift`
- `Orest's Journal/Views/Medications/MedicationDetailView.swift`

### iOS (modify)
- `Orest's Journal/APIClient.swift` - medication CRUD + photo endpoints
- `Orest's Journal/DataService.swift` - medication caching
- `Orest's Journal/ContentView.swift` - replace placeholder with MedicationsListView
- `Orest's Journal/NavigationManager.swift` - handle medication notifications
- `Orest's Journal/NotificationManager.swift` - cache invalidation for medications
- `Orest's Journal/Views/Settings/NotificationPreferencesView.swift` - add medication section
- `Orest's Journal/Models/NotificationPreferences.swift` - add medication fields

---

## Out of Scope (for this implementation)
- Dose administration/recording (separate feature)
- Medication interaction warnings
- Refill reminders
- Prescription tracking
