//
//  AddHealthEventView.swift
//  Orest's Journal
//
//  Form for creating or editing health events with category, notes, date, and photos.
//

import SwiftUI
import PhotosUI

struct AddHealthEventView: View {
    let pet: Pet
    var existingEvent: HealthEventWithCategory?
    let onSave: (HealthEvent) -> Void

    @Environment(\.dismiss) private var dismiss

    @State private var categoryName = ""
    @State private var notes = ""
    @State private var occurredAt = Date()
    @State private var notifyFamily = false

    // Photo state - supports multiple photos
    @State private var selectedPhotos: [PhotosPickerItem] = []
    @State private var showPhotosPicker = false
    @State private var newPhotos: [NewPhoto] = []
    @State private var existingPhotos: [HealthEventPhoto] = []
    @State private var photosToDelete: Set<UUID> = []

    // Struct for new photos with stable ID
    private struct NewPhoto: Identifiable {
        let id = UUID()
        let data: Data
        let mimeType: String
    }

    @State private var isSaving = false
    @State private var showError = false
    @State private var errorMessage = ""
    @State private var categories: [HealthCategory] = []
    @State private var showCategorySuggestions = false
    @State private var familyMemberCount = 1
    @State private var showCamera = false

    private let dataService = DataService.shared
    private let authManager = AuthManager.shared
    private let imageCompressor = ImageCompressor.shared

    private let maxPhotos = 3

    private var isEditing: Bool { existingEvent != nil }

    private var totalPhotoCount: Int {
        newPhotos.count + existingPhotos.filter { !photosToDelete.contains($0.id) }.count
    }

    private var canAddMorePhotos: Bool {
        totalPhotoCount < maxPhotos
    }

    init(pet: Pet, existingEvent: HealthEventWithCategory? = nil, onSave: @escaping (HealthEvent) -> Void) {
        self.pet = pet
        self.existingEvent = existingEvent
        self.onSave = onSave
    }

