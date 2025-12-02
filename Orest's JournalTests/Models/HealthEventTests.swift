//
//  HealthEventTests.swift
//  Orest's JournalTests
//
//  Unit tests for HealthEvent model and related types.
//

import XCTest
@testable import Orest_s_Journal

final class HealthEventTests: XCTestCase {

    // MARK: - HealthEvent JSON Decoding Tests

    func testDecodingHealthEventFromJSON() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "category_id": "660e8400-e29b-41d4-a716-446655440001",
            "occurred_at": "2024-01-15T14:30:00Z",
            "notes": "Seems better today",
            "created_at": "2024-01-15T14:35:00Z",
            "created_by": "user-123"
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let event = try decoder.decode(HealthEvent.self, from: json)

        XCTAssertEqual(event.id, UUID(uuidString: "550e8400-e29b-41d4-a716-446655440000"))
        XCTAssertEqual(event.categoryId, UUID(uuidString: "660e8400-e29b-41d4-a716-446655440001"))
        XCTAssertEqual(event.notes, "Seems better today")
        XCTAssertEqual(event.createdBy, "user-123")
    }

    func testDecodingHealthEventWithNullOptionals() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "category_id": "660e8400-e29b-41d4-a716-446655440001",
            "occurred_at": "2024-01-15T14:30:00Z",
            "notes": null,
            "created_at": "2024-01-15T14:35:00Z",
            "created_by": null
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let event = try decoder.decode(HealthEvent.self, from: json)

        XCTAssertNil(event.notes)
        XCTAssertNil(event.createdBy)
    }

    // MARK: - HealthEvent Encoding Tests

    func testEncodingHealthEvent() throws {
        let event = HealthEvent(
            id: UUID(uuidString: "550e8400-e29b-41d4-a716-446655440000")!,
            categoryId: UUID(uuidString: "660e8400-e29b-41d4-a716-446655440001")!,
            occurredAt: Date(timeIntervalSince1970: 1705329000),
            notes: "Test notes",
            createdAt: Date(timeIntervalSince1970: 1705329300),
            createdBy: "user-456"
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.dateEncodingStrategy = .iso8601

        let data = try encoder.encode(event)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["notes"] as? String, "Test notes")
        XCTAssertEqual(jsonObject["created_by"] as? String, "user-456")
    }

    // MARK: - HealthEvent Identifiable Tests

    func testHealthEventIdentifiable() {
        let uuid = UUID()
        let event = HealthEvent(
            id: uuid,
            categoryId: UUID(),
            occurredAt: Date(),
            notes: nil,
            createdAt: Date(),
            createdBy: nil
        )

        XCTAssertEqual(event.id, uuid)
    }

    // MARK: - HealthEvent Hashable Tests

    func testHealthEventHashable() {
        let uuid = UUID()
        let categoryId = UUID()
        let date = Date()

        let event1 = HealthEvent(
            id: uuid,
            categoryId: categoryId,
            occurredAt: date,
            notes: "Test",
            createdAt: date,
            createdBy: nil
        )

        let event2 = HealthEvent(
            id: uuid,
            categoryId: categoryId,
            occurredAt: date,
            notes: "Test",
            createdAt: date,
            createdBy: nil
        )

        XCTAssertEqual(event1.hashValue, event2.hashValue)

        var set = Set<HealthEvent>()
        set.insert(event1)
        XCTAssertTrue(set.contains(event1))
    }

    // MARK: - HealthEventWithCategory Tests

    func testHealthEventWithCategoryId() {
        let eventId = UUID()
        let categoryId = UUID()
        let petId = UUID()

        let event = HealthEvent(
            id: eventId,
            categoryId: categoryId,
            occurredAt: Date(),
            notes: nil,
            createdAt: Date(),
            createdBy: nil
        )

        let category = HealthCategory(
            id: categoryId,
            petId: petId,
            name: "Vomiting",
            nameNormalized: "vomiting",
            createdAt: Date(),
            createdBy: nil
        )

        let eventWithCategory = HealthEventWithCategory(
            event: event,
            category: category
        )

        // The id should come from the underlying event
        XCTAssertEqual(eventWithCategory.id, eventId)
        XCTAssertEqual(eventWithCategory.event.id, eventId)
        XCTAssertEqual(eventWithCategory.category.name, "Vomiting")
    }

    func testHealthEventWithCategoryDecoding() throws {
        let json = """
        {
            "event": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "category_id": "660e8400-e29b-41d4-a716-446655440001",
                "occurred_at": "2024-01-15T14:30:00Z",
                "notes": "Morning episode",
                "created_at": "2024-01-15T14:35:00Z",
                "created_by": null
            },
            "category": {
                "id": "660e8400-e29b-41d4-a716-446655440001",
                "pet_id": "770e8400-e29b-41d4-a716-446655440002",
                "name": "Diarrhea",
                "name_normalized": "diarrhea",
                "created_at": "2024-01-15T10:00:00Z",
                "created_by": null
            }
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let eventWithCategory = try decoder.decode(HealthEventWithCategory.self, from: json)

        XCTAssertEqual(eventWithCategory.event.notes, "Morning episode")
        XCTAssertEqual(eventWithCategory.category.name, "Diarrhea")
        XCTAssertEqual(eventWithCategory.category.nameNormalized, "diarrhea")
        XCTAssertEqual(eventWithCategory.id, UUID(uuidString: "550e8400-e29b-41d4-a716-446655440000"))
    }
}
