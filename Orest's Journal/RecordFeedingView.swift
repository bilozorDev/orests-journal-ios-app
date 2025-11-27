//
//  RecordFeedingView.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import SwiftUI

struct QuickFeedingButton: View {
    let action: QuickFeedingAction
    let isRecording: Bool
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            VStack(spacing: 4) {
                Text(action.foodName)
                    .font(.subheadline)
                    .fontWeight(.medium)
                    .lineLimit(1)

                Text("\(formatAmount(action.amount)) \(action.amountUnit.abbreviation)")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(Color.blue.opacity(0.1))
            .foregroundColor(isRecording ? .gray : .blue)
            .cornerRadius(16)
        }
        .disabled(isRecording)
    }

    private func formatAmount(_ value: Double) -> String {
        let formatter = NumberFormatter()
        formatter.minimumFractionDigits = 0
        formatter.maximumFractionDigits = 2
        return formatter.string(from: NSNumber(value: value)) ?? "\(value)"
    }
}

struct RecordFeedingView: View {
    let petId: UUID
    var onSave: ((PetFeeding) -> Void)? = nil
    @Environment(\.dismiss) var dismiss

    @State private var foods: [PetFood] = []
    @State private var selectedFood: PetFood?
    @State private var feedingMode: FeedingMode = .customAmount
    @State private var amount: String = ""
    @State private var selectedUnit: ContainerUnit = .grams
    @State private var notes: String = ""
    @State private var isLoading = true
    @State private var isSaving = false
    @State private var showError = false
    @State private var errorMessage = ""
    @State private var quickActions: [QuickFeedingAction] = []
    @State private var recordingQuickActionId: UUID? = nil

    enum FeedingMode: String, CaseIterable {
        case customAmount = "Custom Amount"
        case entireContainer = "Entire Container"
    }

    var calculatedCalories: Double {
        guard let food = selectedFood else {
            return 0
        }

        if feedingMode == .entireContainer {
            return food.caloriesPerContainer
        } else {
            guard let amountValue = Double(amount) else {
                return 0
            }
            return food.calculateCalories(for: amountValue, unit: selectedUnit)
        }
    }

    var feedingAmount: Double {
        guard let food = selectedFood else {
            return 0
        }

        if feedingMode == .entireContainer {
            return food.containerSize
        } else {
            return Double(amount) ?? 0
        }
    }

    var feedingUnit: ContainerUnit {
        if feedingMode == .entireContainer, let food = selectedFood {
            return food.containerSizeUnit
        } else {
            return selectedUnit
        }
    }

