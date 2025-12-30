//
//  MedicationDetailView.swift
//  Orest's Journal
//
//  Detail view for viewing and managing a single medication.
//

import SwiftUI

struct MedicationDetailView: View {
    @State var medication: Medication
    let pet: Pet
    let onUpdate: (Medication) -> Void
    let onDelete: () -> Void

    @Environment(\.dismiss) private var dismiss

    @State private var showEditSheet = false
    @State private var showDeleteConfirmation = false
    @State private var showFullScreenPhoto = false
    @State private var selectedPhotoIndex = 0
    @State private var isDeleting = false
    @State private var showError = false
    @State private var errorMessage = ""

    // Dose tracking
    @State private var showRecordDoseSheet = false
    @State private var recentDoses: [MedicationDose] = []
    @State private var lastDose: MedicationDose?
    @State private var isLoadingDoses = false

    private let dataService = DataService.shared

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                // Header with name and type
                headerSection

                // Dose recording (only for non-archived)
                if !medication.isArchived {
                    doseRecordingSection
                }

                // Recent doses
                if !recentDoses.isEmpty || lastDose != nil {
                    recentDosesSection
                }

                // Schedule info
                scheduleSection

                // Reminders (if enabled)
                if medication.remindersEnabled && !medication.isAsNeeded {
                    remindersSection
                }

                // Photos if present
                if let photos = medication.photos, !photos.isEmpty {
                    photosSection(photos: photos)
                }

                // Notes
                if let notes = medication.notes, !notes.isEmpty {
                    notesSection(notes: notes)
                }

