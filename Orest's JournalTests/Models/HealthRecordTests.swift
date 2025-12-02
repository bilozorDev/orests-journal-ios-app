//
//  HealthRecordTests.swift
//  Orest's JournalTests
//
//  Unit tests for HealthRecord model.
//

import XCTest
@testable import Orest_s_Journal

final class HealthRecordTests: XCTestCase {

    // MARK: - HealthRecord Decoding Tests

    func testDecodingHealthRecordFromJSON() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "pet_id": "660e8400-e29b-41d4-a716-446655440001",
            "recorded_at": "2024-01-15T10:30:00Z",
            "age_years": 3.5,
            "weight_pounds": 25.5,
            "notes": "Annual checkup"
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let record = try decoder.decode(HealthRecord.self, from: json)

        XCTAssertEqual(record.id, UUID(uuidString: "550e8400-e29b-41d4-a716-446655440000"))
        XCTAssertEqual(record.petId, UUID(uuidString: "660e8400-e29b-41d4-a716-446655440001"))
        XCTAssertEqual(record.ageYears, 3.5)
        XCTAssertEqual(record.weightPounds, 25.5)
        XCTAssertEqual(record.notes, "Annual checkup")
    }

    func testDecodingHealthRecordWithNullOptionals() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "pet_id": "660e8400-e29b-41d4-a716-446655440001",
            "recorded_at": "2024-01-15T10:30:00Z",
            "age_years": null,
            "weight_pounds": null,
            "notes": null
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let record = try decoder.decode(HealthRecord.self, from: json)

        XCTAssertNil(record.ageYears)
        XCTAssertNil(record.weightPounds)
        XCTAssertNil(record.notes)
    }

    func testDecodingHealthRecordWeightOnly() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "pet_id": "660e8400-e29b-41d4-a716-446655440001",
            "recorded_at": "2024-01-15T10:30:00Z",
            "age_years": null,
            "weight_pounds": 30.0,
            "notes": "Weight check"
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let record = try decoder.decode(HealthRecord.self, from: json)

        XCTAssertNil(record.ageYears)
        XCTAssertEqual(record.weightPounds, 30.0)
        XCTAssertEqual(record.notes, "Weight check")
    }

    // MARK: - HealthRecord Encoding Tests

    func testEncodingHealthRecord() throws {
        let record = HealthRecord(
            id: UUID(uuidString: "550e8400-e29b-41d4-a716-446655440000")!,
            petId: UUID(uuidString: "660e8400-e29b-41d4-a716-446655440001")!,
            recordedAt: Date(timeIntervalSince1970: 1705315800),
            ageYears: 2.0,
            weightPounds: 20.0,
            notes: "Healthy"
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.dateEncodingStrategy = .iso8601

        let data = try encoder.encode(record)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["age_years"] as? Double, 2.0)
        XCTAssertEqual(jsonObject["weight_pounds"] as? Double, 20.0)
        XCTAssertEqual(jsonObject["notes"] as? String, "Healthy")
    }

    // MARK: - HealthRecord Identifiable Tests

    func testHealthRecordIdentifiable() {
        let uuid = UUID()
        let record = HealthRecord(
            id: uuid,
            petId: UUID(),
            recordedAt: Date(),
            ageYears: nil,
            weightPounds: nil,
            notes: nil
        )

        XCTAssertEqual(record.id, uuid)
    }

    // MARK: - HealthRecordCreate Encoding Tests

    func testHealthRecordCreateEncoding() throws {
        let create = HealthRecordCreate(
            weightPounds: 25.5,
            ageYears: 3.0,
            notes: "Regular checkup"
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase

        let data = try encoder.encode(create)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["weight_pounds"] as? Double, 25.5)
        XCTAssertEqual(jsonObject["age_years"] as? Double, 3.0)
        XCTAssertEqual(jsonObject["notes"] as? String, "Regular checkup")
    }

    func testHealthRecordCreateEncodingWithNilValues() throws {
        let create = HealthRecordCreate(
            weightPounds: 25.5,
            ageYears: nil,
            notes: nil
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase

        let data = try encoder.encode(create)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["weight_pounds"] as? Double, 25.5)
        // Nil values should be encoded as null in JSON
    }
}
