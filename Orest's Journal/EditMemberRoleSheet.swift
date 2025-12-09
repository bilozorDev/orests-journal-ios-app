//
//  EditMemberRoleSheet.swift
//  Orest's Journal
//
//  Created by Claude on 11/26/25.
//

import SwiftUI

struct EditMemberRoleSheet: View {
    @Environment(\.dismiss) var dismiss
    private var authManager = AuthManager.shared

    let member: FamilyMemberResponse
    var onSave: ((FamilyMemberResponse) -> Void)?

    @State private var selectedRole: String
    @State private var isSaving = false
    @State private var errorMessage: String?

    let roles = ["admin", "member"]

    init(member: FamilyMemberResponse, onSave: ((FamilyMemberResponse) -> Void)? = nil) {
        self.member = member
        self.onSave = onSave
        _selectedRole = State(initialValue: member.role)
    }

    var hasChanges: Bool {
        selectedRole != member.role
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    HStack(spacing: 12) {
                        Image(systemName: "person.circle.fill")
                            .font(.title)
                            .foregroundColor(.blue)

                        VStack(alignment: .leading, spacing: 4) {
                            Text(member.displayName)
                                .font(.headline)

                            if let email = member.email {
                                Text(email)
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                        }
                    }
                    .padding(.vertical, 8)
                }

                Section(header: Text("Role")) {
                    Picker("Role", selection: $selectedRole) {
                        ForEach(roles, id: \.self) { role in
                            HStack {
                                Image(systemName: role == "admin" ? "star.fill" : "person.fill")
                                    .foregroundColor(role == "admin" ? .orange : .blue)
                                Text(role.capitalized)
                            }
                            .tag(role)
                        }
                    }
                    .pickerStyle(.inline)
                    .labelsHidden()
                }

                Section {
                    VStack(alignment: .leading, spacing: 8) {
                        Label {
                            Text("Admin")
                                .fontWeight(.medium)
                        } icon: {
                            Image(systemName: "star.fill")
                                .foregroundColor(.orange)
                        }
                        Text("Can manage family members, change roles, and remove members")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    .padding(.vertical, 4)

                    VStack(alignment: .leading, spacing: 8) {
                        Label {
                            Text("Member")
                                .fontWeight(.medium)
                        } icon: {
                            Image(systemName: "person.fill")
                                .foregroundColor(.blue)
                        }
                        Text("Can view and record pet activities but cannot manage family members")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    .padding(.vertical, 4)
                } header: {
                    Text("Role Permissions")
                }

                if let error = errorMessage {
                    Section {
                        Text(error)
                            .foregroundColor(.red)
                            .font(.caption)
                    }
                }
            }
            .navigationTitle("Change Role")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }

                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        Task {
                            await saveRole()
                        }
                    }
                    .disabled(!hasChanges || isSaving)
                }
            }
            .overlay {
                if isSaving {
                    ProgressView("Saving...")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                        .background(Color.black.opacity(0.3))
                }
            }
        }
    }

    private func saveRole() async {
        guard let familyId = authManager.currentFamily?.id else {
            errorMessage = "Family not found"
            return
        }

        isSaving = true
        errorMessage = nil

        do {
            let updatedMember = try await DataService.shared.updateMemberRole(
                familyId: familyId,
                userId: member.userId,
                role: selectedRole
            )
            // Convert FamilyMember to FamilyMemberResponse for the callback
            let response = FamilyMemberResponse(
                id: updatedMember.id,
                userId: updatedMember.userId,
                email: updatedMember.email,
                firstName: updatedMember.firstName,
                lastName: updatedMember.lastName,
                role: updatedMember.role,
                joinedAt: updatedMember.joinedAt
            )
            onSave?(response)
            dismiss()
        } catch {
            errorMessage = error.localizedDescription
            isSaving = false
        }
    }
}

#Preview {
    EditMemberRoleSheet(
        member: FamilyMemberResponse(
            id: "123",
            userId: "user-123",
            email: "john@example.com",
            firstName: "John",
            lastName: "Doe",
            role: "member",
            joinedAt: Date()
        )
    )
}
