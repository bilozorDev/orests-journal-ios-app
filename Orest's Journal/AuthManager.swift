//
//  AuthManager.swift
//  Orest's Journal
//
//  Manages Sign in with Apple authentication and session state.
//

import Foundation
import AuthenticationServices
import Security

/// User model for the app
struct AppUser: Codable {
    let id: String
    let email: String?
    let firstName: String?
    let lastName: String?
}

/// Organization model
struct AppOrganization: Codable, Identifiable {
    let id: String
    let name: String
    let slug: String?
}

/// Auth response from the backend
struct AuthResponse: Codable {
    let token: String
    let user: AppUser
    let organizations: [AppOrganization]
}

/// Me response from the backend
struct MeResponse: Codable {
    let user: AppUser
    let organizations: [AppOrganization]
}

/// Manages authentication state using Sign in with Apple
@MainActor
@Observable
final class AuthManager {
    static let shared = AuthManager()

    var isLoaded = false
    var isAuthenticated = false
    var currentUser: AppUser?
    var organizations: [AppOrganization] = []
    var currentOrganization: AppOrganization?

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
            APIClient.shared.getToken = { token }

            let response: MeResponse = try await APIClient.shared.request(
                endpoint: "/auth/me",
                method: "GET"
            )

            self.currentUser = response.user
            self.organizations = response.organizations
            self.currentOrganization = response.organizations.first
            self.isAuthenticated = true

            // Update API client with org ID
            if let orgId = currentOrganization?.id {
                APIClient.shared.currentOrgId = orgId
            }

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

        // Temporarily set token getter to nil for unauthenticated request
        APIClient.shared.getToken = nil

        let response: AuthResponse = try await APIClient.shared.request(
            endpoint: "/auth/apple",
            method: "POST",
            body: request
        )

        // Save token
        saveTokenToKeychain(response.token)

        // Update state
        self.currentUser = response.user
        self.organizations = response.organizations
        self.currentOrganization = response.organizations.first
        self.isAuthenticated = true

        // Set up API client
        let savedToken = response.token
        APIClient.shared.getToken = { savedToken }
        if let orgId = currentOrganization?.id {
            APIClient.shared.currentOrgId = orgId
        }
    }

    /// Create a new organization (family)
    func createOrganization(name: String) async throws -> AppOrganization {
        struct CreateOrgRequest: Codable {
            let name: String
        }

        let response: AppOrganization = try await APIClient.shared.request(
            endpoint: "/auth/organizations",
            method: "POST",
            body: CreateOrgRequest(name: name)
        )

        // Add to list and select it
        organizations.append(response)
        currentOrganization = response
        APIClient.shared.currentOrgId = response.id

        return response
    }

    /// Select an organization
    func selectOrganization(_ org: AppOrganization) {
        currentOrganization = org
        APIClient.shared.currentOrgId = org.id
    }

    /// Sign out
    func signOut() {
        clearSession()
    }

    /// Check if user has any organizations
    var hasOrganization: Bool {
        !organizations.isEmpty
    }

    /// Get current user's email
    var userEmail: String? {
        currentUser?.email
    }

    /// Get current user's ID
    var userId: String? {
        currentUser?.id
    }

    /// Get current organization ID
    var orgId: String? {
        currentOrganization?.id
    }

    // MARK: - Private Methods

    private func clearSession() {
        deleteTokenFromKeychain()
        currentUser = nil
        organizations = []
        currentOrganization = nil
        isAuthenticated = false
        APIClient.shared.getToken = nil
        APIClient.shared.currentOrgId = nil
    }

    // MARK: - Keychain Operations

    private func saveTokenToKeychain(_ token: String) {
        let data = token.data(using: .utf8)!

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
