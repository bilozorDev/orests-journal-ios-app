//
//  PetFoodTests.swift
//  Orest's JournalTests
//
//  Unit tests for PetFood model and related types.
//

import XCTest
@testable import Orest_s_Journal

final class PetFoodTests: XCTestCase {

    // MARK: - ContainerUnit Tests

    func testContainerUnitToGramsFromGrams() {
        let unit = ContainerUnit.grams
        XCTAssertEqual(unit.toGrams(100), 100, accuracy: 0.001)
        XCTAssertEqual(unit.toGrams(1), 1, accuracy: 0.001)
        XCTAssertEqual(unit.toGrams(0), 0, accuracy: 0.001)
    }

    func testContainerUnitToGramsFromOunces() {
        let unit = ContainerUnit.ounces
        XCTAssertEqual(unit.toGrams(1), 28.3495, accuracy: 0.001)
        XCTAssertEqual(unit.toGrams(10), 283.495, accuracy: 0.001)
    }

    func testContainerUnitToGramsFromKilograms() {
        let unit = ContainerUnit.kilograms
        XCTAssertEqual(unit.toGrams(1), 1000, accuracy: 0.001)
        XCTAssertEqual(unit.toGrams(2.5), 2500, accuracy: 0.001)
    }

    func testContainerUnitToGramsFromPounds() {
        let unit = ContainerUnit.pounds
        XCTAssertEqual(unit.toGrams(1), 453.592, accuracy: 0.001)
        XCTAssertEqual(unit.toGrams(2), 907.184, accuracy: 0.001)
    }

    func testContainerUnitDisplayName() {
        XCTAssertEqual(ContainerUnit.grams.displayName, "Grams (g)")
        XCTAssertEqual(ContainerUnit.ounces.displayName, "Ounces (oz)")
        XCTAssertEqual(ContainerUnit.kilograms.displayName, "Kilograms (kg)")
        XCTAssertEqual(ContainerUnit.pounds.displayName, "Pounds (lb)")
    }

    func testContainerUnitAbbreviation() {
        XCTAssertEqual(ContainerUnit.grams.abbreviation, "g")
        XCTAssertEqual(ContainerUnit.ounces.abbreviation, "oz")
        XCTAssertEqual(ContainerUnit.kilograms.abbreviation, "kg")
        XCTAssertEqual(ContainerUnit.pounds.abbreviation, "lb")
    }

    // MARK: - FoodCategory Tests

    func testFoodCategoryDisplayName() {
        XCTAssertEqual(FoodCategory.dry.displayName, "Dry")
        XCTAssertEqual(FoodCategory.wet.displayName, "Wet")
        XCTAssertEqual(FoodCategory.snack.displayName, "Snack")
    }

    func testFoodCategoryRawValue() {
        XCTAssertEqual(FoodCategory.dry.rawValue, "dry")
        XCTAssertEqual(FoodCategory.wet.rawValue, "wet")
        XCTAssertEqual(FoodCategory.snack.rawValue, "snack")
    }

    // MARK: - PetFood Computed Properties Tests

    func testCaloriesPerGram() {
        let food = PetFood(
            id: UUID(),
            orgId: "family-123",
            name: "Premium Kibble",
            category: .dry,
            caloriesPerKg: 3500,
            containerSize: 1000,
            containerSizeUnit: .grams,
            imageUrl: nil,
            isArchived: false,
            createdAt: Date(),
            createdBy: nil
        )

        XCTAssertEqual(food.caloriesPerGram, 3.5, accuracy: 0.001)
    }

    func testCaloriesPerGramWithLowCalorieFood() {
        let food = PetFood(
            id: UUID(),
            orgId: "family-123",
            name: "Diet Food",
            category: .dry,
            caloriesPerKg: 2000,
            containerSize: 500,
            containerSizeUnit: .grams,
            imageUrl: nil,
            isArchived: false,
            createdAt: Date(),
            createdBy: nil
        )

        XCTAssertEqual(food.caloriesPerGram, 2.0, accuracy: 0.001)
    }

