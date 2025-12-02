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
            VStack(spacing: 24) {
                Spacer()

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
                    .padding(.horizontal)

                Spacer()

                VStack(spacing: 16) {
                    TextField("First Name", text: $firstName)
                        .textFieldStyle(.roundedBorder)
                        .textContentType(.givenName)
                        .autocorrectionDisabled()
                        .padding(.horizontal, 32)

                    TextField("Last Name (optional)", text: $lastName)
                        .textFieldStyle(.roundedBorder)
                        .textContentType(.familyName)
                        .autocorrectionDisabled()
                        .padding(.horizontal, 32)

                    if let error = errorMessage {
                        Text(error)
                            .foregroundColor(.red)
                            .font(.caption)
                            .padding(.horizontal, 32)
                    }

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
                    .padding(.horizontal, 32)
                }

                Spacer()

                // Dev: Floating Sign Out Button
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

    private func signOut() {
        authManager.signOut()
    }
}

#Preview {
    ProfileSetupView()
}
