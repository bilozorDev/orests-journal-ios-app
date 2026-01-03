//
//  MedicationsView.swift
//  Orest's Journal
//
//  Main medications tab view with pet selector and medication list.
//

import SwiftUI

// MARK: - Medication Navigation

enum MedicationDestination: Hashable {
    case medicationDetail(Medication)
}

// MARK: - Medications View

struct MedicationsView: View {
    @State private var pets: [Pet] = []
    @State private var selectedPet: Pet?
    @State private var medications: [Medication] = []
    @State private var isLoading = true
    @State private var isLoadingMedications = false
    @State private var showAddMedication = false
    @State private var showError = false
    @State private var errorMessage = ""
    @State private var navigationPath = NavigationPath()
    @State private var showPetPickerForAdd = false
    @State private var showArchived = false

    // Dose recording
    @State private var medicationForDose: Medication?
    @State private var showRecordDoseSheet = false
    @State private var showMedicationPicker = false

    // Deep link navigation
    @State private var isLoadingDeepLink = false
    @State private var initialDataLoaded = false

    // Search
    @State private var searchText = ""

    // Scene phase for detecting app foreground
    @Environment(\.scenePhase) private var scenePhase
    @State private var lastSceneRefreshTime: Date = .distantPast

    @AppStorage("medication_selected_pet_id") private var savedPetId: String = ""

    private let dataService = DataService.shared
    private let navigationManager = NavigationManager.shared

    var body: some View {
        NavigationStack(path: $navigationPath) {
            coreContent
                .background(Color(uiColor: .systemGroupedBackground))
                .overlay { deepLinkLoadingOverlay }
                .navigationTitle("Medications")
                .toolbar { toolbarContent }
                .navigationDestination(for: MedicationDestination.self) { destination in
                    medicationDetailDestination(for: destination)
                }
        }
        .sheet(isPresented: $showAddMedication, onDismiss: handleAddMedicationDismiss) {
            addMedicationSheet
        }
        .sheet(isPresented: $showRecordDoseSheet) {
            recordDoseSheet
        }
        .confirmationDialog("Select Pet", isPresented: $showPetPickerForAdd, titleVisibility: .visible) {
            petPickerButtons
        } message: {
            Text("Which pet is this medication for?")
        }
        .confirmationDialog("Select Medication", isPresented: $showMedicationPicker, titleVisibility: .visible) {
            medicationPickerButtons
        } message: {
            Text("Which medication do you want to record a dose for?")
        }
        .task { await loadInitialData() }
        .onAppear { handleOnAppear() }
        .onChange(of: navigationManager.tabsNeedingRefresh) { handleTabsNeedingRefreshChange(oldValue: $0, newValue: $1) }
        .onChange(of: navigationManager.pendingDestination) { handlePendingDestinationChange(destination: $1) }
        .onChange(of: scenePhase) { handleScenePhaseChange(newPhase: $1) }
        .searchable(text: $searchText, prompt: "Search medications")
        .alert("Error", isPresented: $showError) {
            Button("OK") {}
        } message: {
            Text(errorMessage)
        }
    }

    // MARK: - Body Subviews

    @ViewBuilder
    private var coreContent: some View {
        if isLoading {
            ProgressView("Loading...")
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        } else if pets.isEmpty {
            emptyPetsView
        } else {
            mainContent
        }
    }

    @ViewBuilder
    private var deepLinkLoadingOverlay: some View {
        if isLoadingDeepLink {
            ZStack {
                Color.black.opacity(0.3)
                    .ignoresSafeArea()
                ProgressView("Loading medication...")
                    .padding()
                    .background(Color(uiColor: .systemBackground))
                    .clipShape(RoundedRectangle(cornerRadius: 12))
            }
        }
    }

