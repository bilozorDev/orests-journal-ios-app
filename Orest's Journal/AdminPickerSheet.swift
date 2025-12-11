//
//  AdminPickerSheet.swift
//  Orest's Journal
//
//  Reusable sheet for selecting a new admin when leaving family or deleting account.
//

import SwiftUI

struct AdminPickerSheet: View {
    @Environment(\.dismiss) private var dismiss

    let members: [FamilyMemberResponse]
    let title: String
    let message: String
    let confirmButtonText: String
    let onConfirm: (FamilyMemberResponse) -> Void

    @State private var selectedMember: FamilyMemberResponse?
    @State private var isProcessing = false

    var body: some View {
        NavigationStack {
            List {
                Section {
                    Text(message)
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }

                Section(header: Text("Select New Admin")) {
                    ForEach(members) { member in
                        Button(action: { selectedMember = member }) {
                            HStack {
                                Image(systemName: "person.circle.fill")
                                    .font(.title3)
                                    .foregroundColor(.blue)

                                VStack(alignment: .leading, spacing: 2) {
                                    Text(member.displayName)
                                        .font(.body)
                                        .foregroundColor(.primary)

                                    if let email = member.email {
                                        Text(email)
                                            .font(.caption)
                                            .foregroundColor(.secondary)
                                    }
                                }

                                Spacer()

                                if selectedMember?.userId == member.userId {
                                    Image(systemName: "checkmark.circle.fill")
                                        .foregroundColor(.blue)
                                } else {
                                    Image(systemName: "circle")
                                        .foregroundColor(.gray.opacity(0.5))
                                }
                            }
                        }
                        .buttonStyle(.plain)
                    }
                }
                .accessibilityIdentifier(AccessibilityIdentifier.adminPickerList)
            }
            .navigationTitle(title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                    .disabled(isProcessing)
                }

                ToolbarItem(placement: .confirmationAction) {
                    Button(confirmButtonText) {
                        if let member = selectedMember {
                            isProcessing = true
                            onConfirm(member)
                        }
                    }
                    .disabled(selectedMember == nil || isProcessing)
                    .accessibilityIdentifier(AccessibilityIdentifier.selectAdminConfirmButton)
                }
            }
            .interactiveDismissDisabled(isProcessing)
        }
    }
}

#Preview {
    AdminPickerSheet(
        members: [],
        title: "Select New Admin",
        message: "You are the only admin. Please select a member to become the new admin before leaving.",
        confirmButtonText: "Confirm & Leave",
        onConfirm: { _ in }
    )
}
