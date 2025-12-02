//
//  ResponseTypesTests.swift
//  Orest's JournalTests
//
//  Unit tests for various API response types.
//

import XCTest
@testable import Orest_s_Journal

final class ResponseTypesTests: XCTestCase {

    // MARK: - FoodDeleteResponse Tests

    func testDecodingFoodDeleteResponseDeleted() throws {
        let json = """
        {
            "deleted": true,
            "archived": false,
            "message": "Food deleted successfully"
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        let response = try decoder.decode(FoodDeleteResponse.self, from: json)

        XCTAssertTrue(response.deleted)
        XCTAssertFalse(response.archived)
        XCTAssertEqual(response.message, "Food deleted successfully")
    }

    func testDecodingFoodDeleteResponseArchived() throws {
        let json = """
        {
            "deleted": false,
            "archived": true,
            "message": "Food archived because it has feeding history"
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        let response = try decoder.decode(FoodDeleteResponse.self, from: json)

        XCTAssertFalse(response.deleted)
        XCTAssertTrue(response.archived)
        XCTAssertEqual(response.message, "Food archived because it has feeding history")
    }

    // MARK: - MedicationDeleteResponse Tests

    func testDecodingMedicationDeleteResponseDeleted() throws {
        let json = """
        {
            "deleted": true,
            "archived": false,
            "message": "Medication deleted successfully"
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        let response = try decoder.decode(MedicationDeleteResponse.self, from: json)

        XCTAssertTrue(response.deleted)
        XCTAssertFalse(response.archived)
        XCTAssertEqual(response.message, "Medication deleted successfully")
    }

    func testDecodingMedicationDeleteResponseArchived() throws {
        let json = """
        {
            "deleted": false,
            "archived": true,
            "message": "Medication archived because it has dose history"
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        let response = try decoder.decode(MedicationDeleteResponse.self, from: json)

        XCTAssertFalse(response.deleted)
        XCTAssertTrue(response.archived)
        XCTAssertEqual(response.message, "Medication archived because it has dose history")
    }

    // MARK: - MedicationUpdate Tests

    func testMedicationUpdateEncoding() throws {
        var update = MedicationUpdate()
        update.name = "New Name"
        update.timesPerDay = 3
        update.notes = "Updated notes"

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase

        let data = try encoder.encode(update)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["name"] as? String, "New Name")
        XCTAssertEqual(jsonObject["times_per_day"] as? Int, 3)
        XCTAssertEqual(jsonObject["notes"] as? String, "Updated notes")
    }

    func testMedicationUpdatePartialEncoding() throws {
        var update = MedicationUpdate()
        update.remindersEnabled = true

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase

        let data = try encoder.encode(update)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["reminders_enabled"] as? Bool, true)
        // Other fields should be null
        XCTAssertTrue(jsonObject["name"] is NSNull || jsonObject["name"] == nil)
    }

    func testMedicationUpdateWithScheduledTimes() throws {
        var update = MedicationUpdate()
        update.scheduledTimes = [
            ScheduledTimeCreate(hour: 8, minute: 0),
            ScheduledTimeCreate(hour: 20, minute: 0)
        ]

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase

        let data = try encoder.encode(update)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        let times = jsonObject["scheduled_times"] as? [[String: Any]]
        XCTAssertNotNil(times)
        XCTAssertEqual(times?.count, 2)
        XCTAssertEqual(times?[0]["hour"] as? Int, 8)
        XCTAssertEqual(times?[1]["hour"] as? Int, 20)
    }

    // MARK: - HealthEventListResponse Tests

