//
//  APIClientFamilyTests.swift
//  Orest's JournalTests
//
//  Tests for family-related API client methods using mock.
//

import XCTest
@testable import Orest_s_Journal

final class APIClientFamilyTests: XCTestCase {

    var mockClient: MockAPIClient!

    override func setUp() {
        super.setUp()
        mockClient = MockAPIClient()
    }

    override func tearDown() {
        mockClient.reset()
        mockClient = nil
        super.tearDown()
    }

    // MARK: - Update Family Name Tests

    func testUpdateFamilyNameSuccess() async throws {
        // Given
        let familyId = "test-family-123"
        let newName = "Updated Family Name"
        let expectedResponse = AppFamily(
            id: familyId,
            name: newName,
            inviteCode: "ABC123",
            role: "admin"
        )

        mockClient.stubbedPatchResponses["/families/\(familyId)"] = expectedResponse

        // When
        struct UpdateFamilyRequest: Encodable {
            let name: String
        }
        let response: AppFamily = try await mockClient.patch(
            "/families/\(familyId)",
            body: UpdateFamilyRequest(name: newName)
        )

        // Then
        XCTAssertEqual(response.id, familyId)
        XCTAssertEqual(response.name, newName)
        XCTAssertEqual(response.role, "admin")

        // Verify request was captured
        XCTAssertEqual(mockClient.capturedPatchRequests.count, 1)
        XCTAssertEqual(mockClient.capturedPatchRequests[0].path, "/families/\(familyId)")
    }

    func testUpdateFamilyNameNotFound() async throws {
        // Given
        let familyId = "nonexistent-family"
        mockClient.stubbedErrors["/families/\(familyId)"] = APIError.notFound

        // When/Then
        struct UpdateFamilyRequest: Encodable {
            let name: String
        }

        do {
            let _: AppFamily = try await mockClient.patch(
                "/families/\(familyId)",
                body: UpdateFamilyRequest(name: "New Name")
            )
            XCTFail("Expected error to be thrown")
        } catch {
            XCTAssertTrue(error is APIError)
            if case APIError.notFound = error {
                // Expected error
            } else {
                XCTFail("Expected notFound error but got \(error)")
            }
        }
    }

    func testUpdateFamilyNameUnauthorized() async throws {
        // Given
        let familyId = "test-family-123"
        mockClient.stubbedErrors["/families/\(familyId)"] = APIError.unauthorized

        // When/Then
        struct UpdateFamilyRequest: Encodable {
            let name: String
        }

        do {
            let _: AppFamily = try await mockClient.patch(
                "/families/\(familyId)",
                body: UpdateFamilyRequest(name: "New Name")
            )
            XCTFail("Expected error to be thrown")
        } catch {
            XCTAssertTrue(error is APIError)
            if case APIError.unauthorized = error {
                // Expected error
            } else {
                XCTFail("Expected unauthorized error but got \(error)")
            }
        }
    }

    // MARK: - Get Family Members Tests

    func testGetFamilyMembersSuccess() async throws {
        // Given
        let familyId = "test-family-123"
        let expectedResponse = FamilyDetailResponse(
            id: familyId,
            name: "Test Family",
            inviteCode: "XYZ789",
            createdAt: Date(),
            members: [
                FamilyMemberResponse(
                    id: "member-1",
                    userId: "user-001",
                    email: "test@example.com",
                    firstName: "Test",
                    lastName: "User",
                    role: "admin",
                    joinedAt: Date()
                )
            ]
        )

        mockClient.stubbedGetResponses["/families/\(familyId)"] = expectedResponse

        // When
        let response: FamilyDetailResponse = try await mockClient.get(
            "/families/\(familyId)",
            queryItems: nil
        )

        // Then
        XCTAssertEqual(response.id, familyId)
        XCTAssertEqual(response.name, "Test Family")
        XCTAssertEqual(response.members.count, 1)
        XCTAssertEqual(response.members[0].displayName, "Test U.")
    }

    // MARK: - Request Tracking Tests

    func testMultiplePatchRequestsTracked() async throws {
        // Given
        let family1Id = "family-1"
        let family2Id = "family-2"

        mockClient.stubbedPatchResponses["/families/\(family1Id)"] = AppFamily(
            id: family1Id, name: "Family 1", inviteCode: "ABC", role: "admin"
        )
        mockClient.stubbedPatchResponses["/families/\(family2Id)"] = AppFamily(
            id: family2Id, name: "Family 2", inviteCode: "XYZ", role: "admin"
        )

        struct UpdateFamilyRequest: Encodable {
            let name: String
        }

        // When
        let _: AppFamily = try await mockClient.patch(
            "/families/\(family1Id)",
            body: UpdateFamilyRequest(name: "New Name 1")
        )
        let _: AppFamily = try await mockClient.patch(
            "/families/\(family2Id)",
            body: UpdateFamilyRequest(name: "New Name 2")
        )

        // Then
        XCTAssertEqual(mockClient.capturedPatchRequests.count, 2)
        XCTAssertEqual(mockClient.capturedPatchRequests[0].path, "/families/\(family1Id)")
        XCTAssertEqual(mockClient.capturedPatchRequests[1].path, "/families/\(family2Id)")
    }
}
