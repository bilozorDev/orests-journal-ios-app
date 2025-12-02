//
//  PetFeedingTests.swift
//  Orest's JournalTests
//
//  Unit tests for PetFeeding model.
//

import XCTest
@testable import Orest_s_Journal

final class PetFeedingTests: XCTestCase {

    // MARK: - PetFeeding Decoding Tests

    func testDecodingPetFeedingFromJSON() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "pet_id": "660e8400-e29b-41d4-a716-446655440001",
            "food_id": "770e8400-e29b-41d4-a716-446655440002",
            "fed_by": "user@example.com",
            "fed_at": "2024-01-15T08:30:00Z",
            "amount": 100.0,
            "amount_unit": "g",
            "calories": 200.0,
            "notes": "Morning feeding",
            "created_at": "2024-01-15T08:30:05Z"
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let feeding = try decoder.decode(PetFeeding.self, from: json)

        XCTAssertEqual(feeding.id, UUID(uuidString: "550e8400-e29b-41d4-a716-446655440000"))
        XCTAssertEqual(feeding.petId, UUID(uuidString: "660e8400-e29b-41d4-a716-446655440001"))
        XCTAssertEqual(feeding.foodId, UUID(uuidString: "770e8400-e29b-41d4-a716-446655440002"))
        XCTAssertEqual(feeding.fedBy, "user@example.com")
        XCTAssertEqual(feeding.amount, 100.0)
        XCTAssertEqual(feeding.amountUnit, .grams)
        XCTAssertEqual(feeding.calories, 200.0)
        XCTAssertEqual(feeding.notes, "Morning feeding")
    }

    func testDecodingPetFeedingWithNullNotes() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "pet_id": "660e8400-e29b-41d4-a716-446655440001",
            "food_id": "770e8400-e29b-41d4-a716-446655440002",
            "fed_by": "user@example.com",
            "fed_at": "2024-01-15T08:30:00Z",
            "amount": 50.0,
            "amount_unit": "oz",
            "calories": 150.0,
            "notes": null,
            "created_at": "2024-01-15T08:30:05Z"
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let feeding = try decoder.decode(PetFeeding.self, from: json)

        XCTAssertNil(feeding.notes)
        XCTAssertEqual(feeding.amountUnit, .ounces)
    }

    func testDecodingPetFeedingWithDifferentUnits() throws {
        let units: [(String, ContainerUnit)] = [
            ("g", .grams),
            ("oz", .ounces),
            ("kg", .kilograms),
            ("lb", .pounds)
        ]

        for (unitString, expectedUnit) in units {
            let json = """
            {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "pet_id": "660e8400-e29b-41d4-a716-446655440001",
                "food_id": "770e8400-e29b-41d4-a716-446655440002",
                "fed_by": "user@example.com",
                "fed_at": "2024-01-15T08:30:00Z",
                "amount": 1.0,
                "amount_unit": "\(unitString)",
                "calories": 100.0,
                "notes": null,
                "created_at": "2024-01-15T08:30:05Z"
            }
            """.data(using: .utf8)!

            let decoder = JSONDecoder()
            decoder.keyDecodingStrategy = .convertFromSnakeCase
            decoder.dateDecodingStrategy = .iso8601

            let feeding = try decoder.decode(PetFeeding.self, from: json)
            XCTAssertEqual(feeding.amountUnit, expectedUnit, "Failed for unit: \(unitString)")
        }
    }

    // MARK: - PetFeeding Encoding Tests

    func testEncodingPetFeeding() throws {
        let feeding = PetFeeding(
            id: UUID(uuidString: "550e8400-e29b-41d4-a716-446655440000")!,
            petId: UUID(uuidString: "660e8400-e29b-41d4-a716-446655440001")!,
            foodId: UUID(uuidString: "770e8400-e29b-41d4-a716-446655440002")!,
            fedBy: "test@example.com",
            fedAt: Date(timeIntervalSince1970: 1705307400),
            amount: 75.0,
            amountUnit: .ounces,
            calories: 175.0,
            notes: "Test feeding",
            createdAt: Date(timeIntervalSince1970: 1705307405)
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.dateEncodingStrategy = .iso8601

        let data = try encoder.encode(feeding)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["amount"] as? Double, 75.0)
        XCTAssertEqual(jsonObject["amount_unit"] as? String, "oz")
        XCTAssertEqual(jsonObject["calories"] as? Double, 175.0)
        XCTAssertEqual(jsonObject["fed_by"] as? String, "test@example.com")
        XCTAssertEqual(jsonObject["notes"] as? String, "Test feeding")
    }

    // MARK: - PetFeeding Identifiable Tests

    func testPetFeedingIdentifiable() {
        let uuid = UUID()
        let feeding = PetFeeding(
            id: uuid,
            petId: UUID(),
            foodId: UUID(),
            fedBy: "user@example.com",
            fedAt: Date(),
            amount: 100,
            amountUnit: .grams,
            calories: 200,
            notes: nil,
            createdAt: Date()
        )

        XCTAssertEqual(feeding.id, uuid)
    }

    // MARK: - Round-Trip Tests

    func testPetFeedingEncodingDecodingRoundTrip() throws {
        let original = PetFeeding(
            id: UUID(),
            petId: UUID(),
            foodId: UUID(),
            fedBy: "round_trip@example.com",
            fedAt: Date(timeIntervalSince1970: 1705307400),
            amount: 123.45,
            amountUnit: .grams,
            calories: 246.9,
            notes: "Round trip test",
            createdAt: Date(timeIntervalSince1970: 1705307405)
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.dateEncodingStrategy = .iso8601

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let data = try encoder.encode(original)
        let decoded = try decoder.decode(PetFeeding.self, from: data)

        XCTAssertEqual(decoded.id, original.id)
        XCTAssertEqual(decoded.petId, original.petId)
        XCTAssertEqual(decoded.foodId, original.foodId)
        XCTAssertEqual(decoded.fedBy, original.fedBy)
        XCTAssertEqual(decoded.amount, original.amount)
        XCTAssertEqual(decoded.amountUnit, original.amountUnit)
        XCTAssertEqual(decoded.calories, original.calories)
        XCTAssertEqual(decoded.notes, original.notes)
    }

    // MARK: - Value Tests

    func testPetFeedingWithZeroCalories() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "pet_id": "660e8400-e29b-41d4-a716-446655440001",
            "food_id": "770e8400-e29b-41d4-a716-446655440002",
            "fed_by": "user@example.com",
            "fed_at": "2024-01-15T08:30:00Z",
            "amount": 10.0,
            "amount_unit": "g",
            "calories": 0.0,
            "notes": "Water only",
            "created_at": "2024-01-15T08:30:05Z"
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let feeding = try decoder.decode(PetFeeding.self, from: json)

        XCTAssertEqual(feeding.calories, 0.0)
    }

    func testPetFeedingWithFractionalAmount() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "pet_id": "660e8400-e29b-41d4-a716-446655440001",
            "food_id": "770e8400-e29b-41d4-a716-446655440002",
            "fed_by": "user@example.com",
            "fed_at": "2024-01-15T08:30:00Z",
            "amount": 0.25,
            "amount_unit": "kg",
            "calories": 50.0,
            "notes": null,
            "created_at": "2024-01-15T08:30:05Z"
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let feeding = try decoder.decode(PetFeeding.self, from: json)

        XCTAssertEqual(feeding.amount, 0.25)
        XCTAssertEqual(feeding.amountUnit, .kilograms)
    }
}
