//
//  AuthManager.swift
//  Orest's Journal
//
//  Manages Sign in with Apple authentication and session state.
//

import Foundation
import AuthenticationServices
import Security
import SwiftUI  // For withAnimation

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

/// Response after leaving a family
struct LeaveFamilyResponse: Codable {
    let success: Bool
    let action: String  // "left", "left_promoted", or "family_deleted"
    let familyName: String
}

/// Response after deleting account
struct DeleteAccountResponse: Codable {
    let success: Bool
    let stepsCompleted: [String]
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

    // Removal state - persisted in UserDefaults to survive app restarts
    // Uses backing storage with manual observation since @Observable doesn't track computed properties
    @ObservationIgnored private var _wasRemovedFromFamily: Bool = UserDefaults.standard.bool(forKey: "was_removed_from_family")
    @ObservationIgnored private var _removedFamilyName: String? = UserDefaults.standard.string(forKey: "removed_family_name")

    // Left family state - persisted in UserDefaults (user voluntarily left)
    @ObservationIgnored private var _leftFamily: Bool = UserDefaults.standard.bool(forKey: "left_family")
    @ObservationIgnored private var _leftFamilyName: String? = UserDefaults.standard.string(forKey: "left_family_name")

    var wasRemovedFromFamily: Bool {
        get {
            access(keyPath: \._wasRemovedFromFamily)
            return _wasRemovedFromFamily
        }
        set {
            withMutation(keyPath: \._wasRemovedFromFamily) {
                _wasRemovedFromFamily = newValue
                UserDefaults.standard.set(newValue, forKey: "was_removed_from_family")
            }
        }
    }
    var removedFamilyName: String? {
        get {
            access(keyPath: \._removedFamilyName)
            return _removedFamilyName
        }
        set {
            withMutation(keyPath: \._removedFamilyName) {
                _removedFamilyName = newValue
                UserDefaults.standard.set(newValue, forKey: "removed_family_name")
            }
        }
    }

    var leftFamily: Bool {
        get {
            access(keyPath: \._leftFamily)
            return _leftFamily
        }
        set {
            withMutation(keyPath: \._leftFamily) {
                _leftFamily = newValue
                UserDefaults.standard.set(newValue, forKey: "left_family")
            }
        }
    }
    var leftFamilyName: String? {
        get {
            access(keyPath: \._leftFamilyName)
            return _leftFamilyName
        }
        set {
            withMutation(keyPath: \._leftFamilyName) {
                _leftFamilyName = newValue
                UserDefaults.standard.set(newValue, forKey: "left_family_name")
            }
        }
    }

    private let keychainService = "com.notip.orests-journal"
    private let tokenKey = "auth_token"
    private let familyIdKey = "current_family_id"
    private let familyNameKey = "current_family_name"
    private let userKey = "current_user"

    private init() {}

    // MARK: - UI Testing Support

    /// Check for test authentication token (for UI testing)
    /// Call this early in app launch to enable test mode authentication
    func checkForTestAuth() {
        // Only in UI testing mode
        guard ProcessInfo.processInfo.arguments.contains("--uitesting") else { return }

        if let testToken = ProcessInfo.processInfo.environment["TEST_AUTH_TOKEN"] {
            // Set the token for API requests
            APIClient.shared.authToken = testToken

            // Mark as authenticated - loadSession will fetch user data
            // We set a flag here so loadSession knows to use the test token
            isTestMode = true
        }
    }

    /// Whether we're running in UI test mode with test token
    private var isTestMode = false

    // MARK: - Public Methods