                // Metadata
                metadataSection
            }
            .padding()
        }
        .background(Color(uiColor: .systemGroupedBackground))
        .navigationTitle("Medication")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            if !medication.isArchived {
                ToolbarItem(placement: .topBarTrailing) {
                    Menu {
                        Button {
                            showEditSheet = true
                        } label: {
                            Label("Edit", systemImage: "pencil")
                        }

                        Button(role: .destructive) {
                            showDeleteConfirmation = true
                        } label: {
                            Label("Delete", systemImage: "trash")
                        }
                    } label: {
                        Image(systemName: "ellipsis.circle")
                    }
                    .accessibilityLabel("More actions")
                    .accessibilityHint("Edit or delete this medication")
                }
            }
        }
        .sheet(isPresented: $showEditSheet) {
            AddMedicationView(
                pet: pet,
                existingMedication: medication
            ) { updated in
                medication = updated
                onUpdate(updated)
            }
        }
        .sheet(isPresented: $showRecordDoseSheet) {
            RecordDoseSheet(
                medication: medication,
                petName: pet.name,
                familyId: pet.familyId,
                onDoseRecorded: {
                    Task { await loadRecentDoses() }
                }
            )
        }
        .task {
            await loadRecentDoses()
        }
        .fullScreenCover(isPresented: $showFullScreenPhoto) {
            if let photos = medication.photos {
                MedicationPhotoGalleryView(
                    photos: photos,
                    initialIndex: selectedPhotoIndex
                )
            }
        }
        .confirmationDialog(
            "Delete Medication",
            isPresented: $showDeleteConfirmation,
            titleVisibility: .visible
        ) {
            Button("Delete", role: .destructive) {
                Task {
                    await deleteMedication()
                }
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("Are you sure you want to delete this medication? If it has recorded doses, it will be archived instead.")
        }
        .alert("Error", isPresented: $showError) {
            Button("OK") {}
        } message: {
            Text(errorMessage)
        }
        .overlay {
            if isDeleting {
                Color.black.opacity(0.3)
                    .ignoresSafeArea()
                ProgressView("Deleting...")
                    .padding()
                    .background(Color(uiColor: .systemBackground))
                    .cornerRadius(10)
            }
        }
    }

    // MARK: - Sections

    private var headerSection: some View {
        HStack(spacing: 16) {
            Image(systemName: medication.medicationType.icon)
                .font(.system(size: 24))
                .foregroundColor(medication.isArchived ? .secondary : .accentColor)
                .frame(width: 56, height: 56)
                .background((medication.isArchived ? Color.secondary : Color.accentColor).opacity(0.15))
                .clipShape(Circle())

            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(medication.displayName)
                        .font(.title2)
                        .fontWeight(.semibold)

                    if medication.isArchived {
                        Text("Archived")
                            .font(.caption)
                            .foregroundColor(.orange)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(Color.orange.opacity(0.15))
                            .clipShape(Capsule())
                    }
                }

                // Show medical name if different from display name (i.e., friendly name is set)
                if medication.friendlyName != nil {
                    Text(medication.name)
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }

                Text(medication.medicationType.displayName)
                    .font(.subheadline)
                    .foregroundColor(.secondary)

                if let dosage = medication.dosage, !dosage.isEmpty {
                    Text(dosage)
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
            }

            Spacer()
        }
        .padding()
        .background(Color(uiColor: .secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private var scheduleSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Schedule", systemImage: "calendar")
                .font(.headline)

            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text("Type")
                        .foregroundColor(.secondary)
                    Spacer()
                    Text(medication.isAsNeeded ? "As Needed (PRN)" : "Scheduled")
                }

                if !medication.isAsNeeded {
                    HStack {
                        Text("Frequency")
                            .foregroundColor(.secondary)
                        Spacer()
                        Text(medication.intervalDescription)
                    }
                }

                HStack {
                    Text("Start Date")
                        .foregroundColor(.secondary)
                    Spacer()
                    Text(Formatters.shortDate.string(from: medication.startDate))
                }

                if let endDate = medication.endDate {
                    HStack {
                        Text("End Date")
                            .foregroundColor(.secondary)
                        Spacer()
                        Text(Formatters.shortDate.string(from: endDate))
                    }
                }

                // Status
                HStack {
                    Text("Status")
                        .foregroundColor(.secondary)
                    Spacer()
                    HStack(spacing: 4) {
                        Circle()
                            .fill(statusColor)
                            .frame(width: 8, height: 8)
                        Text(statusText)
                            .foregroundColor(statusColor)
                    }
                }
            }
            .font(.subheadline)
        }
        .padding()
        .background(Color(uiColor: .secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private var remindersSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Reminders", systemImage: "bell.fill")
                .font(.headline)
                .foregroundColor(.green)

            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text("Times per day")
                        .foregroundColor(.secondary)
                    Spacer()
                    Text("\(medication.timesPerDay)")
                }

                if let scheduledTimes = medication.scheduledTimes, !scheduledTimes.isEmpty {
                    HStack {
                        Text("Times")
                            .foregroundColor(.secondary)
                        Spacer()
                        Text(scheduledTimes.map { $0.formattedTime }.joined(separator: ", "))
                    }
                }
            }
            .font(.subheadline)
        }
        .padding()
        .background(Color(uiColor: .secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private func photosSection(photos: [MedicationPhoto]) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Photos", systemImage: "photo")
                .font(.headline)

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 12) {
                    ForEach(Array(photos.enumerated()), id: \.element.id) { index, photo in
                        Button {
                            selectedPhotoIndex = index
                            showFullScreenPhoto = true
                        } label: {
                            AsyncImage(url: URL(string: photo.photoUrl)) { image in
                                image
                                    .resizable()
                                    .scaledToFill()
                            } placeholder: {
                                Rectangle()
                                    .fill(Color(uiColor: .tertiarySystemGroupedBackground))
                            }
                            .frame(width: 100, height: 100)
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                        }
                    }
                }
            }
        }
        .padding()
        .background(Color(uiColor: .secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private func notesSection(notes: String) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Notes", systemImage: "note.text")
                .font(.headline)

            Text(notes)
                .font(.body)
                .foregroundColor(.primary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(Color(uiColor: .secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private var metadataSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("Created")
                    .foregroundColor(.secondary)
                Spacer()
                Text(Formatters.shortDate.string(from: medication.createdAt))
                    .foregroundColor(.secondary)
            }
        }
        .font(.caption)
        .padding()
        .background(Color(uiColor: .secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private var doseRecordingSection: some View {
        VStack(spacing: 12) {
            Button {
                showRecordDoseSheet = true
            } label: {
                HStack {
                    Image(systemName: "pills.fill")
                        .font(.title3)
                    Text("Record Dose")
                        .fontWeight(.semibold)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 14)
                .background(Color.accentColor)
                .foregroundColor(.white)
                .clipShape(RoundedRectangle(cornerRadius: 12))
            }
            .accessibilityLabel("Record dose of \(medication.displayName)")
            .accessibilityHint("Double tap to record a new dose")

            if let lastDose = lastDose {
                HStack {
                    Image(systemName: "clock")
                        .foregroundColor(.secondary)
                    Text("Last given: \(lastDose.relativeTimeString)")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                    if lastDose.givenBy != "You" {
                        Text("by \(lastDose.givenBy)")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }
                }
            }
        }
        .padding()
        .background(Color(uiColor: .secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private var recentDosesSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Label("Recent Doses", systemImage: "list.bullet.clipboard")
                    .font(.headline)

                Spacer()

                NavigationLink {
                    DoseHistoryView(
                        medication: medication,
                        petName: pet.name,
                        familyId: pet.familyId
                    )
                } label: {
                    HStack(spacing: 4) {
                        Text("View All")
                        Image(systemName: "chevron.right")
                    }
                    .font(.subheadline)
                    .foregroundColor(.accentColor)
                }
            }

            if isLoadingDoses {
                ProgressView()
                    .frame(maxWidth: .infinity, alignment: .center)
                    .padding(.vertical, 8)
            } else if recentDoses.isEmpty {
                Text("No doses recorded yet")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                    .padding(.vertical, 8)
            } else {
                VStack(spacing: 8) {
                    ForEach(recentDoses.prefix(5)) { dose in
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(formatDoseDate(dose.givenAt))
                                    .font(.subheadline)
                                Text(dose.givenBy)
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }

                            Spacer()

                            Text(dose.formattedTime)
                                .font(.subheadline)
                                .foregroundColor(.secondary)
                        }
                        .padding(.vertical, 4)

                        if dose.id != recentDoses.prefix(5).last?.id {
                            Divider()
                        }
                    }
                }
            }
        }
        .padding()
        .background(Color(uiColor: .secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private func formatDoseDate(_ date: Date) -> String {
        let calendar = Calendar.current
        if calendar.isDateInToday(date) {
            return "Today"
        } else if calendar.isDateInYesterday(date) {
            return "Yesterday"
        } else {
            return Formatters.shortDate.string(from: date)
        }
    }

    // MARK: - Computed Properties

    private var statusText: String {
        if medication.isArchived {
            return "Archived"
        } else if medication.isActive {
            return "Active"
        } else if medication.startDate > Date() {
            return "Upcoming"
        } else {
            return "Ended"
        }
    }

    private var statusColor: Color {
        if medication.isArchived {
            return .orange
        } else if medication.isActive {
            return .green
        } else if medication.startDate > Date() {
            return .blue
        } else {
            return .secondary
        }
    }

    // MARK: - Actions

    private func loadRecentDoses() async {
        isLoadingDoses = true
        defer { isLoadingDoses = false }

        do {
            // Load last dose
            lastDose = try await dataService.getLastDose(medicationId: medication.id)

            // Load recent doses
            recentDoses = try await dataService.getDosesForMedication(medicationId: medication.id, limit: 10)
        } catch {
            // Silently fail - not critical
            print("Failed to load doses: \(error)")
        }
    }

    private func deleteMedication() async {
        isDeleting = true

        do {
            _ = try await dataService.deleteMedication(id: medication.id, familyId: pet.familyId)

            await MainActor.run {
                isDeleting = false
                onDelete()
                dismiss()
            }
        } catch {
            await MainActor.run {
                isDeleting = false
                errorMessage = error.localizedDescription
                showError = true
            }
        }
    }
}

// MARK: - Medication Photo Gallery View

struct MedicationPhotoGalleryView: View {
    let photos: [MedicationPhoto]
    let initialIndex: Int

    @Environment(\.dismiss) private var dismiss
    @State private var currentIndex: Int

    init(photos: [MedicationPhoto], initialIndex: Int) {
        self.photos = photos
        self.initialIndex = initialIndex
        _currentIndex = State(initialValue: initialIndex)
    }

    var body: some View {
        ZStack(alignment: .topTrailing) {
            Color.black.ignoresSafeArea()

            TabView(selection: $currentIndex) {
                ForEach(Array(photos.enumerated()), id: \.element.id) { index, photo in
                    AsyncImage(url: URL(string: photo.photoUrl)) { image in
                        image
                            .resizable()
                            .scaledToFit()
                    } placeholder: {
                        ProgressView()
                            .tint(.white)
                    }
                    .tag(index)
                }
            }
            .tabViewStyle(.page)
            .indexViewStyle(.page(backgroundDisplayMode: .always))

            Button {
                dismiss()
            } label: {
                Image(systemName: "xmark.circle.fill")
                    .font(.system(size: 30))
                    .foregroundColor(.white.opacity(0.8))
            }
            .padding()
        }
    }
}

// MARK: - Preview

#Preview {
    NavigationStack {
        MedicationDetailView(
            medication: Medication(
                id: UUID(),
                petId: UUID(),
                name: "Apoquel",
                medicationType: .tablet,
                dosage: "16mg",
                intervalDays: 1,
                isAsNeeded: false,
                startDate: Date(),
                endDate: nil,
                timesPerDay: 2,
                notes: "Give with food",
                remindersEnabled: true,
                timezone: "America/New_York",
                isArchived: false,
                createdBy: nil,
                createdAt: Date(),
                scheduledTimes: nil,
                photos: nil
            ),
            pet: Pet(
                id: UUID(),
                familyId: UUID().uuidString,
                name: "Buddy",
                kind: "dog",
                photoUrl: nil,
                currentWeight: nil,
                dateOfBirth: nil,
                isArchived: nil,
                createdAt: Date(),
                createdBy: nil
            ),
            onUpdate: { _ in },
            onDelete: {}
        )
    }
}
