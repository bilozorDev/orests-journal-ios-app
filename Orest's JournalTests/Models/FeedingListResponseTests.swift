//
//  FeedingListResponseTests.swift
//  Orest's JournalTests
//
//  Unit tests for FeedingListResponse and related response types.
//

import XCTest
@testable import Orest_s_Journal

final class FeedingListResponseTests: XCTestCase {

    // MARK: - FeedingListResponse Decoding Tests

    func testDecodingFeedingListResponse() throws {
        let json = """
        {
            "feedings": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "pet_id": "660e8400-e29b-41d4-a716-446655440001",
                    "food_id": "770e8400-e29b-41d4-a716-446655440002",
                    "amount": 50.0,
                    "amount_unit": "g",
                    "calories": 175.0,
                    "notes": "Morning feeding",
                    "fed_at": "2024-01-15T08:30:00Z",
                    "fed_by": "user@example.com",
                    "created_at": "2024-01-15T08:30:05Z"
                }
            ],
            "total_calories": 175.0,
            "total": 1
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let response = try decoder.decode(FeedingListResponse.self, from: json)

        XCTAssertEqual(response.feedings.count, 1)
        XCTAssertEqual(response.totalCalories, 175.0)
        XCTAssertEqual(response.total, 1)
        XCTAssertEqual(response.feedings[0].fedBy, "user@example.com")
        XCTAssertEqual(response.feedings[0].calories, 175.0)
    }

    func testDecodingEmptyFeedingListResponse() throws {
        let json = """
        {
            "feedings": [],
            "total_calories": 0.0,
            "total": 0
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase

        let response = try decoder.decode(FeedingListResponse.self, from: json)

        XCTAssertEqual(response.feedings.count, 0)
        XCTAssertEqual(response.totalCalories, 0.0)
        XCTAssertEqual(response.total, 0)
    }

    func testDecodingMultipleFeedingsResponse() throws {
        let json = """
        {
            "feedings": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "pet_id": "660e8400-e29b-41d4-a716-446655440001",
                    "food_id": "770e8400-e29b-41d4-a716-446655440002",
                    "amount": 50.0,
                    "amount_unit": "g",
                    "calories": 175.0,
                    "notes": null,
                    "fed_at": "2024-01-15T08:30:00Z",
                    "fed_by": "user@example.com",
                    "created_at": "2024-01-15T08:30:05Z"
                },
                {
                    "id": "880e8400-e29b-41d4-a716-446655440003",
                    "pet_id": "660e8400-e29b-41d4-a716-446655440001",
                    "food_id": "990e8400-e29b-41d4-a716-446655440004",
                    "amount": 100.0,
                    "amount_unit": "g",
                    "calories": 80.0,
                    "notes": "Dinner",
                    "fed_at": "2024-01-15T18:00:00Z",
                    "fed_by": "other@example.com",
                    "created_at": "2024-01-15T18:00:05Z"
                }
            ],
            "total_calories": 255.0,
            "total": 2
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let response = try decoder.decode(FeedingListResponse.self, from: json)

        XCTAssertEqual(response.feedings.count, 2)
        XCTAssertEqual(response.totalCalories, 255.0)
        XCTAssertEqual(response.total, 2)
        XCTAssertEqual(response.feedings[0].calories, 175.0)
        XCTAssertEqual(response.feedings[1].notes, "Dinner")
    }

    // MARK: - FeedingListResponse Encoding Tests

    func testEncodingFeedingListResponse() throws {
        let feeding = PetFeeding(
            id: UUID(),
            petId: UUID(),
            foodId: UUID(),
            fedBy: "test@example.com",
            fedAt: Date(),
            amount: 50.0,
            amountUnit: .grams,
            calories: 175.0,
            notes: nil,
            createdAt: Date()
        )

        let response = FeedingListResponse(
            feedings: [feeding],
            totalCalories: 175.0,
            total: 1
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.dateEncodingStrategy = .iso8601

        let data = try encoder.encode(response)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["total_calories"] as? Double, 175.0)
        XCTAssertEqual(jsonObject["total"] as? Int, 1)
        XCTAssertNotNil(jsonObject["feedings"])
    }

    // MARK: - PetListResponse Tests

    func testDecodingPetListResponse() throws {
        let json = """
        {
            "pets": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "org_id": "org-123",
                    "name": "Buddy",
                    "kind": "Dog",
                    "photo_url": null,
                    "current_weight": 25.5,
                    "created_at": "2024-01-01T00:00:00Z",
                    "created_by": "owner@example.com"
                }
            ]
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let response = try decoder.decode(PetListResponse.self, from: json)

        XCTAssertEqual(response.pets.count, 1)
        XCTAssertEqual(response.pets[0].name, "Buddy")
    }

