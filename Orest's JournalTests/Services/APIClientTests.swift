//
//  APIClientTests.swift
//  Orest's JournalTests
//
//  Unit tests for APIClient using MockURLProtocol.
//

import XCTest
@testable import Orest_s_Journal

final class APIClientTests: XCTestCase {

    // MARK: - APIError Tests

    func testAPIErrorInvalidURLDescription() {
        let error = APIError.invalidURL
        XCTAssertEqual(error.errorDescription, "Invalid URL")
    }

    func testAPIErrorInvalidResponseDescription() {
        let error = APIError.invalidResponse
        XCTAssertEqual(error.errorDescription, "Invalid response from server")
    }

    func testAPIErrorHTTPErrorDescription() {
        let error = APIError.httpError(statusCode: 500, message: "Internal Server Error")
        XCTAssertEqual(error.errorDescription, "HTTP 500: Internal Server Error")
    }

    func testAPIErrorUnauthorizedDescription() {
        let error = APIError.unauthorized
        XCTAssertEqual(error.errorDescription, "Unauthorized. Please sign in again.")
    }

    func testAPIErrorNotFoundDescription() {
        let error = APIError.notFound
        XCTAssertEqual(error.errorDescription, "Resource not found")
    }

    func testAPIErrorDecodingErrorDescription() {
        let underlyingError = NSError(domain: "Test", code: 1, userInfo: [NSLocalizedDescriptionKey: "Invalid JSON"])
        let error = APIError.decodingError(underlyingError)
        XCTAssertTrue(error.errorDescription?.contains("Failed to decode response") ?? false)
    }

    func testAPIErrorNetworkErrorDescription() {
        let underlyingError = NSError(domain: NSURLErrorDomain, code: NSURLErrorTimedOut, userInfo: [NSLocalizedDescriptionKey: "The request timed out"])
        let error = APIError.networkError(underlyingError)
        XCTAssertTrue(error.errorDescription?.contains("Network error") ?? false)
    }

    // MARK: - APIConfiguration Tests

    func testAPIConfigurationBaseURL() {
        // Verify the base URL is set (actual value may vary by environment)
        XCTAssertFalse(APIConfiguration.baseURL.isEmpty)
        XCTAssertTrue(APIConfiguration.baseURL.contains("/api/v1"))
    }

    // MARK: - Request/Response Type Tests

