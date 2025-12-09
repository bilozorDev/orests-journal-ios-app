//
//  PetTests.swift
//  Orest's JournalTests
//
//  Unit tests for Pet model.
//

import XCTest
@testable import Orest_s_Journal

final class PetTests: XCTestCase {

    // MARK: - JSON Decoding Tests

    func testDecodingFromJSON() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "org_id": "family-123",
            "name": "Max",
            "kind": "dog",
            "photo_url": "https://example.com/photo.jpg",
            "current_weight": 25.5,
            "date_of_birth": "2022-03-15",
            "is_archived": false,
            "created_at": "2024-01-15T10:30:00Z",
            "created_by": "user-123"
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let pet = try decoder.decode(Pet.self, from: json)

        XCTAssertEqual(pet.id, UUID(uuidString: "550e8400-e29b-41d4-a716-446655440000"))
        XCTAssertEqual(pet.orgId, "family-123")
        XCTAssertEqual(pet.name, "Max")
        XCTAssertEqual(pet.kind, "dog")
        XCTAssertEqual(pet.photoUrl, "https://example.com/photo.jpg")
        XCTAssertEqual(pet.currentWeight, 25.5)
        XCTAssertNotNil(pet.dateOfBirth)
        XCTAssertEqual(pet.isArchived, false)
        XCTAssertEqual(pet.createdBy, "user-123")
    }

    func testDecodingWithNullOptionals() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "org_id": "family-123",
            "name": "Whiskers",
            "kind": "cat",
            "photo_url": null,
            "current_weight": null,
            "date_of_birth": null,
            "is_archived": null,
            "created_at": "2024-01-15T10:30:00Z",
            "created_by": null
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let pet = try decoder.decode(Pet.self, from: json)

        XCTAssertEqual(pet.name, "Whiskers")
        XCTAssertEqual(pet.kind, "cat")
        XCTAssertNil(pet.photoUrl)
        XCTAssertNil(pet.currentWeight)
        XCTAssertNil(pet.dateOfBirth)
        XCTAssertNil(pet.isArchived)
        XCTAssertNil(pet.createdBy)
    }

    // MARK: - JSON Encoding Tests

    func testEncodingToJSON() throws {
        let pet = Pet(
            id: UUID(uuidString: "550e8400-e29b-41d4-a716-446655440000")!,
            orgId: "family-123",
            name: "Buddy",
            kind: "dog",
            photoUrl: nil,
            currentWeight: 30.0,
            dateOfBirth: Date(timeIntervalSince1970: 1647302400), // 2022-03-15
            isArchived: false,
            createdAt: Date(timeIntervalSince1970: 1705315800),
            createdBy: nil
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.dateEncodingStrategy = .iso8601

        let data = try encoder.encode(pet)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["name"] as? String, "Buddy")
        XCTAssertEqual(jsonObject["kind"] as? String, "dog")
        XCTAssertEqual(jsonObject["current_weight"] as? Double, 30.0)
        XCTAssertNotNil(jsonObject["date_of_birth"])
    }

    // MARK: - Identifiable Tests

    func testIdentifiableConformance() {
        let uuid = UUID()
        let pet = Pet(
            id: uuid,
            orgId: "family-123",
            name: "Test",
            kind: "dog",
            photoUrl: nil,
            currentWeight: nil,
            dateOfBirth: nil,
            isArchived: nil,
            createdAt: Date(),
            createdBy: nil
        )

        XCTAssertEqual(pet.id, uuid)
    }

    // MARK: - Hashable Tests

    func testHashableConformance() {
        let uuid = UUID()
        let date = Date()  // Same date for both to ensure same hash
        let pet1 = Pet(
            id: uuid,
            orgId: "family-123",
            name: "Test",
            kind: "dog",
            photoUrl: nil,
            currentWeight: nil,
            dateOfBirth: nil,
            isArchived: nil,
            createdAt: date,
            createdBy: nil
        )

        let pet2 = Pet(
            id: uuid,
            orgId: "family-123",
            name: "Test",
            kind: "dog",
            photoUrl: nil,
            currentWeight: nil,
            dateOfBirth: nil,
            isArchived: nil,
            createdAt: date,
            createdBy: nil
        )

        XCTAssertEqual(pet1.hashValue, pet2.hashValue)

        var set = Set<Pet>()
        set.insert(pet1)
        XCTAssertTrue(set.contains(pet1))
    }
}