    func testDecodingHealthEventListResponse() throws {
        let json = """
        {
            "events": [
                {
                    "event": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "category_id": "770e8400-e29b-41d4-a716-446655440002",
                        "occurred_at": "2024-01-15T10:00:00Z",
                        "notes": "Vomited after eating",
                        "created_by": "user@example.com",
                        "created_at": "2024-01-15T10:05:00Z"
                    },
                    "category": {
                        "id": "770e8400-e29b-41d4-a716-446655440002",
                        "pet_id": "660e8400-e29b-41d4-a716-446655440001",
                        "name": "Vomiting",
                        "name_normalized": "vomiting",
                        "created_at": "2024-01-01T00:00:00Z",
                        "created_by": null
                    }
                }
            ]
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let response = try decoder.decode(HealthEventListResponse.self, from: json)

        XCTAssertEqual(response.events.count, 1)
        XCTAssertEqual(response.events[0].category.name, "Vomiting")
    }

    func testDecodingEmptyHealthEventListResponse() throws {
        let json = """
        {
            "events": []
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let response = try decoder.decode(HealthEventListResponse.self, from: json)

        XCTAssertEqual(response.events.count, 0)
    }

    // MARK: - FamilyDetailResponse Tests

    func testDecodingFamilyDetailResponse() throws {
        let json = """
        {
            "id": "family-123",
            "name": "Smith Family",
            "invite_code": "ABC123",
            "created_at": "2024-01-01T00:00:00Z",
            "members": [
                {
                    "id": "member-1",
                    "user_id": "user-1",
                    "email": "owner@example.com",
                    "first_name": "John",
                    "last_name": "Smith",
                    "role": "owner",
                    "joined_at": "2024-01-01T00:00:00Z"
                },
                {
                    "id": "member-2",
                    "user_id": "user-2",
                    "email": "member@example.com",
                    "first_name": "Jane",
                    "last_name": null,
                    "role": "member",
                    "joined_at": "2024-01-02T00:00:00Z"
                }
            ]
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let response = try decoder.decode(FamilyDetailResponse.self, from: json)

        XCTAssertEqual(response.id, "family-123")
        XCTAssertEqual(response.name, "Smith Family")
        XCTAssertEqual(response.inviteCode, "ABC123")
        XCTAssertEqual(response.members.count, 2)
        XCTAssertEqual(response.members[0].displayName, "John S.")
        XCTAssertEqual(response.members[1].displayName, "Jane")
    }

    // MARK: - FamilyMemberResponse Display Name Tests

    func testFamilyMemberResponseDisplayNameWithBothNames() {
        let member = FamilyMemberResponse(
            id: "1",
            userId: "user-1",
            email: "test@example.com",
            firstName: "John",
            lastName: "Doe",
            role: "owner",
            joinedAt: Date()
        )

        XCTAssertEqual(member.displayName, "John D.")
    }

    func testFamilyMemberResponseDisplayNameFirstNameOnly() {
        let member = FamilyMemberResponse(
            id: "1",
            userId: "user-1",
            email: "test@example.com",
            firstName: "Jane",
            lastName: nil,
            role: "member",
            joinedAt: Date()
        )

        XCTAssertEqual(member.displayName, "Jane")
    }

    func testFamilyMemberResponseDisplayNameEmptyLastName() {
        let member = FamilyMemberResponse(
            id: "1",
            userId: "user-1",
            email: "test@example.com",
            firstName: "Bob",
            lastName: "",
            role: "member",
            joinedAt: Date()
        )

        XCTAssertEqual(member.displayName, "Bob")
    }

    func testFamilyMemberResponseDisplayNameNoNames() {
        let member = FamilyMemberResponse(
            id: "1",
            userId: "user-1",
            email: "fallback@example.com",
            firstName: nil,
            lastName: nil,
            role: "member",
            joinedAt: Date()
        )

        XCTAssertEqual(member.displayName, "fallback@example.com")
    }

    func testFamilyMemberResponseDisplayNameEmptyFirstName() {
        let member = FamilyMemberResponse(
            id: "1",
            userId: "user-1",
            email: "email@example.com",
            firstName: "",
            lastName: "Smith",
            role: "member",
            joinedAt: Date()
        )

        XCTAssertEqual(member.displayName, "email@example.com")
    }

    func testFamilyMemberResponseDisplayNameNoNamesNoEmail() {
        let member = FamilyMemberResponse(
            id: "1",
            userId: "user-1",
            email: nil,
            firstName: nil,
            lastName: nil,
            role: "member",
            joinedAt: nil
        )

        XCTAssertEqual(member.displayName, "Unknown")
    }

    // MARK: - DeviceTokenRequest Tests

    func testDeviceTokenRequestEncoding() throws {
        let request = DeviceTokenRequest(
            deviceToken: "abc123token",
            deviceName: "iPhone 16 Pro"
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase

        let data = try encoder.encode(request)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["device_token"] as? String, "abc123token")
        XCTAssertEqual(jsonObject["device_name"] as? String, "iPhone 16 Pro")
    }

    // MARK: - DeviceTokenDeleteRequest Tests

    func testDeviceTokenDeleteRequestEncoding() throws {
        let request = DeviceTokenDeleteRequest(deviceToken: "token_to_delete")

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase

        let data = try encoder.encode(request)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["device_token"] as? String, "token_to_delete")
    }
}
