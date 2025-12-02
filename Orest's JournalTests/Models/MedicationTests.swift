//
//  MedicationTests.swift
//  Orest's JournalTests
//
//  Unit tests for Medication model and related types.
//

import XCTest
@testable import Orest_s_Journal

final class MedicationTests: XCTestCase {

    // MARK: - MedicationType Tests

    func testMedicationTypeDisplayName() {
        XCTAssertEqual(MedicationType.drops.displayName, "Drops")
        XCTAssertEqual(MedicationType.pill.displayName, "Pill")
        XCTAssertEqual(MedicationType.inhaler.displayName, "Inhaler")
        XCTAssertEqual(MedicationType.shot.displayName, "Shot")
        XCTAssertEqual(MedicationType.liquid.displayName, "Liquid")
        XCTAssertEqual(MedicationType.tablet.displayName, "Tablet")
        XCTAssertEqual(MedicationType.capsule.displayName, "Capsule")
        XCTAssertEqual(MedicationType.topical.displayName, "Topical")
    }

    func testMedicationTypeRawValue() {
        XCTAssertEqual(MedicationType.drops.rawValue, "drops")
        XCTAssertEqual(MedicationType.pill.rawValue, "pill")
        XCTAssertEqual(MedicationType.tablet.rawValue, "tablet")
    }

    // MARK: - ScheduledTime Tests

    func testScheduledTimeDisplayTimeMorning() {
        let time = ScheduledTime(
            id: UUID(),
            medicationId: UUID(),
            scheduledHour: 8,
            scheduledMinute: 0
        )

        XCTAssertEqual(time.displayTime, "8 AM")
    }

    func testScheduledTimeDisplayTimeAfternoon() {
        let time = ScheduledTime(
            id: UUID(),
            medicationId: UUID(),
            scheduledHour: 14,
            scheduledMinute: 30
        )

        XCTAssertEqual(time.displayTime, "2:30 PM")
    }

    func testScheduledTimeDisplayTimeNoon() {
        let time = ScheduledTime(
            id: UUID(),
            medicationId: UUID(),
            scheduledHour: 12,
            scheduledMinute: 0
        )

        XCTAssertEqual(time.displayTime, "12 PM")
    }

    func testScheduledTimeDisplayTimeMidnight() {
        let time = ScheduledTime(
            id: UUID(),
            medicationId: UUID(),
            scheduledHour: 0,
            scheduledMinute: 0
        )

        XCTAssertEqual(time.displayTime, "12 AM")
    }

    func testScheduledTimeDisplayTimeWithMinutes() {
        let time = ScheduledTime(
            id: UUID(),
            medicationId: UUID(),
            scheduledHour: 9,
            scheduledMinute: 15
        )

        XCTAssertEqual(time.displayTime, "9:15 AM")
    }

    func testScheduledTimeDisplayTimeSingleDigitMinute() {
        let time = ScheduledTime(
            id: UUID(),
            medicationId: UUID(),
            scheduledHour: 10,
            scheduledMinute: 5
        )

        XCTAssertEqual(time.displayTime, "10:05 AM")
    }

    // MARK: - PetMedication isActive Tests

    func testIsActiveWithNoEndDate() {
        let medication = createMedication(
            startDate: Date().addingTimeInterval(-86400), // Yesterday
            endDate: nil
        )

        XCTAssertTrue(medication.isActive)
    }

    func testIsActiveWithFutureEndDate() {
        let medication = createMedication(
            startDate: Date().addingTimeInterval(-86400), // Yesterday
            endDate: Date().addingTimeInterval(86400 * 7) // 7 days from now
        )

        XCTAssertTrue(medication.isActive)
    }

    func testIsActiveWithPastEndDate() {
        let medication = createMedication(
            startDate: Date().addingTimeInterval(-86400 * 10), // 10 days ago
            endDate: Date().addingTimeInterval(-86400) // Yesterday
        )

        XCTAssertFalse(medication.isActive)
    }

    func testIsActiveWithFutureStartDate() {
        let medication = createMedication(
            startDate: Date().addingTimeInterval(86400), // Tomorrow
            endDate: nil
        )

        XCTAssertFalse(medication.isActive)
    }

    func testIsActiveOnStartDate() {
        let today = Calendar.current.startOfDay(for: Date())
        let medication = createMedication(
            startDate: today,
            endDate: nil
        )

        XCTAssertTrue(medication.isActive)
    }

    func testIsActiveOnEndDate() {
        let today = Calendar.current.startOfDay(for: Date())
        let medication = createMedication(
            startDate: today.addingTimeInterval(-86400), // Yesterday
            endDate: today
        )

        XCTAssertTrue(medication.isActive)
    }

    // MARK: - JSON Decoding Tests

    func testDecodingFromJSON() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "pet_id": "660e8400-e29b-41d4-a716-446655440001",
            "name": "Antibiotics",
            "medication_type": "pill",
            "start_date": "2024-01-15T00:00:00Z",
            "end_date": "2024-01-22T00:00:00Z",
            "times_per_day": 2,
            "notes": "Give with food",
            "reminders_enabled": true,
            "timezone": "America/New_York",
            "is_archived": false,
            "created_at": "2024-01-15T10:30:00Z",
            "created_by": "user-123",
            "scheduled_times": [
                {
                    "id": "770e8400-e29b-41d4-a716-446655440002",
                    "medication_id": "550e8400-e29b-41d4-a716-446655440000",
                    "scheduled_hour": 8,
                    "scheduled_minute": 0
                },
                {
                    "id": "880e8400-e29b-41d4-a716-446655440003",
                    "medication_id": "550e8400-e29b-41d4-a716-446655440000",
                    "scheduled_hour": 20,
                    "scheduled_minute": 0
                }
            ]
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let medication = try decoder.decode(PetMedication.self, from: json)

        XCTAssertEqual(medication.name, "Antibiotics")
        XCTAssertEqual(medication.medicationType, .pill)
        XCTAssertEqual(medication.timesPerDay, 2)
        XCTAssertEqual(medication.notes, "Give with food")
        XCTAssertTrue(medication.remindersEnabled)
        XCTAssertEqual(medication.timezone, "America/New_York")
        XCTAssertEqual(medication.scheduledTimes?.count, 2)
    }

    func testDecodingWithDefaultValues() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "pet_id": "660e8400-e29b-41d4-a716-446655440001",
            "name": "Eye Drops",
            "medication_type": "drops",
            "start_date": "2024-01-15T00:00:00Z",
            "times_per_day": 3,
            "created_at": "2024-01-15T10:30:00Z"
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let medication = try decoder.decode(PetMedication.self, from: json)

        // Test default values from custom decoder
        XCTAssertFalse(medication.remindersEnabled) // Default false
        XCTAssertFalse(medication.isArchived) // Default false
        XCTAssertEqual(medication.timezone, TimeZone.current.identifier) // Default current timezone
        XCTAssertNil(medication.endDate)
        XCTAssertNil(medication.notes)
        XCTAssertNil(medication.scheduledTimes)
    }

    // MARK: - Helper Methods

    private func createMedication(startDate: Date, endDate: Date?) -> PetMedication {
        PetMedication(
            id: UUID(),
            petId: UUID(),
            name: "Test Medication",
            medicationType: .pill,
            startDate: startDate,
            endDate: endDate,
            timesPerDay: 1,
            notes: nil,
            remindersEnabled: false,
            timezone: TimeZone.current.identifier,
            isArchived: false,
            createdAt: Date(),
            createdBy: nil,
            scheduledTimes: nil
        )
    }
}
