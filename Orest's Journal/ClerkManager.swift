//
//  ClerkManager.swift
//  Orest's Journal
//
//  Manages Clerk authentication and organization context.
//

import Foundation
import SwiftUI
import Clerk

/// Manages Clerk authentication state and provides access to the current user and organization.
@MainActor
class ClerkManager: ObservableObject {
    static let shared = ClerkManager()

    @Published var isLoaded = false
    @Published var isSignedIn = false
    @Published var currentUser: User?
    @Published var currentOrganization: Organization?
    @Published var organizations: [Organization] = []

    private init() {
        setupAPIClient()
    }

    /// Configure Clerk with your publishable key
    func configure() async {
        // Clerk is configured via Info.plist with ClerkPublishableKey
        await loadAuthState()
    }

    /// Load the current authentication state
    func loadAuthState() async {
        do {
            let clerk = Clerk.shared

            // Check if user is signed in
            if let user = clerk.user {
                self.currentUser = user
                self.isSignedIn = true

                // Load user's organizations (families)
                await loadOrganizations()

                // Set up API client with token provider
                setupAPIClient()
            } else {
                self.isSignedIn = false
                self.currentUser = nil
                self.currentOrganization = nil
                self.organizations = []
            }
        } catch {
            print("Error loading auth state: \(error)")
        }

        self.isLoaded = true
    }

    /// Load user's organizations
    func loadOrganizations() async {
        guard let memberships = Clerk.shared.user?.organizationMemberships else {
            organizations = []
            return
        }

        organizations = memberships.compactMap { $0.organization }

        // Select first organization as current if none selected
        if currentOrganization == nil, let first = organizations.first {
            await selectOrganization(first)
        }
    }

    /// Select an organization (family) as the current context
    func selectOrganization(_ org: Organization) async {
        currentOrganization = org
        APIClient.shared.currentOrgId = org.id
    }

    /// Create a new organization (family)
    func createOrganization(name: String) async throws -> Organization {
        let org = try await Clerk.shared.createOrganization(name: name)
        await loadOrganizations()
        await selectOrganization(org)
        return org
    }

    /// Set up APIClient with Clerk token provider
    private func setupAPIClient() {
        APIClient.shared.getToken = { [weak self] in
            guard let token = try await Clerk.shared.session?.getToken()?.jwt else {
                throw APIError.unauthorized
            }
            return token
        }

        if let orgId = currentOrganization?.id {
            APIClient.shared.currentOrgId = orgId
        }
    }

    /// Sign out the current user
    func signOut() async {
        do {
            try await Clerk.shared.signOut()
            isSignedIn = false
            currentUser = nil
            currentOrganization = nil
            organizations = []
            APIClient.shared.currentOrgId = nil
        } catch {
            print("Error signing out: \(error)")
        }
    }

    /// Check if user has any organizations (families)
    var hasOrganization: Bool {
        !organizations.isEmpty
    }

    /// Get current user's email
    var userEmail: String? {
        currentUser?.emailAddresses.first?.emailAddress
    }

    /// Get current user's display name
    var userName: String? {
        if let first = currentUser?.firstName, let last = currentUser?.lastName {
            return "\(first) \(last)"
        }
        return currentUser?.firstName ?? userEmail
    }
}

// MARK: - User Convenience Extension
extension ClerkManager {
    /// Get user ID for API calls
    var userId: String? {
        currentUser?.id
    }

    /// Get organization ID for API calls
    var orgId: String? {
        currentOrganization?.id
    }
}
