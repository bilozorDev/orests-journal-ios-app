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
                if isCheckingStatus {
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
        guard !isCheckingStatus else {
            print("⚠️ checkPetStatus already in progress, skipping")
            return
        }

        guard authManager.hasOrganization else {
            hasPet = false
            return
        }

        isCheckingStatus = true
        do {
            let pets = try await DataService.shared.getPets()
            hasPet = !pets.isEmpty
            hasCheckedPetStatus = true
            print("✅ Pet status loaded: hasPet=\(hasPet)")
        } catch {
            print("❌ Error checking pet status: \(error)")
            print("❌ Error details: \(error.localizedDescription)")
            errorMessage = "Failed to load pet data: \(error.localizedDescription)"
            showError = true
            hasPet = false
        }
        isCheckingStatus = false
    }
}

// MARK: - Main Tab View

struct MainTabView: View {
    @State private var selectedTab = 0

    var body: some View {
        TabView(selection: $selectedTab) {
            PlaceholderView(title: "Dashboard", icon: "house")
                .tabItem { Label("Home", systemImage: "house") }
                .tag(0)

            PlaceholderView(title: "Food", icon: "pawprint")
                .tabItem { Label("Food", systemImage: "pawprint") }
                .tag(1)

            PlaceholderView(title: "Medication", icon: "syringe")
                .tabItem { Label("Medication", systemImage: "syringe") }
                .tag(2)

            PlaceholderView(title: "Health", icon: "heart")
                .tabItem { Label("Health", systemImage: "heart") }
                .tag(3)

            FamilyManagementView()
                .tabItem { Label("Family", systemImage: "figure.2.and.child.holdinghands") }
                .tag(4)

            SettingsView()
                .tabItem { Label("Settings", systemImage: "gear") }
                .tag(5)
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
    @State private var pets: [Pet] = []
    @State private var isLoading = false
    @State private var hasLoaded = false
    @State private var errorMessage: String?
    @State private var showSignOutError = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 20) {
                    accountSection

                    if let family = authManager.currentFamily {
                        familySection(family: family)
                    }

                    petsSection

                    Spacer()

                    signOutButton
                }
                .padding()
            }
            .overlay {
                if isLoading && !hasLoaded {
                    ProgressView("Loading...")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                        .background(Color(uiColor: .systemBackground))
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .task {
                guard !hasLoaded else { return }
                await loadData()
            }
            .refreshable {
                await loadData()
            }
            .alert("Sign Out Error", isPresented: $showSignOutError) {
                Button("OK") {
                    showSignOutError = false
                }
            } message: {
                Text(errorMessage ?? "Failed to sign out")
            }
        }
    }

    private var accountSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Account")
                .font(.headline)
                .foregroundColor(.secondary)

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

    private func familySection(family: AppFamily) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Family")
                .font(.headline)
                .foregroundColor(.secondary)

            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Image(systemName: "house.circle.fill")
                        .font(.title2)
                        .foregroundColor(.green)

                    VStack(alignment: .leading, spacing: 4) {
                        Text(family.name)
                            .font(.body)
                            .fontWeight(.medium)

                        Text("Role: \(family.role.capitalized)")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }

                    Spacer()
                }
                .padding()
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color.gray.opacity(0.1))
                .cornerRadius(12)

                VStack(alignment: .leading, spacing: 4) {
                    Text("Invite Code")
                        .font(.caption)
                        .foregroundColor(.secondary)

                    HStack {
                        Text(family.inviteCode)
                            .font(.system(.body, design: .monospaced))
                            .fontWeight(.semibold)

                        Spacer()

                        Button(action: {
                            UIPasteboard.general.string = family.inviteCode
                        }) {
                            Image(systemName: "doc.on.doc")
                                .foregroundColor(.blue)
                        }
                    }
                    .padding()
                    .background(Color.blue.opacity(0.1))
                    .cornerRadius(8)
                }
                .padding(.top, 4)

                Text("Share this code to invite family members")
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }
        }
    }

    private var petsSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Pets")
                .font(.headline)
                .foregroundColor(.secondary)

            if pets.isEmpty {
                VStack(spacing: 8) {
                    Image(systemName: "pawprint.circle")
                        .font(.system(size: 40))
                        .foregroundColor(.gray)
                    Text("No pets in family")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 20)
                .background(Color.gray.opacity(0.1))
                .cornerRadius(12)
            } else {
                VStack(spacing: 12) {
                    ForEach(pets) { pet in
                        HStack(spacing: 12) {
                            if let photoUrl = pet.photoUrl, let url = URL(string: photoUrl) {
                                AsyncImage(url: url) { image in
                                    image
                                        .resizable()
                                        .scaledToFill()
                                } placeholder: {
                                    Rectangle()
                                        .fill(Color.gray.opacity(0.2))
                                        .overlay(ProgressView())
                                }
                                .frame(width: 60, height: 60)
                                .clipShape(Circle())
                            } else {
                                Circle()
                                    .fill(Color.gray.opacity(0.2))
                                    .frame(width: 60, height: 60)
                                    .overlay(
                                        Image(systemName: "pawprint.fill")
                                            .foregroundColor(.gray)
                                    )
                            }

                            VStack(alignment: .leading, spacing: 4) {
                                Text(pet.name)
                                    .font(.body)
                                    .fontWeight(.medium)

                                Text(pet.kind)
                                    .font(.subheadline)
                                    .foregroundColor(.secondary)

                                if let weight = pet.currentWeight {
                                    Text("\(formatWeight(weight)) lbs")
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }
                            }

                            Spacer()
                        }
                        .padding()
                        .background(Color.gray.opacity(0.1))
                        .cornerRadius(12)
                    }
                }
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
    }

    private func loadData() async {
        isLoading = true
        errorMessage = nil

        do {
            pets = try await DataService.shared.getPets()
            hasLoaded = true
        } catch let error as NSError where error.domain == NSURLErrorDomain && error.code == NSURLErrorCancelled {
            print("Settings load cancelled (this is normal during navigation)")
        } catch {
            errorMessage = error.localizedDescription
            print("Error loading settings data: \(error)")
        }

        isLoading = false
    }

    private func signOut() {
        authManager.signOut()
    }

    private func formatWeight(_ weight: Double) -> String {
        Formatters.weight.string(from: NSNumber(value: weight)) ?? "\(weight)"
    }
}

// MARK: - Preview

#Preview {
    ContentView()
}
