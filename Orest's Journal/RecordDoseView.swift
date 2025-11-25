//
//  RecordDoseView.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import SwiftUI

struct RecordDoseView: View {
    let petId: UUID?
    @Environment(\.dismiss) var dismiss

    @State private var medications: [PetMedication] = []
    @State private var selectedMedication: PetMedication?
    @State private var notes: String = ""
    @State private var isLoading = true
    @State private var isSaving = false
    @State private var showError = false
    @State private var errorMessage = ""

    init(petId: UUID? = nil) {
        self.petId = petId
    }

    var body: some View {
        NavigationView {
            Form {
                Section("Select Medication") {
                    if isLoading {
                        ProgressView()
                    } else if medications.isEmpty {
                        Text("No active medications")
                            .foregroundColor(.secondary)
                        Button("Add Medication First") {
                            dismiss()
                        }
                    } else {
                        Picker("Medication", selection: $selectedMedication) {
                            Text("Select...").tag(nil as PetMedication?)
                            ForEach(medications) { medication in
                                VStack(alignment: .leading) {
                                    Text(medication.name)
                                    Text("\(medication.timesPerDay)x per day")
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }
                                .tag(medication as PetMedication?)
                            }
                        }
                    }
                }

                if selectedMedication != nil {
                    Section("Notes (Optional)") {
                        TextEditor(text: $notes)
                            .frame(height: 80)
                    }
                }
            }
            .navigationTitle("Record Dose")
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
                            await saveDose()
                        }
                    }
                    .disabled(selectedMedication == nil || isSaving)
                }
            }
            .task {
                await loadMedications()
            }
            .alert("Error", isPresented: $showError) {
                Button("OK") {}
            } message: {
                Text(errorMessage)
            }
        }
    }

    private func loadMedications() async {
        isLoading = true
        do {
            if let petId = petId {
                // Load medications for specific pet
                medications = try await DataService.shared.getActiveMedications(for: petId)
            } else {
                // Load all active medications
                let allMedications = try await DataService.shared.getMedications(activeOnly: true)
                medications = allMedications
            }
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
        isLoading = false
    }

    private func saveDose() async {
        guard let medication = selectedMedication else {
            return
        }

        isSaving = true
        do {
            _ = try await DataService.shared.recordDose(
                medicationId: medication.id,
                notes: notes.isEmpty ? nil : notes
            )
            dismiss()
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
        isSaving = false
    }
}

#Preview {
    RecordDoseView()
}
