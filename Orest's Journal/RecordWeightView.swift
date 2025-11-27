//
//  RecordWeightView.swift
//  Orest's Journal
//
//  Created by Claude on 11/26/25.
//

import SwiftUI

struct RecordWeightView: View {
    let petId: UUID
    let petName: String
    let currentWeight: Double?

    @Environment(\.dismiss) var dismiss

    @State private var weight = ""
    @State private var notes = ""
    @State private var isSaving = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationView {
            Form {
                Section {
                    HStack {
                        TextField("Weight", text: $weight)
                            .keyboardType(.decimalPad)
                        Text("lbs")
                            .foregroundColor(.secondary)
                    }

                    if let current = currentWeight {
                        HStack {
                            Text("Current weight")
                                .foregroundColor(.secondary)
                            Spacer()
                            Text(String(format: "%.1f lbs", current))
                                .foregroundColor(.secondary)
                        }
                        .font(.caption)
                    }
                } header: {
                    Text("Weight for \(petName)")
                }

                Section("Notes (Optional)") {
                    TextField("Any observations...", text: $notes, axis: .vertical)
                        .lineLimit(3...6)
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
                        Button(action: saveWeight) {
                            Text("Save Weight")
                                .frame(maxWidth: .infinity)
                                .foregroundColor(.blue)
                        }
                        .disabled(!isFormValid)
                    }
                }
            }
            .navigationTitle("Record Weight")
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
        guard let weightValue = Double(weight) else { return false }
        return weightValue > 0
    }

    private func saveWeight() {
        guard let weightValue = Double(weight) else { return }

        Task {
            isSaving = true
            errorMessage = nil

            do {
                _ = try await DataService.shared.recordWeight(
                    petId: petId,
                    weight: weightValue,
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
    RecordWeightView(petId: UUID(), petName: "Orest", currentWeight: 12.5)
}
