//
//  FamilySetupView.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import SwiftUI
import Supabase

struct FamilySetupView: View {
    @State private var familyName = ""
    @State private var memberEmail = ""
    @State private var memberEmails: [String] = []
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

                    Section(header: Text("Invite Family Members (Optional)")) {
                        HStack {
                            TextField("Email address", text: $memberEmail)
                                .textInputAutocapitalization(.never)
                                .keyboardType(.emailAddress)

                            Button(action: addMemberEmail) {
                                Image(systemName: "plus.circle.fill")
                                    .foregroundColor(.blue)
                            }
                            .disabled(memberEmail.isEmpty || !isValidEmail(memberEmail))
                        }

                        if !memberEmails.isEmpty {
                            ForEach(memberEmails, id: \.self) { email in
                                HStack {
                                    Text(email)
                                        .font(.body)
                                    Spacer()
                                    Button(action: { removeMemberEmail(email) }) {
                                        Image(systemName: "minus.circle.fill")
                                            .foregroundColor(.red)
                                    }
                                }
                            }
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
                            Button(action: createFamily) {
                                Text("Continue")
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
                    // Check if user already has a family
                    do {
                        let status = try await SupabaseService.shared.checkUserFamilyAndPet()
                        if status.hasFamily {
                            // User already has a family, trigger refresh to navigate away
                            NotificationCenter.default.post(name: NSNotification.Name("RefreshFamilyStatus"), object: nil)
                        }
                    } catch {
                        print("Error checking family status: \(error)")
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

    private func isValidEmail(_ email: String) -> Bool {
        let emailRegex = "[A-Z0-9a-z._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,64}"
        let emailPredicate = NSPredicate(format: "SELF MATCHES %@", emailRegex)
        return emailPredicate.evaluate(with: email)
    }

    private func addMemberEmail() {
        let trimmedEmail = memberEmail.trimmingCharacters(in: .whitespaces)
        if !memberEmails.contains(trimmedEmail) && isValidEmail(trimmedEmail) {
            memberEmails.append(trimmedEmail)
            memberEmail = ""
        }
    }

    private func removeMemberEmail(_ email: String) {
        memberEmails.removeAll { $0 == email }
    }

    private func createFamily() {
        Task {
            isLoading = true
            errorMessage = nil

            do {
                // Create family
                _ = try await SupabaseService.shared.createFamily(name: familyName)

                // TODO: Send invites to member emails
                // For now, we'll just store them for future implementation
                if !memberEmails.isEmpty {
                    print("Invites to send: \(memberEmails)")
                }

                // Notify ContentView to refresh
                NotificationCenter.default.post(name: NSNotification.Name("RefreshFamilyStatus"), object: nil)
            } catch {
                errorMessage = error.localizedDescription
                isLoading = false
            }
        }
    }

    private func signOut() {
        Task {
            try? await supabase.auth.signOut()
        }
    }
}

#Preview {
    FamilySetupView()
}
