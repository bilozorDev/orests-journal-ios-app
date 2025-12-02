//
//  MedicationTypeTests.swift
//  Orest's JournalTests
//
//  Unit tests for MedicationType enum.
//

import XCTest
@testable import Orest_s_Journal

final class MedicationTypeTests: XCTestCase {

    // MARK: - Raw Value Tests

    func testRawValues() {
        XCTAssertEqual(MedicationType.drops.rawValue, "drops")
        XCTAssertEqual(MedicationType.pill.rawValue, "pill")
        XCTAssertEqual(MedicationType.inhaler.rawValue, "inhaler")
        XCTAssertEqual(MedicationType.shot.rawValue, "shot")
        XCTAssertEqual(MedicationType.liquid.rawValue, "liquid")
        XCTAssertEqual(MedicationType.tablet.rawValue, "tablet")
        XCTAssertEqual(MedicationType.capsule.rawValue, "capsule")
        XCTAssertEqual(MedicationType.topical.rawValue, "topical")
    }

    func testInitFromRawValue() {
        XCTAssertEqual(MedicationType(rawValue: "drops"), .drops)
        XCTAssertEqual(MedicationType(rawValue: "pill"), .pill)
        XCTAssertEqual(MedicationType(rawValue: "inhaler"), .inhaler)
        XCTAssertEqual(MedicationType(rawValue: "shot"), .shot)
        XCTAssertEqual(MedicationType(rawValue: "liquid"), .liquid)
        XCTAssertEqual(MedicationType(rawValue: "tablet"), .tablet)
        XCTAssertEqual(MedicationType(rawValue: "capsule"), .capsule)
        XCTAssertEqual(MedicationType(rawValue: "topical"), .topical)
        XCTAssertNil(MedicationType(rawValue: "invalid"))
        XCTAssertNil(MedicationType(rawValue: ""))
        XCTAssertNil(MedicationType(rawValue: "PILL")) // Case sensitive
    }

    // MARK: - Display Name Tests

    func testDisplayNames() {
        XCTAssertEqual(MedicationType.drops.displayName, "Drops")
        XCTAssertEqual(MedicationType.pill.displayName, "Pill")
        XCTAssertEqual(MedicationType.inhaler.displayName, "Inhaler")
        XCTAssertEqual(MedicationType.shot.displayName, "Shot")
        XCTAssertEqual(MedicationType.liquid.displayName, "Liquid")
        XCTAssertEqual(MedicationType.tablet.displayName, "Tablet")
        XCTAssertEqual(MedicationType.capsule.displayName, "Capsule")
        XCTAssertEqual(MedicationType.topical.displayName, "Topical")
    }

    // MARK: - CaseIterable Tests

    func testAllCases() {
        let allCases = MedicationType.allCases
        XCTAssertEqual(allCases.count, 8)
        XCTAssertTrue(allCases.contains(.drops))
        XCTAssertTrue(allCases.contains(.pill))
        XCTAssertTrue(allCases.contains(.inhaler))
        XCTAssertTrue(allCases.contains(.shot))
        XCTAssertTrue(allCases.contains(.liquid))
        XCTAssertTrue(allCases.contains(.tablet))
        XCTAssertTrue(allCases.contains(.capsule))
        XCTAssertTrue(allCases.contains(.topical))
    }

    // MARK: - Codable Tests

    func testEncodingDecoding() throws {
        let encoder = JSONEncoder()
        let decoder = JSONDecoder()

        for type in MedicationType.allCases {
            let data = try encoder.encode(type)
            let decoded = try decoder.decode(MedicationType.self, from: data)
            XCTAssertEqual(decoded, type)
        }
    }

    func testDecodingFromJSON() throws {
        let json = "\"pill\"".data(using: .utf8)!
        let decoder = JSONDecoder()
        let type = try decoder.decode(MedicationType.self, from: json)
        XCTAssertEqual(type, .pill)
    }

    func testDecodingInvalidThrows() {
        let json = "\"invalid\"".data(using: .utf8)!
        let decoder = JSONDecoder()

        XCTAssertThrowsError(try decoder.decode(MedicationType.self, from: json))
    }

    // MARK: - Usage in PetMedication Tests

    func testPetMedicationWithPillType() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "pet_id": "660e8400-e29b-41d4-a716-446655440001",
            "name": "Pain Relief",
            "medication_type": "pill",
            "start_date": "2024-01-01T00:00:00Z",
            "end_date": null,
            "times_per_day": 2,
            "notes": null,
            "reminders_enabled": true,
            "timezone": "America/Los_Angeles",
            "is_archived": false,
            "created_at": "2024-01-01T00:00:00Z",
            "created_by": null
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let medication = try decoder.decode(PetMedication.self, from: json)
        XCTAssertEqual(medication.medicationType, .pill)
    }

    func testPetMedicationWithDropsType() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "pet_id": "660e8400-e29b-41d4-a716-446655440001",
            "name": "Eye Drops",
            "medication_type": "drops",
            "start_date": "2024-01-01T00:00:00Z",
            "end_date": "2024-01-14T00:00:00Z",
            "times_per_day": 3,
            "notes": "Apply to both eyes",
            "reminders_enabled": true,
            "timezone": "America/Los_Angeles",
            "is_archived": false,
            "created_at": "2024-01-01T00:00:00Z",
            "created_by": null
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let medication = try decoder.decode(PetMedication.self, from: json)
        XCTAssertEqual(medication.medicationType, .drops)
    }

    func testPetMedicationWithTopicalType() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "pet_id": "660e8400-e29b-41d4-a716-446655440001",
            "name": "Flea Treatment",
            "medication_type": "topical",
            "start_date": "2024-01-01T00:00:00Z",
            "end_date": null,
            "times_per_day": 1,
            "notes": "Apply monthly",
            "reminders_enabled": true,
            "timezone": "America/Los_Angeles",
            "is_archived": false,
            "created_at": "2024-01-01T00:00:00Z",
            "created_by": null
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let medication = try decoder.decode(PetMedication.self, from: json)
        XCTAssertEqual(medication.medicationType, .topical)
    }

    func testAllMedicationTypesInPetMedication() throws {
        for type in MedicationType.allCases {
            let json = """
            {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "pet_id": "660e8400-e29b-41d4-a716-446655440001",
                "name": "Test Medication",
                "medication_type": "\(type.rawValue)",
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": null,
                "times_per_day": 1,
                "notes": null,
                "reminders_enabled": false,
                "timezone": "UTC",
                "is_archived": false,
                "created_at": "2024-01-01T00:00:00Z",
                "created_by": null
            }
            """.data(using: .utf8)!

            let decoder = JSONDecoder()
            decoder.keyDecodingStrategy = .convertFromSnakeCase
            decoder.dateDecodingStrategy = .iso8601

            let medication = try decoder.decode(PetMedication.self, from: json)
            XCTAssertEqual(medication.medicationType, type, "Failed for type: \(type.rawValue)")
        }
    }
}
