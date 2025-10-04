//
//  SetCalorieGoalView.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import SwiftUI

struct SetCalorieGoalView: View {
    let petId: UUID
    let currentGoal: Double

    @Environment(\.dismiss) var dismiss

    @State private var dailyCalories: String = ""
    @State private var notes: String = ""
    @State private var isSaving = false
    @State private var showError = false
    @State private var errorMessage = ""

    var body: some View {
        NavigationView {
            Form {
                Section("Daily Calorie Goal") {
                    HStack {
                        TextField("Calories", text: $dailyCalories)
                            .keyboardType(.numberPad)
                        Text("cal/day")
                            .foregroundColor(.secondary)
                    }

                    if currentGoal > 0 {
                        HStack {
                            Text("Current Goal")
                                .foregroundColor(.secondary)
                            Spacer()
                            Text("\(Int(currentGoal)) cal/day")
                        }
                    }
                }

                Section("Notes (Optional)") {
                    TextEditor(text: $notes)
                        .frame(height: 80)
                }

                Section {
                    Text("This goal will be used to track your pet's daily calorie intake on the dashboard.")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            .navigationTitle("Set Calorie Goal")
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
                            await saveGoal()
                        }
                    }
                    .disabled(dailyCalories.isEmpty || isSaving)
                }
            }
            .onAppear {
                if currentGoal > 0 {
                    dailyCalories = "\(Int(currentGoal))"
                }
            }
            .alert("Error", isPresented: $showError) {
                Button("OK") {}
            } message: {
                Text(errorMessage)
            }
        }
    }

    private func saveGoal() async {
        guard let caloriesValue = Double(dailyCalories), caloriesValue > 0 else {
            errorMessage = "Please enter a valid calorie amount"
            showError = true
            return
        }

        isSaving = true
        do {
            _ = try await SupabaseService.shared.setCalorieGoal(
                for: petId,
                dailyCalories: caloriesValue,
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