    @ToolbarContentBuilder
    private var toolbarContent: some ToolbarContent {
        if !pets.isEmpty {
            ToolbarItem(placement: .topBarLeading) {
                Button {
                    showArchived.toggle()
                } label: {
                    Image(systemName: showArchived ? "archivebox.fill" : "archivebox")
                }
                .accessibilityLabel(showArchived ? "Hide archived" : "Show archived")
            }

            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    if selectedPet != nil {
                        showAddMedication = true
                    } else {
                        showPetPickerForAdd = true
                    }
                } label: {
                    Image(systemName: "plus")
                }
                .accessibilityLabel("Add medication")
            }
        }
    }

    @ViewBuilder
    private func medicationDetailDestination(for destination: MedicationDestination) -> some View {
        switch destination {
        case .medicationDetail(let medication):
            if let pet = petForMedication(medication) {
                MedicationDetailView(
                    medication: medication,
                    pet: pet,
                    onUpdate: { updateMedicationInList($0) },
                    onDelete: { removeMedicationFromList(medication.id) }
                )
            } else {
                ContentUnavailableView(
                    "Pet Not Found",
                    systemImage: "exclamationmark.triangle",
                    description: Text("Unable to load pet information for this medication.")
                )
            }
        }
    }

    @ViewBuilder
    private var addMedicationSheet: some View {
        if let pet = selectedPet ?? pets.first {
            AddMedicationView(pet: pet) { newMedication in
                handleNewMedication(newMedication)
            }
        }
    }

    @ViewBuilder
    private var recordDoseSheet: some View {
        if let medication = medicationForDose,
           let pet = petForMedication(medication) {
            RecordDoseSheet(
                medication: medication,
                petName: pet.name,
                familyId: pet.familyId,
                onDoseRecorded: {}
            )
        }
    }

    @ViewBuilder
    private var petPickerButtons: some View {
        ForEach(pets) { pet in
            Button(pet.name) {
                selectedPet = pet
                savedPetId = pet.id.uuidString
                showAddMedication = true
            }
        }
        Button("Cancel", role: .cancel) {}
    }

    @ViewBuilder
    private var medicationPickerButtons: some View {
        ForEach(activeMedications) { medication in
            Button(medicationPickerLabel(for: medication)) {
                medicationForDose = medication
                showRecordDoseSheet = true
            }
        }
        Button("Cancel", role: .cancel) {}
    }

    private func handleAddMedicationDismiss() {
        #if DEBUG
        print("📋 [Medications] Sheet dismissed, refreshing list...")
        #endif
        Task { @MainActor in
            await loadMedications(forceRefresh: true)
            #if DEBUG
            print("📋 [Medications] Refresh complete, \(medications.count) medications loaded")
            #endif
        }
    }

    private func handleNewMedication(_ newMedication: Medication) {
        Task { @MainActor in
            #if DEBUG
            print("📋 [Medications] onSave called - medication: \(newMedication.displayName), petId: \(newMedication.petId)")
            print("📋 [Medications] Current filter - selectedPet: \(selectedPet?.name ?? "All") (id: \(selectedPet?.id.uuidString ?? "nil"))")
            #endif
            if !medications.contains(where: { $0.id == newMedication.id }) {
                medications.insert(newMedication, at: 0)
                medications.sort { lhs, rhs in
                    if lhs.isArchived != rhs.isArchived {
                        return !lhs.isArchived
                    }
                    return lhs.name.localizedCaseInsensitiveCompare(rhs.name) == .orderedAscending
                }
                #if DEBUG
                print("📋 [Medications] Added new medication to list: \(newMedication.displayName), total: \(medications.count)")
                #endif
            }
        }
    }

    // MARK: - Main Content

    private var mainContent: some View {
        ScrollView {
            VStack(spacing: 0) {
                // Pet selector if multiple pets
                if pets.count > 1 {
                    petSelector
                }

                // Medications content
                if isLoadingMedications {
                    ProgressView()
                        .frame(maxWidth: .infinity, minHeight: 200)
                } else if displayedMedications.isEmpty {
                    emptyMedicationsView
                } else {
                    medicationsContent
                }
            }
        }
        .refreshable {
            await loadMedications(forceRefresh: true)
        }
    }

    // MARK: - Pet Selector

    private var petSelector: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 12) {
                // "All" option
                if pets.count > 1 {
                    Button {
                        selectPet(nil)
                    } label: {
                        HStack(spacing: 8) {
                            Image(systemName: "pawprint.fill")
                                .font(.system(size: 14))
                                .frame(width: 28, height: 28)

                            Text("All")
                                .font(.subheadline)
                                .fontWeight(selectedPet == nil ? .semibold : .regular)
                        }
                        .padding(.horizontal, 12)
                        .padding(.vertical, 8)
                        .background(
                            selectedPet == nil
                                ? Color.accentColor.opacity(0.15)
                                : Color(uiColor: .secondarySystemGroupedBackground)
                        )
                        .foregroundColor(selectedPet == nil ? .accentColor : .primary)
                        .clipShape(Capsule())
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Show all pets")
                    .accessibilityAddTraits(selectedPet == nil ? .isSelected : [])
                }

                ForEach(pets) { pet in
                    Button {
                        selectPet(pet)
                    } label: {
                        HStack(spacing: 8) {
                            if let photoUrl = pet.photoUrl, let url = URL(string: photoUrl) {
                                AsyncImage(url: url) { image in
                                    image
                                        .resizable()
                                        .scaledToFill()
                                } placeholder: {
                                    petPlaceholder(for: pet)
                                }
                                .frame(width: 28, height: 28)
                                .clipShape(Circle())
                            } else {
                                petPlaceholder(for: pet)
                                    .frame(width: 28, height: 28)
                            }

                            Text(pet.name)
                                .font(.subheadline)
                                .fontWeight(selectedPet?.id == pet.id ? .semibold : .regular)
                        }
                        .padding(.horizontal, 12)
                        .padding(.vertical, 8)
                        .background(
                            selectedPet?.id == pet.id
                                ? Color.accentColor.opacity(0.15)
                                : Color(uiColor: .secondarySystemGroupedBackground)
                        )
                        .foregroundColor(selectedPet?.id == pet.id ? .accentColor : .primary)
                        .clipShape(Capsule())
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Select \(pet.name)")
                    .accessibilityAddTraits(selectedPet?.id == pet.id ? .isSelected : [])
                }
            }
            .padding(.horizontal)
            .padding(.vertical, 12)
        }
        .background(Color(uiColor: .systemGroupedBackground))
    }

    private func petPlaceholder(for pet: Pet) -> some View {
        Image(systemName: pet.kind == "cat" ? "cat.fill" : "dog.fill")
            .font(.system(size: 14))
            .foregroundColor(.secondary)
            .frame(width: 28, height: 28)
            .background(Color(uiColor: .tertiarySystemGroupedBackground))
            .clipShape(Circle())
    }

    // MARK: - Medications Content

    private var medicationsContent: some View {
        LazyVStack(spacing: 0, pinnedViews: [.sectionHeaders]) {
            // Active medications section
            if !activeMedications.isEmpty {
                Section {
                    ForEach(activeMedications) { medication in
                        medicationRow(medication)
                    }
                } header: {
                    sectionHeader("Active Medications", count: activeMedications.count)
                }
            }

            // Archived medications section (if showing)
            if showArchived {
                if !archivedMedications.isEmpty {
                    Section {
                        ForEach(archivedMedications) { medication in
                            medicationRow(medication)
                        }
                    } header: {
                        sectionHeader("Archived", count: archivedMedications.count)
                    }
                } else {
                    // Empty archived state
                    Section {
                        HStack {
                            Spacer()
                            VStack(spacing: 8) {
                                Image(systemName: "archivebox")
                                    .font(.title2)
                                    .foregroundColor(.secondary)
                                Text("No archived medications")
                                    .font(.subheadline)
                                    .foregroundColor(.secondary)
                            }
                            .padding(.vertical, 20)
                            Spacer()
                        }
                    } header: {
                        sectionHeader("Archived", count: 0)
                    }
                }
            }
        }
        .padding(.bottom, 20)
    }

    private func medicationRow(_ medication: Medication) -> some View {
        Button {
            navigationPath.append(MedicationDestination.medicationDetail(medication))
        } label: {
            MedicationRow(
                medication: medication,
                petName: selectedPet == nil ? petName(for: medication) : nil
            )
        }
        .buttonStyle(.plain)
        .accessibilityLabel("\(medication.displayName), \(medication.intervalDescription)")
        .accessibilityHint("Double tap to view details")
        .swipeActions(edge: .trailing, allowsFullSwipe: true) {
            if !medication.isArchived {
                Button {
                    medicationForDose = medication
                    showRecordDoseSheet = true
                } label: {
                    Label("Dose", systemImage: "pills.fill")
                }
                .tint(.green)
            }
        }
    }

    private func sectionHeader(_ title: String, count: Int) -> some View {
        HStack {
            Text(title)
                .font(.subheadline)
                .fontWeight(.semibold)
                .foregroundColor(.secondary)
            Text("(\(count))")
                .font(.subheadline)
                .foregroundColor(.secondary)
            Spacer()
        }
        .padding(.horizontal)
        .padding(.vertical, 8)
        .background(Color(uiColor: .systemGroupedBackground))
    }

    private func petName(for medication: Medication) -> String? {
        pets.first { $0.id == medication.petId }?.name
    }

    /// Label for medication picker - includes pet name if multiple pets
    private func medicationPickerLabel(for medication: Medication) -> String {
        if pets.count > 1, let petName = petName(for: medication) {
            return "\(medication.displayName) (\(petName))"
        }
        return medication.displayName
    }

    private func petForMedication(_ medication: Medication) -> Pet? {
        if let pet = selectedPet {
            return pet
        }
        return pets.first { $0.id == medication.petId }
    }

    private func handlePendingDestination(_ destination: AppDestination?) {
        guard let destination = destination else { return }

        switch destination {
        case .recordDose:
            // Only handle if we have medications loaded
            guard !activeMedications.isEmpty else {
                navigationManager.clearPendingDestination()
                return
            }

            if activeMedications.count == 1 {
                // Single medication: go directly to dose sheet
                medicationForDose = activeMedications.first
                showRecordDoseSheet = true
            } else {
                // Multiple medications: show picker
                showMedicationPicker = true
            }
            navigationManager.clearPendingDestination()

        case .medications:
            // Already on medications tab, just clear
            navigationManager.clearPendingDestination()

        case .medicationDetail(let medicationId):
            // Navigate to specific medication from deep link
            // Clear the pending destination first to prevent re-triggering
            navigationManager.clearPendingDestination()
            Task {
                await navigateToMedication(id: medicationId)
            }

        default:
            // Not for us
            break
        }
    }

    /// Navigate to a specific medication by ID (for deep links)
    private func navigateToMedication(id medicationId: UUID) async {
        #if DEBUG
        print("📋 [Medications] navigateToMedication called for: \(medicationId)")
        print("📋 [Medications] Current medications count: \(medications.count), pets count: \(pets.count)")
        #endif

        // First check if medication is already in our list
        if let medication = medications.first(where: { $0.id == medicationId }) {
            #if DEBUG
            print("📋 [Medications] Found medication in list, navigating to: \(medication.displayName)")
            #endif
            navigationPath.append(MedicationDestination.medicationDetail(medication))
            return
        }

        #if DEBUG
        print("📋 [Medications] Medication not in list, loading from API...")
        #endif

        // Load the medication from API
        isLoadingDeepLink = true
        defer { isLoadingDeepLink = false }

        do {
            let medication = try await dataService.getMedication(id: medicationId)
            #if DEBUG
            print("📋 [Medications] Loaded medication from API: \(medication.displayName)")
            #endif

            // Make sure we have the pet loaded
            if pets.isEmpty {
                #if DEBUG
                print("📋 [Medications] Pets empty, loading pets...")
                #endif
                pets = try await dataService.getPets(forceRefresh: true)
            }

            // Navigate to the medication detail
            #if DEBUG
            print("📋 [Medications] Appending to navigationPath...")
            #endif
            navigationPath.append(MedicationDestination.medicationDetail(medication))
            #if DEBUG
            print("📋 [Medications] Navigation path count after append: \(navigationPath.count)")
            #endif

            // Also add it to our list if not already there
            if !medications.contains(where: { $0.id == medication.id }) {
                medications.insert(medication, at: 0)
            }
        } catch {
            #if DEBUG
            print("📋 [Medications] Failed to load medication for deep link: \(error)")
            #endif
            errorMessage = "Unable to load medication"
            showError = true
        }
    }

    // MARK: - Empty Views

    private var emptyPetsView: some View {
        VStack(spacing: 16) {
            Image(systemName: "pawprint")
                .font(.system(size: 48))
                .foregroundColor(.secondary)
            Text("No Pets")
                .font(.title2)
                .fontWeight(.semibold)
            Text("Add a pet to start tracking medications")
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var emptyMedicationsView: some View {
        VStack(spacing: 16) {
            Image(systemName: "pills")
                .font(.system(size: 48))
                .foregroundColor(.secondary)
            Text("No Medications")
                .font(.title2)
                .fontWeight(.semibold)
            Text("Tap + to add a medication")
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)

            Button {
                if selectedPet != nil {
                    showAddMedication = true
                } else {
                    showPetPickerForAdd = true
                }
            } label: {
                Label("Add Medication", systemImage: "plus")
                    .font(.headline)
                    .padding(.horizontal, 20)
                    .padding(.vertical, 12)
                    .background(Color.accentColor)
                    .foregroundColor(.white)
                    .clipShape(Capsule())
            }
            .padding(.top, 8)
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Lifecycle Handlers

    private func handleOnAppear() {
        // Check if we need to refresh (handles returning from sheet or other views)
        if navigationManager.tabsNeedingRefresh.contains(.medication) {
            navigationManager.markTabRefreshed(.medication)
            Task {
                await loadMedications(forceRefresh: true)
            }
        }
    }

    private func handleTabsNeedingRefreshChange(oldValue: Set<Tab>, newValue: Set<Tab>) {
        #if DEBUG
        print("📋 [Medications] tabsNeedingRefresh changed: \(oldValue) -> \(newValue)")
        #endif
        if newValue.contains(.medication) {
            navigationManager.markTabRefreshed(.medication)
            #if DEBUG
            print("📋 [Medications] Refreshing due to navigation manager flag")
            #endif
            Task {
                await loadMedications(forceRefresh: true)
            }
        }
    }

    private func handlePendingDestinationChange(destination: AppDestination?) {
        // Only handle if initial data is loaded, otherwise loadInitialData will handle it
        if initialDataLoaded {
            handlePendingDestination(destination)
        }
    }

    private func handleScenePhaseChange(newPhase: ScenePhase) {
        // Refresh when app becomes active (e.g., after widget dose recording)
        // This bypasses NavigationManager coordination which has race conditions
        // with the app-level scenePhase handler
        guard newPhase == .active && initialDataLoaded else { return }

        let timeSinceLastRefresh = Date().timeIntervalSince(lastSceneRefreshTime)

        // Only refresh if more than 5 seconds since last scene-triggered refresh
        // This prevents excessive refreshes when user rapidly switches apps
        if timeSinceLastRefresh > 5 {
            #if DEBUG
            print("📋 [Medications] Scene became active, refreshing (last: \(Int(timeSinceLastRefresh))s ago)")
            #endif
            lastSceneRefreshTime = Date()

            // Clear any pending flag since we're refreshing anyway
            navigationManager.markTabRefreshed(.medication)

            Task {
                await loadMedications(forceRefresh: true)
            }
        } else {
            #if DEBUG
            print("📋 [Medications] Scene became active, skipping refresh (last: \(Int(timeSinceLastRefresh))s ago)")
            #endif
        }
    }

    // MARK: - Computed Properties

    private var displayedMedications: [Medication] {
        var result = showArchived ? medications : medications.filter { !$0.isArchived }

        // Apply search filter if search text is not empty
        if !searchText.isEmpty {
            let query = searchText.lowercased()
            result = result.filter { medication in
                medication.displayName.lowercased().contains(query) ||
                medication.name.lowercased().contains(query) ||
                (medication.dosage?.lowercased().contains(query) ?? false) ||
                (medication.notes?.lowercased().contains(query) ?? false)
            }
        }

        return result
    }

    private var activeMedications: [Medication] {
        displayedMedications.filter { !$0.isArchived }
    }

    private var archivedMedications: [Medication] {
        displayedMedications.filter { $0.isArchived }
    }

    // MARK: - Data Loading

    private func loadInitialData() async {
        do {
            pets = try await dataService.getPets(forceRefresh: true)

            guard !Task.isCancelled else { return }

            // Restore saved pet selection
            if let savedId = UUID(uuidString: savedPetId),
               let savedPet = pets.first(where: { $0.id == savedId }) {
                selectedPet = savedPet
            } else if savedPetId.isEmpty && pets.count > 1 {
                // "All" was selected
                selectedPet = nil
            } else if let firstPet = pets.first {
                selectedPet = firstPet
                savedPetId = firstPet.id.uuidString
            }

            await loadMedications()
        } catch {
            guard !Task.isCancelled else { return }
            errorMessage = error.localizedDescription
            showError = true
        }

        guard !Task.isCancelled else { return }
        isLoading = false
        initialDataLoaded = true

        // Handle any pending deep link navigation after data is loaded
        if let destination = navigationManager.pendingDestination {
            #if DEBUG
            print("📋 [Medications] Initial data loaded, handling pending destination: \(destination)")
            #endif
            handlePendingDestination(destination)
        }
    }

    private func selectPet(_ pet: Pet?) {
        guard pet?.id != selectedPet?.id else { return }
        selectedPet = pet
        savedPetId = pet?.id.uuidString ?? ""
        medications = []
        isLoadingMedications = true

        Task {
            await loadMedications()
            guard !Task.isCancelled else { return }
            isLoadingMedications = false
        }
    }

    private func loadMedications(forceRefresh: Bool = false) async {
        guard let firstPet = pets.first else { return }
        let familyId = firstPet.familyId

        #if DEBUG
        print("📋 [Medications] Loading medications - forceRefresh: \(forceRefresh), petFilter: \(selectedPet?.name ?? "All")")
        #endif

        do {
            let loaded = try await dataService.getMedications(
                for: familyId,
                petId: selectedPet?.id,
                includeArchived: true,
                forceRefresh: forceRefresh
            )
            #if DEBUG
            print("📋 [Medications] API returned \(loaded.count) medications:")
            for med in loaded {
                print("   - \(med.displayName) (pet: \(med.petId), archived: \(med.isArchived))")
            }
            #endif

            guard !Task.isCancelled else { return }

            // Sort: active first, then by name
            medications = loaded.sorted { lhs, rhs in
                if lhs.isArchived != rhs.isArchived {
                    return !lhs.isArchived
                }
                return lhs.name.localizedCaseInsensitiveCompare(rhs.name) == .orderedAscending
            }
        } catch {
            guard !Task.isCancelled else { return }
            errorMessage = error.localizedDescription
            showError = true
        }
    }

    private func updateMedicationInList(_ updatedMedication: Medication) {
        if let index = medications.firstIndex(where: { $0.id == updatedMedication.id }) {
            medications[index] = updatedMedication
            // Re-sort in case archived status changed
            medications.sort { lhs, rhs in
                if lhs.isArchived != rhs.isArchived {
                    return !lhs.isArchived
                }
                return lhs.name.localizedCaseInsensitiveCompare(rhs.name) == .orderedAscending
            }
        }
        // Also do a background refresh to ensure full sync
        Task {
            await loadMedications(forceRefresh: true)
        }
    }

    private func removeMedicationFromList(_ medicationId: UUID) {
        medications.removeAll { $0.id == medicationId }
    }
}

// MARK: - Medication Row

struct MedicationRow: View {
    let medication: Medication
    var petName: String?

    var body: some View {
        HStack(spacing: 12) {
            // Medication type icon
            Image(systemName: medication.medicationType.icon)
                .font(.system(size: 18))
                .foregroundColor(medication.isArchived ? .secondary : .accentColor)
                .frame(width: 40, height: 40)
                .background(
                    (medication.isArchived ? Color.secondary : Color.accentColor)
                        .opacity(0.15)
                )
                .clipShape(Circle())

            // Medication details
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(medication.displayName)
                        .font(.headline)
                        .lineLimit(1)
                        .foregroundColor(medication.isArchived ? .secondary : .primary)

                    if medication.isArchived {
                        Text("Archived")
                            .font(.caption)
                            .foregroundColor(.orange)
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(Color.orange.opacity(0.15))
                            .clipShape(Capsule())
                    }
                }

                // Pet name when showing all pets
                if let petName = petName {
                    Text(petName)
                        .font(.subheadline)
                        .foregroundColor(.accentColor)
                }

                HStack(spacing: 4) {
                    Text(medication.intervalDescription)
                        .font(.subheadline)
                        .foregroundColor(.secondary)

                    if let dosage = medication.dosage, !dosage.isEmpty {
                        Text("·")
                            .foregroundColor(.secondary)
                        Text(dosage)
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                            .lineLimit(1)
                    }
                }

                // Reminders indicator
                if medication.remindersEnabled && !medication.isAsNeeded {
                    HStack(spacing: 4) {
                        Image(systemName: "bell.fill")
                            .font(.caption)
                            .foregroundColor(.green)
                        Text("\(medication.timesPerDay)x daily")
                            .font(.caption)
                            .foregroundColor(.green)
                    }
                }
            }

            Spacer()

            // Photo thumbnail if present
            if let firstPhoto = medication.photos?.first, let url = URL(string: firstPhoto.photoUrl) {
                AsyncImage(url: url) { image in
                    image
                        .resizable()
                        .scaledToFill()
                } placeholder: {
                    Rectangle()
                        .fill(Color(uiColor: .tertiarySystemGroupedBackground))
                }
                .frame(width: 44, height: 44)
                .clipShape(RoundedRectangle(cornerRadius: 8))
            }

            Image(systemName: "chevron.right")
                .font(.system(size: 14, weight: .semibold))
                .foregroundColor(Color(uiColor: .tertiaryLabel))
        }
        .padding(.horizontal)
        .padding(.vertical, 12)
        .background(Color(uiColor: .secondarySystemGroupedBackground))
    }
}

// MARK: - Preview

#Preview {
    MedicationsView()
}
