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
    @Environment(\.scenePhase) private var scenePhase

    @State private var showEditSheet = false
    @State private var showDeleteConfirmation = false
    @State private var showRestoreConfirmation = false
    @State private var showFullScreenPhoto = false
    @State private var selectedPhotoIndex = 0
    @State private var isDeleting = false
    @State private var isRestoring = false
    @State private var showError = false
    @State private var errorMessage = ""

    // Dose tracking
    @State private var showRecordDoseSheet = false
    @State private var recentDoses: [MedicationDose] = []
    @State private var lastDose: MedicationDose?
    @State private var isLoadingDoses = false
    @State private var todayDoses: [MedicationDose] = []

    // Today's schedule interaction
    @State private var selectedScheduledTime: Date?
    @State private var isRecordingDose = false
    @State private var recordingForSlot: Date?

    // Widget dose confirmation
    @State private var showDoseConfirmation = false

    private let dataService = DataService.shared
    private let navigationManager = NavigationManager.shared

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                // Header with name and type
                headerSection

                // Dose recording (only for non-archived)
                if !medication.isArchived {
                    doseRecordingSection
                }

                // Today's schedule (for scheduled medications with reminders)
                if !medication.isArchived && !medication.isAsNeeded && medication.isActive {
                    if let scheduledTimes = medication.scheduledTimes, !scheduledTimes.isEmpty {
                        todayScheduleSection
                    }
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
        .refreshable {
            await loadRecentDoses()
        }
        .background(Color(uiColor: .systemGroupedBackground))
        .navigationTitle("Medication")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                if medication.isArchived {
                    Button {
                        showRestoreConfirmation = true
                    } label: {
                        Label("Restore", systemImage: "arrow.uturn.backward")
                    }
                    .disabled(isRestoring)
                    .accessibilityLabel("Restore medication")
                    .accessibilityHint("Unarchive this medication to make it active again")
                } else {
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
            checkForWidgetDoseConfirmation()
        }
        .onAppear {
            // Check on every appear (handles returning from background, re-navigation)
            checkForWidgetDoseConfirmation()
        }
        .onChange(of: navigationManager.widgetDoseRecorded?.medicationId) { _, newValue in
            // Also watch for changes while view is on screen
            guard newValue == medication.id else { return }
            Task {
                await loadRecentDoses()
            }
            checkForWidgetDoseConfirmation()
        }
        .onChange(of: scenePhase) { _, newPhase in
            // When app becomes active (e.g., from widget tap), check for pending confirmation
            if newPhase == .active {
                checkForWidgetDoseConfirmation()
            }
        }
        .overlay(alignment: .top) {
            if showDoseConfirmation {
                doseConfirmationBanner
                    .transition(.move(edge: .top).combined(with: .opacity))
            }
        }
        .animation(.easeInOut(duration: 0.3), value: showDoseConfirmation)
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
        .confirmationDialog(
            "Restore Medication",
            isPresented: $showRestoreConfirmation,
            titleVisibility: .visible
        ) {
            Button("Restore") {
                Task {
                    await restoreMedication()
                }
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("This will restore the medication and make it active again. You can continue recording doses for it.")
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
            if isRestoring {
                Color.black.opacity(0.3)
                    .ignoresSafeArea()
                ProgressView("Restoring...")
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

    private var todayScheduleSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Today's Schedule", systemImage: "clock.badge.checkmark")
                .font(.headline)

            if isLoadingDoses {
                ProgressView()
                    .frame(maxWidth: .infinity, alignment: .center)
                    .padding(.vertical, 8)
            } else if let scheduledTimes = medication.scheduledTimes {
                let slots = buildTodaySlots(from: scheduledTimes)
                VStack(spacing: 8) {
                    ForEach(slots, id: \.scheduledFor) { slot in
                        todaySlotRow(slot: slot)

                        if slot.scheduledFor != slots.last?.scheduledFor {
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

    private struct ScheduleSlot {
        let scheduledFor: Date
        let formattedTime: String
        let isGiven: Bool
        let dose: MedicationDose?
        let isPast: Bool
    }

    private func buildTodaySlots(from scheduledTimes: [ScheduledTime]) -> [ScheduleSlot] {
        let calendar = Calendar.current
        let now = Date()

        return scheduledTimes
            .sorted { ($0.scheduledHour, $0.scheduledMinute) < ($1.scheduledHour, $1.scheduledMinute) }
            .compactMap { time -> ScheduleSlot? in
                // Build today's date with this scheduled time
                var components = calendar.dateComponents([.year, .month, .day], from: now)
                components.hour = time.scheduledHour
                components.minute = time.scheduledMinute
                guard let scheduledFor = calendar.date(from: components) else { return nil }

                // Find dose with matching scheduledFor
                let matchingDose = todayDoses.first { dose in
                    guard let doseScheduledFor = dose.scheduledFor else { return false }
                    return calendar.isDate(doseScheduledFor, equalTo: scheduledFor, toGranularity: .minute)
                }

                return ScheduleSlot(
                    scheduledFor: scheduledFor,
                    formattedTime: time.formattedTime,
                    isGiven: matchingDose != nil,
                    dose: matchingDose,
                    isPast: scheduledFor < now
                )
            }
    }

    private func todaySlotRow(slot: ScheduleSlot) -> some View {
        HStack {
            // Time
            Text(slot.formattedTime)
                .font(.headline)
                .frame(width: 80, alignment: .leading)

            Spacer()

            if slot.isGiven {
                // Show given status
                HStack(spacing: 6) {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(.green)
                    Text("Given")
                        .font(.subheadline)
                        .foregroundColor(.green)
                    if let dose = slot.dose {
                        Text(dose.formattedTime)
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
            } else {
                // Show Give button
                Button {
                    recordDoseForSlot(slot.scheduledFor)
                } label: {
                    HStack(spacing: 4) {
                        if isRecordingDose && recordingForSlot == slot.scheduledFor {
                            ProgressView()
                                .tint(.white)
                        } else {
                            Image(systemName: "pills.fill")
                        }
                        Text("Give")
                    }
                    .font(.subheadline.weight(.semibold))
                    .padding(.horizontal, 16)
                    .padding(.vertical, 8)
                    .background(slot.isPast ? Color.orange : Color.accentColor)
                    .foregroundColor(.white)
                    .clipShape(Capsule())
                }
                .disabled(isRecordingDose)
                .accessibilityLabel("Record dose for \(slot.formattedTime)")
            }
        }
        .padding(.vertical, 4)
    }

    private func recordDoseForSlot(_ scheduledFor: Date) {
        Task {
            isRecordingDose = true
            recordingForSlot = scheduledFor
            defer {
                isRecordingDose = false
                recordingForSlot = nil
            }

            do {
                _ = try await dataService.recordDose(
                    medicationId: medication.id,
                    scheduledFor: scheduledFor,
                    familyId: pet.familyId
                )
                // Reload doses to update UI
                await loadRecentDoses()
            } catch {
                errorMessage = error.localizedDescription
                showError = true
            }
        }
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

    // MARK: - Widget Dose Confirmation

    private var doseConfirmationBanner: some View {
        HStack(spacing: 12) {
            Image(systemName: "checkmark.circle.fill")
                .font(.title2)
                .foregroundColor(.white)

            VStack(alignment: .leading, spacing: 2) {
                Text("Dose Recorded")
                    .font(.headline)
                    .foregroundColor(.white)
                Text("from widget")
                    .font(.subheadline)
                    .foregroundColor(.white.opacity(0.9))
            }

            Spacer()

            Button {
                withAnimation {
                    showDoseConfirmation = false
                }
            } label: {
                Image(systemName: "xmark")
                    .font(.subheadline.weight(.semibold))
                    .foregroundColor(.white.opacity(0.8))
            }
        }
        .padding()
        .background(Color.green)
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .shadow(color: .black.opacity(0.15), radius: 8, y: 4)
        .padding(.horizontal)
        .padding(.top, 8)
    }

    private func checkForWidgetDoseConfirmation() {
        guard let recorded = navigationManager.widgetDoseRecorded,
              recorded.medicationId == medication.id else {
            return
        }

        #if DEBUG
        print("✅ [Widget] Found widget dose confirmation for \(recorded.medicationName)")
        #endif

        // Clear the flag first to prevent duplicate handling
        navigationManager.widgetDoseRecorded = nil

        // Refresh doses to show updated "Given" status in Today's Schedule
        Task {
            await loadRecentDoses()

            // Show confirmation banner after data loads
            withAnimation {
                showDoseConfirmation = true
            }

            // Auto-dismiss after 4 seconds
            try? await Task.sleep(for: .seconds(4))
            await MainActor.run {
                withAnimation {
                    showDoseConfirmation = false
                }
            }
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

            // Load today's doses for schedule matching
            todayDoses = try await dataService.getTodaysDoses(medicationId: medication.id)
        } catch {
            // Silently fail - not critical
            print("Failed to load doses: \(error)")
        }
    }

    private func deleteMedication() async {
        isDeleting = true

        do {
            _ = try await dataService.deleteMedication(id: medication.id, familyId: pet.familyId)

            // Cancel any local reminders for this medication
            await LocalMedicationReminderManager.shared.cancelReminders(for: medication.id)

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

    private func restoreMedication() async {
        isRestoring = true

        do {
            let restored = try await dataService.unarchiveMedication(id: medication.id, familyId: pet.familyId)

            // Schedule local reminders if enabled
            if restored.remindersEnabled {
                await LocalMedicationReminderManager.shared.scheduleReminders(for: restored, petName: pet.name)
            }

            await MainActor.run {
                isRestoring = false
                medication = restored
                onUpdate(restored)
            }
        } catch {
            await MainActor.run {
                isRestoring = false
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
