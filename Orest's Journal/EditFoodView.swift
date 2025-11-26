//
//  EditFoodView.swift
//  Orest's Journal
//
//  Edit an existing pet food item.
//

import SwiftUI
import PhotosUI

struct EditFoodView: View {
    @Environment(\.dismiss) var dismiss

    let food: PetFood
    var onSave: ((PetFood) -> Void)?

    @State private var foodName: String
    @State private var selectedCategory: FoodCategory
    @State private var caloriesPerKg: String
    @State private var containerSize: String
    @State private var selectedUnit: ContainerUnit
    @State private var selectedPhoto: PhotosPickerItem?
    @State private var selectedImage: UIImage?
    @State private var isLoading = false
    @State private var errorMessage: String?

    init(food: PetFood, onSave: ((PetFood) -> Void)? = nil) {
        self.food = food
        self.onSave = onSave
        _foodName = State(initialValue: food.name)
        _selectedCategory = State(initialValue: food.category)
        _caloriesPerKg = State(initialValue: String(format: "%.0f", food.caloriesPerKg))
        _containerSize = State(initialValue: String(format: "%.2f", food.containerSize).trimmingCharacters(in: CharacterSet(charactersIn: "0")).trimmingCharacters(in: CharacterSet(charactersIn: ".")))
        _selectedUnit = State(initialValue: food.containerSizeUnit)
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
                        } else if let imageUrl = food.imageUrl, let url = URL(string: imageUrl) {
                            AsyncImage(url: url) { image in
                                image
                                    .resizable()
                                    .scaledToFit()
                                    .frame(maxHeight: 200)
                                    .cornerRadius(10)
                            } placeholder: {
                                Label("Select Photo", systemImage: "photo")
                            }
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
                            Text("Save Changes")
                                .frame(maxWidth: .infinity)
                                .foregroundColor(.blue)
                        }
                        .disabled(!isFormValid || !hasChanges)
                    }
                }
            }
            .navigationTitle("Edit Food")
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

    private var hasChanges: Bool {
        foodName != food.name ||
        selectedCategory != food.category ||
        Double(caloriesPerKg) != food.caloriesPerKg ||
        Double(containerSize) != food.containerSize ||
        selectedUnit != food.containerSizeUnit ||
        selectedImage != nil
    }

    private func saveFood() {
        Task {
            isLoading = true
            errorMessage = nil

            do {
                guard let caloriesKg = Double(caloriesPerKg),
                      let size = Double(containerSize) else {
                    throw NSError(domain: "EditFoodView", code: 400, userInfo: [NSLocalizedDescriptionKey: "Invalid number format"])
                }

                let updatedFood = try await DataService.shared.updateFood(
                    id: food.id,
                    name: foodName != food.name ? foodName : nil,
                    category: selectedCategory != food.category ? selectedCategory : nil,
                    caloriesPerKg: caloriesKg != food.caloriesPerKg ? caloriesKg : nil,
                    containerSize: size != food.containerSize ? size : nil,
                    containerSizeUnit: selectedUnit != food.containerSizeUnit ? selectedUnit : nil,
                    imageUrl: nil // TODO: Implement image upload
                )

                onSave?(updatedFood)
                dismiss()
            } catch {
                errorMessage = error.localizedDescription
                isLoading = false
            }
        }
    }
}

#Preview {
    EditFoodView(food: PetFood(
        id: UUID(),
        orgId: "test",
        name: "Test Food",
        category: .dry,
        caloriesPerKg: 3500,
        containerSize: 1000,
        containerSizeUnit: .grams,
        imageUrl: nil,
        isArchived: false,
        createdAt: Date(),
        createdBy: nil
    ))
}
