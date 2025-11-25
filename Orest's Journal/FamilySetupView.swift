//
//  FamilySetupView.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import SwiftUI

enum FamilySetupMode {
    case choose
    case create
    case join
}

struct FamilySetupView: View {
    private var authManager = AuthManager.shared
    @State private var mode: FamilySetupMode = .choose
    @State private var familyName = ""
    @State private var inviteCode = ""
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationView {
            ZStack {
                switch mode {
                case .choose:
                    chooseModeView
                case .create:
                    createFamilyView
                case .join:
                    joinFamilyView
                }

                // Dev: Floating Sign Out Button
                VStack {
                    Spacer()
                    HStack {
                        Spacer()
                        Button(action: signOut) {
                            Image(systemName: "rectangle.portrait.and.arrow.right")
                                .foregroundColor(.white)
                                .padding()
                                .background(Color.red)
                                .clipShape(Circle())
                                .shadow(radius: 4)
                        }
                        .padding()
                    }
                }
            }
        }
    }

    // MARK: - Choose Mode View

    private var chooseModeView: some View {
        VStack(spacing: 24) {
            Spacer()

            Image(systemName: "house.fill")
                .font(.system(size: 80))
                .foregroundColor(.blue)

            Text("Setup Your Family")
                .font(.largeTitle)
                .fontWeight(.bold)

            Text("Create a new family or join an existing one")
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal)

            Spacer()

            VStack(spacing: 16) {
                Button(action: { mode = .create }) {
                    HStack {
                        Image(systemName: "plus.circle.fill")
                        Text("Create New Family")
                    }
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.blue)
                    .foregroundColor(.white)
                    .cornerRadius(12)
                }

                Button(action: { mode = .join }) {
                    HStack {
                        Image(systemName: "person.badge.plus")
                        Text("Join Existing Family")
                    }
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.green)
                    .foregroundColor(.white)
                    .cornerRadius(12)
                }
            }
            .padding(.horizontal, 32)

            Spacer()
        }
        .task {
            // Check if user already has families
            if authManager.hasFamily {
                NotificationCenter.default.post(name: NSNotification.Name("RefreshFamilyStatus"), object: nil)
            }
        }
    }

    // MARK: - Create Family View

    private var createFamilyView: some View {
        Form {
            Section(header: Text("Family Name")) {
                TextField("Enter family name", text: $familyName)
                    .textInputAutocapitalization(.words)
            }

            Section(footer: Text("You can invite family members later by sharing your invite code.")) {
                EmptyView()
            }

            if let error = errorMessage {
                Section {
                    Text(error)
                        .foregroundColor(.red)
                        .font(.caption)
                }
            }

            Section {
                if isLoading {
                    HStack {
                        Spacer()
                        ProgressView()
                        Spacer()
                    }
                } else {
                    Button(action: createFamily) {
                        Text("Create Family")
                            .frame(maxWidth: .infinity)
                            .foregroundColor(.blue)
                    }
                    .disabled(familyName.isEmpty)
                }
            }
        }
        .navigationTitle("Create Family")
        .navigationBarTitleDisplayMode(.large)
        .toolbar {
            ToolbarItem(placement: .navigationBarLeading) {
                Button("Back") {
                    mode = .choose
                    errorMessage = nil
                }
            }
        }
    }

    // MARK: - Join Family View

    private var joinFamilyView: some View {
        Form {
            Section(header: Text("Invite Code"), footer: Text("Ask a family member to share their invite code with you.")) {
                TextField("Enter invite code", text: $inviteCode)
                    .textInputAutocapitalization(.characters)
                    .autocorrectionDisabled()
                    .font(.system(.body, design: .monospaced))
                    .onChange(of: inviteCode) { _, newValue in
                        inviteCode = newValue.uppercased()
                    }
            }

            if let error = errorMessage {
                Section {
                    Text(error)
                        .foregroundColor(.red)
                        .font(.caption)
                }
            }

            Section {
                if isLoading {
                    HStack {
                        Spacer()
                        ProgressView()
                        Spacer()
                    }
                } else {
                    Button(action: joinFamily) {
                        Text("Join Family")
                            .frame(maxWidth: .infinity)
                            .foregroundColor(.green)
                    }
                    .disabled(inviteCode.isEmpty)
                }
            }
        }
        .navigationTitle("Join Family")
        .navigationBarTitleDisplayMode(.large)
        .toolbar {
            ToolbarItem(placement: .navigationBarLeading) {
                Button("Back") {
                    mode = .choose
                    errorMessage = nil
                }
            }
        }
    }

    // MARK: - Actions

    private func createFamily() {
        Task {
            isLoading = true
            errorMessage = nil

            do {
                // Create family via backend API
                _ = try await authManager.createFamily(name: familyName)

                // Notify ContentView to refresh
                NotificationCenter.default.post(name: NSNotification.Name("RefreshFamilyStatus"), object: nil)
            } catch {
                errorMessage = error.localizedDescription
                isLoading = false
            }
        }
    }

    private func joinFamily() {
        Task {
            isLoading = true
            errorMessage = nil

            do {
                // Join family via backend API
                _ = try await authManager.joinFamily(inviteCode: inviteCode)

                // Notify ContentView to refresh
                NotificationCenter.default.post(name: NSNotification.Name("RefreshFamilyStatus"), object: nil)
            } catch {
                errorMessage = error.localizedDescription
                isLoading = false
            }
        }
    }

    private func signOut() {
        authManager.signOut()
    }
}

#Preview {
    FamilySetupView()
}
