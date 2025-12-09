//
//  EditFamilyNameSheet.swift
//  Orest's Journal
//
//  Sheet for editing the family name.
//

import SwiftUI

struct EditFamilyNameSheet: View {
    @Environment(\.dismiss) private var dismiss

    let familyId: String
    let currentName: String
    var onSave: ((AppFamily) -> Void)?

    @State private var familyName: String
    @State private var isSaving = false
    @State private var errorMessage: String?

    init(familyId: String, currentName: String, onSave: ((AppFamily) -> Void)? = nil) {
        self.familyId = familyId
        self.currentName = currentName
        self.onSave = onSave
        _familyName = State(initialValue: currentName)
    }

    private var isFormValid: Bool {
        !familyName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty &&
        familyName != currentName
    }

    var body: some View {
        NavigationStack {
            Form {
                Section(header: Text("Family Name")) {
                    TextField("Family Name", text: $familyName)
                        .textContentType(.organizationName)
                        .autocorrectionDisabled(false)
                }

                if let error = errorMessage {
                    Section {
                        Text(error)
                            .foregroundColor(.red)
                            .font(.caption)
                    }
                }
            }
            .navigationTitle("Edit Family Name")
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
                            await saveFamilyName()
                        }
                    }
                    .disabled(!isFormValid || isSaving)
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

    private func saveFamilyName() async {
        isSaving = true
        errorMessage = nil

        do {
            let trimmedName = familyName.trimmingCharacters(in: .whitespacesAndNewlines)
            let updatedFamily = try await DataService.shared.updateFamilyName(
                familyId: familyId,
                name: trimmedName
            )

            // Update AuthManager with new family info
            AuthManager.shared.updateCurrentFamily(updatedFamily)

            onSave?(updatedFamily)
            dismiss()
        } catch {
            errorMessage = error.localizedDescription
            isSaving = false
        }
    }
}

#Preview {
    EditFamilyNameSheet(familyId: "test-id", currentName: "Test Family")
}
