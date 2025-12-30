//
//  AddMedicationView.swift
//  Orest's Journal
//
//  Form for creating or editing medications with scheduling and reminders.
//

import SwiftUI
import PhotosUI

struct AddMedicationView: View {
    let pet: Pet
    var existingMedication: Medication?
    let onSave: (Medication) -> Void

    @Environment(\.dismiss) private var dismiss

    // Basic info
    @State private var name = ""
    @State private var friendlyName = ""
    @State private var medicationType: MedicationType = .pill
    @State private var dosage = ""
    @State private var notes = ""

    // Schedule type
    @State private var isAsNeeded = false

    // Schedule details (for scheduled medications)
    @State private var intervalDays = 1
    @State private var startDate = Date()
    @State private var hasEndDate = false
    @State private var endDate = Date().addingTimeInterval(30 * 24 * 60 * 60) // 30 days from now

    // Reminders
    @State private var remindersEnabled = false
    @State private var timesPerDay = 1
    @State private var reminderTimes: [Date] = [defaultTime(hour: 9)]

    // Photos
    @State private var selectedPhotos: [PhotosPickerItem] = []
    @State private var showPhotosPicker = false
    @State private var newPhotos: [NewPhoto] = []
    @State private var existingPhotos: [MedicationPhoto] = []
    @State private var photosToDelete: Set<UUID> = []
    @State private var showCamera = false

    // State
    @State private var isSaving = false
    @State private var showError = false
    @State private var errorMessage = ""

    private let dataService = DataService.shared
    private let imageCompressor = ImageCompressor.shared

    private let maxPhotos = 3

    private var isEditing: Bool { existingMedication != nil }

    private var totalPhotoCount: Int {
        newPhotos.count + existingPhotos.filter { !photosToDelete.contains($0.id) }.count
    }

    private var canAddMorePhotos: Bool {
        totalPhotoCount < maxPhotos
    }

