//
//  DashboardDataTests.swift
//  Orest's JournalTests
//
//  Unit tests for DashboardData and MedicationWithDoses models.
//

import XCTest
@testable import Orest_s_Journal

final class DashboardDataTests: XCTestCase {

    // MARK: - DashboardData Decoding Tests

    func testDecodingEmptyDashboard() throws {
        let json = """
        {
            "calorie_goal": null,
            "today_feedings": [],
            "total_calories": 0.0,
            "foods": [],
            "medications": []
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let dashboard = try decoder.decode(DashboardData.self, from: json)

        XCTAssertNil(dashboard.calorieGoal)
        XCTAssertEqual(dashboard.todayFeedings.count, 0)
        XCTAssertEqual(dashboard.totalCalories, 0.0)
        XCTAssertEqual(dashboard.foods.count, 0)
        XCTAssertEqual(dashboard.medications.count, 0)
    }

    func testDecodingDashboardWithCalorieGoal() throws {
        let json = """
        {
            "calorie_goal": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "pet_id": "660e8400-e29b-41d4-a716-446655440001",
                "daily_calories": 350.0,
                "effective_from": "2024-01-01T00:00:00Z",
                "effective_until": null,
                "notes": null,
                "created_at": "2024-01-01T10:00:00Z",
                "created_by": null
            },
            "today_feedings": [],
            "total_calories": 150.0,
            "foods": [],
            "medications": []
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let dashboard = try decoder.decode(DashboardData.self, from: json)

        XCTAssertNotNil(dashboard.calorieGoal)
        XCTAssertEqual(dashboard.calorieGoal?.dailyCalories, 350.0)
        XCTAssertEqual(dashboard.totalCalories, 150.0)
    }