    var body: some View {
        NavigationView {
            Form {
                Section("Select Food") {
                    if isLoading {
                        ProgressView()
                    } else if foods.isEmpty {
                        Text("No foods available")
                            .foregroundColor(.secondary)
                        Button("Add Food First") {
                            dismiss()
                            DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
                                NotificationCenter.default.post(name: NSNotification.Name("SwitchToFoodTab"), object: nil)
                                NotificationCenter.default.post(name: NSNotification.Name("ShowAddFood"), object: nil)
                            }
                        }
                    } else {
                        Picker("Food", selection: $selectedFood) {
                            Text("Select...").tag(nil as PetFood?)
                            ForEach(foods) { food in
                                Text(food.name).tag(food as PetFood?)
                            }
                        }
                    }
                }

                // Quick Actions Section - show after Select Food
                if !quickActions.isEmpty {
                    Section {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Quick Record")
                                .font(.caption)
                                .foregroundColor(.secondary)

                            ScrollView(.horizontal, showsIndicators: false) {
                                HStack(spacing: 8) {
                                    ForEach(quickActions) { action in
                                        QuickFeedingButton(
                                            action: action,
                                            isRecording: recordingQuickActionId == action.id
                                        ) {
                                            Task {
                                                await recordQuickFeeding(action)
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                if selectedFood != nil {
                    Section("Feeding Mode") {
                        Picker("Mode", selection: $feedingMode) {
                            ForEach(FeedingMode.allCases, id: \.self) { mode in
                                Text(mode.rawValue).tag(mode)
                            }
                        }
                        .pickerStyle(.segmented)
                    }

                    Section("Amount") {
                        if feedingMode == .customAmount {
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
                        } else if let food = selectedFood {
                            HStack {
                                Text("Container Size")
                                Spacer()
                                Text("\(formatNumber(food.containerSize)) \(food.containerSizeUnit.abbreviation)")
                                    .foregroundColor(.secondary)
                            }
                        }

                        if calculatedCalories > 0 {
                            HStack {
                                Text("Calories")
                                Spacer()
                                Text("\(Int(calculatedCalories)) cal")
                                    .foregroundColor(.secondary)
                            }
                        }
                    }

                    Section("Notes (Optional)") {
                        TextEditor(text: $notes)
                            .frame(height: 80)
                    }
                }
            }
            .navigationTitle("Record Feeding")
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
                            await saveFeeding()
                        }
                    }
                    .disabled(selectedFood == nil || (feedingMode == .customAmount && amount.isEmpty) || isSaving)
                }
            }
            .onAppear {
                // Show cached foods immediately (synchronous)
                if let cached = DataService.shared.getCachedFoodsData() {
                    foods = cached
                    isLoading = false
                    // Load quick actions after foods are available
                    loadQuickActions()
                }
            }
            .task {
                // Refresh in background
                await loadFoods(showLoading: foods.isEmpty)
                // Reload quick actions with fresh foods
                loadQuickActions()

                // If quick actions still empty, try loading from disk cache
                if quickActions.isEmpty && !foods.isEmpty {
                    quickActions = await DataService.shared.getQuickFeedingActionsAsync(
                        for: petId,
                        foods: foods
                    )
                }
            }
            .alert("Error", isPresented: $showError) {
                Button("OK") {}
            } message: {
                Text(errorMessage)
            }
        }
    }

    private func loadFoods(showLoading: Bool = true) async {
        if showLoading {
            isLoading = true
        }
        do {
            foods = try await DataService.shared.getFoods()
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
        isLoading = false
    }

    private func saveFeeding() async {
        guard let food = selectedFood else {
            return
        }

        isSaving = true

        // Get current user name for optimistic display
        let userName = AuthManager.shared.currentUser?.firstName ?? "You"

        // Create optimistic feeding entry
        let optimisticFeeding = PetFeeding(
            id: UUID(),
            petId: petId,
            foodId: food.id,
            fedBy: userName,
            fedAt: Date(),
            amount: feedingAmount,
            amountUnit: feedingUnit,
            calories: calculatedCalories,
            notes: notes.isEmpty ? nil : notes,
            createdAt: Date()
        )

        // Call callback for optimistic update and dismiss immediately
        onSave?(optimisticFeeding)
        dismiss()

        // Make API call in background
        do {
            _ = try await DataService.shared.createFeeding(
                petId: petId,
                foodId: food.id,
                amount: feedingAmount,
                amountUnit: feedingUnit,
                calories: calculatedCalories,
                notes: notes.isEmpty ? nil : notes
            )
        } catch {
            // Log error - dashboard will sync on next refresh
            print("Error saving feeding: \(error)")
        }
        isSaving = false
    }

    private func recordQuickFeeding(_ action: QuickFeedingAction) async {
        recordingQuickActionId = action.id

        // Get current user name for optimistic display
        let userName = AuthManager.shared.currentUser?.firstName ?? "You"

        // Create optimistic feeding entry
        let optimisticFeeding = PetFeeding(
            id: UUID(),
            petId: petId,
            foodId: action.foodId,
            fedBy: userName,
            fedAt: Date(),
            amount: action.amount,
            amountUnit: action.amountUnit,
            calories: action.calories,
            notes: nil,
            createdAt: Date()
        )

        // Call callback for optimistic update and dismiss immediately
        onSave?(optimisticFeeding)
        dismiss()

        // Make API call in background
        do {
            _ = try await DataService.shared.createFeeding(
                petId: petId,
                foodId: action.foodId,
                amount: action.amount,
                amountUnit: action.amountUnit,
                calories: action.calories,
                notes: nil
            )
        } catch {
            // Log error - dashboard will sync on next refresh
            print("Error saving quick feeding: \(error)")
        }

        recordingQuickActionId = nil
    }

    private func loadQuickActions() {
        quickActions = DataService.shared.getQuickFeedingActions(for: petId, foods: foods)
    }

    private func formatNumber(_ value: Double) -> String {
        let formatter = NumberFormatter()
        formatter.minimumFractionDigits = 0
        formatter.maximumFractionDigits = 2
        return formatter.string(from: NSNumber(value: value)) ?? "\(value)"
    }
}