    private var isValid: Bool {
        !name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    // Struct for new photos with stable ID
    private struct NewPhoto: Identifiable {
        let id = UUID()
        let data: Data
        let mimeType: String
    }

    init(pet: Pet, existingMedication: Medication? = nil, onSave: @escaping (Medication) -> Void) {
        self.pet = pet
        self.existingMedication = existingMedication
        self.onSave = onSave
    }

    var body: some View {
        NavigationStack {
            Form {
                // Basic info section
                Section {
                    TextField("Medical Name", text: $name)
                        .textContentType(.none)
                        .accessibilityLabel("Medication name")

                    TextField("e.g., Asthma inhaler", text: $friendlyName)
                        .textContentType(.none)
                        .accessibilityLabel("Friendly name for notifications")

                    Picker("Type", selection: $medicationType) {
                        ForEach(MedicationType.allCases, id: \.self) { type in
                            Label(type.displayName, systemImage: type.icon)
                                .tag(type)
                        }
                    }

                    TextField("Dosage (optional)", text: $dosage)
                        .textContentType(.none)
                        .accessibilityLabel("Dosage")
                } header: {
                    Text("Medication")
                } footer: {
                    Text("Friendly name is shown in notifications and widgets instead of the full medical name")
                }

                // Schedule type section
                Section("Schedule") {
                    Picker("Schedule Type", selection: $isAsNeeded) {
                        Text("Scheduled").tag(false)
                        Text("As Needed (PRN)").tag(true)
                    }
                    .pickerStyle(.segmented)
                    .onChange(of: isAsNeeded) { _, newValue in
                        if newValue {
                            // Clear reminder settings for PRN
                            remindersEnabled = false
                            hasEndDate = false
                        }
                    }
                }

                // Schedule details (for scheduled medications)
                if !isAsNeeded {
                    Section("Schedule Details") {
                        Stepper("Every \(intervalDays) day\(intervalDays == 1 ? "" : "s")", value: $intervalDays, in: 1...30)
                            .accessibilityLabel("Interval: every \(intervalDays) days")

                        DatePicker("Start Date", selection: $startDate, displayedComponents: .date)

                        Toggle("Has End Date", isOn: $hasEndDate)

                        if hasEndDate {
                            DatePicker("End Date", selection: $endDate, in: startDate..., displayedComponents: .date)
                        }
                    }

                    // Reminders section
                    Section {
                        Toggle("Setup Reminders", isOn: $remindersEnabled)

                        if remindersEnabled {
                            Stepper("Times per day: \(timesPerDay)", value: $timesPerDay, in: 1...8)
                                .onChange(of: timesPerDay) { oldValue, newValue in
                                    adjustReminderTimes(from: oldValue, to: newValue)
                                }

                            ForEach(0..<timesPerDay, id: \.self) { index in
                                DatePicker(
                                    "Time \(index + 1)",
                                    selection: Binding(
                                        get: { reminderTimes.indices.contains(index) ? reminderTimes[index] : Self.defaultTime(hour: 9 + index * 3) },
                                        set: { if index < reminderTimes.count { reminderTimes[index] = $0 } }
                                    ),
                                    displayedComponents: .hourAndMinute
                                )
                            }
                        }
                    } header: {
                        Text("Reminders")
                    } footer: {
                        if remindersEnabled {
                            Text("All family members will receive reminders at these times")
                        }
                    }
                } else {
                    // As-needed section
                    Section("Start Date") {
                        DatePicker("When Prescribed", selection: $startDate, displayedComponents: .date)
                    }
                }

                // Photos section
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

                // Notes section
                Section("Notes") {
                    TextEditor(text: $notes)
                        .frame(minHeight: 80)
                }
            }
            .navigationTitle(isEditing ? "Edit Medication" : "Add Medication")
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
                            await saveMedication()
                        }
                    }
                    .disabled(!isValid || isSaving)
                }
            }
            .task {
                populateExistingMedication()
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

    // MARK: - Photo Section

    private var photoSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Existing photos
            if !existingPhotos.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 12) {
                        ForEach(existingPhotos) { photo in
                            if !photosToDelete.contains(photo.id) {
                                ZStack(alignment: .topTrailing) {
                                    AsyncImage(url: URL(string: photo.photoUrl)) { image in
                                        image
                                            .resizable()
                                            .scaledToFill()
                                    } placeholder: {
                                        Rectangle()
                                            .fill(Color(uiColor: .tertiarySystemGroupedBackground))
                                    }
                                    .frame(width: 80, height: 80)
                                    .clipShape(RoundedRectangle(cornerRadius: 8))

                                    Button {
                                        photosToDelete.insert(photo.id)
                                    } label: {
                                        Image(systemName: "xmark.circle.fill")
                                            .font(.system(size: 22))
                                            .foregroundColor(.white)
                                            .background(Color.black.opacity(0.5))
                                            .clipShape(Circle())
                                    }
                                    .accessibilityLabel("Remove photo")
                                    .offset(x: 4, y: -4)
                                }
                            }
                        }
                    }
                }
            }

            // New photos
            if !newPhotos.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 12) {
                        ForEach(newPhotos) { photo in
                            ZStack(alignment: .topTrailing) {
                                Image(uiImage: UIImage(data: photo.data) ?? UIImage())
                                    .resizable()
                                    .scaledToFill()
                                    .frame(width: 80, height: 80)
                                    .clipShape(RoundedRectangle(cornerRadius: 8))

                                Button {
                                    newPhotos.removeAll { $0.id == photo.id }
                                } label: {
                                    Image(systemName: "xmark.circle.fill")
                                        .font(.system(size: 22))
                                        .foregroundColor(.white)
                                        .background(Color.black.opacity(0.5))
                                        .clipShape(Circle())
                                }
                                .accessibilityLabel("Remove photo")
                                .offset(x: 4, y: -4)
                            }
                        }
                    }
                }
            }

            // Add photo buttons
            if canAddMorePhotos {
                HStack(spacing: 12) {
                    Button {
                        showPhotosPicker = true
                    } label: {
                        Label("Photos", systemImage: "photo.on.rectangle")
                            .font(.subheadline)
                    }
                    .buttonStyle(.bordered)

                    Button {
                        showCamera = true
                    } label: {
                        Label("Camera", systemImage: "camera")
                            .font(.subheadline)
                    }
                    .buttonStyle(.bordered)
                }
            }
        }
    }

    // MARK: - Helpers

    private static func defaultTime(hour: Int) -> Date {
        let calendar = Calendar.current
        var components = DateComponents()
        components.hour = hour
        components.minute = 0
        return calendar.date(from: components) ?? Date()
    }

    private func adjustReminderTimes(from oldValue: Int, to newValue: Int) {
        if newValue > oldValue {
            // Add new times
            for i in oldValue..<newValue {
                let hour = min(9 + i * 3, 21) // 9am, 12pm, 3pm, 6pm, 9pm...
                reminderTimes.append(Self.defaultTime(hour: hour))
            }
        } else if newValue < oldValue {
            // Remove extra times
            reminderTimes = Array(reminderTimes.prefix(newValue))
        }
    }

    private func populateExistingMedication() {
        guard let medication = existingMedication else { return }

        name = medication.name
        friendlyName = medication.friendlyName ?? ""
        medicationType = medication.medicationType
        dosage = medication.dosage ?? ""
        notes = medication.notes ?? ""
        isAsNeeded = medication.isAsNeeded
        intervalDays = medication.intervalDays ?? 1
        startDate = medication.startDate
        hasEndDate = medication.endDate != nil
        if let end = medication.endDate {
            endDate = end
        }
        remindersEnabled = medication.remindersEnabled
        timesPerDay = medication.timesPerDay

        // Load scheduled times
        if let scheduledTimes = medication.scheduledTimes {
            reminderTimes = scheduledTimes.map { scheduled in
                let calendar = Calendar.current
                var components = DateComponents()
                components.hour = scheduled.scheduledHour
                components.minute = scheduled.scheduledMinute
                return calendar.date(from: components) ?? Date()
            }
        }

        // Load existing photos
        existingPhotos = medication.photos ?? []
    }

    // MARK: - Photo Loading

    private func loadPhotos(from items: [PhotosPickerItem]) async {
        for item in items {
            guard canAddMorePhotos else { break }

            do {
                if let data = try await item.loadTransferable(type: Data.self),
                   let image = UIImage(data: data) {
                    // Compress the image
                    let compressed = try imageCompressor.compressForUpload(image, hasTransparency: false)
                    await MainActor.run {
                        newPhotos.append(NewPhoto(data: compressed.data, mimeType: compressed.mimeType))
                    }
                }
            } catch {
                print("Failed to load photo: \(error)")
            }
        }
        // Clear selection after loading
        await MainActor.run {
            selectedPhotos = []
        }
    }

    private func handleCapturedImage(_ image: UIImage) {
        guard canAddMorePhotos else { return }

        do {
            let compressed = try imageCompressor.compressForUpload(image, hasTransparency: false)
            newPhotos.append(NewPhoto(data: compressed.data, mimeType: compressed.mimeType))
        } catch {
            print("Failed to compress photo: \(error)")
        }
    }

    // MARK: - Save

    private func saveMedication() async {
        isSaving = true

        do {
            let scheduledTimes: [ScheduledTimeCreate]? = remindersEnabled && !isAsNeeded
                ? reminderTimes.prefix(timesPerDay).map { ScheduledTimeCreate(from: $0) }
                : nil

            if isEditing, let existing = existingMedication {
                // Update existing medication
                var update = MedicationUpdate()
                update.name = name.trimmingCharacters(in: .whitespacesAndNewlines)
                update.friendlyName = friendlyName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? nil : friendlyName.trimmingCharacters(in: .whitespacesAndNewlines)
                update.medicationType = medicationType
                update.dosage = dosage.isEmpty ? nil : dosage
                update.isAsNeeded = isAsNeeded
                update.intervalDays = isAsNeeded ? nil : intervalDays
                update.startDate = startDate
                update.endDate = isAsNeeded ? nil : (hasEndDate ? endDate : nil)
                update.timesPerDay = isAsNeeded ? 1 : timesPerDay
                update.remindersEnabled = isAsNeeded ? false : remindersEnabled
                update.notes = notes.isEmpty ? nil : notes
                update.scheduledTimes = scheduledTimes

                _ = try await dataService.updateMedication(id: existing.id, update, orgId: pet.orgId)

                // Handle photo deletions (track failures)
                var photoErrors: [String] = []
                for photoId in photosToDelete {
                    do {
                        try await dataService.deleteMedicationPhoto(medicationId: existing.id, photoId: photoId, orgId: pet.orgId)
                    } catch {
                        photoErrors.append("Failed to delete photo")
                    }
                }

                // Upload new photos (track failures)
                for photo in newPhotos {
                    do {
                        _ = try await dataService.uploadMedicationPhoto(medicationId: existing.id, imageData: photo.data, mimeType: photo.mimeType, orgId: pet.orgId)
                    } catch {
                        photoErrors.append("Failed to upload photo")
                    }
                }

                // Fetch updated medication with photos
                let refreshed = try await dataService.getMedication(id: existing.id)

                // Warn user if some photos failed but medication was saved
                if !photoErrors.isEmpty {
                    await MainActor.run {
                        errorMessage = "Medication saved, but \(photoErrors.count) photo(s) failed to sync."
                        showError = true
                    }
                }

                onSave(refreshed)
            } else {
                // Create new medication
                let trimmedFriendlyName = friendlyName.trimmingCharacters(in: .whitespacesAndNewlines)
                let medication = MedicationCreate(
                    petId: pet.id,
                    name: name.trimmingCharacters(in: .whitespacesAndNewlines),
                    friendlyName: trimmedFriendlyName.isEmpty ? nil : trimmedFriendlyName,
                    medicationType: medicationType,
                    dosage: dosage.isEmpty ? nil : dosage,
                    intervalDays: isAsNeeded ? nil : intervalDays,
                    isAsNeeded: isAsNeeded,
                    startDate: startDate,
                    endDate: isAsNeeded ? nil : (hasEndDate ? endDate : nil),
                    timesPerDay: isAsNeeded ? 1 : timesPerDay,
                    notes: notes.isEmpty ? nil : notes,
                    remindersEnabled: isAsNeeded ? false : remindersEnabled,
                    scheduledTimes: scheduledTimes
                )

                let created = try await dataService.createMedication(medication, orgId: pet.orgId)

                // Upload photos (track failures)
                var photoUploadErrors = 0
                for photo in newPhotos {
                    do {
                        _ = try await dataService.uploadMedicationPhoto(medicationId: created.id, imageData: photo.data, mimeType: photo.mimeType, orgId: pet.orgId)
                    } catch {
                        photoUploadErrors += 1
                    }
                }

                // Fetch with photos
                let refreshed = try await dataService.getMedication(id: created.id)

                // Warn user if some photos failed but medication was created
                if photoUploadErrors > 0 {
                    await MainActor.run {
                        errorMessage = "Medication created, but \(photoUploadErrors) photo(s) failed to upload."
                        showError = true
                    }
                }

                onSave(refreshed)
            }

            await MainActor.run {
                dismiss()
            }
        } catch {
            await MainActor.run {
                errorMessage = error.localizedDescription
                showError = true
                isSaving = false
            }
        }
    }
}

// MARK: - Preview

#Preview {
    AddMedicationView(
        pet: Pet(
            id: UUID(),
            orgId: UUID().uuidString,
            name: "Buddy",
            kind: "dog",
            photoUrl: nil,
            currentWeight: nil,
            dateOfBirth: nil,
            isArchived: nil,
            createdAt: Date(),
            createdBy: nil
        )
    ) { _ in }
}
