//
//  HealthSearchResultTests.swift
//  Orest's JournalTests
//
//  Unit tests for HealthSearchResult and EmbeddingResponse models.
//

import XCTest
@testable import Orest_s_Journal

final class HealthSearchResultTests: XCTestCase {

    // MARK: - HealthSearchResult Decoding Tests

    func testDecodingHealthSearchResultFromJSON() throws {
        let json = """
        {
            "event_id": "550e8400-e29b-41d4-a716-446655440000",
            "category_id": "660e8400-e29b-41d4-a716-446655440001",
            "category_name": "Vomiting",
            "occurred_at": "2024-01-15T14:30:00Z",
            "notes": "After eating",
            "pet_id": "770e8400-e29b-41d4-a716-446655440002",
            "pet_name": "Max",
            "created_by_id": "880e8400-e29b-41d4-a716-446655440003",
            "created_by_email": "user@example.com",
            "similarity": 0.95
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let result = try decoder.decode(HealthSearchResult.self, from: json)

        XCTAssertEqual(result.eventId, UUID(uuidString: "550e8400-e29b-41d4-a716-446655440000"))
        XCTAssertEqual(result.categoryId, UUID(uuidString: "660e8400-e29b-41d4-a716-446655440001"))
        XCTAssertEqual(result.categoryName, "Vomiting")
        XCTAssertEqual(result.notes, "After eating")
        XCTAssertEqual(result.petId, UUID(uuidString: "770e8400-e29b-41d4-a716-446655440002"))
        XCTAssertEqual(result.petName, "Max")
        XCTAssertEqual(result.createdByEmail, "user@example.com")
        XCTAssertEqual(result.similarity, 0.95, accuracy: 0.001)
    }

    func testDecodingHealthSearchResultWithNullNotes() throws {
        let json = """
        {
            "event_id": "550e8400-e29b-41d4-a716-446655440000",
            "category_id": "660e8400-e29b-41d4-a716-446655440001",
            "category_name": "Diarrhea",
            "occurred_at": "2024-01-15T14:30:00Z",
            "notes": null,
            "pet_id": "770e8400-e29b-41d4-a716-446655440002",
            "pet_name": "Buddy",
            "created_by_id": null,
            "created_by_email": "family@example.com",
            "similarity": 0.85
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let result = try decoder.decode(HealthSearchResult.self, from: json)

        XCTAssertNil(result.notes)
        XCTAssertNil(result.createdById)
        XCTAssertEqual(result.categoryName, "Diarrhea")
    }

    // MARK: - HealthSearchResult Identifiable Tests

    func testHealthSearchResultIdentifiable() {
        let eventId = UUID()
        let result = HealthSearchResult(
            eventId: eventId,
            categoryId: UUID(),
            categoryName: "Test",
            occurredAt: Date(),
            notes: nil,
            petId: UUID(),
            petName: "Test Pet",
            createdById: nil,
            createdByEmail: "test@example.com",
            similarity: 0.9
        )

        // The id property should return eventId
        XCTAssertEqual(result.id, eventId)
    }

    // MARK: - HealthSearchResult Hashable Tests

    func testHealthSearchResultHashable() {
        let eventId = UUID()
        let categoryId = UUID()
        let petId = UUID()
        let date = Date()

        let result1 = HealthSearchResult(
            eventId: eventId,
            categoryId: categoryId,
            categoryName: "Vomiting",
            occurredAt: date,
            notes: "Test",
            petId: petId,
            petName: "Max",
            createdById: nil,
            createdByEmail: "test@example.com",
            similarity: 0.9
        )

        let result2 = HealthSearchResult(
            eventId: eventId,
            categoryId: categoryId,
            categoryName: "Vomiting",
            occurredAt: date,
            notes: "Test",
            petId: petId,
            petName: "Max",
            createdById: nil,
            createdByEmail: "test@example.com",
            similarity: 0.9
        )

        XCTAssertEqual(result1.hashValue, result2.hashValue)

        var set = Set<HealthSearchResult>()
        set.insert(result1)
        XCTAssertTrue(set.contains(result1))
    }

    // MARK: - EmbeddingResponse Tests

    func testDecodingEmbeddingResponseSuccess() throws {
        let json = """
        {
            "success": true,
            "query": "when did my dog vomit",
            "embedding": [0.1, 0.2, 0.3, 0.4, 0.5],
            "dimensions": 5,
            "error": null
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()

        let response = try decoder.decode(EmbeddingResponse.self, from: json)

        XCTAssertTrue(response.success)
        XCTAssertEqual(response.query, "when did my dog vomit")
        XCTAssertEqual(response.embedding?.count, 5)
        XCTAssertEqual(response.dimensions, 5)
        XCTAssertNil(response.error)
    }

    func testDecodingEmbeddingResponseError() throws {
        let json = """
        {
            "success": false,
            "query": null,
            "embedding": null,
            "dimensions": null,
            "error": "Failed to generate embedding"
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()

        let response = try decoder.decode(EmbeddingResponse.self, from: json)

        XCTAssertFalse(response.success)
        XCTAssertNil(response.query)
        XCTAssertNil(response.embedding)
        XCTAssertNil(response.dimensions)
        XCTAssertEqual(response.error, "Failed to generate embedding")
    }

    func testEmbeddingResponseEmbeddingValues() throws {
        let json = """
        {
            "success": true,
            "query": "test",
            "embedding": [0.123, -0.456, 0.789],
            "dimensions": 3,
            "error": null
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()

        let response = try decoder.decode(EmbeddingResponse.self, from: json)

        let embedding = try XCTUnwrap(response.embedding)
        XCTAssertEqual(embedding[0], 0.123, accuracy: 0.0001)
        XCTAssertEqual(embedding[1], -0.456, accuracy: 0.0001)
        XCTAssertEqual(embedding[2], 0.789, accuracy: 0.0001)
    }
}
