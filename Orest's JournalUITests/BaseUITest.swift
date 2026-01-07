//
//  BaseUITest.swift
//  Orest's JournalUITests
//
//  Base class for UI tests with common setup and helpers.
//

import XCTest

@MainActor
class BaseUITest: XCTestCase {
    var app: XCUIApplication!

    // MARK: - Test Configuration

    /// Base URL for the backend API.
    /// UPDATE THIS when your ngrok URL changes or when testing against a different server.
    /// For local testing: http://localhost:8000/api/v1
    /// For ngrok: https://your-tunnel.ngrok-free.app/api/v1
    static let apiBaseURL = "https://climbing-helping-hermit.ngrok-free.app/api/v1"

    /// Track created test user IDs for cleanup
    var createdTestUserIds: [String] = []

    /// Primary test user ID for this test run
    private var _primaryTestUserId: String?
    var primaryTestUserId: String {
        if let id = _primaryTestUserId { return id }
        let id = "uitest-\(UUID().uuidString.prefix(8))"
        _primaryTestUserId = id
        return id
    }

    /// Alias for backwards compatibility
    var testUserId: String { primaryTestUserId }

    // MARK: - Setup & Teardown

    override func setUpWithError() throws {
        try super.setUpWithError()
        continueAfterFailure = false

        app = XCUIApplication()
        app.launchArguments = ["--uitesting"]

        // Clean launch environment
        app.launchEnvironment = [
            "UITEST_MODE": "true"
        ]

        // Reset tracking
        createdTestUserIds = []
        _primaryTestUserId = nil

        // Add handler for system alerts (notification permissions, etc.)
        addUIInterruptionMonitor(withDescription: "System Alert") { alert in
            // Handle notification permission alert
            let allowButton = alert.buttons["Allow"]
            let dontAllowButton = alert.buttons["Don't Allow"]

            if allowButton.exists {
                allowButton.tap()
                return true
            } else if dontAllowButton.exists {
                dontAllowButton.tap()
                return true
            }
            return false
        }
    }

    override func tearDownWithError() throws {
        // Clean up all created test users
        let userIds = createdTestUserIds
        Task {
            for userId in userIds {
                try? await cleanupTestUser(userId)
            }
        }

        app = nil
        try super.tearDownWithError()
    }

    // MARK: - Launch Helpers

    /// Launch app in clean state (no auth)
    func launchAppClean() {
        app.launch()
    }

    /// Launch app with test user authenticated via backend test endpoint
    func launchAppAuthenticated(
        createFamily: Bool = false,
        familyName: String = "Test Family"
    ) async throws {
        // Get auth token from backend
        let result = try await createTestUser(
            testUserId: primaryTestUserId,
            createFamily: createFamily,
            familyName: familyName
        )

        // Pass token to app via environment
        app.launchEnvironment["TEST_AUTH_TOKEN"] = result.token
        app.launchEnvironment["TEST_USER_ID"] = primaryTestUserId
        app.launch()
    }

    // MARK: - Multi-User Helpers

    /// Result from creating a test user
    struct TestUserResult {
        let token: String
        let userId: String
        let testUserId: String
        let families: [TestFamilyInfo]
    }

    struct TestFamilyInfo {
        let id: String
        let name: String
        let inviteCode: String
        let role: String
    }

    /// Create a test user and optionally a family
    func createTestUser(
        testUserId: String? = nil,
        email: String? = nil,
        firstName: String = "UI",
        lastName: String = "Test",
        createFamily: Bool = false,
        familyName: String = "Test Family"
    ) async throws -> TestUserResult {
        let userId = testUserId ?? "uitest-\(UUID().uuidString.prefix(8))"

        guard let url = URL(string: "\(Self.apiBaseURL)/auth/test-login") else {
            throw TestError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let body: [String: Any] = [
            "test_user_id": userId,
            "email": email ?? "\(userId)@test.com",
            "first_name": firstName,
            "last_name": lastName,
            "create_family": createFamily,
            "family_name": familyName
        ]

        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw TestError.authFailed
        }

        let json = try JSONSerialization.jsonObject(with: data) as? [String: Any]

        guard let token = json?["token"] as? String,
              let user = json?["user"] as? [String: Any],
              let backendUserId = user["id"] as? String else {
            throw TestError.invalidResponse
        }

        // Parse families
        var families: [TestFamilyInfo] = []
        if let familiesArray = json?["families"] as? [[String: Any]] {
            for familyDict in familiesArray {
                if let id = familyDict["id"] as? String,
                   let name = familyDict["name"] as? String,
                   let inviteCode = familyDict["invite_code"] as? String,
                   let role = familyDict["role"] as? String {
                    families.append(TestFamilyInfo(id: id, name: name, inviteCode: inviteCode, role: role))
                }
            }
        }

        // Track for cleanup
        createdTestUserIds.append(userId)

        return TestUserResult(
            token: token,
            userId: backendUserId,
            testUserId: userId,
            families: families
        )
    }

    /// Create a second test user (for multi-user scenarios)
    func createSecondTestUser(
        firstName: String = "Member",
        lastName: String = "User"
    ) async throws -> TestUserResult {
        let secondUserId = "uitest-member-\(UUID().uuidString.prefix(8))"
        return try await createTestUser(
            testUserId: secondUserId,
            firstName: firstName,
            lastName: lastName,
            createFamily: false
        )
    }

