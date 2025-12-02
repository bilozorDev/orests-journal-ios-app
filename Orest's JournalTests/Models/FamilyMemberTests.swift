//
//  FamilyMemberTests.swift
//  Orest's JournalTests
//
//  Unit tests for FamilyMember model.
//

import XCTest
@testable import Orest_s_Journal

final class FamilyMemberTests: XCTestCase {

    // MARK: - FamilyMember Decoding Tests

    func testDecodingFamilyMemberFromJSON() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "family_id": "660e8400-e29b-41d4-a716-446655440001",
            "user_id": "770e8400-e29b-41d4-a716-446655440002",
            "role": "owner",
            "joined_at": "2024-01-15T10:30:00Z"
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let member = try decoder.decode(FamilyMember.self, from: json)

        XCTAssertEqual(member.id, UUID(uuidString: "550e8400-e29b-41d4-a716-446655440000"))
        XCTAssertEqual(member.familyId, UUID(uuidString: "660e8400-e29b-41d4-a716-446655440001"))
        XCTAssertEqual(member.userId, UUID(uuidString: "770e8400-e29b-41d4-a716-446655440002"))
        XCTAssertEqual(member.role, .owner)
    }

    func testDecodingFamilyMemberWithMemberRole() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "family_id": "660e8400-e29b-41d4-a716-446655440001",
            "user_id": "770e8400-e29b-41d4-a716-446655440002",
            "role": "member",
            "joined_at": "2024-01-15T10:30:00Z"
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let member = try decoder.decode(FamilyMember.self, from: json)

        XCTAssertEqual(member.role, .member)
    }

    // MARK: - FamilyMember Encoding Tests

    func testEncodingFamilyMember() throws {
        let member = FamilyMember(
            id: UUID(uuidString: "550e8400-e29b-41d4-a716-446655440000")!,
            familyId: UUID(uuidString: "660e8400-e29b-41d4-a716-446655440001")!,
            userId: UUID(uuidString: "770e8400-e29b-41d4-a716-446655440002")!,
            role: .owner,
            joinedAt: Date(timeIntervalSince1970: 1705315800)
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.dateEncodingStrategy = .iso8601

        let data = try encoder.encode(member)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["role"] as? String, "owner")
    }

    // MARK: - FamilyMember.Role Tests

    func testRoleRawValues() {
        XCTAssertEqual(FamilyMember.Role.owner.rawValue, "owner")
        XCTAssertEqual(FamilyMember.Role.member.rawValue, "member")
    }

    func testRoleFromRawValue() {
        XCTAssertEqual(FamilyMember.Role(rawValue: "owner"), .owner)
        XCTAssertEqual(FamilyMember.Role(rawValue: "member"), .member)
        XCTAssertNil(FamilyMember.Role(rawValue: "admin"))
        XCTAssertNil(FamilyMember.Role(rawValue: ""))
    }

    // MARK: - FamilyMember Identifiable Tests

    func testFamilyMemberIdentifiable() {
        let uuid = UUID()
        let member = FamilyMember(
            id: uuid,
            familyId: UUID(),
            userId: UUID(),
            role: .member,
            joinedAt: Date()
        )

        XCTAssertEqual(member.id, uuid)
    }
}
