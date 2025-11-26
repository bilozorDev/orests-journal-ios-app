//
//  EditFeedingView.swift
//  Orest's Journal
//
//  Edit an existing feeding record.
//

import SwiftUI

struct EditFeedingView: View {
    @Environment(\.dismiss) var dismiss

    let feeding: PetFeeding
    let food: PetFood?
    var onSave: ((PetFeeding) -> Void)?

    @State private var amount: String
    @State private var selectedUnit: ContainerUnit
    @State private var notes: String
    @State private var fedAt: Date
    @State private var isLoading = false
    @State private var errorMessage: String?

    init(feeding: PetFeeding, food: PetFood?, onSave: ((PetFeeding) -> Void)? = nil) {
        self.feeding = feeding
        self.food = food
        self.onSave = onSave
        _amount = State(initialValue: String(format: "%.2f", feeding.amount).trimmingCharacters(in: CharacterSet(charactersIn: "0")).trimmingCharacters(in: CharacterSet(charactersIn: ".")))
        _selectedUnit = State(initialValue: feeding.amountUnit)
        _notes = State(initialValue: feeding.notes ?? "")
        _fedAt = State(initialValue: feeding.fedAt)
    }

    var body: some View {
        NavigationView {
            Form {
                Section(header: Text("Food")) {
                    HStack {
                        Text(food?.name ?? "Unknown Food")
                            .foregroundColor(.primary)
                        Spacer()
                        Text(food?.category.displayName ?? "")
                            .foregroundColor(.secondary)
                    }
                }

                Section(header: Text("Amount")) {
                    HStack {
                        TextField("Amount", text: $amount)
                            .keyboardType(.decimalPad)

                        Picker("Unit", selection: $selectedUnit) {
                            ForEach(ContainerUnit.allCases, id: \.self) { unit in
                                Text(unit.abbreviation).tag(unit)
                            }
                        }
                        .pickerStyle(.menu)
                    }

                    if let food = food, let amountValue = Double(amount) {
                        let calculatedCalories = food.calculateCalories(for: amountValue, unit: selectedUnit)
                        HStack {
                            Text("Calories")
                                .foregroundColor(.secondary)
                            Spacer()
                            Text("\(Int(calculatedCalories)) cal")
                                .foregroundColor(.blue)
                                .fontWeight(.semibold)
                        }
                    }
                }

                Section(header: Text("Time")) {
                    DatePicker("Fed at", selection: $fedAt, displayedComponents: [.date, .hourAndMinute])
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
                        Button(action: saveFeeding) {
                            Text("Save Changes")
                                .frame(maxWidth: .infinity)
                                .foregroundColor(.blue)
                        }
                        .disabled(!isFormValid || !hasChanges)
                    }
                }
            }
            .navigationTitle("Edit Feeding")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
            }
        }
    }

    private var isFormValid: Bool {
        !amount.isEmpty && Double(amount) != nil
    }

    private var hasChanges: Bool {
        Double(amount) != feeding.amount ||
        selectedUnit != feeding.amountUnit ||
        notes != (feeding.notes ?? "") ||
        fedAt != feeding.fedAt
    }

    private func saveFeeding() {
        Task {
            isLoading = true
            errorMessage = nil

            do {
                guard let amountValue = Double(amount) else {
                    throw NSError(domain: "EditFeedingView", code: 400, userInfo: [NSLocalizedDescriptionKey: "Invalid amount format"])
                }

                // Calculate new calories if food is available
                let newCalories: Double?
                if let food = food {
                    let calculatedCalories = food.calculateCalories(for: amountValue, unit: selectedUnit)
                    newCalories = calculatedCalories != feeding.calories ? calculatedCalories : nil
                } else {
                    newCalories = nil
                }

                let updatedFeeding = try await DataService.shared.updateFeeding(
                    id: feeding.id,
                    amount: amountValue != feeding.amount ? amountValue : nil,
                    amountUnit: selectedUnit != feeding.amountUnit ? selectedUnit : nil,
                    calories: newCalories,
                    notes: notes != (feeding.notes ?? "") ? (notes.isEmpty ? nil : notes) : nil,
                    fedAt: fedAt != feeding.fedAt ? fedAt : nil,
                    petId: feeding.petId
                )

                onSave?(updatedFeeding)
                dismiss()
            } catch {
                errorMessage = error.localizedDescription
                isLoading = false
            }
        }
    }
}
