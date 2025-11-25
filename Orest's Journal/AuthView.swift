//
//  AuthView.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import SwiftUI
import AuthenticationServices

struct SignInScreen: View {
    private var authManager = AuthManager.shared
    @State private var isSigningIn = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                Spacer()

                Image(systemName: "pawprint.circle.fill")
                    .font(.system(size: 80))
                    .foregroundColor(.blue)

                Text("Orest's Journal")
                    .font(.largeTitle)
                    .bold()

                Text("Track your pet's health and wellness")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                    .padding(.bottom, 30)

                if isSigningIn {
                    ProgressView("Signing in...")
                } else {
                    // Sign in with Apple button
                    SignInWithAppleButton(
                        onRequest: { request in
                            request.requestedScopes = [.fullName, .email]
                        },
                        onCompletion: { result in
                            handleSignInResult(result)
                        }
                    )
                    .signInWithAppleButtonStyle(.black)
                    .frame(height: 50)
                    .frame(maxWidth: 280)
                }

                if let error = errorMessage {
                    Text(error)
                        .foregroundColor(.red)
                        .font(.caption)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal)
                }

                Spacer()
            }
            .padding()
        }
    }

    private func handleSignInResult(_ result: Result<ASAuthorization, Error>) {
        switch result {
        case .success(let authorization):
            guard let credential = authorization.credential as? ASAuthorizationAppleIDCredential else {
                errorMessage = "Invalid credential type"
                return
            }

            isSigningIn = true
            errorMessage = nil

            Task {
                do {
                    try await authManager.signInWithApple(credential: credential)
                } catch {
                    errorMessage = error.localizedDescription
                }
                isSigningIn = false
            }

        case .failure(let error):
            // User cancelled or other error
            if (error as NSError).code != ASAuthorizationError.canceled.rawValue {
                errorMessage = error.localizedDescription
            }
        }
    }
}

#Preview {
    SignInScreen()
}