    /// Load saved session on app launch
    func loadSession() async {
        isLoaded = false

        // Check if user was previously removed or left (persisted state)
        // Skip this check in test mode
        if (wasRemovedFromFamily || leftFamily) && !isTestMode {
            isLoaded = true
            return
        }

        // In test mode, token is already set by checkForTestAuth()
        // In normal mode, try to load saved token from Keychain
        let token: String?
        if isTestMode {
            token = APIClient.shared.authToken
        } else {
            token = loadTokenFromKeychain()
        }

        guard let token = token else {
            isLoaded = true
            return
        }

        // Load previous family ID from Keychain (persists across app restarts)
        // Skip in test mode since we don't persist test data
        let previousFamilyId = isTestMode ? nil : loadFamilyIdFromKeychain()
        let previousFamilyName = isTestMode ? nil : loadFamilyNameFromKeychain()

        // Validate token by calling /auth/me
        do {
            // Set token for API client first (in case not test mode)
            APIClient.shared.authToken = token

            let response: MeResponse = try await APIClient.shared.request(
                endpoint: "/auth/me",
                method: "GET"
            )

            self.currentUser = response.user
            self.families = response.families
            self.isAuthenticated = true

            // Check if user was removed from their previous family
            if let prevId = previousFamilyId,
               !response.families.contains(where: { $0.id == prevId }) {
                // User was removed from their family
                self.currentFamily = response.families.first
                handleRemovedFromFamily(familyName: previousFamilyName)
            } else {
                self.currentFamily = response.families.first
            }

            // Update API client with family ID and persist to Keychain
            if let family = currentFamily {
                APIClient.shared.currentFamilyId = family.id
                saveFamilyIdToKeychain(family.id)
                saveFamilyNameToKeychain(family.name)
            }

            // Register device token for notifications
            await NotificationManager.shared.registerAfterAuthentication()

        } catch {
            // Token invalid, clear it
            #if DEBUG
            print("Session invalid: \(error)")
            #endif
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
        if let family = currentFamily {
            APIClient.shared.currentFamilyId = family.id
            saveFamilyIdToKeychain(family.id)
            saveFamilyNameToKeychain(family.name)
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
        APIClient.shared.currentFamilyId = family.id
        saveFamilyIdToKeychain(family.id)
        saveFamilyNameToKeychain(family.name)

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
        APIClient.shared.currentFamilyId = response.family.id
        saveFamilyIdToKeychain(response.family.id)
        saveFamilyNameToKeychain(response.family.name)

        return response.family
    }

    /// Select a family
    func selectFamily(_ family: AppFamily) {
        currentFamily = family
        APIClient.shared.currentFamilyId = family.id
        saveFamilyIdToKeychain(family.id)
        saveFamilyNameToKeychain(family.name)
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
    func signOut() async {
        // Unregister device token before clearing session
        await NotificationManager.shared.unregisterDeviceToken()
        clearSession()
    }

    /// Handle when user is removed from a family (via notification or 403 error)
    func handleRemovedFromFamily(familyName: String? = nil) {
        withAnimation(.easeInOut(duration: 0.3)) {
            wasRemovedFromFamily = true
            removedFamilyName = familyName ?? currentFamily?.name

            // Remove current family from the list
            if let currentId = currentFamily?.id {
                families.removeAll { $0.id == currentId }
            }

            // Switch to any remaining family, or nil
            currentFamily = families.first
            if let family = currentFamily {
                APIClient.shared.currentFamilyId = family.id
                saveFamilyIdToKeychain(family.id)
                saveFamilyNameToKeychain(family.name)
            } else {
                APIClient.shared.currentFamilyId = nil
                deleteFamilyIdFromKeychain()
                deleteFamilyNameFromKeychain()
            }
        }

        // Invalidate caches
        Task {
            await DataService.shared.invalidateAllCaches()
        }
    }

    /// Reset removal state when user taps "Start Over"
    func resetRemovedState() {
        withAnimation(.easeInOut(duration: 0.3)) {
            wasRemovedFromFamily = false
            removedFamilyName = nil
        }
    }

    /// Handle when user voluntarily leaves a family
    func handleLeftFamily(familyName: String?) {
        withAnimation(.easeInOut(duration: 0.3)) {
            leftFamily = true
            leftFamilyName = familyName ?? currentFamily?.name

            // Remove current family from the list
            if let currentId = currentFamily?.id {
                families.removeAll { $0.id == currentId }
            }

            // Switch to any remaining family, or nil
            currentFamily = families.first
            if let family = currentFamily {
                APIClient.shared.currentFamilyId = family.id
                saveFamilyIdToKeychain(family.id)
                saveFamilyNameToKeychain(family.name)
            } else {
                APIClient.shared.currentFamilyId = nil
                deleteFamilyIdFromKeychain()
                deleteFamilyNameFromKeychain()
            }
        }

        // Invalidate caches
        Task {
            await DataService.shared.invalidateAllCaches()
        }
    }

    /// Reset left family state when user taps "Start Over"
    func resetLeftFamilyState() {
        withAnimation(.easeInOut(duration: 0.3)) {
            leftFamily = false
            leftFamilyName = nil
        }
    }

    /// Leave the current family
    func leaveFamily(newAdminUserId: String? = nil) async throws -> LeaveFamilyResponse {
        guard let familyId = currentFamily?.id else {
            throw AuthError.serverError("No family to leave")
        }

        struct LeaveFamilyRequest: Codable {
            let newAdminUserId: String?
        }

        let response: LeaveFamilyResponse = try await APIClient.shared.request(
            endpoint: "/families/\(familyId)/leave",
            method: "POST",
            body: LeaveFamilyRequest(newAdminUserId: newAdminUserId)
        )

        // Handle local state update
        handleLeftFamily(familyName: response.familyName)

        return response
    }

    /// Delete the user's account
    func deleteAccount(newAdminUserId: String? = nil) async throws -> DeleteAccountResponse {
        struct DeleteAccountRequest: Codable {
            let newAdminUserId: String?
        }

        let response: DeleteAccountResponse = try await APIClient.shared.request(
            endpoint: "/auth/account",
            method: "DELETE",
            body: DeleteAccountRequest(newAdminUserId: newAdminUserId)
        )

        // Don't clear session here - the UI will handle sign out after showing completion
        return response
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
        return Formatters.formatDisplayName(firstName: firstName, lastName: user.lastName)
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

    // MARK: - Private Methods

    private func clearSession() {
        deleteTokenFromKeychain()
        deleteFamilyIdFromKeychain()
        deleteFamilyNameFromKeychain()
        // Clear shared keychain for widget
        SharedKeychainManager.deleteAll()
        // Clear removal and left family state from UserDefaults
        wasRemovedFromFamily = false
        removedFamilyName = nil
        leftFamily = false
        leftFamilyName = nil
        currentUser = nil
        families = []
        currentFamily = nil
        isAuthenticated = false
        APIClient.shared.authToken = nil
        APIClient.shared.currentFamilyId = nil
        NavigationManager.shared.reset()
        // Clear widget data
        WidgetDataManager.shared.clearWidgetData()
    }

    // MARK: - Keychain Operations

    private func saveTokenToKeychain(_ token: String) {
        guard let data = token.data(using: .utf8) else {
            print("⚠️ [Auth] Failed to encode token data")
            return
        }

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: tokenKey,
        ]

        // Delete existing
        let deleteStatus = SecItemDelete(query as CFDictionary)
        if deleteStatus != errSecSuccess && deleteStatus != errSecItemNotFound {
            print("⚠️ [Auth] Keychain delete warning: \(deleteStatus)")
        }

        // Add new with persistent storage
        var newQuery = query
        newQuery[kSecValueData as String] = data
        newQuery[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlock

        let addStatus = SecItemAdd(newQuery as CFDictionary, nil)
        if addStatus != errSecSuccess {
            print("❌ [Auth] Keychain save failed with status: \(addStatus)")
            // Don't fail silently - if keychain save fails, the token won't persist
            // This is important for debugging but we don't show UI since login will appear to work
            // but fail on next app launch. The SharedKeychainManager below serves as backup.
        }

        // Sync to shared keychain for widget access
        // This also serves as a fallback if main keychain fails
        SharedKeychainManager.save(token, for: .authToken)
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

    // MARK: - Family ID Keychain Operations

    private func saveFamilyIdToKeychain(_ familyId: String) {
        guard let data = familyId.data(using: .utf8) else { return }

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: familyIdKey,
        ]

        SecItemDelete(query as CFDictionary)

        var newQuery = query
        newQuery[kSecValueData as String] = data
        SecItemAdd(newQuery as CFDictionary, nil)

        // Sync to shared keychain for widget access
        SharedKeychainManager.save(familyId, for: .familyId)
    }

    private func loadFamilyIdFromKeychain() -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: familyIdKey,
            kSecReturnData as String: true,
        ]

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)

        guard status == errSecSuccess,
              let data = result as? Data,
              let familyId = String(data: data, encoding: .utf8) else {
            return nil
        }

        return familyId
    }

    private func deleteFamilyIdFromKeychain() {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: familyIdKey,
        ]

        SecItemDelete(query as CFDictionary)
    }

    // MARK: - Family Name Keychain Operations

    private func saveFamilyNameToKeychain(_ familyName: String) {
        guard let data = familyName.data(using: .utf8) else { return }

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: familyNameKey,
        ]

        SecItemDelete(query as CFDictionary)

        var newQuery = query
        newQuery[kSecValueData as String] = data
        SecItemAdd(newQuery as CFDictionary, nil)
    }

    private func loadFamilyNameFromKeychain() -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: familyNameKey,
            kSecReturnData as String: true,
        ]

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)

        guard status == errSecSuccess,
              let data = result as? Data,
              let familyName = String(data: data, encoding: .utf8) else {
            return nil
        }

        return familyName
    }

    private func deleteFamilyNameFromKeychain() {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: familyNameKey,
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
