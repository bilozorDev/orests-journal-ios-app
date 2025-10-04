//
//  AuthView.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import SwiftUI
import Supabase

struct AuthView: View {
    @State private var email = ""
    @State private var password = ""
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var showingSignUp = false

    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                Text("Orest's Journal")
                    .font(.largeTitle)
                    .bold()
                    .padding(.bottom, 30)

                TextField("Email", text: $email)
                    .textInputAutocapitalization(.never)
                    .keyboardType(.emailAddress)
                    .textFieldStyle(.roundedBorder)
                    .disabled(isLoading)

                SecureField("Password", text: $password)
                    .textFieldStyle(.roundedBorder)
                    .disabled(isLoading)

                if let error = errorMessage {
                    Text(error)
                        .foregroundColor(.red)
                        .font(.caption)
                }

                if isLoading {
                    ProgressView()
                } else {
                    Button(action: showingSignUp ? signUp : signIn) {
                        Text(showingSignUp ? "Sign Up" : "Sign In")
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color.blue)
                            .foregroundColor(.white)
                            .cornerRadius(10)
                    }
                    .disabled(email.isEmpty || password.isEmpty)

                    Button(action: { showingSignUp.toggle() }) {
                        Text(showingSignUp ? "Already have an account? Sign In" : "Don't have an account? Sign Up")
                            .font(.caption)
                    }

                    Divider()
                        .padding(.vertical)

                    Button(action: signInWithMagicLink) {
                        Text("Sign in with Magic Link")
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color.purple)
                            .foregroundColor(.white)
                            .cornerRadius(10)
                    }
                    .disabled(email.isEmpty)
                }
            }
            .padding()
            .navigationTitle("Welcome")
        }
    }

    private func signIn() {
        Task {
            isLoading = true
            errorMessage = nil

            do {
                try await supabase.auth.signIn(email: email, password: password)
            } catch {
                errorMessage = error.localizedDescription
            }

            isLoading = false
        }
    }

    private func signUp() {
        Task {
            isLoading = true
            errorMessage = nil

            do {
                try await supabase.auth.signUp(email: email, password: password)
                errorMessage = nil
            } catch {
                errorMessage = error.localizedDescription
            }

            isLoading = false
        }
    }

    private func signInWithMagicLink() {
        Task {
            isLoading = true
            errorMessage = nil

            do {
                try await supabase.auth.signInWithOTP(email: email)
                errorMessage = "Check your email for the magic link!"
            } catch {
                errorMessage = error.localizedDescription
            }

            isLoading = false
        }
    }
}

#Preview {
    AuthView()
}