    func testDecodingEmptyPetListResponse() throws {
        let json = """
        {
            "pets": []
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase

        let response = try decoder.decode(PetListResponse.self, from: json)

        XCTAssertEqual(response.pets.count, 0)
    }

    // MARK: - FoodListResponse Tests

    func testDecodingFoodListResponse() throws {
        let json = """
        {
            "foods": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "org_id": "org-123",
                    "name": "Premium Kibble",
                    "category": "dry",
                    "calories_per_kg": 3500.0,
                    "container_size": 2000.0,
                    "container_size_unit": "g",
                    "image_url": null,
                    "is_archived": false,
                    "created_at": "2024-01-01T00:00:00Z",
                    "created_by": null
                }
            ]
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let response = try decoder.decode(FoodListResponse.self, from: json)

        XCTAssertEqual(response.foods.count, 1)
        XCTAssertEqual(response.foods[0].name, "Premium Kibble")
    }

    // MARK: - MedicationListResponse Tests

    func testDecodingMedicationListResponse() throws {
        let json = """
        {
            "medications": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "pet_id": "660e8400-e29b-41d4-a716-446655440001",
                    "name": "Antibiotics",
                    "medication_type": "pill",
                    "start_date": "2024-01-01T00:00:00Z",
                    "end_date": null,
                    "times_per_day": 2,
                    "notes": null,
                    "reminders_enabled": true,
                    "timezone": "America/Los_Angeles",
                    "is_archived": false,
                    "created_at": "2024-01-01T00:00:00Z",
                    "created_by": null,
                    "scheduled_times": null
                }
            ]
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let response = try decoder.decode(MedicationListResponse.self, from: json)

        XCTAssertEqual(response.medications.count, 1)
        XCTAssertEqual(response.medications[0].name, "Antibiotics")
    }

    // MARK: - DoseListResponse Tests

    func testDecodingDoseListResponse() throws {
        let json = """
        {
            "doses": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "medication_id": "660e8400-e29b-41d4-a716-446655440001",
                    "given_at": "2024-01-15T08:30:00Z",
                    "given_by": "user@example.com",
                    "notes": null,
                    "created_at": "2024-01-15T08:30:05Z"
                }
            ]
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let response = try decoder.decode(DoseListResponse.self, from: json)

        XCTAssertEqual(response.doses.count, 1)
        XCTAssertEqual(response.doses[0].givenBy, "user@example.com")
    }

    func testDecodingEmptyDoseListResponse() throws {
        let json = """
        {
            "doses": []
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase

        let response = try decoder.decode(DoseListResponse.self, from: json)

        XCTAssertEqual(response.doses.count, 0)
    }

    // MARK: - MedicationWithDoses Tests

    func testDecodingMedicationWithDoses() throws {
        let json = """
        {
            "medication": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "pet_id": "660e8400-e29b-41d4-a716-446655440001",
                "name": "Pain Relief",
                "medication_type": "pill",
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": null,
                "times_per_day": 2,
                "notes": null,
                "reminders_enabled": false,
                "timezone": "UTC",
                "is_archived": false,
                "created_at": "2024-01-01T00:00:00Z",
                "created_by": null,
                "scheduled_times": null
            },
            "last_dose": {
                "id": "770e8400-e29b-41d4-a716-446655440002",
                "medication_id": "550e8400-e29b-41d4-a716-446655440000",
                "given_at": "2024-01-15T08:30:00Z",
                "given_by": "user@example.com",
                "notes": null,
                "created_at": "2024-01-15T08:30:05Z"
            },
            "today_dose_count": 1,
            "doses_remaining": 1
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let response = try decoder.decode(MedicationWithDoses.self, from: json)

        XCTAssertEqual(response.medication.name, "Pain Relief")
        XCTAssertNotNil(response.lastDose)
        XCTAssertEqual(response.todayDoseCount, 1)
        XCTAssertEqual(response.dosesRemaining, 1)
    }

    func testDecodingMedicationWithDosesNoLastDose() throws {
        let json = """
        {
            "medication": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "pet_id": "660e8400-e29b-41d4-a716-446655440001",
                "name": "Vitamins",
                "medication_type": "liquid",
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": null,
                "times_per_day": 1,
                "notes": null,
                "reminders_enabled": false,
                "timezone": "UTC",
                "is_archived": false,
                "created_at": "2024-01-01T00:00:00Z",
                "created_by": null,
                "scheduled_times": null
            },
            "last_dose": null,
            "today_dose_count": 0,
            "doses_remaining": 1
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let response = try decoder.decode(MedicationWithDoses.self, from: json)

        XCTAssertEqual(response.medication.name, "Vitamins")
        XCTAssertNil(response.lastDose)
        XCTAssertEqual(response.todayDoseCount, 0)
        XCTAssertEqual(response.dosesRemaining, 1)
    }
}