    func testCaloriesPerContainerWithGrams() {
        let food = PetFood(
            id: UUID(),
            orgId: "family-123",
            name: "Wet Food",
            category: .wet,
            caloriesPerKg: 1000, // 1 cal/gram
            containerSize: 150,
            containerSizeUnit: .grams,
            imageUrl: nil,
            isArchived: false,
            createdAt: Date(),
            createdBy: nil
        )

        XCTAssertEqual(food.caloriesPerContainer, 150, accuracy: 0.001)
    }

    func testCaloriesPerContainerWithOunces() {
        let food = PetFood(
            id: UUID(),
            orgId: "family-123",
            name: "Canned Food",
            category: .wet,
            caloriesPerKg: 1000, // 1 cal/gram
            containerSize: 5.5, // 5.5 oz
            containerSizeUnit: .ounces,
            imageUrl: nil,
            isArchived: false,
            createdAt: Date(),
            createdBy: nil
        )

        // 5.5 oz = 155.92225 grams, at 1 cal/gram = ~155.92 calories
        XCTAssertEqual(food.caloriesPerContainer, 155.92225, accuracy: 0.01)
    }

    func testCaloriesPerContainerWithKilograms() {
        let food = PetFood(
            id: UUID(),
            orgId: "family-123",
            name: "Bulk Food",
            category: .dry,
            caloriesPerKg: 3500,
            containerSize: 2.5, // 2.5 kg
            containerSizeUnit: .kilograms,
            imageUrl: nil,
            isArchived: false,
            createdAt: Date(),
            createdBy: nil
        )

        // 2.5 kg = 2500 grams, at 3.5 cal/gram = 8750 calories
        XCTAssertEqual(food.caloriesPerContainer, 8750, accuracy: 0.01)
    }

    func testCalculateCaloriesForAmount() {
        let food = PetFood(
            id: UUID(),
            orgId: "family-123",
            name: "Test Food",
            category: .dry,
            caloriesPerKg: 4000, // 4 cal/gram
            containerSize: 1000,
            containerSizeUnit: .grams,
            imageUrl: nil,
            isArchived: false,
            createdAt: Date(),
            createdBy: nil
        )

        // 50 grams at 4 cal/gram = 200 calories
        XCTAssertEqual(food.calculateCalories(for: 50, unit: .grams), 200, accuracy: 0.001)

        // 1 oz = 28.3495g, at 4 cal/gram = 113.398 calories
        XCTAssertEqual(food.calculateCalories(for: 1, unit: .ounces), 113.398, accuracy: 0.01)
    }

    // MARK: - JSON Decoding Tests

    func testDecodingFromJSON() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "org_id": "family-123",
            "name": "Royal Canin",
            "category": "dry",
            "calories_per_kg": 3800,
            "container_size": 2000,
            "container_size_unit": "g",
            "image_url": "https://example.com/food.jpg",
            "is_archived": false,
            "created_at": "2024-01-15T10:30:00Z",
            "created_by": "user-123"
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let food = try decoder.decode(PetFood.self, from: json)

        XCTAssertEqual(food.name, "Royal Canin")
        XCTAssertEqual(food.category, .dry)
        XCTAssertEqual(food.caloriesPerKg, 3800)
        XCTAssertEqual(food.containerSize, 2000)
        XCTAssertEqual(food.containerSizeUnit, .grams)
        XCTAssertEqual(food.imageUrl, "https://example.com/food.jpg")
    }

    // MARK: - Identifiable & Hashable Tests

    func testIdentifiableConformance() {
        let uuid = UUID()
        let food = PetFood(
            id: uuid,
            orgId: "family-123",
            name: "Test",
            category: .dry,
            caloriesPerKg: 3000,
            containerSize: 100,
            containerSizeUnit: .grams,
            imageUrl: nil,
            isArchived: false,
            createdAt: Date(),
            createdBy: nil
        )

        XCTAssertEqual(food.id, uuid)
    }
}
