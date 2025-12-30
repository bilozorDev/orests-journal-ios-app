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
        NavigationStack {
            switch mode {
            case .choose:
                chooseModeView
            case .create:
                createFamilyView
            case .join:
                joinFamilyView
            }
        }
    }

    // MARK: - Choose Mode View

    private var chooseModeView: some View {
        VStack(spacing: 24) {
            Spacer()

            Image(systemName: "house.fill")
                .font(.system(size: 80))
                .foregroundStyle(.blue)

            Text("Setup Your Family")
                .font(.largeTitle)
                .fontWeight(.bold)

            Text("Create a new family or join an existing one")
                .font(.subheadline)
                .foregroundStyle(.secondary)
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
                    .foregroundStyle(.white)
                    .clipShape(.rect(cornerRadius: 12))
                }
                .accessibilityIdentifier(AccessibilityIdentifier.createFamilyButton)

                Button(action: { mode = .join }) {
                    HStack {
                        Image(systemName: "person.badge.plus")
                        Text("Join Existing Family")
                    }
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.green)
                    .foregroundStyle(.white)
                    .clipShape(.rect(cornerRadius: 12))
                }
                .accessibilityIdentifier(AccessibilityIdentifier.joinFamilyButton)
            }
            .padding(.horizontal, 32)

            Spacer()
        }
    }

    // MARK: - Create Family View

    private var createFamilyView: some View {
        Form {
            Section(header: Text("Family Name")) {
                TextField("Enter family name", text: $familyName)
                    .textContentType(.organizationName)
                    .textInputAutocapitalization(.words)
                    .autocorrectionDisabled(false)
                    .accessibilityIdentifier(AccessibilityIdentifier.familyNameTextField)
            }

            Section(footer: Text("You can invite family members later by sharing your invite code.")) {
                EmptyView()
            }

            if let error = errorMessage {
                Section {
                    Text(error)
                        .foregroundStyle(.red)
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
                            .foregroundStyle(.blue)
                    }
                    .disabled(familyName.isEmpty)
                    .accessibilityIdentifier(AccessibilityIdentifier.submitCreateFamilyButton)
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
                    .accessibilityIdentifier(AccessibilityIdentifier.inviteCodeTextField)
            }

            if let error = errorMessage {
                Section {
                    Text(error)
                        .foregroundStyle(.red)
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
                            .foregroundStyle(.green)
                    }
                    .disabled(inviteCode.isEmpty)
                    .accessibilityIdentifier(AccessibilityIdentifier.submitJoinFamilyButton)
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
                // AuthManager is @Observable, so ContentView will react automatically
            } catch {
                errorMessage = error.localizedDescription
            }
            isLoading = false
        }
    }

    private func joinFamily() {
        Task {
            isLoading = true
            errorMessage = nil

            do {
                // Join family via backend API
                _ = try await authManager.joinFamily(inviteCode: inviteCode)
                // AuthManager is @Observable, so ContentView will react automatically
            } catch {
                errorMessage = error.localizedDescription
            }
            isLoading = false
        }
    }
}

#Preview {
    FamilySetupView()
}
