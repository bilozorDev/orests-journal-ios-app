//
//  FoodCategoryTests.swift
//  Orest's JournalTests
//
//  Unit tests for FoodCategory enum.
//

import XCTest
@testable import Orest_s_Journal

final class FoodCategoryTests: XCTestCase {

    // MARK: - Raw Value Tests

    func testRawValues() {
        XCTAssertEqual(FoodCategory.dry.rawValue, "dry")
        XCTAssertEqual(FoodCategory.wet.rawValue, "wet")
        XCTAssertEqual(FoodCategory.snack.rawValue, "snack")
    }

    func testInitFromRawValue() {
        XCTAssertEqual(FoodCategory(rawValue: "dry"), .dry)
        XCTAssertEqual(FoodCategory(rawValue: "wet"), .wet)
        XCTAssertEqual(FoodCategory(rawValue: "snack"), .snack)
        XCTAssertNil(FoodCategory(rawValue: "invalid"))
        XCTAssertNil(FoodCategory(rawValue: ""))
        XCTAssertNil(FoodCategory(rawValue: "DRY")) // Case sensitive
    }

    // MARK: - Display Name Tests

    func testDisplayNames() {
        XCTAssertEqual(FoodCategory.dry.displayName, "Dry")
        XCTAssertEqual(FoodCategory.wet.displayName, "Wet")
        XCTAssertEqual(FoodCategory.snack.displayName, "Snack")
    }

    // MARK: - CaseIterable Tests

    func testAllCases() {
        let allCases = FoodCategory.allCases
        XCTAssertEqual(allCases.count, 3)
        XCTAssertTrue(allCases.contains(.dry))
        XCTAssertTrue(allCases.contains(.wet))
        XCTAssertTrue(allCases.contains(.snack))
    }

    // MARK: - Codable Tests

    func testEncodingDecoding() throws {
        let encoder = JSONEncoder()
        let decoder = JSONDecoder()

        for category in FoodCategory.allCases {
            let data = try encoder.encode(category)
            let decoded = try decoder.decode(FoodCategory.self, from: data)
            XCTAssertEqual(decoded, category)
        }
    }

    func testDecodingFromJSON() throws {
        let json = "\"dry\"".data(using: .utf8)!
        let decoder = JSONDecoder()
        let category = try decoder.decode(FoodCategory.self, from: json)
        XCTAssertEqual(category, .dry)
    }

    func testDecodingInvalidThrows() {
        let json = "\"invalid\"".data(using: .utf8)!
        let decoder = JSONDecoder()

        XCTAssertThrowsError(try decoder.decode(FoodCategory.self, from: json))
    }

    // MARK: - Usage in PetFood Tests

    func testPetFoodWithDryCategory() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "org_id": "org-123",
            "name": "Premium Kibble",
            "category": "dry",
            "calories_per_kg": 3500.0,
            "container_size": 1000.0,
            "container_size_unit": "g",
            "image_url": null,
            "is_archived": false,
            "created_at": "2024-01-01T00:00:00Z",
            "created_by": null
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let food = try decoder.decode(PetFood.self, from: json)
        XCTAssertEqual(food.category, .dry)
    }

    func testPetFoodWithWetCategory() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "org_id": "org-123",
            "name": "Canned Chicken",
            "category": "wet",
            "calories_per_kg": 1000.0,
            "container_size": 150.0,
            "container_size_unit": "g",
            "image_url": null,
            "is_archived": false,
            "created_at": "2024-01-01T00:00:00Z",
            "created_by": null
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let food = try decoder.decode(PetFood.self, from: json)
        XCTAssertEqual(food.category, .wet)
    }

    func testPetFoodWithSnackCategory() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "org_id": "org-123",
            "name": "Training Treats",
            "category": "snack",
            "calories_per_kg": 4000.0,
            "container_size": 200.0,
            "container_size_unit": "g",
            "image_url": null,
            "is_archived": false,
            "created_at": "2024-01-01T00:00:00Z",
            "created_by": null
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let food = try decoder.decode(PetFood.self, from: json)
        XCTAssertEqual(food.category, .snack)
    }
}
