//
//  AuthManager.swift
//  Orest's Journal
//
//  Manages Sign in with Apple authentication and session state.
//

import Foundation
import AuthenticationServices
import Security

/// User model for the app (uses automatic snake_case conversion from APIClient)
struct AppUser: Codable {
    let id: String
    let email: String?
    let firstName: String?
    let lastName: String?
}

/// Family model (was Organization) - uses automatic snake_case conversion from APIClient
struct AppFamily: Codable, Identifiable {
    let id: String
    let name: String
    let inviteCode: String
    let role: String  // "admin" or "member"
}

/// Auth response from the backend
struct AuthResponse: Codable {
    let token: String
    let user: AppUser
    let families: [AppFamily]
}

/// Me response from the backend
struct MeResponse: Codable {
    let user: AppUser
    let families: [AppFamily]
}

/// Response after creating a family (uses automatic snake_case conversion from APIClient)
struct CreateFamilyResponse: Codable {
    let id: String
    let name: String
    let inviteCode: String
    let role: String

    var asAppFamily: AppFamily {
        AppFamily(id: id, name: name, inviteCode: inviteCode, role: role)
    }
}

/// Response after joining a family
struct JoinFamilyResponse: Codable {
    let family: AppFamily
    let message: String
}

/// Manages authentication state using Sign in with Apple
@MainActor
@Observable
final class AuthManager {
    static let shared = AuthManager()

    var isLoaded = false
    var isAuthenticated = false
    var currentUser: AppUser?
    var families: [AppFamily] = []
    var currentFamily: AppFamily?

    private let keychainService = "com.notip.orests-journal"
    private let tokenKey = "auth_token"
    private let userKey = "current_user"

    private init() {}

    // MARK: - Public Methods

    /// Load saved session on app launch
    func loadSession() async {
        isLoaded = false

        // Try to load saved token
        guard let token = loadTokenFromKeychain() else {
            isLoaded = true
            return
        }

        // Validate token by calling /auth/me
        do {
            // Set token for API client first
            APIClient.shared.authToken = token

            let response: MeResponse = try await APIClient.shared.request(
                endpoint: "/auth/me",
                method: "GET"
            )

            self.currentUser = response.user
            self.families = response.families
            self.currentFamily = response.families.first
            self.isAuthenticated = true

            // Update API client with family ID
            if let familyId = currentFamily?.id {
                APIClient.shared.currentOrgId = familyId
            }

            // Register device token for notifications
            await NotificationManager.shared.registerAfterAuthentication()

        } catch {
            // Token invalid, clear it
            print("Session invalid: \(error)")
            clearSession()
        }

        isLoaded = true
    }

    /// Handle Sign in with Apple credential
    func signInWithApple(credential: ASAuthorizationAppleIDCredential) async throws {
        guard let identityTokenData = credential.identityToken,
              let identityToken = String(data: identityTokenData, encoding: .utf8) else {
            throw AuthError.invalidCredential
        }

        // Extract user info (only available on first sign-in)
        let email = credential.email
        let firstName = credential.fullName?.givenName
        let lastName = credential.fullName?.familyName

        // Call backend to authenticate
        // APIClient uses .convertToSnakeCase encoder automatically
        struct AppleAuthRequest: Codable {
            let identityToken: String
            let userId: String
            let email: String?
            let firstName: String?
            let lastName: String?
        }

        let request = AppleAuthRequest(
            identityToken: identityToken,
            userId: credential.user,
            email: email,
            firstName: firstName,
            lastName: lastName
        )

        // Temporarily clear token for unauthenticated request
        APIClient.shared.authToken = nil

        let response: AuthResponse = try await APIClient.shared.request(
            endpoint: "/auth/apple",
            method: "POST",
            body: request
        )

        // Save token
        saveTokenToKeychain(response.token)

        // Update state
        self.currentUser = response.user
        self.families = response.families
        self.currentFamily = response.families.first
        self.isAuthenticated = true

        // Set up API client
        APIClient.shared.authToken = response.token
        if let familyId = currentFamily?.id {
            APIClient.shared.currentOrgId = familyId
        }

        // Register device token for notifications
        await NotificationManager.shared.registerAfterAuthentication()
    }

    /// Create a new family
    func createFamily(name: String) async throws -> AppFamily {
        struct CreateFamilyRequest: Codable {
            let name: String
        }

        let response: CreateFamilyResponse = try await APIClient.shared.request(
            endpoint: "/families",
            method: "POST",
            body: CreateFamilyRequest(name: name)
        )

        let family = response.asAppFamily

        // Add to list and select it
        families.append(family)
        currentFamily = family
        APIClient.shared.currentOrgId = family.id

        return family
    }

