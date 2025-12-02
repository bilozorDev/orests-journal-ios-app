//
//  APIRequestTypesTests.swift
//  Orest's JournalTests
//
//  Unit tests for API request types (Create/Update structs).
//

import XCTest
@testable import Orest_s_Journal

final class APIRequestTypesTests: XCTestCase {

    // MARK: - PetCreate Tests

    func testPetCreateEncodingWithAllFields() throws {
        let create = PetCreate(
            name: "Buddy",
            kind: "Dog",
            photoUrl: "https://example.com/photo.jpg",
            currentWeight: 25.5
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase

        let data = try encoder.encode(create)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["name"] as? String, "Buddy")
        XCTAssertEqual(jsonObject["kind"] as? String, "Dog")
        XCTAssertEqual(jsonObject["photo_url"] as? String, "https://example.com/photo.jpg")
        XCTAssertEqual(jsonObject["current_weight"] as? Double, 25.5)
    }

    func testPetCreateEncodingWithOptionalFieldsNil() throws {
        let create = PetCreate(
            name: "Whiskers",
            kind: "Cat",
            photoUrl: nil,
            currentWeight: nil
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase

        let data = try encoder.encode(create)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["name"] as? String, "Whiskers")
        XCTAssertEqual(jsonObject["kind"] as? String, "Cat")
        XCTAssertTrue(jsonObject["photo_url"] is NSNull || jsonObject["photo_url"] == nil)
        XCTAssertTrue(jsonObject["current_weight"] is NSNull || jsonObject["current_weight"] == nil)
    }

    // MARK: - PetUpdate Tests

    func testPetUpdateEncodingPartial() throws {
        let update = PetUpdate(
            name: "New Name",
            kind: nil,
            photoUrl: nil,
            currentWeight: nil
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase

        let data = try encoder.encode(update)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["name"] as? String, "New Name")
    }

    func testPetUpdateEncodingFullUpdate() throws {
        let update = PetUpdate(
            name: "Updated Pet",
            kind: "Cat",
            photoUrl: "https://example.com/new-photo.jpg",
            currentWeight: 15.0
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase

        let data = try encoder.encode(update)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["name"] as? String, "Updated Pet")
        XCTAssertEqual(jsonObject["kind"] as? String, "Cat")
        XCTAssertEqual(jsonObject["photo_url"] as? String, "https://example.com/new-photo.jpg")
        XCTAssertEqual(jsonObject["current_weight"] as? Double, 15.0)
    }

    // MARK: - FoodCreate Tests

    func testFoodCreateEncoding() throws {
        let create = FoodCreate(
            name: "Premium Kibble",
            category: "dry",
            caloriesPerKg: 3500,
            containerSize: 2000,
            containerSizeUnit: "g",
            imageUrl: "https://example.com/food.jpg"
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase

        let data = try encoder.encode(create)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["name"] as? String, "Premium Kibble")
        XCTAssertEqual(jsonObject["category"] as? String, "dry")
        XCTAssertEqual(jsonObject["calories_per_kg"] as? Double, 3500)
        XCTAssertEqual(jsonObject["container_size"] as? Double, 2000)
        XCTAssertEqual(jsonObject["container_size_unit"] as? String, "g")
        XCTAssertEqual(jsonObject["image_url"] as? String, "https://example.com/food.jpg")
    }

    func testFoodCreateEncodingWithNilImage() throws {
        let create = FoodCreate(
            name: "Basic Food",
            category: "wet",
            caloriesPerKg: 1000,
            containerSize: 400,
            containerSizeUnit: "g",
            imageUrl: nil
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase

        let data = try encoder.encode(create)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["name"] as? String, "Basic Food")
        XCTAssertEqual(jsonObject["category"] as? String, "wet")
    }

    // MARK: - FoodUpdate Tests

