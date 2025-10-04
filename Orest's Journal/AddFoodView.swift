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
    @State private var selectedCategory: FoodCategory = .dry
    @State private var caloriesPerContainer = ""
    @State private var containerSizeGrams = ""
    @State private var selectedPhoto: PhotosPickerItem?
    @State private var selectedImage: UIImage?
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationView {
            Form {
                Section(header: Text("Food Information")) {
                    TextField("Food Name", text: $foodName)

                    Picker("Category", selection: $selectedCategory) {
                        ForEach(FoodCategory.allCases, id: \.self) { category in
                            Text(category.displayName).tag(category)
                        }
                    }
                }

                Section(header: Text("Photo")) {
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
                    TextField("Calories per Container", text: $caloriesPerContainer)
                        .keyboardType(.decimalPad)

                    TextField("Container Size (grams)", text: $containerSizeGrams)
                        .keyboardType(.decimalPad)
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
        !caloriesPerContainer.isEmpty &&
        Double(caloriesPerContainer) != nil &&
        !containerSizeGrams.isEmpty &&
        Double(containerSizeGrams) != nil
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
                guard let calories = Double(caloriesPerContainer),
                      let containerSize = Double(containerSizeGrams) else {
                    throw NSError(domain: "AddFoodView", code: 400, userInfo: [NSLocalizedDescriptionKey: "Invalid number format"])
                }

                let _ = try await SupabaseService.shared.createFood(
                    familyId: family.id,
                    name: foodName,
                    category: selectedCategory,
                    caloriesPerContainer: calories,
                    containerSizeGrams: containerSize,
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
