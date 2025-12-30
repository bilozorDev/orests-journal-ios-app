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

    @AppStorage("medication_selected_pet_id") private var savedPetId: String = ""

    private let dataService = DataService.shared
    private let navigationManager = NavigationManager.shared

    var body: some View {
        NavigationStack(path: $navigationPath) {
            Group {
                if isLoading {
                    ProgressView("Loading...")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if pets.isEmpty {
                    emptyPetsView
                } else {
                    mainContent
                }
            }
            .background(Color(uiColor: .systemGroupedBackground))
            .navigationTitle("Medications")
            .toolbar {
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
            .navigationDestination(for: MedicationDestination.self) { destination in
                switch destination {
                case .medicationDetail(let medication):
                    if let pet = petForMedication(medication) {
                        MedicationDetailView(
                            medication: medication,
                            pet: pet,
                            onUpdate: { updatedMedication in
                                updateMedicationInList(updatedMedication)
                            },
                            onDelete: {
                                removeMedicationFromList(medication.id)
                            }
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
            .sheet(isPresented: $showAddMedication, onDismiss: {
                // Reload after sheet dismisses to ensure we have latest data
                Task {
                    await loadMedications(forceRefresh: true)
                }
            }) {
                if let pet = selectedPet ?? pets.first {
                    AddMedicationView(pet: pet) { _ in
                        // Sheet will dismiss and trigger onDismiss reload
                    }
                }
            }
            .sheet(isPresented: $showRecordDoseSheet) {
                if let medication = medicationForDose,
                   let pet = petForMedication(medication) {
                    RecordDoseSheet(
                        medication: medication,
                        petName: pet.name,
                        familyId: pet.familyId,
                        onDoseRecorded: {
                            // No need to refresh the list, dose is recorded
                        }
                    )
                }
            }
            .confirmationDialog(
                "Select Pet",
                isPresented: $showPetPickerForAdd,
                titleVisibility: .visible
            ) {
                ForEach(pets) { pet in
                    Button(pet.name) {
                        selectedPet = pet
                        savedPetId = pet.id.uuidString
                        showAddMedication = true
                    }
                }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("Which pet is this medication for?")
            }
            .task {
                await loadInitialData()
            }
            .onChange(of: navigationManager.tabsNeedingRefresh) { _, newValue in
                if newValue.contains(.medication) {
                    navigationManager.markTabRefreshed(.medication)
                    Task {
                        await loadMedications(forceRefresh: true)
                    }
                }
            }
            .onChange(of: navigationManager.pendingDestination) { _, destination in
                handlePendingDestination(destination)
            }
            .onAppear {
                // Handle pending destination on appear (e.g., from quick action)
                if let destination = navigationManager.pendingDestination {
                    handlePendingDestination(destination)
                }
            }
            .confirmationDialog(
                "Select Medication",
                isPresented: $showMedicationPicker,
                titleVisibility: .visible
            ) {
                ForEach(activeMedications) { medication in
                    Button(medicationPickerLabel(for: medication)) {
                        medicationForDose = medication
                        showRecordDoseSheet = true
                    }
                }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("Which medication do you want to record a dose for?")
            }
            .alert("Error", isPresented: $showError) {
                Button("OK") {}
            } message: {
                Text(errorMessage)
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
        .accessibilityLabel("\(medication.name), \(medication.intervalDescription)")
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
            return "\(medication.name) (\(petName))"
        }
        return medication.name
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

        default:
            // Not for us
            break
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

    // MARK: - Computed Properties

    private var displayedMedications: [Medication] {
        if showArchived {
            return medications
        } else {
            return medications.filter { !$0.isArchived }
        }
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
    }

    private func selectPet(_ pet: Pet?) {
        guard pet?.id != selectedPet?.id else { return }
        selectedPet = pet
        savedPetId = pet?.id.uuidString ?? ""
        medications = []
        isLoadingMedications = true

        Task {
            await loadMedications()
            isLoadingMedications = false
        }
    }

    private func loadMedications(forceRefresh: Bool = false) async {
        guard let firstPet = pets.first else { return }
        let familyId = firstPet.familyId

        do {
            let loaded = try await dataService.getMedications(
                for: familyId,
                petId: selectedPet?.id,
                includeArchived: true,
                forceRefresh: forceRefresh
            )

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
                    Text(medication.name)
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