    func testFoodUpdatePartialEncoding() throws {
        let update = FoodUpdate(
            name: "New Food Name",
            category: nil,
            caloriesPerKg: nil,
            containerSize: nil,
            containerSizeUnit: nil,
            imageUrl: nil
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase

        let data = try encoder.encode(update)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["name"] as? String, "New Food Name")
    }

    func testFoodUpdateFullEncoding() throws {
        let update = FoodUpdate(
            name: "Updated Food",
            category: "treats",
            caloriesPerKg: 4000.0,
            containerSize: 500.0,
            containerSizeUnit: "g",
            imageUrl: "https://example.com/updated.jpg"
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase

        let data = try encoder.encode(update)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["name"] as? String, "Updated Food")
        XCTAssertEqual(jsonObject["category"] as? String, "treats")
        XCTAssertEqual(jsonObject["calories_per_kg"] as? Double, 4000.0)
    }

    // MARK: - FeedingCreate Tests

    func testFeedingCreateEncoding() throws {
        let petId = UUID()
        let foodId = UUID()

        let create = FeedingCreate(
            petId: petId,
            foodId: foodId,
            amount: 50.0,
            amountUnit: "g",
            calories: 175.0,
            notes: "Morning feeding",
            fedAt: nil
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase

        let data = try encoder.encode(create)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["pet_id"] as? String, petId.uuidString)
        XCTAssertEqual(jsonObject["food_id"] as? String, foodId.uuidString)
        XCTAssertEqual(jsonObject["amount"] as? Double, 50.0)
        XCTAssertEqual(jsonObject["amount_unit"] as? String, "g")
        XCTAssertEqual(jsonObject["calories"] as? Double, 175.0)
        XCTAssertEqual(jsonObject["notes"] as? String, "Morning feeding")
    }

