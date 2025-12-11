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
    @State private var dateOfBirth: Date?
    @State private var selectedPhoto: PhotosPickerItem?
    @State private var selectedImage: UIImage?
    @State private var existingPhotoUrl: String?
    @State private var isSaving = false
    @State private var isUploadingPhoto = false
    @State private var errorMessage: String?
    @State private var hasSaved = false  // Prevent double-tap duplicate creation
    @State private var isRemovingBackground = false
    @State private var photoLoadTask: Task<Void, Never>?  // For cancelling rapid photo selections
    @State private var originalImage: UIImage?  // Store original before bg removal
    @State private var hasRemovedBackground = false
    @State private var isLoadingPhoto = false  // Loading state for photo selection
    @State private var photoWasRemoved = false  // Track if user explicitly removed photo

    // Calorie goal state
    @State private var calorieGoal: String = ""
    @State private var originalCalorieGoal: String = ""
    @State private var usesSuggestedGoal: Bool = false
    @State private var isLoadingCalorieGoal = false
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
            _dateOfBirth = State(initialValue: nil)
            _existingPhotoUrl = State(initialValue: nil)
        case .edit(let pet):
            _petName = State(initialValue: pet.name)
            _petKind = State(initialValue: pet.kind)
            _currentWeight = State(initialValue: pet.currentWeight.map { String($0) } ?? "")
            _dateOfBirth = State(initialValue: pet.dateOfBirth)
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
        NavigationStack {
            Form {
                Section(header: Text("Pet Information")) {
                    TextField("Pet Name", text: $petName)
                        .textContentType(.name)
                        .autocorrectionDisabled(true)
                        .accessibilityIdentifier(AccessibilityIdentifier.petNameTextField)

                    Picker("Kind", selection: $petKind) {
                        ForEach(petKinds, id: \.self) { kind in
                            Text(kind).tag(kind)
                        }
                    }
                    .accessibilityIdentifier(AccessibilityIdentifier.petKindPicker)
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
                        .accessibilityIdentifier(AccessibilityIdentifier.petWeightTextField)
                }

                Section(header: Text("Nutrition (Optional)")) {
                    VStack(alignment: .leading, spacing: 12) {
                        HStack {
                            ZStack(alignment: .leading) {
                                TextField("Daily Calorie Goal", text: $calorieGoal)
                                    .keyboardType(.numberPad)
                                    .opacity(isLoadingCalorieGoal ? 0 : 1)
                                if isLoadingCalorieGoal {
                                    HStack(spacing: 4) {
                                        ProgressView()
                                            .scaleEffect(0.8)
                                        Text("Loading...")
                                            .font(.subheadline)
                                            .foregroundColor(.secondary)
                                    }
                                }
                            }
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

                Section(header: Text("Date of Birth (Optional)")) {
                    DatePicker(
                        "Birthday",
                        selection: Binding(
                            get: { dateOfBirth ?? Date() },
                            set: { dateOfBirth = $0 }
                        ),
                        in: ...Date(),
                        displayedComponents: .date
                    )
                    .datePickerStyle(.compact)

                    if dateOfBirth != nil {
                        Button("Clear Date", role: .destructive) {
                            dateOfBirth = nil
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
                            .accessibilityIdentifier(AccessibilityIdentifier.savePetButton)

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
                            .accessibilityIdentifier(AccessibilityIdentifier.saveAndAddAnotherPetButton)
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
                    Task {
                        try? await Task.sleep(for: .seconds(2))
                        withAnimation {
                            showSuccessToast = false
                        }
                    }
                }
            }
            .task {
                await loadExistingCalorieGoal()
            }
            .onDisappear {
                photoLoadTask?.cancel()
            }
        }
    }

    private func loadExistingCalorieGoal() async {
        guard let pet = editingPet else { return }

        isLoadingCalorieGoal = true
        do {
            if let goal = try await DataService.shared.getCalorieGoal(for: pet.id) {
                let goalString = String(Int(goal.dailyCalories))
                calorieGoal = goalString
                originalCalorieGoal = goalString
            }
        } catch {
            // Silently fail - calorie goal is optional
            print("Failed to load calorie goal: \(error)")
        }
        isLoadingCalorieGoal = false
    }

    @ViewBuilder
    private var photoSection: some View {
        VStack(spacing: 16) {
            // Current/Selected Image Display
            if let selectedImage {
                ZStack {
                    Image(uiImage: selectedImage)
                        .resizable()
                        .scaledToFit()
                        .frame(maxHeight: 200)
                        .cornerRadius(10)
                        .accessibilityLabel("Selected photo of \(petName.isEmpty ? "pet" : petName)")

                    // Loading overlay during background removal
                    if isRemovingBackground {
                        RoundedRectangle(cornerRadius: 10)
                            .fill(Color.black.opacity(0.5))
                            .frame(maxHeight: 200)
                        VStack(spacing: 8) {
                            ProgressView()
                                .scaleEffect(1.2)
                                .tint(.white)
                            Text("Processing...")
                                .font(.caption)
                                .foregroundColor(.white)
                        }
                        .accessibilityLabel("Processing photo, please wait")
                    }
                }
            } else if let existingUrl = existingPhotoUrl, let url = URL(string: existingUrl) {
                AsyncImage(url: url) { image in
                    image
                        .resizable()
                        .scaledToFit()
                        .frame(maxHeight: 200)
                        .cornerRadius(10)
                        .accessibilityLabel("Current photo of \(petName.isEmpty ? "pet" : petName)")
                } placeholder: {
                    Rectangle()
                        .fill(Color.gray.opacity(0.2))
                        .frame(height: 200)
                        .cornerRadius(10)
                        .overlay(ProgressView())
                        .accessibilityLabel("Loading photo")
                }
            }

            // Show Photo Library picker only when no photo selected
            if selectedImage == nil && existingPhotoUrl == nil {
                if isLoadingPhoto {
                    HStack {
                        ProgressView()
                        Text("Loading photo...")
                            .foregroundColor(.secondary)
                    }
                } else {
                    PhotosPicker(
                        selection: $selectedPhoto,
                        matching: .images
                    ) {
                        Label("Select from Photo Library", systemImage: "photo.on.rectangle")
                    }
                    .accessibilityIdentifier(AccessibilityIdentifier.photoPickerButton)
                    .accessibilityHint("Opens photo library to select a pet photo")
                    .onChange(of: selectedPhoto) { _, newValue in
                        // Ignore new selections while one is already being processed
                        // This prevents the "double-tap" issue where users select again
                        // thinking the first selection didn't work
                        guard !isLoadingPhoto else { return }

                        photoLoadTask = Task {
                            isLoadingPhoto = true
                            errorMessage = nil  // Clear previous errors

                            do {
                                if let data = try await newValue?.loadTransferable(type: Data.self) {
                                    // Check if task was cancelled while loading
                                    if Task.isCancelled { return }

                                    if let image = UIImage(data: data) {
                                        selectedImage = image
                                        originalImage = image  // Store original
                                        hasRemovedBackground = false
                                        photoWasRemoved = false  // Reset removal flag when new photo selected
                                    } else {
                                        errorMessage = "Could not decode the selected photo"
                                    }
                                } else if newValue != nil {
                                    errorMessage = "Could not load the selected photo"
                                }
                            } catch {
                                // Don't show error if task was cancelled
                                if !Task.isCancelled {
                                    errorMessage = "Failed to load photo: \(error.localizedDescription)"
                                }
                            }
                            isLoadingPhoto = false
                        }
                    }
                }
            }

            // Actions for selected photo
            if selectedImage != nil {
                VStack(spacing: 12) {
                    // Background removal toggle (iOS 17+)
                    if #available(iOS 17.0, *) {
                        Button {
                            Task {
                                await toggleBackgroundRemoval()
                            }
                        } label: {
                            Label(
                                hasRemovedBackground ? "Restore Original" : "Remove Background",
                                systemImage: hasRemovedBackground ? "arrow.uturn.backward" : "wand.and.stars"
                            )
                            .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.bordered)
                        .tint(hasRemovedBackground ? .orange : .blue)
                        .disabled(isRemovingBackground)
                        .accessibilityIdentifier(AccessibilityIdentifier.removeBackgroundButton)
                        .accessibilityHint(hasRemovedBackground ? "Restores the original photo" : "Removes the background from the photo")
                    }

                    // Remove photo button
                    Button(role: .destructive) {
                        clearPhoto()
                    } label: {
                        Label("Remove Photo", systemImage: "trash")
                    }
                    .disabled(isRemovingBackground)
                    .accessibilityIdentifier(AccessibilityIdentifier.removePhotoButton)
                }
            } else if existingPhotoUrl != nil {
                // Remove existing photo button
                Button(role: .destructive) {
                    clearPhoto()
                } label: {
                    Label("Remove Photo", systemImage: "trash")
                }
                .accessibilityIdentifier(AccessibilityIdentifier.removePhotoButton)
            }
        }
    }

    private func clearPhoto() {
        selectedImage = nil
        originalImage = nil
        existingPhotoUrl = nil
        selectedPhoto = nil
        hasRemovedBackground = false
        photoWasRemoved = true  // Mark that user explicitly removed the photo
    }

    @available(iOS 17.0, *)
    private func toggleBackgroundRemoval() async {
        if hasRemovedBackground {
            // Restore original
            if let original = originalImage {
                selectedImage = original
                hasRemovedBackground = false
            }
        } else {
            // Remove background
            guard let image = selectedImage else { return }
            isRemovingBackground = true
            do {
                let processed = try await ImageProcessor.shared.removeBackground(from: image)
                selectedImage = processed
                hasRemovedBackground = true
                errorMessage = nil  // Clear any previous error on success
            } catch {
                errorMessage = error.localizedDescription
            }
            isRemovingBackground = false
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
            var photoUrl: String? = nil
            var shouldClearPhoto = false

            // Upload new photo if selected
            if let image = selectedImage {
                isUploadingPhoto = true

                // Compress image with adaptive quality to ensure it's under 5MB
                let compressed = try ImageCompressor.shared.compressForUpload(
                    image,
                    hasTransparency: hasRemovedBackground
                )
                photoUrl = try await DataService.shared.uploadPetPhoto(
                    imageData: compressed.data,
                    mimeType: compressed.mimeType
                )
                isUploadingPhoto = false
            } else if photoWasRemoved {
                // User explicitly removed the photo
                photoUrl = nil
                shouldClearPhoto = true
            } else if let existing = editingPet?.photoUrl {
                // Keep existing photo if not changed
                photoUrl = existing
            }

            let weight = currentWeight.isEmpty ? nil : Double(currentWeight)

            let savedPet: Pet
            if let existingPet = editingPet {
                // Update existing pet
                savedPet = try await DataService.shared.updatePet(
                    id: existingPet.id,
                    name: petName,
                    kind: petKind,
                    photoUrl: photoUrl,
                    currentWeight: weight,
                    dateOfBirth: dateOfBirth,
                    clearPhoto: shouldClearPhoto
                )

                // Update calorie goal if changed
                if calorieGoal != originalCalorieGoal {
                    if let calorieValue = Double(calorieGoal), calorieValue > 0 {
                        _ = try await DataService.shared.setCalorieGoal(
                            for: savedPet.id,
                            dailyCalories: calorieValue,
                            notes: nil
                        )
                    }
                }
            } else {
                // Create new pet
                savedPet = try await DataService.shared.createPet(
                    name: petName,
                    kind: petKind,
                    photoUrl: photoUrl,
                    currentWeight: weight,
                    dateOfBirth: dateOfBirth
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
        dateOfBirth = nil
        selectedPhoto = nil
        selectedImage = nil
        originalImage = nil
        existingPhotoUrl = nil
        hasRemovedBackground = false
        photoWasRemoved = false
        isLoadingPhoto = false
        calorieGoal = ""
        usesSuggestedGoal = false
        hasSaved = false  // Allow saving again for "Add Another"
    }
}

#Preview {
    AddEditPetView(mode: .add)
}
