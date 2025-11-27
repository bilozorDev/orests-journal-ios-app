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
                }

                Section(header: Text("Photo")) {
                    photoSection
                }

                Section(header: Text("Current Weight (lbs)")) {
                    TextField("Weight", text: $currentWeight)
                        .keyboardType(.decimalPad)
                }

                if let error = errorMessage {
                    Section {
                        Text(error)
                            .foregroundColor(.red)
                            .font(.caption)
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

                ToolbarItem(placement: .confirmationAction) {
                    Button(isEditing ? "Save" : "Add") {
                        Task {
                            await savePet()
                        }
                    }
                    .disabled(!isFormValid || isSaving)
                }
            }
            .overlay {
                if isSaving {
                    ProgressView(isUploadingPhoto ? "Uploading photo..." : "Saving...")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                        .background(Color.black.opacity(0.3))
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

    private func savePet() async {
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
                // Update existing pet
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
            }

            onSave?(savedPet)
            dismiss()
        } catch {
            errorMessage = error.localizedDescription
            isSaving = false
        }
    }
}

#Preview {
    AddEditPetView(mode: .add)
}
