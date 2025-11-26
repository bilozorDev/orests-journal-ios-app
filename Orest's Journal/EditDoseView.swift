//
//  EditDoseView.swift
//  Orest's Journal
//
//  Edit an existing medication dose record.
//

import SwiftUI

struct EditDoseView: View {
    @Environment(\.dismiss) var dismiss

    let dose: PetMedicationDose
    let medication: PetMedication?
    let petId: UUID?
    var onSave: ((PetMedicationDose) -> Void)?

    @State private var givenAt: Date
    @State private var selectedGivenByUserId: String
    @State private var originalGivenByName: String
    @State private var notes: String
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var familyMembers: [FamilyMemberResponse] = []
    @State private var isLoadingMembers = false

    init(dose: PetMedicationDose, medication: PetMedication?, petId: UUID?, onSave: ((PetMedicationDose) -> Void)? = nil) {
        self.dose = dose
        self.medication = medication
        self.petId = petId
        self.onSave = onSave
        _givenAt = State(initialValue: dose.givenAt)
        _selectedGivenByUserId = State(initialValue: "")  // Will be set when members load
        _originalGivenByName = State(initialValue: dose.givenBy)
        _notes = State(initialValue: dose.notes ?? "")
    }

    var body: some View {
        NavigationView {
            Form {
                if let medication = medication {
                    Section(header: Text("Medication")) {
                        HStack {
                            Text(medication.name)
                                .foregroundColor(.primary)
                            Spacer()
                            Text(medication.medicationType.displayName)
                                .foregroundColor(.secondary)
                        }
                    }
                }

                Section(header: Text("Time")) {
                    DatePicker("Given at", selection: $givenAt, displayedComponents: [.date, .hourAndMinute])
                }

                // Only show "Who gave" if there are multiple family members
                if familyMembers.count > 1 {
                    Section(header: Text("Who gave")) {
                        Picker("Given by", selection: $selectedGivenByUserId) {
                            ForEach(familyMembers) { member in
                                Text(member.displayName).tag(member.userId)
                            }
                        }
                        .pickerStyle(.menu)
                    }
                }

                Section(header: Text("Notes (Optional)")) {
                    TextEditor(text: $notes)
                        .frame(minHeight: 80)
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
                        Button(action: saveDose) {
                            Text("Save Changes")
                                .frame(maxWidth: .infinity)
                                .foregroundColor(.blue)
                        }
                        .disabled(!hasChanges)
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
                }
            }
            .task {
                await loadFamilyMembers()
            }
        }
    }

    private var selectedMemberName: String {
        familyMembers.first { $0.userId == selectedGivenByUserId }?.displayName ?? originalGivenByName
    }

    private var hasChanges: Bool {
        givenAt != dose.givenAt ||
        (selectedGivenByUserId.isEmpty ? false : selectedMemberName != originalGivenByName) ||
        notes != (dose.notes ?? "")
    }

    private func loadFamilyMembers() async {
        guard let familyId = AuthManager.shared.currentFamily?.id else { return }

        isLoadingMembers = true
        do {
            familyMembers = try await DataService.shared.getFamilyMembers(familyId: familyId)
            // Find and select the member whose name matches the original givenBy
            if let matchingMember = familyMembers.first(where: { $0.displayName == originalGivenByName }) {
                selectedGivenByUserId = matchingMember.userId
            } else if let firstMember = familyMembers.first {
                // Fallback to first member if no match found
                selectedGivenByUserId = firstMember.userId
            }
        } catch {
            print("Error loading family members: \(error)")
            // Don't show error - just don't show the picker
        }
        isLoadingMembers = false
    }

    private func saveDose() {
        Task {
            isLoading = true
            errorMessage = nil

            do {
                // Only send changed fields
                let newGivenAt = givenAt != dose.givenAt ? givenAt : nil
                let newGivenBy = selectedMemberName != originalGivenByName ? UUID(uuidString: selectedGivenByUserId) : nil
                let newNotes: String? = notes != (dose.notes ?? "") ? (notes.isEmpty ? nil : notes) : nil

                let updatedDose = try await DataService.shared.updateDose(
                    id: dose.id,
                    givenAt: newGivenAt,
                    givenBy: newGivenBy,
                    notes: newNotes,
                    petId: petId
                )

                onSave?(updatedDose)
                dismiss()
            } catch {
                errorMessage = error.localizedDescription
                isLoading = false
            }
        }
    }
}
