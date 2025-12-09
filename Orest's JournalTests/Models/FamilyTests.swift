//
//  FamilyTests.swift
//  Orest's JournalTests
//
//  Unit tests for Family model and related types.
//

import XCTest
@testable import Orest_s_Journal

final class FamilyTests: XCTestCase {

    // MARK: - Family JSON Decoding Tests

    func testDecodingFamilyFromJSON() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "Smith Family",
            "created_at": "2024-01-15T10:30:00Z",
            "created_by": "660e8400-e29b-41d4-a716-446655440001"
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let family = try decoder.decode(Family.self, from: json)

        XCTAssertEqual(family.id, UUID(uuidString: "550e8400-e29b-41d4-a716-446655440000"))
        XCTAssertEqual(family.name, "Smith Family")
        XCTAssertEqual(family.createdBy, UUID(uuidString: "660e8400-e29b-41d4-a716-446655440001"))
    }

    func testDecodingFamilyWithNullCreatedBy() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "Jones Family",
            "created_at": "2024-01-15T10:30:00Z",
            "created_by": null
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let family = try decoder.decode(Family.self, from: json)

        XCTAssertEqual(family.name, "Jones Family")
        XCTAssertNil(family.createdBy)
    }

    // MARK: - Family Encoding Tests

    func testEncodingFamily() throws {
        let family = Family(
            id: UUID(uuidString: "550e8400-e29b-41d4-a716-446655440000")!,
            name: "Test Family",
            createdAt: Date(timeIntervalSince1970: 1705315800),
            createdBy: UUID(uuidString: "660e8400-e29b-41d4-a716-446655440001")!
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.dateEncodingStrategy = .iso8601

        let data = try encoder.encode(family)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["name"] as? String, "Test Family")
    }

    // MARK: - Family Identifiable Tests

    func testFamilyIdentifiable() {
        let uuid = UUID()
        let family = Family(
            id: uuid,
            name: "Test",
            createdAt: Date(),
            createdBy: nil
        )

        XCTAssertEqual(family.id, uuid)
    }

    // MARK: - FamilyMemberResponse Tests

    func testFamilyMemberResponseDisplayNameWithFullName() {
        let member = FamilyMemberResponse(
            id: "member-1",
            userId: "user-123",
            email: "john@example.com",
            firstName: "John",
            lastName: "Doe",
            role: "admin",
            joinedAt: Date()
        )

        XCTAssertEqual(member.displayName, "John D.")
    }

    func testFamilyMemberResponseDisplayNameFirstNameOnly() {
        let member = FamilyMemberResponse(
            id: "member-1",
            userId: "user-123",
            email: "jane@example.com",
            firstName: "Jane",
            lastName: nil,
            role: "member",
            joinedAt: Date()
        )

        XCTAssertEqual(member.displayName, "Jane")
    }

    func testFamilyMemberResponseDisplayNameEmptyLastName() {
        let member = FamilyMemberResponse(
            id: "member-1",
            userId: "user-123",
            email: "bob@example.com",
            firstName: "Bob",
            lastName: "",
            role: "member",
            joinedAt: Date()
        )

        XCTAssertEqual(member.displayName, "Bob")
    }

    func testFamilyMemberResponseDisplayNameNoFirstName() {
        let member = FamilyMemberResponse(
            id: "member-1",
            userId: "user-123",
            email: "anonymous@example.com",
            firstName: nil,
            lastName: "Smith",
            role: "member",
            joinedAt: Date()
        )

        XCTAssertEqual(member.displayName, "anonymous@example.com")
    }

    func testFamilyMemberResponseDisplayNameEmptyFirstName() {
        let member = FamilyMemberResponse(
            id: "member-1",
            userId: "user-123",
            email: "test@example.com",
            firstName: "",
            lastName: "Johnson",
            role: "member",
            joinedAt: Date()
        )

        XCTAssertEqual(member.displayName, "test@example.com")
    }

    func testFamilyMemberResponseDisplayNameNoNameNoEmail() {
        let member = FamilyMemberResponse(
            id: "member-1",
            userId: "user-123",
            email: nil,
            firstName: nil,
            lastName: nil,
            role: "member",
            joinedAt: nil
        )

        XCTAssertEqual(member.displayName, "Unknown")
    }

    func testFamilyMemberResponseIdentifiable() {
        let member = FamilyMemberResponse(
            id: "unique-member-id",
            userId: "user-123",
            email: "test@example.com",
            firstName: "Test",
            lastName: "User",
            role: "admin",
            joinedAt: Date()
        )

        XCTAssertEqual(member.id, "unique-member-id")
    }

    // MARK: - FamilyDetailResponse Tests

    func testFamilyDetailResponseDecoding() throws {
        let json = """
        {
            "id": "family-123",
            "name": "The Smiths",
            "invite_code": "ABC123",
            "created_at": "2024-01-15T10:30:00Z",
            "members": [
                {
                    "id": "member-1",
                    "user_id": "user-001",
                    "email": "john@example.com",
                    "first_name": "John",
                    "last_name": "Smith",
                    "role": "admin",
                    "joined_at": "2024-01-15T10:30:00Z"
                },
                {
                    "id": "member-2",
                    "user_id": "user-002",
                    "email": "jane@example.com",
                    "first_name": "Jane",
                    "last_name": "Smith",
                    "role": "member",
                    "joined_at": "2024-01-16T12:00:00Z"
                }
            ]
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let detail = try decoder.decode(FamilyDetailResponse.self, from: json)

        XCTAssertEqual(detail.id, "family-123")
        XCTAssertEqual(detail.name, "The Smiths")
        XCTAssertEqual(detail.inviteCode, "ABC123")
        XCTAssertEqual(detail.members.count, 2)
        XCTAssertEqual(detail.members[0].displayName, "John S.")
        XCTAssertEqual(detail.members[1].displayName, "Jane S.")
        XCTAssertEqual(detail.members[0].role, "admin")
        XCTAssertEqual(detail.members[1].role, "member")
    }

    // MARK: - AppFamily Tests (API response model)

    func testAppFamilyDecoding() throws {
        let json = """
        {
            "id": "app-family-123",
            "name": "Updated Family Name",
            "invite_code": "XYZ789",
            "role": "admin"
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase

        let appFamily = try decoder.decode(AppFamily.self, from: json)

        XCTAssertEqual(appFamily.id, "app-family-123")
        XCTAssertEqual(appFamily.name, "Updated Family Name")
        XCTAssertEqual(appFamily.inviteCode, "XYZ789")
        XCTAssertEqual(appFamily.role, "admin")
    }

    func testAppFamilyIdentifiable() {
        let family = AppFamily(
            id: "test-family-id",
            name: "Test Family",
            inviteCode: "ABC123",
            role: "admin"
        )

        XCTAssertEqual(family.id, "test-family-id")
    }

    // MARK: - Family Update Request Encoding Tests

    func testFamilyUpdateRequestEncoding() throws {
        struct UpdateFamilyRequest: Encodable {
            let name: String
        }

        let request = UpdateFamilyRequest(name: "New Family Name")

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase

        let data = try encoder.encode(request)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["name"] as? String, "New Family Name")
    }
}
