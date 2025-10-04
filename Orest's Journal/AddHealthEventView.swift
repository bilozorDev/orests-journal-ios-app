//
//  AddHealthEventView.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import SwiftUI

struct AddHealthEventView: View {
    let petId: UUID

    @Environment(\.dismiss) var dismiss

    @State private var categoryName = ""
    @State private var occurredAt = Date()
    @State private var notes = ""
    @State private var existingCategories: [HealthCategory] = []
    @State private var isLoading = true
    @State private var isSaving = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationView {
            Form {
                Section("Event Type") {
                    VStack(alignment: .leading, spacing: 8) {
                        TextField("e.g., Asthma attack", text: $categoryName)
                            .textInputAutocapitalization(.words)

                        if !existingCategories.isEmpty && categoryName.isEmpty {
                            Text("Or select from existing:")
                                .font(.caption)
                                .foregroundColor(.secondary)
                                .padding(.top, 4)

                            ScrollView(.horizontal, showsIndicators: false) {
                                HStack(spacing: 8) {
                                    ForEach(existingCategories) { category in
                                        Button(action: {
                                            categoryName = category.name
                                        }) {
                                            Text(category.name)
                                                .font(.subheadline)
                                                .padding(.horizontal, 12)
                                                .padding(.vertical, 6)
                                                .background(Color.blue.opacity(0.1))
                                                .foregroundColor(.blue)
                                                .cornerRadius(16)
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                Section("When") {
                    DatePicker("Occurred at", selection: $occurredAt, displayedComponents: [.date, .hourAndMinute])
                }

                Section("Notes (Optional)") {
                    TextEditor(text: $notes)
                        .frame(height: 100)
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
                        Button(action: saveEvent) {
                            Text("Save Event")
                                .frame(maxWidth: .infinity)
                                .foregroundColor(.blue)
                        }
                        .disabled(!isFormValid)
                    }
                }
            }
            .navigationTitle("Add Health Event")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
            }
            .task {
                await loadCategories()
            }
        }
    }

    private var isFormValid: Bool {
        !categoryName.trimmingCharacters(in: .whitespaces).isEmpty
    }

    private func loadCategories() async {
        isLoading = true
        do {
            existingCategories = try await SupabaseService.shared.getHealthCategories(for: petId)
        } catch {
            errorMessage = error.localizedDescription
            print("Error loading categories: \(error)")
        }
        isLoading = false
    }

    private func saveEvent() {
        Task {
            isSaving = true
            errorMessage = nil

            do {
                _ = try await SupabaseService.shared.createHealthEvent(
                    petId: petId,
                    categoryName: categoryName,
                    occurredAt: occurredAt,
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
    AddHealthEventView(petId: UUID())
}
