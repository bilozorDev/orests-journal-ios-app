//
//  AddFoodView.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import SwiftUI
import PhotosUI

struct AddFoodView: View {
    @Environment(\.dismiss) var dismiss

    @State private var foodName = ""
    @State private var selectedCategory: FoodCategory
    @State private var caloriesPerKg = ""
    @State private var containerSize = ""
    @State private var selectedUnit: ContainerUnit = .grams
    @State private var selectedPhoto: PhotosPickerItem?
    @State private var selectedImage: UIImage?
    @State private var isLoading = false
    @State private var errorMessage: String?

    init(defaultCategory: FoodCategory? = nil) {
        _selectedCategory = State(initialValue: defaultCategory ?? .dry)
    }

    var body: some View {
        NavigationView {
            Form {
                Section(header: Text("Food Information")) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Food Name *")
                            .font(.caption)
                            .foregroundColor(.secondary)
                        TextField("Enter food name", text: $foodName)
                    }

                    Picker("Category", selection: $selectedCategory) {
                        ForEach(FoodCategory.allCases, id: \.self) { category in
                            Text(category.displayName).tag(category)
                        }
                    }
                }

                Section(header: Text("Photo (Optional)")) {
                    PhotosPicker(
                        selection: $selectedPhoto,
                        matching: .images
                    ) {
                        if let selectedImage {
                            Image(uiImage: selectedImage)
                                .resizable()
                                .scaledToFit()
                                .frame(maxHeight: 200)
                                .cornerRadius(10)
                        } else {
                            Label("Select Photo", systemImage: "photo")
                        }
                    }
                    .onChange(of: selectedPhoto) { _, newValue in
                        Task {
                            if let data = try? await newValue?.loadTransferable(type: Data.self),
                               let image = UIImage(data: data) {
                                selectedImage = image
                            }
                        }
                    }
                }

                Section(header: Text("Nutrition")) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Calories per Kilogram (kcal/kg) *")
                            .font(.caption)
                            .foregroundColor(.secondary)
                        TextField("Enter calories per kg", text: $caloriesPerKg)
                            .keyboardType(.decimalPad)
                    }
                }

                Section(header: Text("Container Size")) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Container Size *")
                            .font(.caption)
                            .foregroundColor(.secondary)
                        HStack {
                            TextField("Enter size", text: $containerSize)
                                .keyboardType(.decimalPad)

                            Picker("Unit", selection: $selectedUnit) {
                                ForEach(ContainerUnit.allCases, id: \.self) { unit in
                                    Text(unit.abbreviation).tag(unit)
                                }
                            }
                            .pickerStyle(.menu)
                        }
                    }
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
                        Button(action: saveFood) {
                            Text("Add Food")
                                .frame(maxWidth: .infinity)
                                .foregroundColor(.blue)
                        }
                        .disabled(!isFormValid)
                    }
                }
            }
            .navigationTitle("Add Pet Food")
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
        !foodName.isEmpty &&
        !caloriesPerKg.isEmpty &&
        Double(caloriesPerKg) != nil &&
        !containerSize.isEmpty &&
        Double(containerSize) != nil
    }

    private func saveFood() {
        Task {
            isLoading = true
            errorMessage = nil

            do {
                // Get current user's family
                guard let family = try await SupabaseService.shared.getCurrentUserFamily() else {
                    throw NSError(domain: "AddFoodView", code: 500, userInfo: [NSLocalizedDescriptionKey: "No family found. Please contact support."])
                }

                // Upload photo if selected
                var imageUrl: String?
                if let image = selectedImage {
                    imageUrl = try await SupabaseService.shared.uploadFoodImage(image)
                }

                // Create food
                guard let caloriesKg = Double(caloriesPerKg),
                      let size = Double(containerSize) else {
                    throw NSError(domain: "AddFoodView", code: 400, userInfo: [NSLocalizedDescriptionKey: "Invalid number format"])
                }

                let _ = try await SupabaseService.shared.createFood(
                    familyId: family.id,
                    name: foodName,
                    category: selectedCategory,
                    caloriesPerKg: caloriesKg,
                    containerSize: size,
                    containerSizeUnit: selectedUnit,
                    imageUrl: imageUrl
                )

                dismiss()
            } catch {
                errorMessage = error.localizedDescription
                isLoading = false
            }
        }
    }
}

#Preview {
    AddFoodView()
}
