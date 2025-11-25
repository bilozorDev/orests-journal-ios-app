//
//  ProfileView.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import SwiftUI

struct ProfileView: View {
    private var authManager = AuthManager.shared
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                if authManager.isAuthenticated {
                    Text("Welcome!")
                        .font(.largeTitle)
                        .bold()

                    VStack(alignment: .leading, spacing: 10) {
                        HStack {
                            Text("Email:")
                                .bold()
                            Text(authManager.userEmail ?? "No email")
                        }

                        HStack {
                            Text("User ID:")
                                .bold()
                            Text(authManager.userId ?? "Unknown")
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
        }
    }

    private func signOut() {
        authManager.signOut()
    }
}

#Preview {
    ProfileView()
}
