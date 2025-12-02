//
//  HealthCategoryTests.swift
//  Orest's JournalTests
//
//  Unit tests for HealthCategory model.
//

import XCTest
@testable import Orest_s_Journal

final class HealthCategoryTests: XCTestCase {

    // MARK: - HealthCategory Decoding Tests

    func testDecodingHealthCategoryFromJSON() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "pet_id": "660e8400-e29b-41d4-a716-446655440001",
            "name": "Vomiting",
            "name_normalized": "vomiting",
            "created_at": "2024-01-01T00:00:00Z",
            "created_by": "user@example.com"
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let category = try decoder.decode(HealthCategory.self, from: json)

        XCTAssertEqual(category.id, UUID(uuidString: "550e8400-e29b-41d4-a716-446655440000"))
        XCTAssertEqual(category.petId, UUID(uuidString: "660e8400-e29b-41d4-a716-446655440001"))
        XCTAssertEqual(category.name, "Vomiting")
        XCTAssertEqual(category.nameNormalized, "vomiting")
        XCTAssertEqual(category.createdBy, "user@example.com")
    }

    func testDecodingHealthCategoryWithNullCreatedBy() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "pet_id": "660e8400-e29b-41d4-a716-446655440001",
            "name": "Diarrhea",
            "name_normalized": "diarrhea",
            "created_at": "2024-01-01T00:00:00Z",
            "created_by": null
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let category = try decoder.decode(HealthCategory.self, from: json)

        XCTAssertNil(category.createdBy)
        XCTAssertEqual(category.name, "Diarrhea")
    }

    // MARK: - HealthCategory Encoding Tests

    func testEncodingHealthCategory() throws {
        let category = HealthCategory(
            id: UUID(uuidString: "550e8400-e29b-41d4-a716-446655440000")!,
            petId: UUID(uuidString: "660e8400-e29b-41d4-a716-446655440001")!,
            name: "Lethargy",
            nameNormalized: "lethargy",
            createdAt: Date(timeIntervalSince1970: 1704067200),
            createdBy: "test@example.com"
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.dateEncodingStrategy = .iso8601

        let data = try encoder.encode(category)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["name"] as? String, "Lethargy")
        XCTAssertEqual(jsonObject["name_normalized"] as? String, "lethargy")
        XCTAssertEqual(jsonObject["created_by"] as? String, "test@example.com")
    }

    // MARK: - HealthCategory Identifiable Tests

    func testHealthCategoryIdentifiable() {
        let uuid = UUID()
        let category = HealthCategory(
            id: uuid,
            petId: UUID(),
            name: "Test",
            nameNormalized: "test",
            createdAt: Date(),
            createdBy: nil
        )

        XCTAssertEqual(category.id, uuid)
    }

    // MARK: - HealthCategory Hashable Tests

    func testHealthCategoryHashable() {
        let id = UUID()
        let petId = UUID()
        let date = Date(timeIntervalSince1970: 1704067200)

        let category1 = HealthCategory(
            id: id,
            petId: petId,
            name: "Seizure",
            nameNormalized: "seizure",
            createdAt: date,
            createdBy: nil
        )

        let category2 = HealthCategory(
            id: id,
            petId: petId,
            name: "Seizure",
            nameNormalized: "seizure",
            createdAt: date,
            createdBy: nil
        )

        XCTAssertEqual(category1.hashValue, category2.hashValue)

        var set = Set<HealthCategory>()
        set.insert(category1)
        XCTAssertTrue(set.contains(category1))
    }

    // MARK: - Round-Trip Tests

    func testHealthCategoryRoundTrip() throws {
        let original = HealthCategory(
            id: UUID(),
            petId: UUID(),
            name: "Coughing",
            nameNormalized: "coughing",
            createdAt: Date(timeIntervalSince1970: 1704067200),
            createdBy: "owner@example.com"
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.dateEncodingStrategy = .iso8601

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let data = try encoder.encode(original)
        let decoded = try decoder.decode(HealthCategory.self, from: data)

        XCTAssertEqual(decoded.id, original.id)
        XCTAssertEqual(decoded.petId, original.petId)
        XCTAssertEqual(decoded.name, original.name)
        XCTAssertEqual(decoded.nameNormalized, original.nameNormalized)
        XCTAssertEqual(decoded.createdBy, original.createdBy)
    }

    // MARK: - HealthEventWithCategory Tests

    func testDecodingHealthEventWithCategory() throws {
        let json = """
        {
            "event": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "category_id": "660e8400-e29b-41d4-a716-446655440001",
                "occurred_at": "2024-01-15T10:00:00Z",
                "notes": "After eating breakfast",
                "created_at": "2024-01-15T10:05:00Z",
                "created_by": "user@example.com"
            },
            "category": {
                "id": "660e8400-e29b-41d4-a716-446655440001",
                "pet_id": "770e8400-e29b-41d4-a716-446655440002",
                "name": "Vomiting",
                "name_normalized": "vomiting",
                "created_at": "2024-01-01T00:00:00Z",
                "created_by": null
            }
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let eventWithCategory = try decoder.decode(HealthEventWithCategory.self, from: json)

        XCTAssertEqual(eventWithCategory.event.notes, "After eating breakfast")
        XCTAssertEqual(eventWithCategory.category.name, "Vomiting")
        XCTAssertEqual(eventWithCategory.id, eventWithCategory.event.id)
    }

    func testHealthEventWithCategoryIdentifiable() throws {
        let json = """
        {
            "event": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "category_id": "660e8400-e29b-41d4-a716-446655440001",
                "occurred_at": "2024-01-15T10:00:00Z",
                "notes": null,
                "created_at": "2024-01-15T10:05:00Z",
                "created_by": null
            },
            "category": {
                "id": "660e8400-e29b-41d4-a716-446655440001",
                "pet_id": "770e8400-e29b-41d4-a716-446655440002",
                "name": "Test",
                "name_normalized": "test",
                "created_at": "2024-01-01T00:00:00Z",
                "created_by": null
            }
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let eventWithCategory = try decoder.decode(HealthEventWithCategory.self, from: json)

        // id property should return event.id
        XCTAssertEqual(eventWithCategory.id, UUID(uuidString: "550e8400-e29b-41d4-a716-446655440000"))
    }

    func testHealthEventWithCategoryHashable() throws {
        let json = """
        {
            "event": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "category_id": "660e8400-e29b-41d4-a716-446655440001",
                "occurred_at": "2024-01-15T10:00:00Z",
                "notes": null,
                "created_at": "2024-01-15T10:05:00Z",
                "created_by": null
            },
            "category": {
                "id": "660e8400-e29b-41d4-a716-446655440001",
                "pet_id": "770e8400-e29b-41d4-a716-446655440002",
                "name": "Test",
                "name_normalized": "test",
                "created_at": "2024-01-01T00:00:00Z",
                "created_by": null
            }
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let eventWithCategory1 = try decoder.decode(HealthEventWithCategory.self, from: json)
        let eventWithCategory2 = try decoder.decode(HealthEventWithCategory.self, from: json)

        XCTAssertEqual(eventWithCategory1.hashValue, eventWithCategory2.hashValue)

        var set = Set<HealthEventWithCategory>()
        set.insert(eventWithCategory1)
        XCTAssertTrue(set.contains(eventWithCategory1))
    }

    // MARK: - Common Health Categories

    func testCommonHealthCategories() throws {
        let commonCategories = ["Vomiting", "Diarrhea", "Lethargy", "Seizure", "Coughing", "Sneezing"]

        for categoryName in commonCategories {
            let json = """
            {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "pet_id": "660e8400-e29b-41d4-a716-446655440001",
                "name": "\(categoryName)",
                "name_normalized": "\(categoryName.lowercased())",
                "created_at": "2024-01-01T00:00:00Z",
                "created_by": null
            }
            """.data(using: .utf8)!

            let decoder = JSONDecoder()
            decoder.keyDecodingStrategy = .convertFromSnakeCase
            decoder.dateDecodingStrategy = .iso8601

            let category = try decoder.decode(HealthCategory.self, from: json)
            XCTAssertEqual(category.name, categoryName)
            XCTAssertEqual(category.nameNormalized, categoryName.lowercased())
        }
    }
}
