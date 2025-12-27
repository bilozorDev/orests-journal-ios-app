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

            HealthView()
                .tabItem { Label("Health", systemImage: "heart") }
                .tag(Tab.health)
                .accessibilityIdentifier(AccessibilityIdentifier.healthTab)

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
                    .foregroundStyle(.secondary)
                Text("Coming Soon")
                    .font(.title2)
                    .foregroundStyle(.secondary)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(Color(uiColor: .systemGroupedBackground))
            .navigationTitle(title)
        }
    }
}

// MARK: - Settings Navigation Destinations

enum SettingsDestination: Hashable {
    case family
    case notifications
}

// MARK: - Settings View

struct SettingsView: View {
    private var authManager = AuthManager.shared
    @Bindable private var navigationManager = NavigationManager.shared
    @State private var navigationPath = NavigationPath()
    @State private var familyMembers: [FamilyMemberResponse] = []
    @State private var hasLoaded = false
    @State private var showEditProfile = false
    @State private var showDeleteAccount = false

    var body: some View {
        NavigationStack(path: $navigationPath) {
            ScrollView {
                VStack(spacing: 20) {
                    // Settings menu group
                    VStack(spacing: 0) {
                        familySection
                        Divider().padding(.leading, 54)
                        accountSection
                        Divider().padding(.leading, 54)
                        notificationsSection
                    }
                    .clipShape(RoundedRectangle(cornerRadius: 10))

                    Spacer()

                    signOutButton

                    deleteAccountButton
                }
                .padding()
            }
            .background(Color(uiColor: .systemGroupedBackground))
            .navigationTitle("Settings")
            .navigationDestination(for: SettingsDestination.self) { destination in
                switch destination {
                case .family:
                    FamilyManagementView()
                case .notifications:
                    NotificationPreferencesView()
                }
            }
            .task {
                guard !hasLoaded else { return }
                await loadFamilyMembers()
            }
            .onChange(of: navigationManager.pendingDestination) { _, destination in
                handlePendingDestination(destination)
            }
            .onAppear {
                // Handle pending destination on appear (e.g., from deeplink)
                if let destination = navigationManager.pendingDestination {
                    handlePendingDestination(destination)
                }
            }
            .sheet(isPresented: $showEditProfile) {
                EditProfileSheet()
            }
            .sheet(isPresented: $showDeleteAccount) {
                DeleteAccountSheet(familyMembers: familyMembers)
            }
        }
    }

    private var familySection: some View {
        NavigationLink(value: SettingsDestination.family) {
            settingsRow(
                icon: "house.fill",
                iconColor: .green,
                title: "Family"
            )
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier(AccessibilityIdentifier.familyTab)
    }

    private var accountSection: some View {
        Button {
            showEditProfile = true
        } label: {
            settingsRow(
                icon: "person.fill",
                iconColor: .blue,
                title: "Account"
            )
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier(AccessibilityIdentifier.editProfileButton)
    }

    private var notificationsSection: some View {
        NavigationLink(value: SettingsDestination.notifications) {
            settingsRow(
                icon: "bell.badge.fill",
                iconColor: .red,
                title: "Notifications"
            )
        }
        .buttonStyle(.plain)
    }

    private func settingsRow(icon: String, iconColor: Color, title: String) -> some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .font(.system(size: 15, weight: .medium))
                .foregroundStyle(.white)
                .frame(width: 29, height: 29)
                .background(iconColor)
                .clipShape(.rect(cornerRadius: 6))

            Text(title)
                .font(.body)
                .foregroundStyle(.primary)

            Spacer()

            Image(systemName: "chevron.right")
                .font(.system(size: 14, weight: .semibold))
                .foregroundStyle(Color(uiColor: .tertiaryLabel))
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 11)
        .background(Color(uiColor: .secondarySystemGroupedBackground))
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
            .foregroundStyle(.white)
            .clipShape(.rect(cornerRadius: 12))
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
            .foregroundStyle(.red)
            .clipShape(.rect(cornerRadius: 12))
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(Color.red, lineWidth: 1)
            )
        }
        .accessibilityIdentifier(AccessibilityIdentifier.deleteAccountButton)
    }

    private func handlePendingDestination(_ destination: AppDestination?) {
        guard let destination = destination else { return }

        switch destination {
        case .familyManagement:
            // Clear path first then push family
            navigationPath = NavigationPath()
            navigationPath.append(SettingsDestination.family)
        }

        navigationManager.clearPendingDestination()
    }

    private func loadFamilyMembers() async {
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
