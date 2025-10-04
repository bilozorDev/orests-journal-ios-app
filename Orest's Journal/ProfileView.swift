//
//  ProfileView.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import SwiftUI
import Supabase

struct ProfileView: View {
    @State private var user: User?
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                if let user = user {
                    Text("Welcome!")
                        .font(.largeTitle)
                        .bold()

                    VStack(alignment: .leading, spacing: 10) {
                        HStack {
                            Text("Email:")
                                .bold()
                            Text(user.email ?? "No email")
                        }

                        HStack {
                            Text("User ID:")
                                .bold()
                            Text(user.id.uuidString)
                                .font(.caption)
                        }
                    }
                    .padding()
                    .background(Color.gray.opacity(0.1))
                    .cornerRadius(10)

                    Spacer()

                    Button(action: signOut) {
                        Text("Sign Out")
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color.red)
                            .foregroundColor(.white)
                            .cornerRadius(10)
                    }
                } else {
                    ProgressView("Loading profile...")
                }

                if let error = errorMessage {
                    Text(error)
                        .foregroundColor(.red)
                        .font(.caption)
                }
            }
            .padding()
            .navigationTitle("Profile")
            .task {
                await loadUser()
            }
        }
    }

    private func loadUser() async {
        do {
            user = try await supabase.auth.session.user
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func signOut() {
        Task {
            isLoading = true
            errorMessage = nil

            do {
                try await supabase.auth.signOut()
            } catch {
                errorMessage = error.localizedDescription
            }

            isLoading = false
        }
    }
}

#Preview {
    ProfileView()
}
