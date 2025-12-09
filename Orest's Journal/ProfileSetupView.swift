//
//  ProfileSetupView.swift
//  Orest's Journal
//
//  Prompts user to enter their name if Apple didn't provide it.
//

import SwiftUI

struct ProfileSetupView: View {
    private var authManager = AuthManager.shared
    @State private var firstName = ""
    @State private var lastName = ""
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationView {
            ZStack {
                Form {
                    Section {
                        VStack(spacing: 16) {
                            Image(systemName: "person.crop.circle.fill")
                                .font(.system(size: 80))
                                .foregroundColor(.blue)

                            Text("Complete Your Profile")
                                .font(.largeTitle)
                                .fontWeight(.bold)

                            Text("Let us know what to call you")
                                .font(.subheadline)
                                .foregroundColor(.secondary)
                                .multilineTextAlignment(.center)
                        }
                        .frame(maxWidth: .infinity)
                        .listRowBackground(Color.clear)
                    }

                    Section(header: Text("Your Name")) {
                        TextField("First Name", text: $firstName)
                            .textContentType(.givenName)
                            .autocorrectionDisabled(true)

                        TextField("Last Name (optional)", text: $lastName)
                            .textContentType(.familyName)
                            .autocorrectionDisabled(true)
                    }

                    if let error = errorMessage {
                        Section {
                            Text(error)
                                .foregroundColor(.red)
                                .font(.caption)
                        }
                    }

                    Section {
                        Button(action: saveProfile) {
                            HStack {
                                if isLoading {
                                    ProgressView()
                                        .tint(.white)
                                } else {
                                    Text("Continue")
                                }
                            }
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(firstName.isEmpty || isLoading ? Color.gray.opacity(0.3) : Color.blue)
                            .foregroundColor(.white)
                            .cornerRadius(12)
                        }
                        .disabled(firstName.isEmpty || isLoading)
                        .listRowInsets(EdgeInsets())
                        .listRowBackground(Color.clear)
                    }
                }
            }
        }
    }

    private func saveProfile() {
        Task {
            isLoading = true
            errorMessage = nil

            do {
                try await authManager.updateProfile(
                    firstName: firstName.trimmingCharacters(in: .whitespaces),
                    lastName: lastName.isEmpty ? nil : lastName.trimmingCharacters(in: .whitespaces)
                )
                // State change will trigger ContentView to navigate away
            } catch {
                errorMessage = error.localizedDescription
            }

            isLoading = false
        }
    }
}

#Preview {
    ProfileSetupView()
}