    func testDecodingDashboardWithFeedings() throws {
        let json = """
        {
            "calorie_goal": null,
            "today_feedings": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "pet_id": "660e8400-e29b-41d4-a716-446655440001",
                    "food_id": "770e8400-e29b-41d4-a716-446655440002",
                    "fed_by": "user@example.com",
                    "fed_at": "2024-01-15T08:30:00Z",
                    "amount": 100.0,
                    "amount_unit": "g",
                    "calories": 200.0,
                    "notes": null,
                    "created_at": "2024-01-15T08:30:05Z"
                },
                {
                    "id": "880e8400-e29b-41d4-a716-446655440003",
                    "pet_id": "660e8400-e29b-41d4-a716-446655440001",
                    "food_id": "990e8400-e29b-41d4-a716-446655440004",
                    "fed_by": "user@example.com",
                    "fed_at": "2024-01-15T18:00:00Z",
                    "amount": 50.0,
                    "amount_unit": "g",
                    "calories": 100.0,
                    "notes": "Evening meal",
                    "created_at": "2024-01-15T18:00:05Z"
                }
            ],
            "total_calories": 300.0,
            "foods": [],
            "medications": []
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let dashboard = try decoder.decode(DashboardData.self, from: json)

        XCTAssertEqual(dashboard.todayFeedings.count, 2)
        XCTAssertEqual(dashboard.totalCalories, 300.0)
        XCTAssertEqual(dashboard.todayFeedings[0].calories, 200.0)
        XCTAssertEqual(dashboard.todayFeedings[1].notes, "Evening meal")
    }

    func testDecodingDashboardWithFoods() throws {
        let json = """
        {
            "calorie_goal": null,
            "today_feedings": [],
            "total_calories": 0.0,
            "foods": [
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
            ],
            "medications": []
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let dashboard = try decoder.decode(DashboardData.self, from: json)

        XCTAssertEqual(dashboard.foods.count, 1)
        XCTAssertEqual(dashboard.foods[0].name, "Premium Kibble")
        XCTAssertEqual(dashboard.foods[0].category, .dry)
    }

    // MARK: - DashboardData Encoding Tests

    func testEncodingDashboard() throws {
        let dashboard = DashboardData(
            calorieGoal: nil,
            todayFeedings: [],
            totalCalories: 250.0,
            foods: [],
            medications: []
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase

        let data = try encoder.encode(dashboard)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["total_calories"] as? Double, 250.0)
    }

    // MARK: - MedicationWithDoses Decoding Tests

    func testDecodingMedicationWithDoses() throws {
        let json = """
        {
            "medication": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "pet_id": "660e8400-e29b-41d4-a716-446655440001",
                "name": "Antibiotics",
                "medication_type": "pill",
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-01-14T00:00:00Z",
                "times_per_day": 2,
                "notes": "Take with food",
                "reminders_enabled": true,
                "timezone": "America/Los_Angeles",
                "is_archived": false,
                "created_at": "2024-01-01T00:00:00Z",
                "created_by": null
            },
            "last_dose": null,
            "today_dose_count": 1,
            "doses_remaining": 1
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let medWithDoses = try decoder.decode(MedicationWithDoses.self, from: json)

        XCTAssertEqual(medWithDoses.medication.name, "Antibiotics")
        XCTAssertNil(medWithDoses.lastDose)
        XCTAssertEqual(medWithDoses.todayDoseCount, 1)
        XCTAssertEqual(medWithDoses.dosesRemaining, 1)
    }

    func testDecodingMedicationWithLastDose() throws {
        let json = """
        {
            "medication": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "pet_id": "660e8400-e29b-41d4-a716-446655440001",
                "name": "Pain Relief",
                "medication_type": "tablet",
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": null,
                "times_per_day": 1,
                "notes": null,
                "reminders_enabled": false,
                "timezone": "America/Los_Angeles",
                "is_archived": false,
                "created_at": "2024-01-01T00:00:00Z",
                "created_by": null
            },
            "last_dose": {
                "id": "770e8400-e29b-41d4-a716-446655440002",
                "medication_id": "550e8400-e29b-41d4-a716-446655440000",
                "given_at": "2024-01-15T08:00:00Z",
                "given_by": "user@example.com",
                "notes": null,
                "created_at": "2024-01-15T08:00:05Z"
            },
            "today_dose_count": 2,
            "doses_remaining": 0
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let medWithDoses = try decoder.decode(MedicationWithDoses.self, from: json)

        XCTAssertNotNil(medWithDoses.lastDose)
        XCTAssertEqual(medWithDoses.lastDose?.givenBy, "user@example.com")
        XCTAssertEqual(medWithDoses.todayDoseCount, 2)
        XCTAssertEqual(medWithDoses.dosesRemaining, 0)
    }

    // MARK: - MedicationWithDoses Encoding Tests

    func testEncodingMedicationWithDoses() throws {
        let medication = PetMedication(
            id: UUID(),
            petId: UUID(),
            name: "Test Med",
            medicationType: .pill,
            startDate: Date(),
            endDate: nil,
            timesPerDay: 2,
            notes: nil,
            remindersEnabled: true,
            timezone: "America/Los_Angeles",
            isArchived: false,
            createdAt: Date(),
            createdBy: nil,
            scheduledTimes: nil
        )

        let medWithDoses = MedicationWithDoses(
            medication: medication,
            lastDose: nil,
            todayDoseCount: 0,
            dosesRemaining: 2
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase

        let data = try encoder.encode(medWithDoses)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["today_dose_count"] as? Int, 0)
        XCTAssertEqual(jsonObject["doses_remaining"] as? Int, 2)
    }

    // MARK: - Dashboard with Medications Tests

    func testDecodingDashboardWithMedications() throws {
        let json = """
        {
            "calorie_goal": null,
            "today_feedings": [],
            "total_calories": 0.0,
            "foods": [],
            "medications": [
                {
                    "medication": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "pet_id": "660e8400-e29b-41d4-a716-446655440001",
                        "name": "Heartworm Prevention",
                        "medication_type": "tablet",
                        "start_date": "2024-01-01T00:00:00Z",
                        "end_date": null,
                        "times_per_day": 1,
                        "notes": null,
                        "reminders_enabled": true,
                        "timezone": "America/Los_Angeles",
                        "is_archived": false,
                        "created_at": "2024-01-01T00:00:00Z",
                        "created_by": null
                    },
                    "last_dose": null,
                    "today_dose_count": 0,
                    "doses_remaining": 1
                }
            ]
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let dashboard = try decoder.decode(DashboardData.self, from: json)

        XCTAssertEqual(dashboard.medications.count, 1)
        XCTAssertEqual(dashboard.medications[0].medication.name, "Heartworm Prevention")
        XCTAssertEqual(dashboard.medications[0].dosesRemaining, 1)
    }

    // MARK: - Complete Dashboard Tests

    func testDecodingCompleteDashboard() throws {
        let json = """
        {
            "calorie_goal": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "pet_id": "660e8400-e29b-41d4-a716-446655440001",
                "daily_calories": 400.0,
                "effective_from": "2024-01-01T00:00:00Z",
                "effective_until": null,
                "notes": "Weight management",
                "created_at": "2024-01-01T10:00:00Z",
                "created_by": "vet@example.com"
            },
            "today_feedings": [
                {
                    "id": "770e8400-e29b-41d4-a716-446655440002",
                    "pet_id": "660e8400-e29b-41d4-a716-446655440001",
                    "food_id": "880e8400-e29b-41d4-a716-446655440003",
                    "fed_by": "owner@example.com",
                    "fed_at": "2024-01-15T08:30:00Z",
                    "amount": 100.0,
                    "amount_unit": "g",
                    "calories": 200.0,
                    "notes": null,
                    "created_at": "2024-01-15T08:30:05Z"
                }
            ],
            "total_calories": 200.0,
            "foods": [
                {
                    "id": "880e8400-e29b-41d4-a716-446655440003",
                    "org_id": "org-123",
                    "name": "Healthy Kibble",
                    "category": "dry",
                    "calories_per_kg": 3500.0,
                    "container_size": 1000.0,
                    "container_size_unit": "g",
                    "image_url": null,
                    "is_archived": false,
                    "created_at": "2024-01-01T00:00:00Z",
                    "created_by": null
                }
            ],
            "medications": [
                {
                    "medication": {
                        "id": "990e8400-e29b-41d4-a716-446655440004",
                        "pet_id": "660e8400-e29b-41d4-a716-446655440001",
                        "name": "Joint Supplement",
                        "medication_type": "tablet",
                        "start_date": "2024-01-01T00:00:00Z",
                        "end_date": null,
                        "times_per_day": 1,
                        "notes": null,
                        "reminders_enabled": true,
                        "timezone": "America/Los_Angeles",
                        "is_archived": false,
                        "created_at": "2024-01-01T00:00:00Z",
                        "created_by": null
                    },
                    "last_dose": null,
                    "today_dose_count": 0,
                    "doses_remaining": 1
                }
            ]
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let dashboard = try decoder.decode(DashboardData.self, from: json)

        // Verify calorie goal
        XCTAssertNotNil(dashboard.calorieGoal)
        XCTAssertEqual(dashboard.calorieGoal?.dailyCalories, 400.0)
        XCTAssertEqual(dashboard.calorieGoal?.notes, "Weight management")

        // Verify feedings
        XCTAssertEqual(dashboard.todayFeedings.count, 1)
        XCTAssertEqual(dashboard.totalCalories, 200.0)

        // Verify foods
        XCTAssertEqual(dashboard.foods.count, 1)
        XCTAssertEqual(dashboard.foods[0].name, "Healthy Kibble")

        // Verify medications
        XCTAssertEqual(dashboard.medications.count, 1)
        XCTAssertEqual(dashboard.medications[0].medication.name, "Joint Supplement")
    }
}