    /// Join a family using invite code
    func joinFamily(token: String, inviteCode: String) async throws {
        guard let url = URL(string: "\(Self.apiBaseURL)/families/join") else {
            throw TestError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

        let body: [String: Any] = ["invite_code": inviteCode]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (_, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw TestError.joinFamilyFailed
        }
    }

    /// Remove a member from family (admin action)
    func removeFamilyMember(
        adminToken: String,
        familyId: String,
        memberUserId: String
    ) async throws {
        guard let url = URL(string: "\(Self.apiBaseURL)/families/\(familyId)/members/\(memberUserId)") else {
            throw TestError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"
        request.setValue("Bearer \(adminToken)", forHTTPHeaderField: "Authorization")

        let (_, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw TestError.removeMemberFailed
        }
    }

    /// Change member role (admin action)
    func changeMemberRole(
        adminToken: String,
        familyId: String,
        memberUserId: String,
        newRole: String
    ) async throws {
        guard let url = URL(string: "\(Self.apiBaseURL)/families/\(familyId)/members/\(memberUserId)/role") else {
            throw TestError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "PATCH"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(adminToken)", forHTTPHeaderField: "Authorization")

        let body: [String: Any] = ["role": newRole]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (_, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw TestError.changeRoleFailed
        }
    }

    /// Clean up test user via backend
    func cleanupTestUser(_ testUserId: String) async throws {
        guard let url = URL(string: "\(Self.apiBaseURL)/auth/test-cleanup/\(testUserId)") else {
            throw TestError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"

        let (_, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            // Cleanup failure is not critical - may already be deleted
            return
        }
    }

    // MARK: - Multi-User Setup Helper

    /// Setup helper for scenarios requiring admin + member in same family
    struct MultiUserSetup {
        let adminToken: String
        let adminUserId: String
        let adminTestUserId: String
        let memberToken: String
        let memberUserId: String
        let memberTestUserId: String
        let familyId: String
        let inviteCode: String
    }

    /// Create admin with family and member who has joined
    func setupAdminAndMember(familyName: String = "Test Family") async throws -> MultiUserSetup {
        // 1. Create admin with family
        let adminResult = try await createTestUser(
            testUserId: primaryTestUserId,
            firstName: "Admin",
            lastName: "User",
            createFamily: true,
            familyName: familyName
        )

        guard let family = adminResult.families.first else {
            throw TestError.invalidResponse
        }

        // 2. Create member user
        let memberResult = try await createSecondTestUser()

        // 3. Member joins family
        try await joinFamily(token: memberResult.token, inviteCode: family.inviteCode)

        return MultiUserSetup(
            adminToken: adminResult.token,
            adminUserId: adminResult.userId,
            adminTestUserId: adminResult.testUserId,
            memberToken: memberResult.token,
            memberUserId: memberResult.userId,
            memberTestUserId: memberResult.testUserId,
            familyId: family.id,
            inviteCode: family.inviteCode
        )
    }

    // MARK: - Wait Helpers

    /// Wait for element to exist with timeout
    func waitForElement(
        _ element: XCUIElement,
        timeout: TimeInterval = 10
    ) -> Bool {
        element.waitForExistence(timeout: timeout)
    }

    /// Wait for element and tap it
    func waitAndTap(
        _ element: XCUIElement,
        timeout: TimeInterval = 10
    ) {
        XCTAssertTrue(waitForElement(element, timeout: timeout), "Element not found: \(element)")
        element.tap()
    }

    /// Wait for element and type text
    func waitAndType(
        _ element: XCUIElement,
        text: String,
        timeout: TimeInterval = 10,
        dismissKeyboard: Bool = true
    ) {
        XCTAssertTrue(waitForElement(element, timeout: timeout), "Element not found: \(element)")
        element.tap()
        element.typeText(text)

        // Dismiss keyboard by tapping elsewhere (helps on iOS 26+)
        if dismissKeyboard {
            // Try to dismiss by tapping on a non-interactive area
            // The coordinate (0, 0) is typically safe
            app.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.1)).tap()
        }
    }

    // MARK: - Assertion Helpers

    /// Assert element exists within timeout
    func assertExists(
        _ element: XCUIElement,
        timeout: TimeInterval = 10,
        message: String? = nil
    ) {
        XCTAssertTrue(
            element.waitForExistence(timeout: timeout),
            message ?? "Expected element to exist: \(element)"
        )
    }

    /// Assert element does not exist
    func assertNotExists(
        _ element: XCUIElement,
        timeout: TimeInterval = 5,
        message: String? = nil
    ) {
        XCTAssertFalse(
            element.waitForExistence(timeout: timeout),
            message ?? "Expected element to not exist: \(element)"
        )
    }
}

// MARK: - Test Errors

enum TestError: Error {
    case invalidURL
    case authFailed
    case invalidResponse
    case joinFamilyFailed
    case removeMemberFailed
    case changeRoleFailed
}

// MARK: - XCUIApplication Helpers

extension XCUIApplication {
    /// Get element by accessibility identifier
    func element(id: String) -> XCUIElement {
        descendants(matching: .any).matching(identifier: id).firstMatch
    }

    /// Get button by accessibility identifier
    func button(id: String) -> XCUIElement {
        buttons[id]
    }

    /// Get text field by accessibility identifier
    func textField(id: String) -> XCUIElement {
        textFields[id]
    }

    /// Get tab bar button by accessibility identifier
    func tabBarButton(id: String) -> XCUIElement {
        tabBars.buttons[id]
    }

    /// Check if on sign-in screen
    var isOnSignInScreen: Bool {
        staticTexts["Orest's Journal"].exists
    }

    /// Check if on family setup screen
    var isOnFamilySetupScreen: Bool {
        staticTexts["Setup Your Family"].exists
    }

    /// Check if on add pet screen
    var isOnAddPetScreen: Bool {
        navigationBars["Add Pet"].exists
    }

    /// Check if on main tab view
    var isOnMainTabView: Bool {
        tabBars.firstMatch.exists
    }

    /// Check if on removed from family screen
    var isOnRemovedFromFamilyScreen: Bool {
        staticTexts["You were removed"].exists
    }
}
