//
//  QuickFeedingActionTests.swift
//  Orest's JournalTests
//
//  Unit tests for QuickFeedingAction model.
//

import XCTest
@testable import Orest_s_Journal

final class QuickFeedingActionTests: XCTestCase {

    // MARK: - Test Helpers

    private func makeFood(id: UUID = UUID(), name: String = "Test Food") -> PetFood {
        return PetFood(
            id: id,
            orgId: "org-123",
            name: name,
            category: .dry,
            caloriesPerKg: 3500,
            containerSize: 1000,
            containerSizeUnit: .grams,
            imageUrl: nil,
            isArchived: false,
            createdAt: Date(),
            createdBy: nil
        )
    }

    private func makeFeeding(
        id: UUID = UUID(),
        foodId: UUID,
        amount: Double = 100,
        amountUnit: ContainerUnit = .grams,
        calories: Double = 200
    ) -> PetFeeding {
        return PetFeeding(
            id: id,
            petId: UUID(),
            foodId: foodId,
            fedBy: "test@example.com",
            fedAt: Date(),
            amount: amount,
            amountUnit: amountUnit,
            calories: calories,
            notes: nil,
            createdAt: Date()
        )
    }

    // MARK: - Initialization Tests

    func testInitFromFeedingAndFood() {
        let foodId = UUID()
        let food = makeFood(id: foodId, name: "Premium Kibble")
        let feeding = makeFeeding(foodId: foodId, amount: 150, amountUnit: .grams, calories: 300)

        let action = QuickFeedingAction(from: feeding, food: food)

        XCTAssertEqual(action.foodId, foodId)
        XCTAssertEqual(action.foodName, "Premium Kibble")
        XCTAssertEqual(action.amount, 150)
        XCTAssertEqual(action.amountUnit, .grams)
        XCTAssertEqual(action.calories, 300)
    }

    func testIdUsesFoodId() {
        let foodId = UUID()
        let food = makeFood(id: foodId)
        let feeding = makeFeeding(foodId: foodId)

        let action = QuickFeedingAction(from: feeding, food: food)

        // id should be the foodId for deduplication purposes
        XCTAssertEqual(action.id, foodId)
    }

    // MARK: - Identifiable Tests

    func testQuickFeedingActionIdentifiable() {
        let foodId = UUID()
        let food = makeFood(id: foodId)
        let feeding = makeFeeding(foodId: foodId)

        let action = QuickFeedingAction(from: feeding, food: food)

        XCTAssertEqual(action.id, foodId)
    }

    // MARK: - Equatable Tests

    func testEquatableSameValues() {
        let foodId = UUID()
        let food = makeFood(id: foodId, name: "Kibble")
        let feeding1 = makeFeeding(foodId: foodId, amount: 100, amountUnit: .grams, calories: 200)
        let feeding2 = makeFeeding(foodId: foodId, amount: 100, amountUnit: .grams, calories: 200)

        let action1 = QuickFeedingAction(from: feeding1, food: food)
        let action2 = QuickFeedingAction(from: feeding2, food: food)

        XCTAssertEqual(action1, action2)
    }

    func testEquatableDifferentAmounts() {
        let foodId = UUID()
        let food = makeFood(id: foodId)
        let feeding1 = makeFeeding(foodId: foodId, amount: 100, calories: 200)
        let feeding2 = makeFeeding(foodId: foodId, amount: 150, calories: 300)

        let action1 = QuickFeedingAction(from: feeding1, food: food)
        let action2 = QuickFeedingAction(from: feeding2, food: food)

        XCTAssertNotEqual(action1, action2)
    }

    func testEquatableDifferentFoods() {
        let foodId1 = UUID()
        let foodId2 = UUID()
        let food1 = makeFood(id: foodId1, name: "Kibble")
        let food2 = makeFood(id: foodId2, name: "Wet Food")
        let feeding1 = makeFeeding(foodId: foodId1)
        let feeding2 = makeFeeding(foodId: foodId2)

        let action1 = QuickFeedingAction(from: feeding1, food: food1)
        let action2 = QuickFeedingAction(from: feeding2, food: food2)

        XCTAssertNotEqual(action1, action2)
    }

    func testEquatableDifferentUnits() {
        let foodId = UUID()
        let food = makeFood(id: foodId)
        let feeding1 = makeFeeding(foodId: foodId, amountUnit: .grams)
        let feeding2 = makeFeeding(foodId: foodId, amountUnit: .ounces)

        let action1 = QuickFeedingAction(from: feeding1, food: food)
        let action2 = QuickFeedingAction(from: feeding2, food: food)

        XCTAssertNotEqual(action1, action2)
    }

    // MARK: - Unit Type Tests

    func testWithGramsUnit() {
        let foodId = UUID()
        let food = makeFood(id: foodId)
        let feeding = makeFeeding(foodId: foodId, amountUnit: .grams)

        let action = QuickFeedingAction(from: feeding, food: food)

        XCTAssertEqual(action.amountUnit, .grams)
    }

    func testWithOuncesUnit() {
        let foodId = UUID()
        let food = makeFood(id: foodId)
        let feeding = makeFeeding(foodId: foodId, amountUnit: .ounces)

        let action = QuickFeedingAction(from: feeding, food: food)

        XCTAssertEqual(action.amountUnit, .ounces)
    }

    func testWithKilogramsUnit() {
        let foodId = UUID()
        let food = makeFood(id: foodId)
        let feeding = makeFeeding(foodId: foodId, amountUnit: .kilograms)

        let action = QuickFeedingAction(from: feeding, food: food)

        XCTAssertEqual(action.amountUnit, .kilograms)
    }

    func testWithPoundsUnit() {
        let foodId = UUID()
        let food = makeFood(id: foodId)
        let feeding = makeFeeding(foodId: foodId, amountUnit: .pounds)

        let action = QuickFeedingAction(from: feeding, food: food)

        XCTAssertEqual(action.amountUnit, .pounds)
    }

    // MARK: - Value Tests

    func testSmallAmount() {
        let foodId = UUID()
        let food = makeFood(id: foodId)
        let feeding = makeFeeding(foodId: foodId, amount: 0.5, calories: 10)

        let action = QuickFeedingAction(from: feeding, food: food)

        XCTAssertEqual(action.amount, 0.5)
        XCTAssertEqual(action.calories, 10)
    }

    func testLargeAmount() {
        let foodId = UUID()
        let food = makeFood(id: foodId)
        let feeding = makeFeeding(foodId: foodId, amount: 1000, calories: 2000)

        let action = QuickFeedingAction(from: feeding, food: food)

        XCTAssertEqual(action.amount, 1000)
        XCTAssertEqual(action.calories, 2000)
    }
}