    var body: some View {
        NavigationStack {
            Form {
                // Category section
                Section {
                    categoryField
                } header: {
                    Text("Category")
                } footer: {
                    Text("e.g., Vet Visit, Vaccination, Blood Work")
                }

                // Date section
                Section("Date") {
                    DatePicker("When", selection: $occurredAt, in: ...Date(), displayedComponents: [.date, .hourAndMinute])
                        .accessibilityIdentifier(AccessibilityIdentifier.healthDatePicker)
                }

                // Notes section
                Section("Notes") {
                    TextEditor(text: $notes)
                        .frame(minHeight: 100)
                        .accessibilityIdentifier(AccessibilityIdentifier.healthNotesField)
                }

                // Photo section
                Section {
                    photoSection
                } header: {
                    HStack {
                        Text("Photos")
                        Spacer()
                        Text("\(totalPhotoCount)/\(maxPhotos)")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }

                // Notify family (only show if multi-member family)
                if familyMemberCount > 1 && !isEditing {
                    Section {
                        Toggle("Notify Family", isOn: $notifyFamily)
                            .accessibilityIdentifier(AccessibilityIdentifier.healthNotifyFamilyToggle)
                    } footer: {
                        Text("Send a notification to other family members about this health event")
                    }
                }
            }
            .navigationTitle(isEditing ? "Edit Health Event" : "Add Health Event")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                    .accessibilityIdentifier(AccessibilityIdentifier.cancelHealthEventButton)
                }

                ToolbarItem(placement: .confirmationAction) {
                    Button(isEditing ? "Save" : "Add") {
                        Task {
                            await saveEvent()
                        }
                    }
                    .disabled(categoryName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isSaving)
                    .accessibilityIdentifier(AccessibilityIdentifier.saveHealthEventButton)
                }
            }
            .task {
                await loadCategories()
                await loadFamilyMemberCount()
                populateExistingEvent()
            }
            .onChange(of: selectedPhotos) { _, newItems in
                Task {
                    await loadPhotos(from: newItems)
                }
            }
            .photosPicker(
                isPresented: $showPhotosPicker,
                selection: $selectedPhotos,
                maxSelectionCount: min(3, maxPhotos - totalPhotoCount),
                matching: .images
            )
            .alert("Error", isPresented: $showError) {
                Button("OK") {}
            } message: {
                Text(errorMessage)
            }
            .fullScreenCover(isPresented: $showCamera) {
                CameraView { image in
                    if let image = image, canAddMorePhotos {
                        handleCapturedImage(image)
                    }
                }
            }
            .overlay {
                if isSaving {
                    Color.black.opacity(0.3)
                        .ignoresSafeArea()
                    ProgressView("Saving...")
                        .padding()
                        .background(Color(uiColor: .systemBackground))
                        .cornerRadius(10)
                }
            }
        }
    }

    // MARK: - Category Field

    private var categoryField: some View {
        VStack(alignment: .leading, spacing: 8) {
            TextField("Category name", text: $categoryName)
                .textFieldStyle(.plain)
                .accessibilityIdentifier(AccessibilityIdentifier.healthCategoryField)
                .onChange(of: categoryName) { _, _ in
                    showCategorySuggestions = !categoryName.isEmpty && !filteredCategories.isEmpty
                }

            if showCategorySuggestions {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        ForEach(filteredCategories) { category in
                            Button {
                                categoryName = category.name
                                showCategorySuggestions = false
                            } label: {
                                Text(category.name)
                                    .font(.subheadline)
                                    .padding(.horizontal, 12)
                                    .padding(.vertical, 6)
                                    .background(Color.accentColor.opacity(0.15))
                                    .foregroundColor(.accentColor)
                                    .clipShape(Capsule())
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
            }
        }
    }

    private var filteredCategories: [HealthCategory] {
        guard !categoryName.isEmpty else { return categories }
        let query = categoryName.lowercased()
        return categories.filter { $0.nameNormalized.contains(query) }
    }

    // MARK: - Photo Section

    private var photoSection: some View {
        let columns = [
            GridItem(.flexible(), spacing: 12),
            GridItem(.flexible(), spacing: 12)
        ]

        return LazyVGrid(columns: columns, spacing: 12) {
            // Camera button as first item (if can add more photos)
            if canAddMorePhotos {
                cameraGridItem
            }

            // Existing photos (not marked for deletion)
            ForEach(existingPhotos.filter { !photosToDelete.contains($0.id) }) { photo in
                existingPhotoThumbnail(photo)
            }

            // New photos
            ForEach(newPhotos) { photo in
                newPhotoThumbnail(photo: photo)
            }

            // Add from library button as last item (if can add more photos)
            if canAddMorePhotos {
                addFromLibraryGridItem
            }
        }
    }

    private var cameraGridItem: some View {
        Button {
            showCamera = true
        } label: {
            VStack(spacing: 6) {
                Image(systemName: "camera.fill")
                    .font(.title2)
                Text("Camera")
                    .font(.caption)
            }
            .frame(maxWidth: .infinity)
            .frame(height: 100)
            .background(Color(uiColor: .tertiarySystemGroupedBackground))
            .foregroundColor(.accentColor)
            .clipShape(RoundedRectangle(cornerRadius: 8))
        }
        .buttonStyle(.plain)
    }

    private var addFromLibraryGridItem: some View {
        Button {
            showPhotosPicker = true
        } label: {
            VStack(spacing: 6) {
                Image(systemName: "plus")
                    .font(.title2)
                Text("Add")
                    .font(.caption)
            }
            .frame(maxWidth: .infinity)
            .frame(height: 100)
            .background(Color(uiColor: .tertiarySystemGroupedBackground))
            .foregroundColor(.accentColor)
            .clipShape(RoundedRectangle(cornerRadius: 8))
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier(AccessibilityIdentifier.healthPhotoPickerButton)
    }

    private func existingPhotoThumbnail(_ photo: HealthEventPhoto) -> some View {
        ZStack(alignment: .topLeading) {
            AsyncImage(url: URL(string: photo.photoUrl)) { image in
                image
                    .resizable()
                    .scaledToFill()
            } placeholder: {
                Rectangle()
                    .fill(Color(uiColor: .tertiarySystemGroupedBackground))
                    .overlay {
                        ProgressView()
                    }
            }
            .frame(height: 100)
            .clipShape(RoundedRectangle(cornerRadius: 8))

            // Delete button
            deleteButton {
                photosToDelete.insert(photo.id)
            }
        }
    }

    private func newPhotoThumbnail(photo: NewPhoto) -> some View {
        ZStack(alignment: .topLeading) {
            if let uiImage = UIImage(data: photo.data) {
                Image(uiImage: uiImage)
                    .resizable()
                    .scaledToFill()
                    .frame(height: 100)
                    .clipShape(RoundedRectangle(cornerRadius: 8))
            }

            // Delete button
            deleteButton {
                newPhotos.removeAll { $0.id == photo.id }
            }
        }
    }

    private func deleteButton(action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: "xmark")
                .font(.caption.weight(.bold))
                .foregroundColor(.white)
                .frame(width: 24, height: 24)
                .background(Color.black.opacity(0.6))
                .clipShape(Circle())
        }
        .padding(6)
    }

    // MARK: - Data Loading

    private func loadCategories() async {
        do {
            categories = try await dataService.getHealthCategories(for: pet.id)
        } catch {
            // Ignore - suggestions are optional
        }
    }

    private func loadFamilyMemberCount() async {
        guard let familyId = authManager.currentFamily?.id else {
            // User is not in a family, keep default familyMemberCount of 1
            print("[Health] No family ID available, skipping family member count")
            return
        }
        do {
            let response = try await dataService.getFamilyMembers(for: familyId)
            familyMemberCount = response.members.count
        } catch {
            // On error, default to showing the toggle (assume multi-member family)
            // This is a better UX than hiding the toggle when we can't determine
            print("[Health] Failed to load family members: \(error), defaulting to show toggle")
            familyMemberCount = 2
        }
    }

    private func populateExistingEvent() {
        guard let event = existingEvent else { return }
        categoryName = event.category.name
        notes = event.event.notes ?? ""
        occurredAt = event.event.occurredAt
        existingPhotos = event.event.photos
    }

    private func loadPhotos(from items: [PhotosPickerItem]) async {
        guard !items.isEmpty else { return }

        for item in items {
            guard canAddMorePhotos else {
                await MainActor.run {
                    errorMessage = "Maximum \(maxPhotos) photos allowed"
                    showError = true
                }
                break
            }

            do {
                if let data = try await item.loadTransferable(type: Data.self) {
                    await MainActor.run {
                        compressAndAddPhoto(data)
                    }
                }
            } catch {
                await MainActor.run {
                    errorMessage = "Failed to load photo"
                    showError = true
                }
            }
        }

        // Reset selection for next use
        await MainActor.run {
            selectedPhotos = []
        }
    }

    private func handleCapturedImage(_ image: UIImage) {
        guard let data = image.jpegData(compressionQuality: 0.8) else { return }
        compressAndAddPhoto(data)
    }

    private func compressAndAddPhoto(_ data: Data) {
        guard let image = UIImage(data: data) else {
            newPhotos.append(NewPhoto(data: data, mimeType: "image/jpeg"))
            return
        }

        // Determine if image has transparency (PNG vs JPEG)
        let hasTransparency = data.starts(with: [0x89, 0x50, 0x4E, 0x47]) // PNG magic bytes

        do {
            let compressed = try imageCompressor.compressForUpload(image, hasTransparency: hasTransparency)
            newPhotos.append(NewPhoto(data: compressed.data, mimeType: compressed.mimeType))
        } catch {
            // If compression fails, use original with reasonable quality
            let fallbackData = hasTransparency ? (image.pngData() ?? data) : (image.jpegData(compressionQuality: 0.8) ?? data)
            let mimeType = hasTransparency ? "image/png" : "image/jpeg"
            newPhotos.append(NewPhoto(data: fallbackData, mimeType: mimeType))
        }
    }

    // MARK: - Save

    private func saveEvent() async {
        let trimmedCategory = categoryName.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedCategory.isEmpty else { return }

        isSaving = true
        defer { isSaving = false }

        do {
            if let existing = existingEvent {
                // Update existing event
                let updatedEvent = try await dataService.updateHealthEvent(
                    eventId: existing.id,
                    petId: pet.id,
                    categoryName: trimmedCategory != existing.category.name ? trimmedCategory : nil,
                    occurredAt: occurredAt != existing.event.occurredAt ? occurredAt : nil,
                    notes: notes != (existing.event.notes ?? "") ? notes : nil
                )

                // Delete photos marked for removal
                for photoId in photosToDelete {
                    try await dataService.deleteHealthEventPhoto(
                        eventId: existing.id,
                        photoId: photoId,
                        petId: pet.id
                    )
                }

                // Upload new photos
                for photo in newPhotos {
                    _ = try await dataService.uploadHealthEventPhoto(
                        eventId: existing.id,
                        petId: pet.id,
                        imageData: photo.data,
                        mimeType: photo.mimeType
                    )
                }

                onSave(updatedEvent.event)
            } else {
                // Create new event
                let newEvent = try await dataService.createHealthEvent(
                    petId: pet.id,
                    categoryName: trimmedCategory,
                    occurredAt: occurredAt,
                    notes: notes.isEmpty ? nil : notes,
                    notifyFamily: notifyFamily
                )

                // Upload all photos
                for photo in newPhotos {
                    _ = try await dataService.uploadHealthEventPhoto(
                        eventId: newEvent.id,
                        petId: pet.id,
                        imageData: photo.data,
                        mimeType: photo.mimeType
                    )
                }

                onSave(newEvent)
            }

            dismiss()
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
    }
}

// MARK: - Preview

#Preview {
    AddHealthEventView(
        pet: Pet(
            id: UUID(),
            orgId: UUID().uuidString,
            name: "Max",
            kind: "dog",
            photoUrl: nil,
            currentWeight: nil,
            dateOfBirth: nil,
            isArchived: false,
            createdAt: Date(),
            createdBy: nil
        )
    ) { _ in }
}
