//
//  AddEditPetView.swift
//  Orest's Journal
//
//  Created by Claude on 11/26/25.
//

import SwiftUI
import PhotosUI

enum PetEditMode {
    case add
    case edit(Pet)
}

enum SaveAction {
    case saveAndDismiss
    case saveAndAddAnother
}

struct AddEditPetView: View {
    @Environment(\.dismiss) var dismiss
    let mode: PetEditMode
    var onSave: ((Pet) -> Void)?

    @State private var petName: String
    @State private var petKind: String
    @State private var currentWeight: String
    @State private var selectedPhoto: PhotosPickerItem?
    @State private var selectedImage: UIImage?
    @State private var existingPhotoUrl: String?
    @State private var isSaving = false
    @State private var isUploadingPhoto = false
    @State private var errorMessage: String?
    @State private var hasSaved = false  // Prevent double-tap duplicate creation

    // Calorie goal state (only for add mode)
    @State private var calorieGoal: String = ""
    @State private var usesSuggestedGoal: Bool = false
    @State private var showSuccessToast = false
    @State private var successMessage = ""

    let petKinds = ["Dog", "Cat", "Bird", "Rabbit", "Hamster", "Guinea Pig", "Other"]

    init(mode: PetEditMode, onSave: ((Pet) -> Void)? = nil) {
        self.mode = mode
        self.onSave = onSave

        switch mode {
        case .add:
            _petName = State(initialValue: "")
            _petKind = State(initialValue: "Dog")
            _currentWeight = State(initialValue: "")
            _existingPhotoUrl = State(initialValue: nil)
        case .edit(let pet):
            _petName = State(initialValue: pet.name)
            _petKind = State(initialValue: pet.kind)
            _currentWeight = State(initialValue: pet.currentWeight.map { String($0) } ?? "")
            _existingPhotoUrl = State(initialValue: pet.photoUrl)
        }
    }

    var isEditing: Bool {
        if case .edit = mode { return true }
        return false
    }

    var editingPet: Pet? {
        if case .edit(let pet) = mode { return pet }
        return nil
    }

    /// Returns suggested daily calorie goal based on pet type
    var suggestedCalorieGoal: Int? {
        switch petKind {
        case "Dog":
            return 1000  // ~800-1200 cal/day for medium dog
        case "Cat":
            return 250   // ~200-300 cal/day
        case "Bird":
            return 35    // ~20-50 cal/day (varies by species)
        case "Rabbit":
            return 215   // ~180-250 cal/day
        case "Hamster":
            return 15    // ~10-20 cal/day
        case "Guinea Pig":
            return 125   // ~100-150 cal/day
        default:
            return nil   // "Other" - no suggestion
        }
    }

