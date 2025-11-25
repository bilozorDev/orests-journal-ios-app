//
//  FamilySetupView.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import SwiftUI

struct FamilySetupView: View {
    private var authManager = AuthManager.shared
    @State private var familyName = ""
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationView {
            ZStack {
                Form {
                    Section(header: Text("Family Name")) {
                        TextField("Enter family name", text: $familyName)
                            .textInputAutocapitalization(.words)
                    }

                    Section(footer: Text("You can invite family members later from the Settings tab.")) {
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
                .navigationTitle("Setup Your Family")
                .navigationBarTitleDisplayMode(.large)
                .task {
                    // Check if user already has organizations
                    if authManager.hasOrganization {
                        NotificationCenter.default.post(name: NSNotification.Name("RefreshFamilyStatus"), object: nil)
                    }
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

    private func createFamily() {
        Task {
            isLoading = true
            errorMessage = nil

            do {
                // Create organization (family) via backend API
                _ = try await authManager.createOrganization(name: familyName)

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
