//
//  DeleteAccountSheet.swift
//  Orest's Journal
//
//  Multi-step account deletion with progress UI.
//

import SwiftUI

struct DeleteAccountSheet: View {
    @Environment(\.dismiss) private var dismiss
    private var authManager = AuthManager.shared

    let familyMembers: [FamilyMemberResponse]

    init(familyMembers: [FamilyMemberResponse]) {
        self.familyMembers = familyMembers
    }

    @State private var step: DeletionStep = .confirm
    @State private var isDeleting = false
    @State private var errorMessage: String?
    @State private var showAdminPicker = false
    @State private var selectedNewAdmin: FamilyMemberResponse?

    enum DeletionStep {
        case confirm
        case deleting
        case complete
    }

    /// Whether user is the only admin in their family
    var isOnlyAdmin: Bool {
        guard authManager.currentFamily?.role == "admin" else { return false }
        let otherAdmins = familyMembers.filter { $0.role == "admin" && $0.userId != authManager.userId }
        return otherAdmins.isEmpty
    }

    /// Whether there are other members in the family
    var hasOtherMembers: Bool {
        familyMembers.count > 1
    }

    /// Eligible members to promote as admin
    var eligibleForPromotion: [FamilyMemberResponse] {
        familyMembers.filter { $0.role != "admin" && $0.userId != authManager.userId }
    }

    /// Whether user is part of a family
    var isInFamily: Bool {
        authManager.currentFamily != nil
    }

    var body: some View {
        NavigationStack {
            Group {
                switch step {
                case .confirm:
                    confirmationView
                case .deleting:
                    deletingView
                case .complete:
                    completionView
                }
            }
            .navigationTitle("Delete Account")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    if step == .confirm {
                        Button("Cancel") {
                            dismiss()
                        }
                        .accessibilityIdentifier(AccessibilityIdentifier.cancelDeleteAccountButton)
                    }
                }
            }
            .interactiveDismissDisabled(step != .confirm)
            .sheet(isPresented: $showAdminPicker) {
                AdminPickerSheet(
                    members: eligibleForPromotion,
                    title: "Select New Admin",
                    message: "You are the only admin. Please select a member to become the new admin before deleting your account.",
                    confirmButtonText: "Confirm & Delete",
                    onConfirm: { newAdmin in
                        selectedNewAdmin = newAdmin
                        showAdminPicker = false
                        Task {
                            await deleteAccount(newAdminUserId: newAdmin.userId)
                        }
                    }
                )
            }
        }
    }

    // MARK: - Confirmation View

    private var confirmationView: some View {
        VStack(spacing: 24) {
            Spacer()

            Image(systemName: "exclamationmark.triangle.fill")
                .font(.system(size: 60))
                .foregroundStyle(.red)

            VStack(spacing: 12) {
                Text("Delete Your Account?")
                    .font(.title2)
                    .fontWeight(.bold)

                Text(warningMessage)
                    .font(.body)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal)
            }

            Spacer()

            VStack(spacing: 12) {
                Button(action: handleDeleteTap) {
                    HStack {
                        if isDeleting {
                            ProgressView()
                                .tint(.white)
                        }
                        Text("Delete My Account")
                    }
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.red)
                    .foregroundStyle(.white)
                    .cornerRadius(12)
                }
                .disabled(isDeleting)
                .accessibilityIdentifier(AccessibilityIdentifier.confirmDeleteAccountButton)

                Button("Cancel") {
                    dismiss()
                }
                .foregroundStyle(.blue)
            }
            .padding(.horizontal, 40)
            .padding(.bottom, 40)

            if let error = errorMessage {
                Text(error)
                    .font(.caption)
                    .foregroundStyle(.red)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal)
            }
        }
        .padding()
    }

    private var warningMessage: String {
        if !isInFamily {
            return "This will permanently delete your account and all associated data. This action cannot be undone."
        } else if isOnlyAdmin && !hasOtherMembers {
            return "You are the only member of your family. Deleting your account will also delete the family and all its data. This action cannot be undone."
        } else if isOnlyAdmin && hasOtherMembers {
            return "You are the only admin. You will need to select a new admin before deleting your account."
        } else {
            return "This will remove you from your family and permanently delete your account. This action cannot be undone."
        }
    }

    // MARK: - Deleting View

    private var deletingView: some View {
        VStack(spacing: 24) {
            Spacer()

            ProgressView()
                .scaleEffect(1.5)
                .padding(.bottom, 20)

            Text("Deleting your account...")
                .font(.title3)
                .fontWeight(.medium)

            VStack(alignment: .leading, spacing: 16) {
                deletionStepRow("Removing from family", isComplete: true)
                deletionStepRow("Deleting your data", isComplete: false)
                deletionStepRow("Deleting account", isComplete: false)
            }
            .padding(.horizontal, 40)

            Spacer()
        }
    }

    private func deletionStepRow(_ text: String, isComplete: Bool) -> some View {
        HStack(spacing: 12) {
            if isComplete {
                Image(systemName: "checkmark.circle.fill")
                    .foregroundStyle(.green)
            } else {
                ProgressView()
                    .scaleEffect(0.8)
            }

            Text(text)
                .font(.body)
                .foregroundStyle(isComplete ? .secondary : .primary)
        }
    }

    // MARK: - Completion View

    private var completionView: some View {
        VStack(spacing: 24) {
            Spacer()

            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 80))
                .foregroundStyle(.green)

            VStack(spacing: 12) {
                Text("Account Deleted")
                    .font(.title)
                    .fontWeight(.bold)

                Text("Your account and all associated data have been permanently deleted.")
                    .font(.body)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }

            Spacer()

            Button(action: backToLogin) {
                Text("Back to Login")
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.blue)
                    .foregroundStyle(.white)
                    .cornerRadius(12)
            }
            .accessibilityIdentifier(AccessibilityIdentifier.backToLoginButton)
            .padding(.horizontal, 40)
            .padding(.bottom, 40)
        }
        .padding()
    }

    // MARK: - Actions

    private func handleDeleteTap() {
        // If only admin with other members, need to pick new admin first
        if isOnlyAdmin && hasOtherMembers {
            showAdminPicker = true
        } else {
            Task {
                await deleteAccount(newAdminUserId: nil)
            }
        }
    }

    private func deleteAccount(newAdminUserId: String?) async {
        isDeleting = true
        errorMessage = nil
        step = .deleting

        do {
            _ = try await authManager.deleteAccount(newAdminUserId: newAdminUserId)
            step = .complete
        } catch {
            step = .confirm
            errorMessage = error.localizedDescription
        }

        isDeleting = false
    }

    private func backToLogin() {
        Task {
            await authManager.signOut()
        }
        dismiss()
    }
}

#Preview {
    DeleteAccountSheet(familyMembers: [])
}