    /// Join a family with invite code
    func joinFamily(inviteCode: String) async throws -> AppFamily {
        struct JoinFamilyRequest: Codable {
            let inviteCode: String
            // APIClient uses .convertToSnakeCase encoder automatically
        }

        let response: JoinFamilyResponse = try await APIClient.shared.request(
            endpoint: "/families/join",
            method: "POST",
            body: JoinFamilyRequest(inviteCode: inviteCode)
        )

        // Add to list and select it
        families.append(response.family)
        currentFamily = response.family
        APIClient.shared.currentOrgId = response.family.id

        return response.family
    }

    /// Select a family
    func selectFamily(_ family: AppFamily) {
        currentFamily = family
        APIClient.shared.currentOrgId = family.id
    }

    /// Update current family info (e.g., after name change)
    func updateCurrentFamily(_ family: AppFamily) {
        // Update in families list
        if let index = families.firstIndex(where: { $0.id == family.id }) {
            families[index] = family
        }
        // Update current selection
        currentFamily = family
    }

    /// Sign out
    func signOut() {
        // Unregister device token before clearing session
        Task {
            await NotificationManager.shared.unregisterDeviceToken()
        }
        clearSession()
    }

    /// Check if user has any families
    var hasFamily: Bool {
        !families.isEmpty
    }

    /// Get current user's email
    var userEmail: String? {
        currentUser?.email
    }

    /// Get current user's ID
    var userId: String? {
        currentUser?.id
    }

    /// Get current user's display name (format: "FirstName L." or just "FirstName" if no last name)
    var displayName: String? {
        guard let user = currentUser,
              let firstName = user.firstName,
              !firstName.isEmpty else {
            return nil
        }
        if let lastName = user.lastName, !lastName.isEmpty {
            let initial = String(lastName.prefix(1)).uppercased()
            return "\(firstName) \(initial)."
        }
        return firstName
    }

    /// Check if user needs to complete profile setup (missing first name)
    var needsProfileSetup: Bool {
        guard let user = currentUser else { return false }
        return user.firstName == nil || user.firstName?.isEmpty == true
    }

    /// Update user profile (first name, last name)
    func updateProfile(firstName: String, lastName: String?) async throws {
        struct ProfileUpdateRequest: Codable {
            let firstName: String
            let lastName: String?
        }

        let updatedUser: AppUser = try await APIClient.shared.request(
            endpoint: "/auth/profile",
            method: "PATCH",
            body: ProfileUpdateRequest(firstName: firstName, lastName: lastName)
        )

        // Update local state
        self.currentUser = updatedUser
    }

    /// Get current family ID
    var familyId: String? {
        currentFamily?.id
    }

    // MARK: - Legacy Compatibility

    /// Legacy: organizations property (maps to families)
    var organizations: [AppFamily] {
        families
    }

    /// Legacy: currentOrganization property (maps to currentFamily)
    var currentOrganization: AppFamily? {
        currentFamily
    }

    /// Legacy: hasOrganization property (maps to hasFamily)
    var hasOrganization: Bool {
        hasFamily
    }

    /// Legacy: orgId property (maps to familyId)
    var orgId: String? {
        familyId
    }

    /// Legacy: createOrganization method (maps to createFamily)
    func createOrganization(name: String) async throws -> AppFamily {
        try await createFamily(name: name)
    }

    /// Legacy: selectOrganization method (maps to selectFamily)
    func selectOrganization(_ org: AppFamily) {
        selectFamily(org)
    }

    // MARK: - Private Methods

    private func clearSession() {
        deleteTokenFromKeychain()
        currentUser = nil
        families = []
        currentFamily = nil
        isAuthenticated = false
        APIClient.shared.authToken = nil
        APIClient.shared.currentOrgId = nil
    }

    // MARK: - Keychain Operations

    private func saveTokenToKeychain(_ token: String) {
        guard let data = token.data(using: .utf8) else { return }

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: tokenKey,
        ]

        // Delete existing
        SecItemDelete(query as CFDictionary)

        // Add new
        var newQuery = query
        newQuery[kSecValueData as String] = data
        SecItemAdd(newQuery as CFDictionary, nil)
    }

    private func loadTokenFromKeychain() -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: tokenKey,
            kSecReturnData as String: true,
        ]

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)

        guard status == errSecSuccess,
              let data = result as? Data,
              let token = String(data: data, encoding: .utf8) else {
            return nil
        }

        return token
    }

    private func deleteTokenFromKeychain() {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: tokenKey,
        ]

        SecItemDelete(query as CFDictionary)
    }
}

// MARK: - Auth Errors

enum AuthError: LocalizedError {
    case invalidCredential
    case networkError(Error)
    case serverError(String)

    var errorDescription: String? {
        switch self {
        case .invalidCredential:
            return "Invalid Apple credential"
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        case .serverError(let message):
            return "Server error: \(message)"
        }
    }
}