    func testFeedingCreateEncodingWithFedAtDate() throws {
        let petId = UUID()
        let foodId = UUID()
        let fedAt = Date(timeIntervalSince1970: 1705307400)

        let create = FeedingCreate(
            petId: petId,
            foodId: foodId,
            amount: 100.0,
            amountUnit: "g",
            calories: 350.0,
            notes: nil,
            fedAt: fedAt
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.dateEncodingStrategy = .iso8601

        let data = try encoder.encode(create)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertNotNil(jsonObject["fed_at"])
    }

    // MARK: - FeedingUpdate Tests

    func testFeedingUpdatePartialEncoding() throws {
        let update = FeedingUpdate(
            amount: 75.0,
            amountUnit: nil,
            calories: nil,
            notes: nil,
            fedAt: nil,
            fedBy: nil
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase

        let data = try encoder.encode(update)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["amount"] as? Double, 75.0)
    }

    func testFeedingUpdateWithFedBy() throws {
        let fedByUserId = UUID()

        let update = FeedingUpdate(
            amount: nil,
            amountUnit: nil,
            calories: nil,
            notes: "Updated notes",
            fedAt: nil,
            fedBy: fedByUserId
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase

        let data = try encoder.encode(update)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["notes"] as? String, "Updated notes")
        XCTAssertEqual(jsonObject["fed_by"] as? String, fedByUserId.uuidString)
    }

    // MARK: - MedicationCreate Tests

    func testMedicationCreateEncoding() throws {
        let petId = UUID()
        let startDate = Date(timeIntervalSince1970: 1704067200)

        let create = MedicationCreate(
            petId: petId,
            name: "Antibiotics",
            medicationType: "pill",
            startDate: startDate,
            endDate: nil,
            timesPerDay: 2,
            notes: "Give with food",
            remindersEnabled: true,
            timezone: "America/Los_Angeles",
            scheduledTimes: [
                ScheduledTimeCreate(hour: 8, minute: 0),
                ScheduledTimeCreate(hour: 20, minute: 0)
            ]
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.dateEncodingStrategy = .iso8601

        let data = try encoder.encode(create)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["pet_id"] as? String, petId.uuidString)
        XCTAssertEqual(jsonObject["name"] as? String, "Antibiotics")
        XCTAssertEqual(jsonObject["medication_type"] as? String, "pill")
        XCTAssertEqual(jsonObject["times_per_day"] as? Int, 2)
        XCTAssertEqual(jsonObject["notes"] as? String, "Give with food")
        XCTAssertEqual(jsonObject["reminders_enabled"] as? Bool, true)
        XCTAssertEqual(jsonObject["timezone"] as? String, "America/Los_Angeles")

        let times = jsonObject["scheduled_times"] as? [[String: Any]]
        XCTAssertEqual(times?.count, 2)
    }

    func testMedicationCreateEncodingWithoutReminders() throws {
        let petId = UUID()
        let startDate = Date()

        let create = MedicationCreate(
            petId: petId,
            name: "Vitamins",
            medicationType: "liquid",
            startDate: startDate,
            endDate: nil,
            timesPerDay: 1,
            notes: nil,
            remindersEnabled: nil,
            timezone: nil,
            scheduledTimes: nil
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.dateEncodingStrategy = .iso8601

        let data = try encoder.encode(create)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["name"] as? String, "Vitamins")
        XCTAssertEqual(jsonObject["medication_type"] as? String, "liquid")
        XCTAssertEqual(jsonObject["times_per_day"] as? Int, 1)
    }

    // MARK: - DoseCreate Tests

    func testDoseCreateEncoding() throws {
        let medicationId = UUID()

        let create = DoseCreate(
            medicationId: medicationId,
            notes: "Given with breakfast",
            givenAt: nil
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase

        let data = try encoder.encode(create)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["medication_id"] as? String, medicationId.uuidString)
        XCTAssertEqual(jsonObject["notes"] as? String, "Given with breakfast")
    }

    func testDoseCreateEncodingWithGivenAt() throws {
        let medicationId = UUID()
        let givenAt = Date(timeIntervalSince1970: 1705307400)

        let create = DoseCreate(
            medicationId: medicationId,
            notes: nil,
            givenAt: givenAt
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.dateEncodingStrategy = .iso8601

        let data = try encoder.encode(create)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertNotNil(jsonObject["given_at"])
    }

    // MARK: - DoseUpdate Tests

    func testDoseUpdateEncoding() throws {
        let givenBy = UUID()
        let givenAt = Date(timeIntervalSince1970: 1705307400)

        let update = DoseUpdate(
            givenAt: givenAt,
            givenBy: givenBy,
            notes: "Updated note"
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.dateEncodingStrategy = .iso8601

        let data = try encoder.encode(update)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["given_by"] as? String, givenBy.uuidString)
        XCTAssertEqual(jsonObject["notes"] as? String, "Updated note")
        XCTAssertNotNil(jsonObject["given_at"])
    }

    func testDoseUpdatePartialEncoding() throws {
        let update = DoseUpdate(
            givenAt: nil,
            givenBy: nil,
            notes: "Just updating notes"
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase

        let data = try encoder.encode(update)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["notes"] as? String, "Just updating notes")
    }

    // MARK: - HealthEventCreate Tests

    func testHealthEventCreateEncoding() throws {
        let occurredAt = Date(timeIntervalSince1970: 1705307400)

        let create = HealthEventCreate(
            categoryName: "Vomiting",
            occurredAt: occurredAt,
            notes: "After eating"
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.dateEncodingStrategy = .iso8601

        let data = try encoder.encode(create)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["category_name"] as? String, "Vomiting")
        XCTAssertEqual(jsonObject["notes"] as? String, "After eating")
        XCTAssertNotNil(jsonObject["occurred_at"])
    }

    func testHealthEventCreateEncodingMinimal() throws {
        let create = HealthEventCreate(
            categoryName: "Diarrhea",
            occurredAt: nil,
            notes: nil
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase

        let data = try encoder.encode(create)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["category_name"] as? String, "Diarrhea")
    }
}
