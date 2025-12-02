//
//  CalorieGoalTests.swift
//  Orest's JournalTests
//
//  Unit tests for CalorieGoal model.
//

import XCTest
@testable import Orest_s_Journal

final class CalorieGoalTests: XCTestCase {

    // MARK: - CalorieGoal Decoding Tests

    func testDecodingCalorieGoalFromJSON() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "pet_id": "660e8400-e29b-41d4-a716-446655440001",
            "daily_calories": 350.5,
            "effective_from": "2024-01-01T00:00:00Z",
            "effective_until": "2024-12-31T23:59:59Z",
            "notes": "Weight management plan",
            "created_at": "2024-01-01T10:00:00Z",
            "created_by": "user@example.com"
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let goal = try decoder.decode(CalorieGoal.self, from: json)

        XCTAssertEqual(goal.id, UUID(uuidString: "550e8400-e29b-41d4-a716-446655440000"))
        XCTAssertEqual(goal.petId, UUID(uuidString: "660e8400-e29b-41d4-a716-446655440001"))
        XCTAssertEqual(goal.dailyCalories, 350.5)
        XCTAssertEqual(goal.notes, "Weight management plan")
        XCTAssertEqual(goal.createdBy, "user@example.com")
        XCTAssertNotNil(goal.effectiveUntil)
    }

    func testDecodingCalorieGoalWithNullOptionals() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "pet_id": "660e8400-e29b-41d4-a716-446655440001",
            "daily_calories": 400.0,
            "effective_from": "2024-01-01T00:00:00Z",
            "effective_until": null,
            "notes": null,
            "created_at": "2024-01-01T10:00:00Z",
            "created_by": null
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let goal = try decoder.decode(CalorieGoal.self, from: json)

        XCTAssertNil(goal.effectiveUntil)
        XCTAssertNil(goal.notes)
        XCTAssertNil(goal.createdBy)
        XCTAssertEqual(goal.dailyCalories, 400.0)
    }

    // MARK: - CalorieGoal Encoding Tests

    func testEncodingCalorieGoal() throws {
        let goal = CalorieGoal(
            id: UUID(uuidString: "550e8400-e29b-41d4-a716-446655440000")!,
            petId: UUID(uuidString: "660e8400-e29b-41d4-a716-446655440001")!,
            dailyCalories: 300.0,
            effectiveFrom: Date(timeIntervalSince1970: 1704067200),
            effectiveUntil: nil,
            notes: "Test goal",
            createdAt: Date(timeIntervalSince1970: 1704103200),
            createdBy: "test@example.com"
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.dateEncodingStrategy = .iso8601

        let data = try encoder.encode(goal)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["daily_calories"] as? Double, 300.0)
        XCTAssertEqual(jsonObject["notes"] as? String, "Test goal")
        XCTAssertEqual(jsonObject["created_by"] as? String, "test@example.com")
    }

    // MARK: - CalorieGoal Identifiable Tests

    func testCalorieGoalIdentifiable() {
        let uuid = UUID()
        let goal = CalorieGoal(
            id: uuid,
            petId: UUID(),
            dailyCalories: 350.0,
            effectiveFrom: Date(),
            effectiveUntil: nil,
            notes: nil,
            createdAt: Date(),
            createdBy: nil
        )

        XCTAssertEqual(goal.id, uuid)
    }

    // MARK: - CalorieGoal Round-Trip Tests

    func testCalorieGoalEncodingDecodingRoundTrip() throws {
        let original = CalorieGoal(
            id: UUID(),
            petId: UUID(),
            dailyCalories: 425.5,
            effectiveFrom: Date(timeIntervalSince1970: 1704067200),
            effectiveUntil: Date(timeIntervalSince1970: 1735689599),
            notes: "Special diet",
            createdAt: Date(timeIntervalSince1970: 1704103200),
            createdBy: "owner@test.com"
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.dateEncodingStrategy = .iso8601

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let data = try encoder.encode(original)
        let decoded = try decoder.decode(CalorieGoal.self, from: data)

        XCTAssertEqual(decoded.id, original.id)
        XCTAssertEqual(decoded.petId, original.petId)
        XCTAssertEqual(decoded.dailyCalories, original.dailyCalories)
        XCTAssertEqual(decoded.notes, original.notes)
        XCTAssertEqual(decoded.createdBy, original.createdBy)
    }

    // MARK: - CalorieGoal Value Tests

    func testCalorieGoalWithZeroCalories() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "pet_id": "660e8400-e29b-41d4-a716-446655440001",
            "daily_calories": 0.0,
            "effective_from": "2024-01-01T00:00:00Z",
            "effective_until": null,
            "notes": null,
            "created_at": "2024-01-01T10:00:00Z",
            "created_by": null
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let goal = try decoder.decode(CalorieGoal.self, from: json)

        XCTAssertEqual(goal.dailyCalories, 0.0)
    }

    func testCalorieGoalWithLargeCalorieValue() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "pet_id": "660e8400-e29b-41d4-a716-446655440001",
            "daily_calories": 5000.0,
            "effective_from": "2024-01-01T00:00:00Z",
            "effective_until": null,
            "notes": "Large breed dog",
            "created_at": "2024-01-01T10:00:00Z",
            "created_by": null
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let goal = try decoder.decode(CalorieGoal.self, from: json)

        XCTAssertEqual(goal.dailyCalories, 5000.0)
    }
}
