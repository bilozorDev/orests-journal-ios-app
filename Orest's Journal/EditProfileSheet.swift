//
//  EditProfileSheet.swift
//  Orest's Journal
//
//  Sheet for editing user profile (first name, last name).
//

import SwiftUI

struct EditProfileSheet: View {
    @Environment(\.dismiss) private var dismiss
    private var authManager = AuthManager.shared

    @State private var firstName: String
    @State private var lastName: String
    @State private var isSaving = false
    @State private var errorMessage: String?

    init() {
        _firstName = State(initialValue: AuthManager.shared.currentUser?.firstName ?? "")
        _lastName = State(initialValue: AuthManager.shared.currentUser?.lastName ?? "")
    }

    private var hasChanges: Bool {
        let user = authManager.currentUser
        let originalFirst = user?.firstName ?? ""
        let originalLast = user?.lastName ?? ""
        return firstName.trimmingCharacters(in: .whitespaces) != originalFirst ||
               lastName.trimmingCharacters(in: .whitespaces) != originalLast
    }

    private var canSave: Bool {
        !firstName.trimmingCharacters(in: .whitespaces).isEmpty && hasChanges && !isSaving
    }

    var body: some View {
        NavigationStack {
            Form {
                Section(header: Text("Your Name")) {
                    TextField("First Name", text: $firstName)
                        .textContentType(.givenName)
                        .autocorrectionDisabled(true)
                        .accessibilityIdentifier(AccessibilityIdentifier.firstNameField)

                    TextField("Last Name (optional)", text: $lastName)
                        .textContentType(.familyName)
                        .autocorrectionDisabled(true)
                        .accessibilityIdentifier(AccessibilityIdentifier.lastNameField)
                }

                if let error = errorMessage {
                    Section {
                        Text(error)
                            .foregroundColor(.red)
                            .font(.caption)
                    }
                }
            }
            .navigationTitle("Edit Profile")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                    .accessibilityIdentifier(AccessibilityIdentifier.cancelEditProfileButton)
                }

                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        Task {
                            await saveProfile()
                        }
                    }
                    .disabled(!canSave)
                    .accessibilityIdentifier(AccessibilityIdentifier.saveEditProfileButton)
                }
            }
            .interactiveDismissDisabled(isSaving)
        }
    }

    private func saveProfile() async {
        isSaving = true
        errorMessage = nil

        do {
            try await authManager.updateProfile(
                firstName: firstName.trimmingCharacters(in: .whitespaces),
                lastName: lastName.trimmingCharacters(in: .whitespaces).isEmpty ? nil : lastName.trimmingCharacters(in: .whitespaces)
            )
            dismiss()
        } catch {
            errorMessage = error.localizedDescription
        }

        isSaving = false
    }
}

#Preview {
    EditProfileSheet()
}
