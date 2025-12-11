//
//  ContentView.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import SwiftUI

// MARK: - Extensions

extension UUID: @retroactive Identifiable {
    public var id: UUID { self }
}

// MARK: - Views

struct ContentView: View {
    private var authManager = AuthManager.shared
    @State private var isLoading = true
    @State private var hasPet = false
    @State private var isCheckingStatus = false
    @State private var hasCheckedPetStatus = false
    @State private var showError = false
    @State private var errorMessage = ""

    var body: some View {
        Group {
            if isLoading || !authManager.isLoaded {
                ProgressView("Loading...")
            } else if authManager.isAuthenticated {
                if authManager.wasRemovedFromFamily {
                    RemovedFromFamilyView(familyName: authManager.removedFamilyName)
                        .transition(.opacity.combined(with: .scale(scale: 0.95)))
                } else if authManager.leftFamily {
                    LeftFamilyView(familyName: authManager.leftFamilyName)
                        .transition(.opacity.combined(with: .scale(scale: 0.95)))
                } else if isCheckingStatus {
                    ProgressView("Setting up...")
                } else if authManager.needsProfileSetup {
                    ProfileSetupView()
                } else if !authManager.hasOrganization {
                    FamilySetupView()
                } else if !hasPet {
                    AddEditPetView(mode: .add) { _ in
                        hasPet = true  // Pet was created, proceed to main app
                    }
                } else {
                    MainTabView()
                }
            } else {
                SignInScreen()
            }
        }
        .task {
            await authManager.loadSession()
            if authManager.isAuthenticated {
                await checkPetStatus()
            }
            isLoading = false
        }
        .onChange(of: authManager.isAuthenticated) { _, isAuthenticated in
            if !isAuthenticated {
                hasPet = false
            }
        }
        .onChange(of: authManager.hasOrganization) { _, hasOrg in
            if hasOrg {
                Task {
                    await checkPetStatus()
                }
            }
        }
        .alert("Error Loading Data", isPresented: $showError) {
            Button("OK") {
                showError = false
            }
        } message: {
            Text(errorMessage)
        }
    }

    private func checkPetStatus() async {
        guard !isCheckingStatus else { return }

        guard authManager.hasOrganization else {
            hasPet = false
            return
        }

        isCheckingStatus = true
        do {
            let pets = try await DataService.shared.getPets()
            hasPet = !pets.isEmpty
            hasCheckedPetStatus = true
        } catch {
            errorMessage = "Failed to load pet data: \(error.localizedDescription)"
            showError = true
            hasPet = false
        }
        isCheckingStatus = false
    }
}

// MARK: - Main Tab View

struct MainTabView: View {
    @Bindable private var navigationManager = NavigationManager.shared

    var body: some View {
        TabView(selection: $navigationManager.selectedTab) {
            PlaceholderView(title: "Dashboard", icon: "house")
                .tabItem { Label("Home", systemImage: "house") }
                .tag(Tab.home)
                .accessibilityIdentifier(AccessibilityIdentifier.homeTab)

            PlaceholderView(title: "Food", icon: "pawprint")
                .tabItem { Label("Food", systemImage: "pawprint") }
                .tag(Tab.food)
                .accessibilityIdentifier(AccessibilityIdentifier.foodTab)

            PlaceholderView(title: "Medication", icon: "syringe")
                .tabItem { Label("Medication", systemImage: "syringe") }
                .tag(Tab.medication)
                .accessibilityIdentifier(AccessibilityIdentifier.medicationTab)

            PlaceholderView(title: "Health", icon: "heart")
                .tabItem { Label("Health", systemImage: "heart") }
                .tag(Tab.health)
                .accessibilityIdentifier(AccessibilityIdentifier.healthTab)

            FamilyManagementView()
                .tabItem { Label("Family", systemImage: "figure.2.and.child.holdinghands") }
                .tag(Tab.family)
                .accessibilityIdentifier(AccessibilityIdentifier.familyTab)

            SettingsView()
                .tabItem { Label("Settings", systemImage: "gear") }
                .tag(Tab.settings)
                .accessibilityIdentifier(AccessibilityIdentifier.settingsTab)
        }
    }
}

// MARK: - Placeholder View

struct PlaceholderView: View {
    let title: String
    let icon: String

    var body: some View {
        NavigationStack {
            VStack(spacing: 20) {
                Image(systemName: icon)
                    .font(.system(size: 60))
                    .foregroundColor(.secondary)
                Text("Coming Soon")
                    .font(.title2)
                    .foregroundColor(.secondary)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(Color(uiColor: .systemGroupedBackground))
            .navigationTitle(title)
        }
    }
}

// MARK: - Settings View

struct SettingsView: View {
    private var authManager = AuthManager.shared
    @State private var familyMembers: [FamilyMemberResponse] = []
    @State private var hasLoaded = false
    @State private var showEditProfile = false
    @State private var showDeleteAccount = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 20) {
                    accountSection

                    Spacer()

                    signOutButton

                    deleteAccountButton
                }
                .padding()
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .task {
                guard !hasLoaded else { return }
                await loadFamilyMembers()
            }
            .sheet(isPresented: $showEditProfile) {
                EditProfileSheet()
            }
            .sheet(isPresented: $showDeleteAccount) {
                DeleteAccountSheet(familyMembers: familyMembers)
            }
        }
    }

    private var accountSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Account")
                    .font(.headline)
                    .foregroundColor(.secondary)

                Spacer()

                Button("Edit") {
                    showEditProfile = true
                }
                .font(.subheadline)
                .accessibilityIdentifier(AccessibilityIdentifier.editProfileButton)
            }

            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Image(systemName: "person.circle.fill")
                        .font(.title2)
                        .foregroundColor(.blue)

                    VStack(alignment: .leading, spacing: 4) {
                        Text(authManager.displayName ?? authManager.userEmail ?? "Unknown")
                            .font(.body)
                            .fontWeight(.medium)

                        if let email = authManager.userEmail, authManager.displayName != nil {
                            Text(email)
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }
                }
                .padding()
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color.gray.opacity(0.1))
                .cornerRadius(12)
            }
        }
    }

    private var signOutButton: some View {
        Button(action: signOut) {
            HStack {
                Image(systemName: "arrow.right.square.fill")
                Text("Sign Out")
            }
            .frame(maxWidth: .infinity)
            .padding()
            .background(Color.red)
            .foregroundColor(.white)
            .cornerRadius(12)
        }
        .padding(.top, 20)
        .accessibilityIdentifier(AccessibilityIdentifier.signOutButton)
    }

    private var deleteAccountButton: some View {
        Button(action: { showDeleteAccount = true }) {
            HStack {
                Image(systemName: "trash.fill")
                Text("Delete Account")
            }
            .frame(maxWidth: .infinity)
            .padding()
            .background(Color.red.opacity(0.1))
            .foregroundColor(.red)
            .cornerRadius(12)
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(Color.red, lineWidth: 1)
            )
        }
        .accessibilityIdentifier(AccessibilityIdentifier.deleteAccountButton)
    }

    private func loadFamilyMembers() async {
        // Load family members (needed for delete account flow)
        guard let familyId = authManager.currentFamily?.id else {
            hasLoaded = true
            return
        }

        do {
            let response = try await DataService.shared.getFamilyMembers(for: familyId)
            familyMembers = response.members
        } catch {
            // Silently fail - not critical for settings
        }

        hasLoaded = true
    }

    private func signOut() {
        Task {
            await authManager.signOut()
        }
    }
}

// MARK: - Preview

#Preview {
    ContentView()
}