    var body: some View {
        NavigationView {
            Form {
                Section(header: Text("Pet Information")) {
                    TextField("Pet Name", text: $petName)

                    Picker("Kind", selection: $petKind) {
                        ForEach(petKinds, id: \.self) { kind in
                            Text(kind).tag(kind)
                        }
                    }
                    .onChange(of: petKind) { _, _ in
                        // Update calorie goal if user was using the suggestion
                        if usesSuggestedGoal, let suggested = suggestedCalorieGoal {
                            calorieGoal = "\(suggested)"
                        } else if usesSuggestedGoal && suggestedCalorieGoal == nil {
                            // No suggestion for "Other" type
                            calorieGoal = ""
                            usesSuggestedGoal = false
                        }
                    }
                }

                Section(header: Text("Photo")) {
                    photoSection
                }

                Section(header: Text("Current Weight (lbs)")) {
                    TextField("Weight", text: $currentWeight)
                        .keyboardType(.decimalPad)
                }

                // Nutrition section - only shown in add mode
                if !isEditing {
                    Section(header: Text("Nutrition (Optional)")) {
                        VStack(alignment: .leading, spacing: 12) {
                            HStack {
                                TextField("Daily Calorie Goal", text: $calorieGoal)
                                    .keyboardType(.numberPad)
                                Text("cal/day")
                                    .foregroundColor(.secondary)
                            }

                            if let suggested = suggestedCalorieGoal {
                                Button(action: {
                                    calorieGoal = "\(suggested)"
                                    usesSuggestedGoal = true
                                }) {
                                    HStack {
                                        Image(systemName: "lightbulb.fill")
                                            .foregroundColor(.yellow)
                                        Text("Use suggested: \(suggested) cal/day")
                                            .font(.subheadline)
                                    }
                                }
                                .buttonStyle(.borderless)

                                Text("Based on typical \(petKind.lowercased()) calorie needs")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
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

                // Button footer for add mode
                if !isEditing {
                    Section {
                        VStack(spacing: 12) {
                            Button(action: {
                                Task {
                                    await savePet(action: .saveAndDismiss)
                                }
                            }) {
                                Text("Save")
                                    .frame(maxWidth: .infinity)
                                    .padding()
                                    .background(isFormValid && !isSaving ? Color.blue : Color.gray.opacity(0.3))
                                    .foregroundColor(.white)
                                    .cornerRadius(10)
                            }
                            .disabled(!isFormValid || isSaving)

                            Button(action: {
                                Task {
                                    await savePet(action: .saveAndAddAnother)
                                }
                            }) {
                                Text("Save & Add Another")
                                    .frame(maxWidth: .infinity)
                                    .padding()
                                    .background(isFormValid && !isSaving ? Color.green : Color.gray.opacity(0.3))
                                    .foregroundColor(.white)
                                    .cornerRadius(10)
                            }
                            .disabled(!isFormValid || isSaving)
                        }
                        .listRowInsets(EdgeInsets())
                        .listRowBackground(Color.clear)
                    }
                }
            }
            .navigationTitle(isEditing ? "Edit Pet" : "Add Pet")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }

                // Only show toolbar save button in edit mode
                if isEditing {
                    ToolbarItem(placement: .confirmationAction) {
                        Button("Save") {
                            Task {
                                await savePet(action: .saveAndDismiss)
                            }
                        }
                        .disabled(!isFormValid || isSaving)
                    }
                }
            }
            .overlay {
                if isSaving {
                    ProgressView(isUploadingPhoto ? "Uploading photo..." : "Saving...")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                        .background(Color.black.opacity(0.3))
                }
            }
            .overlay(alignment: .top) {
                if showSuccessToast {
                    HStack {
                        Image(systemName: "checkmark.circle.fill")
                            .foregroundColor(.green)
                        Text(successMessage)
                    }
                    .padding()
                    .background(Color(.systemBackground))
                    .cornerRadius(10)
                    .shadow(radius: 5)
                    .padding(.top, 60)
                    .transition(.move(edge: .top).combined(with: .opacity))
                }
            }
            .onChange(of: showSuccessToast) { _, isShowing in
                if isShowing {
                    DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                        withAnimation {
                            showSuccessToast = false
                        }
                    }
                }
            }
        }
    }

    @ViewBuilder
    private var photoSection: some View {
        VStack(spacing: 12) {
            // Current/Selected Image Display
            if let selectedImage {
                Image(uiImage: selectedImage)
                    .resizable()
                    .scaledToFit()
                    .frame(maxHeight: 200)
                    .cornerRadius(10)
            } else if let existingUrl = existingPhotoUrl, let url = URL(string: existingUrl) {
                AsyncImage(url: url) { image in
                    image
                        .resizable()
                        .scaledToFit()
                        .frame(maxHeight: 200)
                        .cornerRadius(10)
                } placeholder: {
                    Rectangle()
                        .fill(Color.gray.opacity(0.2))
                        .frame(height: 200)
                        .cornerRadius(10)
                        .overlay(ProgressView())
                }
            }

            HStack(spacing: 16) {
                // Photo Library Picker
                PhotosPicker(
                    selection: $selectedPhoto,
                    matching: .images
                ) {
                    Label("Photo Library", systemImage: "photo.on.rectangle")
                }
                .onChange(of: selectedPhoto) { _, newValue in
                    Task {
                        if let data = try? await newValue?.loadTransferable(type: Data.self),
                           let image = UIImage(data: data) {
                            selectedImage = image
                        }
                    }
                }

                // Remove photo button
                if selectedImage != nil || existingPhotoUrl != nil {
                    Button(role: .destructive) {
                        selectedImage = nil
                        existingPhotoUrl = nil
                        selectedPhoto = nil
                    } label: {
                        Label("Remove", systemImage: "trash")
                    }
                }
            }
        }
    }

    private var isFormValid: Bool {
        !petName.isEmpty &&
        (currentWeight.isEmpty || Double(currentWeight) != nil)
    }

    private func savePet(action: SaveAction) async {
        // Prevent double-tap duplicate creation
        guard !hasSaved else { return }
        hasSaved = true

        isSaving = true
        errorMessage = nil

        do {
            var photoUrl = existingPhotoUrl

            // Upload new photo if selected
            if let image = selectedImage {
                isUploadingPhoto = true
                if let imageData = image.jpegData(compressionQuality: 0.8) {
                    photoUrl = try await DataService.shared.uploadPetPhoto(imageData: imageData)
                }
                isUploadingPhoto = false
            } else if selectedImage == nil && existingPhotoUrl == nil {
                // Photo was removed
                photoUrl = nil
            }

            let weight = currentWeight.isEmpty ? nil : Double(currentWeight)

            let savedPet: Pet
            if let existingPet = editingPet {
                // Update existing pet (no calorie goal handling in edit mode)
                savedPet = try await DataService.shared.updatePet(
                    id: existingPet.id,
                    name: petName,
                    kind: petKind,
                    photoUrl: photoUrl,
                    currentWeight: weight
                )
            } else {
                // Create new pet
                savedPet = try await DataService.shared.createPet(
                    name: petName,
                    kind: petKind,
                    photoUrl: photoUrl,
                    currentWeight: weight
                )

                // Set calorie goal if provided (sequential call after pet creation)
                if let calorieValue = Double(calorieGoal), calorieValue > 0 {
                    _ = try await DataService.shared.setCalorieGoal(
                        for: savedPet.id,
                        dailyCalories: calorieValue,
                        notes: nil
                    )
                }
            }

            onSave?(savedPet)

            // Handle based on save action
            switch action {
            case .saveAndDismiss:
                dismiss()
            case .saveAndAddAnother:
                // Clear form for next pet
                clearForm()
                successMessage = "\(savedPet.name) added successfully!"
                withAnimation {
                    showSuccessToast = true
                }
                isSaving = false
            }
        } catch {
            errorMessage = error.localizedDescription
            hasSaved = false  // Allow retry on error
            isSaving = false
        }
    }

    private func clearForm() {
        petName = ""
        petKind = "Dog"
        currentWeight = ""
        selectedPhoto = nil
        selectedImage = nil
        existingPhotoUrl = nil
        calorieGoal = ""
        usesSuggestedGoal = false
        hasSaved = false  // Allow saving again for "Add Another"
    }
}

#Preview {
    AddEditPetView(mode: .add)
}
