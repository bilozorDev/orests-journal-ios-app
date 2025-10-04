//
//  AddMedicationView.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import SwiftUI

struct AddMedicationView: View {
    @Environment(\.dismiss) var dismiss

    @State private var pets: [Pet] = []
    @State private var selectedPet: Pet?
    @State private var medicationName = ""
    @State private var selectedType: MedicationType = .pill
    @State private var startDate = Date()
    @State private var hasEndDate = false
    @State private var endDate = Date()
    @State private var timesPerDay = 1
    @State private var notes = ""
    @State private var isLoading = true
    @State private var isSaving = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationView {
            Form {
                if isLoading {
                    Section {
                        ProgressView()
                    }
                } else if pets.isEmpty {
                    Section {
                        Text("No pets found")
                            .foregroundColor(.secondary)
                    }
                } else {
                    Section("Pet") {
                        if pets.count == 1 {
                            Text(pets.first?.name ?? "")
                                .foregroundColor(.primary)
                        } else {
                            Picker("Select Pet", selection: $selectedPet) {
                                Text("Select...").tag(nil as Pet?)
                                ForEach(pets) { pet in
                                    Text(pet.name).tag(pet as Pet?)
                                }
                            }
                        }
                    }

                    Section("Medication Information") {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Medicine Name *")
                                .font(.caption)
                                .foregroundColor(.secondary)
                            TextField("Enter medicine name", text: $medicationName)
                        }

                        Picker("Type", selection: $selectedType) {
                            ForEach(MedicationType.allCases, id: \.self) { type in
                                Text(type.displayName).tag(type)
                            }
                        }
                    }

                    Section("Schedule") {
                        DatePicker("Start Date", selection: $startDate, displayedComponents: .date)

                        Toggle("Has End Date", isOn: $hasEndDate)

                        if hasEndDate {
                            DatePicker("End Date", selection: $endDate, displayedComponents: .date)
                        }

                        HStack {
                            Text("Times per day")
                            Spacer()
                            HStack(spacing: 12) {
                                Button(action: {
                                    if timesPerDay > 1 {
                                        timesPerDay -= 1
                                    }
                                }) {
                                    Image(systemName: "minus.circle.fill")
                                        .foregroundColor(timesPerDay > 1 ? .blue : .gray)
                                }
                                .disabled(timesPerDay <= 1)

                                Text("\(timesPerDay)")
                                    .frame(minWidth: 30)

                                Button(action: {
                                    if timesPerDay < 10 {
                                        timesPerDay += 1
                                    }
                                }) {
                                    Image(systemName: "plus.circle.fill")
                                        .foregroundColor(timesPerDay < 10 ? .blue : .gray)
                                }
                                .disabled(timesPerDay >= 10)
                            }
                        }
                    }

                    Section("Notes (Optional)") {
                        TextEditor(text: $notes)
                            .frame(height: 80)
                    }

                    if let error = errorMessage {
                        Section {
                            Text(error)
                                .foregroundColor(.red)
                                .font(.caption)
                        }
                    }

                    Section {
                        if isSaving {
                            HStack {
                                Spacer()
                                ProgressView()
                                Spacer()
                            }
                        } else {
                            Button(action: saveMedication) {
                                Text("Add Medication")
                                    .frame(maxWidth: .infinity)
                                    .foregroundColor(.blue)
                            }
                            .disabled(!isFormValid)
                        }
                    }
                }
            }
            .navigationTitle("Add Medication")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
            }
            .task {
                await loadPets()
            }
        }
    }

    private var isFormValid: Bool {
        let petSelected = pets.count == 1 || selectedPet != nil
        let nameValid = !medicationName.isEmpty
        let dateValid = !hasEndDate || endDate >= startDate
        return petSelected && nameValid && dateValid
    }

    private func loadPets() async {
        isLoading = true
        do {
            guard let family = try await SupabaseService.shared.getCurrentUserFamily() else {
                errorMessage = "No family found"
                isLoading = false
                return
            }

            pets = try await SupabaseService.shared.getFamilyPets(familyId: family.id)

            // Auto-select if only one pet
            if pets.count == 1 {
                selectedPet = pets.first
            }
        } catch {
            errorMessage = error.localizedDescription
            print("Error loading pets: \(error)")
        }
        isLoading = false
    }

    private func saveMedication() {
        Task {
            isSaving = true
            errorMessage = nil

            do {
                let pet = pets.count == 1 ? pets.first! : selectedPet!

                _ = try await SupabaseService.shared.createMedication(
                    petId: pet.id,
                    name: medicationName,
                    medicationType: selectedType,
                    startDate: startDate,
                    endDate: hasEndDate ? endDate : nil,
                    timesPerDay: timesPerDay,
                    notes: notes.isEmpty ? nil : notes
                )

                dismiss()
            } catch {
                errorMessage = error.localizedDescription
                isSaving = false
            }
        }
    }
}

#Preview {
    AddMedicationView()
}