    func testPetCreateEncoding() throws {
        let petCreate = PetCreate(
            name: "Max",
            kind: "dog",
            photoUrl: "https://example.com/photo.jpg",
            currentWeight: 25.5
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase

        let data = try encoder.encode(petCreate)
        let json = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(json["name"] as? String, "Max")
        XCTAssertEqual(json["kind"] as? String, "dog")
        XCTAssertEqual(json["photo_url"] as? String, "https://example.com/photo.jpg")
        XCTAssertEqual(json["current_weight"] as? Double, 25.5)
    }

    func testPetUpdateEncoding() throws {
        let petUpdate = PetUpdate(
            name: "Buddy",
            kind: nil,
            photoUrl: nil,
            currentWeight: 30.0
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase

        let data = try encoder.encode(petUpdate)
        let json = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(json["name"] as? String, "Buddy")
        XCTAssertEqual(json["current_weight"] as? Double, 30.0)
    }

    func testPetListResponseDecoding() throws {
        let json = """
        {
            "pets": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "org_id": "family-123",
                    "name": "Max",
                    "kind": "dog",
                    "photo_url": null,
                    "current_weight": 25.5,
                    "is_archived": false,
                    "created_at": "2024-01-15T10:30:00Z",
                    "created_by": null
                }
            ]
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let response = try decoder.decode(PetListResponse.self, from: json)

        XCTAssertEqual(response.pets.count, 1)
        XCTAssertEqual(response.pets[0].name, "Max")
    }

    func testFoodCreateEncoding() throws {
        let foodCreate = FoodCreate(
            name: "Premium Kibble",
            category: "dry",
            caloriesPerKg: 3500,
            containerSize: 2000,
            containerSizeUnit: "g",
            imageUrl: nil
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase

        let data = try encoder.encode(foodCreate)
        let json = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(json["name"] as? String, "Premium Kibble")
        XCTAssertEqual(json["category"] as? String, "dry")
        XCTAssertEqual(json["calories_per_kg"] as? Double, 3500)
        XCTAssertEqual(json["container_size"] as? Double, 2000)
        XCTAssertEqual(json["container_size_unit"] as? String, "g")
    }

    func testFeedingCreateEncoding() throws {
        let petId = UUID()
        let foodId = UUID()

        let feedingCreate = FeedingCreate(
            petId: petId,
            foodId: foodId,
            amount: 50,
            amountUnit: "g",
            calories: 175,
            notes: "Morning meal",
            fedAt: nil
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase

        let data = try encoder.encode(feedingCreate)
        let json = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(json["pet_id"] as? String, petId.uuidString)
        XCTAssertEqual(json["food_id"] as? String, foodId.uuidString)
        XCTAssertEqual(json["amount"] as? Double, 50)
        XCTAssertEqual(json["amount_unit"] as? String, "g")
        XCTAssertEqual(json["calories"] as? Double, 175)
        XCTAssertEqual(json["notes"] as? String, "Morning meal")
    }

    func testFeedingListResponseDecoding() throws {
        let json = """
        {
            "feedings": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "pet_id": "660e8400-e29b-41d4-a716-446655440001",
                    "food_id": "770e8400-e29b-41d4-a716-446655440002",
                    "fed_by": "user-123",
                    "fed_at": "2024-01-15T08:00:00Z",
                    "amount": 50,
                    "amount_unit": "g",
                    "calories": 175,
                    "notes": null,
                    "created_at": "2024-01-15T08:00:00Z"
                }
            ],
            "total_calories": 175,
            "total": 1
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let response = try decoder.decode(FeedingListResponse.self, from: json)

        XCTAssertEqual(response.feedings.count, 1)
        XCTAssertEqual(response.totalCalories, 175)
        XCTAssertEqual(response.total, 1)
        XCTAssertEqual(response.feedings[0].amount, 50)
    }

    func testMedicationCreateEncoding() throws {
        let petId = UUID()
        let startDate = Date()

        let medicationCreate = MedicationCreate(
            petId: petId,
            name: "Antibiotics",
            medicationType: "pill",
            startDate: startDate,
            endDate: nil,
            timesPerDay: 2,
            notes: "Give with food",
            remindersEnabled: true,
            timezone: "America/New_York",
            scheduledTimes: [
                ScheduledTimeCreate(hour: 8, minute: 0),
                ScheduledTimeCreate(hour: 20, minute: 0)
            ]
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.dateEncodingStrategy = .iso8601

        let data = try encoder.encode(medicationCreate)
        let json = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(json["name"] as? String, "Antibiotics")
        XCTAssertEqual(json["medication_type"] as? String, "pill")
        XCTAssertEqual(json["times_per_day"] as? Int, 2)
        XCTAssertEqual(json["reminders_enabled"] as? Bool, true)
        XCTAssertEqual(json["timezone"] as? String, "America/New_York")

        if let scheduledTimes = json["scheduled_times"] as? [[String: Any]] {
            XCTAssertEqual(scheduledTimes.count, 2)
            XCTAssertEqual(scheduledTimes[0]["hour"] as? Int, 8)
            XCTAssertEqual(scheduledTimes[1]["hour"] as? Int, 20)
        } else {
            XCTFail("scheduled_times should be present")
        }
    }

    func testDoseCreateEncoding() throws {
        let medicationId = UUID()

        let doseCreate = DoseCreate(
            medicationId: medicationId,
            notes: "Taken without issues",
            givenAt: nil
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase

        let data = try encoder.encode(doseCreate)
        let json = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(json["medication_id"] as? String, medicationId.uuidString)
        XCTAssertEqual(json["notes"] as? String, "Taken without issues")
    }

    func testHealthEventCreateEncoding() throws {
        let healthEventCreate = HealthEventCreate(
            categoryName: "Vomiting",
            occurredAt: Date(),
            notes: "After breakfast"
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.dateEncodingStrategy = .iso8601

        let data = try encoder.encode(healthEventCreate)
        let json = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(json["category_name"] as? String, "Vomiting")
        XCTAssertEqual(json["notes"] as? String, "After breakfast")
    }

    func testDashboardDataDecoding() throws {
        let json = """
        {
            "calorie_goal": null,
            "today_feedings": [],
            "total_calories": 0,
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
        XCTAssertEqual(dashboard.totalCalories, 0)
        XCTAssertEqual(dashboard.foods.count, 0)
        XCTAssertEqual(dashboard.medications.count, 0)
    }

    // MARK: - Device Token Request/Response Tests

    func testDeviceTokenRequestEncoding() throws {
        let request = DeviceTokenRequest(
            deviceToken: "abc123token",
            deviceName: "iPhone 15 Pro"
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase

        let data = try encoder.encode(request)
        let json = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(json["device_token"] as? String, "abc123token")
        XCTAssertEqual(json["device_name"] as? String, "iPhone 15 Pro")
    }

    func testDeviceTokenResponseDecoding() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "user_id": "660e8400-e29b-41d4-a716-446655440001",
            "device_token": "abc123token",
            "device_name": "iPhone 15 Pro",
            "platform": "ios",
            "is_active": true,
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:30:00Z"
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let response = try decoder.decode(DeviceTokenResponse.self, from: json)

        XCTAssertEqual(response.deviceToken, "abc123token")
        XCTAssertEqual(response.deviceName, "iPhone 15 Pro")
        XCTAssertEqual(response.platform, "ios")
        XCTAssertTrue(response.isActive)
    }

    // MARK: - MockAPIClient Tests

    func testMockAPIClientGetRequest() async throws {
        let mockClient = MockAPIClient()
        mockClient.authToken = "test-token"
        mockClient.currentOrgId = "org-123"

        let expectedPets = [
            Pet(
                id: UUID(),
                orgId: "org-123",
                name: "Max",
                kind: "dog",
                photoUrl: nil,
                currentWeight: 25.5,
                isArchived: false,
                createdAt: Date(),
                createdBy: nil
            )
        ]

        mockClient.stubbedGetResponses["/pets"] = expectedPets

        let pets: [Pet] = try await mockClient.get("/pets", queryItems: nil)

        XCTAssertEqual(pets.count, 1)
        XCTAssertEqual(pets[0].name, "Max")
        XCTAssertEqual(mockClient.capturedGetPaths, ["/pets"])
    }

    func testMockAPIClientPostRequest() async throws {
        let mockClient = MockAPIClient()

        let expectedPet = Pet(
            id: UUID(),
            orgId: "org-123",
            name: "Buddy",
            kind: "dog",
            photoUrl: nil,
            currentWeight: 30.0,
            isArchived: false,
            createdAt: Date(),
            createdBy: nil
        )

        mockClient.stubbedPostResponses["/pets"] = expectedPet

        let petCreate = PetCreate(name: "Buddy", kind: "dog", photoUrl: nil, currentWeight: 30.0)
        let pet: Pet = try await mockClient.post("/pets", body: petCreate, queryItems: nil)

        XCTAssertEqual(pet.name, "Buddy")
        XCTAssertEqual(mockClient.capturedPostRequests.count, 1)
        XCTAssertEqual(mockClient.capturedPostRequests[0].path, "/pets")
    }

    func testMockAPIClientErrorHandling() async {
        let mockClient = MockAPIClient()
        mockClient.stubbedErrors["/pets"] = APIError.unauthorized

        do {
            let _: [Pet] = try await mockClient.get("/pets", queryItems: nil)
            XCTFail("Should have thrown an error")
        } catch {
            XCTAssertTrue(error is APIError)
            if case APIError.unauthorized = error {
                // Expected
            } else {
                XCTFail("Should be unauthorized error")
            }
        }
    }

    func testMockAPIClientReset() async throws {
        let mockClient = MockAPIClient()
        mockClient.stubbedGetResponses["/test"] = "response"
        mockClient.capturedGetPaths = ["/test"]

        mockClient.reset()

        XCTAssertTrue(mockClient.stubbedGetResponses.isEmpty)
        XCTAssertTrue(mockClient.capturedGetPaths.isEmpty)
    }
}
