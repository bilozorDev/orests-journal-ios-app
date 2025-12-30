//
//  EditDoseSheet.swift
//  Orest's Journal
//
//  Sheet for editing an existing dose record (time and notes).
//

import SwiftUI

struct EditDoseSheet: View {
    @Environment(\.dismiss) private var dismiss

    let dose: MedicationDose
    let medicationName: String
    let familyId: String
    var onDoseUpdated: (() -> Void)?

    @State private var givenAt: Date
    @State private var notes: String
    @State private var isSaving = false
    @State private var errorMessage: String?

    init(dose: MedicationDose, medicationName: String, familyId: String, onDoseUpdated: (() -> Void)? = nil) {
        self.dose = dose
        self.medicationName = medicationName
        self.familyId = familyId
        self.onDoseUpdated = onDoseUpdated
        _givenAt = State(initialValue: dose.givenAt)
        _notes = State(initialValue: dose.notes ?? "")
    }

    private var hasChanges: Bool {
        let timeChanged = abs(givenAt.timeIntervalSince(dose.givenAt)) > 60 // More than 1 minute difference
        let notesChanged = notes.trimmingCharacters(in: .whitespaces) != (dose.notes ?? "")
        return timeChanged || notesChanged
    }

    var body: some View {
        NavigationStack {
            Form {
                // Info section
                Section {
                    LabeledContent("Medication", value: medicationName)
                    LabeledContent("Recorded by", value: dose.givenBy)
                }

                // Time
                Section(header: Text("Time Given")) {
                    DatePicker(
                        "When",
                        selection: $givenAt,
                        in: ...Date(),
                        displayedComponents: [.date, .hourAndMinute]
                    )
                }

                // Notes
                Section(header: Text("Notes")) {
                    TextField("Add any notes...", text: $notes, axis: .vertical)
                        .lineLimit(3...6)
                }

                // Error message
                if let error = errorMessage {
                    Section {
                        Text(error)
                            .foregroundStyle(.red)
                            .font(.caption)
                    }
                }
            }
            .navigationTitle("Edit Dose")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                    .disabled(isSaving)
                }

                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        Task {
                            await saveDose()
                        }
                    }
                    .disabled(!hasChanges || isSaving)
                    .fontWeight(.semibold)
                }
            }
            .interactiveDismissDisabled(isSaving)
        }
    }

    private func saveDose() async {
        isSaving = true
        errorMessage = nil

        do {
            let notesText = notes.trimmingCharacters(in: .whitespaces).isEmpty ? nil : notes.trimmingCharacters(in: .whitespaces)

            _ = try await DataService.shared.updateDose(
                doseId: dose.id,
                givenAt: givenAt,
                notes: notesText,
                familyId: familyId
            )

            // Haptic feedback on success
            let generator = UINotificationFeedbackGenerator()
            generator.notificationOccurred(.success)

            onDoseUpdated?()
            dismiss()

        } catch {
            errorMessage = error.localizedDescription
            isSaving = false
        }
    }
}
