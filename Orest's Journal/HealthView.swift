//
//  HealthView.swift
//  Orest's Journal
//
//  Main health events tab view with search, filtering, and event list.
//

import SwiftUI

// MARK: - Health Navigation

enum HealthDestination: Hashable {
    case eventDetail(HealthEventWithCategory)
}

// MARK: - Health View

struct HealthView: View {
    @State private var pets: [Pet] = []
    @State private var selectedPet: Pet?
    @State private var events: [HealthEventWithCategory] = []
    @State private var categories: [HealthCategory] = []
    @State private var selectedCategory: HealthCategory?
    @State private var isLoading = true
    @State private var isLoadingEvents = false
    @State private var isRefreshing = false
    @State private var showAddEvent = false
    @State private var searchText = ""
    @State private var showError = false
    @State private var errorMessage = ""
    @State private var navigationPath = NavigationPath()
    @State private var showSmartSearch = false
    @State private var showPetPickerForAdd = false
    @State private var loadEventsTask: Task<Void, Never>?  // Track current loading task for cancellation

    // Cached computed results for performance
    @State private var cachedFilteredEvents: [HealthEventWithCategory] = []
    @State private var cachedGroupedEvents: [DateSection: [HealthEventWithCategory]] = [:]

    @AppStorage("health_selected_pet_id") private var savedPetId: String = ""

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
            .navigationTitle("Journal")
            .toolbar {
                if !pets.isEmpty {
                    ToolbarItem(placement: .topBarTrailing) {
                        Button {
                            if selectedPet != nil {
                                showAddEvent = true
                            } else {
                                // In "All" mode, default to first pet
                                showPetPickerForAdd = true
                            }
                        } label: {
                            Image(systemName: "plus")
                        }
                        .accessibilityIdentifier(AccessibilityIdentifier.addHealthEventButton)
                        .accessibilityLabel("Add journal entry")
                    }
                }
            }
            .navigationDestination(for: HealthDestination.self) { destination in
                switch destination {
                case .eventDetail(let event):
                    if let pet = petForEvent(event) {
                        HealthEventDetailView(
                            event: event,
                            pet: pet,
                            onUpdate: { updatedEvent in
                                updateEventInList(updatedEvent)
                            },
                            onDelete: {
                                removeEventFromList(event.id)
                            }
                        )
                    } else {
                        // Fallback view when pet data is unavailable
                        ContentUnavailableView(
                            "Pet Not Found",
                            systemImage: "exclamationmark.triangle",
                            description: Text("Unable to load pet information for this event.")
                        )
                    }
                }
            }
            .sheet(isPresented: $showAddEvent) {
                if let pet = selectedPet {
                    AddHealthEventView(pet: pet) { newEvent in
                        Task {
                            await loadEvents(forceRefresh: true)
                        }
                    }
                }
            }
            .sheet(isPresented: $showSmartSearch) {
                if !pets.isEmpty {
                    SmartSearchView(
                        pets: pets,
                        onEventUpdated: { updatedEvent in
                            updateEventInList(updatedEvent)
                        },
                        onEventDeleted: { eventId in
                            removeEventFromList(eventId)
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
                        showAddEvent = true
                    }
                }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("Which pet is this journal entry for?")
            }
            .task {
                await loadInitialData()
            }
            .onChange(of: navigationManager.tabsNeedingRefresh) { _, newValue in
                if newValue.contains(.health) {
                    navigationManager.markTabRefreshed(.health)
                    Task {
                        await loadInitialData()
                    }
                }
            }
            .alert("Error", isPresented: $showError) {
                Button("OK") {}
            } message: {
                Text(errorMessage)
            }
            .onChange(of: events) { _, _ in
                updateCachedEvents()
            }
            .onChange(of: selectedCategory) { _, _ in
                updateCachedEvents()
            }
            .onChange(of: searchText) { _, _ in
                updateCachedEvents()
            }
        }
        .accessibilityIdentifier(AccessibilityIdentifier.healthEventsList)
    }

    // MARK: - Main Content

    private var mainContent: some View {
        ScrollView {
            VStack(spacing: 0) {
                // Pet selector if multiple pets
                if pets.count > 1 {
                    petSelector
                }

                // Search bar
                searchBar

                // Category filter
                if !categories.isEmpty && !isLoadingEvents {
                    categoryFilter
                }

                // Events content
                if isLoadingEvents {
                    ProgressView()
                        .frame(maxWidth: .infinity, minHeight: 200)
                } else if filteredEvents.isEmpty {
                    emptyEventsView
                } else {
                    eventsContent
                }
            }
        }
        .refreshable {
            await loadEvents(forceRefresh: true)
        }
        .scrollDismissesKeyboard(.interactively)
        .onTapGesture {
            UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder), to: nil, from: nil, for: nil)
        }
    }

    // MARK: - Pet Selector

    private var petSelector: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 12) {
                // "All" option - only show when multiple pets
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
                        .foregroundStyle(selectedPet == nil ? Color.accentColor : Color.primary)
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
                        .foregroundStyle(selectedPet?.id == pet.id ? Color.accentColor : Color.primary)
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
            .foregroundStyle(.secondary)
            .frame(width: 28, height: 28)
            .background(Color(uiColor: .tertiarySystemGroupedBackground))
            .clipShape(Circle())
    }

    // MARK: - Search Bar

    private var searchBar: some View {
        HStack(spacing: 12) {
            HStack {
                Image(systemName: "magnifyingglass")
                    .foregroundStyle(.secondary)
                TextField("Search journal entries", text: $searchText)
                    .textFieldStyle(.plain)
                    .accessibilityIdentifier(AccessibilityIdentifier.healthSearchField)
                if !searchText.isEmpty {
                    Button {
                        searchText = ""
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundStyle(.secondary)
                    }
                    .accessibilityLabel("Clear search")
                }
            }
            .padding(10)
            .background(Color(uiColor: .secondarySystemGroupedBackground))
            .clipShape(RoundedRectangle(cornerRadius: 10))

            // Smart search button
            Button {
                showSmartSearch = true
            } label: {
                Image(systemName: "sparkles")
                    .font(.system(size: 18))
                    .foregroundStyle(Color.accentColor)
                    .frame(width: 40, height: 40)
                    .background(Color(uiColor: .secondarySystemGroupedBackground))
                    .clipShape(RoundedRectangle(cornerRadius: 10))
            }
            .accessibilityIdentifier(AccessibilityIdentifier.smartSearchButton)
            .accessibilityLabel("Smart search")
            .accessibilityHint("Search with natural language")
        }
        .padding(.horizontal)
        .padding(.bottom, 8)
    }

    // MARK: - Category Filter

    private var categoryFilter: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                // All categories chip
                Button {
                    selectedCategory = nil
                } label: {
                    Text("All")
                        .font(.subheadline)
                        .padding(.horizontal, 14)
                        .padding(.vertical, 6)
                        .background(
                            selectedCategory == nil
                                ? Color.accentColor
                                : Color(uiColor: .secondarySystemGroupedBackground)
                        )
                        .foregroundStyle(selectedCategory == nil ? .white : .primary)
                        .clipShape(Capsule())
                }
                .buttonStyle(.plain)
                .accessibilityLabel("All categories")
                .accessibilityHint("Double-tap to show all entries")
                .accessibilityAddTraits(selectedCategory == nil ? .isSelected : [])

                ForEach(categories) { category in
                    Button {
                        selectedCategory = category
                    } label: {
                        Text(category.name)
                            .font(.subheadline)
                            .padding(.horizontal, 14)
                            .padding(.vertical, 6)
                            .background(
                                selectedCategory?.id == category.id
                                    ? Color.accentColor
                                    : Color(uiColor: .secondarySystemGroupedBackground)
                            )
                            .foregroundStyle(selectedCategory?.id == category.id ? .white : .primary)
                            .clipShape(Capsule())
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Filter by \(category.name)")
                    .accessibilityHint("Double-tap to show only \(category.name) events")
                    .accessibilityAddTraits(selectedCategory?.id == category.id ? .isSelected : [])
                }
            }
            .padding(.horizontal)
            .padding(.bottom, 12)
        }
    }

    // MARK: - Events Content

    private var eventsContent: some View {
        LazyVStack(spacing: 0, pinnedViews: [.sectionHeaders]) {
            ForEach(groupedEvents.keys.sorted().reversed(), id: \.self) { section in
                Section {
                    ForEach(groupedEvents[section] ?? []) { eventWithCategory in
                        Button {
                            navigationPath.append(HealthDestination.eventDetail(eventWithCategory))
                        } label: {
                            HealthEventRow(
                                event: eventWithCategory,
                                petName: selectedPet == nil ? petName(for: eventWithCategory) : nil
                            )
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel("\(eventWithCategory.category.name) on \(Formatters.shortDate.string(from: eventWithCategory.event.occurredAt))")
                        .accessibilityHint("Double tap to view details")
                    }
                } header: {
                    HStack {
                        Text(sectionTitle(for: section))
                            .font(.subheadline)
                            .fontWeight(.semibold)
                            .foregroundStyle(.secondary)
                        Spacer()
                    }
                    .padding(.horizontal)
                    .padding(.vertical, 8)
                    .background(Color(uiColor: .systemGroupedBackground))
                }
            }
        }
        .padding(.bottom, 20)
    }

    private func petName(for event: HealthEventWithCategory) -> String? {
        guard let petId = event.event.petId else { return nil }
        return pets.first { $0.id == petId }?.name
    }

    private func petForEvent(_ event: HealthEventWithCategory) -> Pet? {
        // If a specific pet is selected, use that
        if let pet = selectedPet {
            return pet
        }
        // Otherwise look up pet from the event's petId
        guard let petId = event.event.petId else { return nil }
        return pets.first { $0.id == petId }
    }

    // MARK: - Empty Views

    private var emptyPetsView: some View {
        VStack(spacing: 16) {
            Image(systemName: "pawprint")
                .font(.system(size: 48))
                .foregroundStyle(.secondary)
            Text("No Pets")
                .font(.title2)
                .fontWeight(.semibold)
            Text("Add a pet to start journaling their behavior")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    /// Check if we're actively filtering/searching
    private var isFiltering: Bool {
        !searchText.isEmpty || selectedCategory != nil
    }

    private var emptyEventsView: some View {
        VStack(spacing: 16) {
            if isFiltering {
                // No results matching filter/search criteria
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 48))
                    .foregroundStyle(.secondary)
                Text("No Matching Entries")
                    .font(.title2)
                    .fontWeight(.semibold)
                Text("No entries match your search criteria")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)

                Button {
                    // Clear filters
                    searchText = ""
                    selectedCategory = nil
                } label: {
                    Text("Clear Filters")
                        .font(.headline)
                        .padding(.horizontal, 20)
                        .padding(.vertical, 12)
                        .background(Color.accentColor)
                        .foregroundStyle(.white)
                        .clipShape(Capsule())
                }
                .padding(.top, 8)
            } else {
                // Truly no events
                Image(systemName: "book.closed")
                    .font(.system(size: 48))
                    .foregroundStyle(.secondary)
                Text("No Entries Yet")
                    .font(.title2)
                    .fontWeight(.semibold)
                Text("Start tracking behavior, symptoms, or anything you want to remember for vet visits")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal)

                Button {
                    if selectedPet != nil {
                        showAddEvent = true
                    } else {
                        // In "All" mode, show pet picker first
                        showPetPickerForAdd = true
                    }
                } label: {
                    Label("Add Entry", systemImage: "plus")
                        .font(.headline)
                        .padding(.horizontal, 20)
                        .padding(.vertical, 12)
                        .background(Color.accentColor)
                        .foregroundStyle(.white)
                        .clipShape(Capsule())
                }
                .padding(.top, 8)
            }
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Computed Properties (cached for performance)

    private var filteredEvents: [HealthEventWithCategory] {
        cachedFilteredEvents
    }

    private var groupedEvents: [DateSection: [HealthEventWithCategory]] {
        cachedGroupedEvents
    }

    /// Updates cached filtered and grouped events when dependencies change
    private func updateCachedEvents() {
        var result = events

        // Filter by category
        if let category = selectedCategory {
            result = result.filter { $0.category.id == category.id }
        }

        // Filter by search text
        if !searchText.isEmpty {
            let query = searchText.lowercased()
            result = result.filter { event in
                event.category.name.lowercased().contains(query) ||
                (event.event.notes?.lowercased().contains(query) ?? false)
            }
        }

        cachedFilteredEvents = result
        cachedGroupedEvents = Dictionary(grouping: result) { event in
            dateSection(for: event.event.occurredAt)
        }
    }

    // MARK: - Date Helpers

    private enum DateSection: Int, Comparable {
        case today = 0
        case yesterday = 1
        case thisWeek = 2
        case thisMonth = 3
        case earlier = 4

        static func < (lhs: DateSection, rhs: DateSection) -> Bool {
            lhs.rawValue < rhs.rawValue
        }
    }

    private func dateSection(for date: Date) -> DateSection {
        let calendar = Calendar.current
        if calendar.isDateInToday(date) {
            return .today
        } else if calendar.isDateInYesterday(date) {
            return .yesterday
        } else if calendar.isDate(date, equalTo: Date(), toGranularity: .weekOfYear) {
            return .thisWeek
        } else if calendar.isDate(date, equalTo: Date(), toGranularity: .month) {
            return .thisMonth
        } else {
            return .earlier
        }
    }

    private func sectionTitle(for section: DateSection) -> String {
        switch section {
        case .today: return "Today"
        case .yesterday: return "Yesterday"
        case .thisWeek: return "This Week"
        case .thisMonth: return "This Month"
        case .earlier: return "Earlier"
        }
    }

    // MARK: - Data Loading

    private func loadInitialData() async {
        do {
            // Force refresh pets on initial load to avoid stale cache issues
            pets = try await dataService.getPets(forceRefresh: true)

            // Check for cancellation before updating state
            guard !Task.isCancelled else { return }

            // Restore saved pet selection
            if let savedId = UUID(uuidString: savedPetId),
               let savedPet = pets.first(where: { $0.id == savedId }) {
                // Restore previously selected pet
                selectedPet = savedPet
                await loadEventsAndCategories(for: savedPet)
            } else if savedPetId.isEmpty && pets.count > 1 {
                // Empty savedPetId with multiple pets means "All" was selected
                selectedPet = nil
                await loadAllPetsEventsAndCategories()
            } else if let firstPet = pets.first {
                // Default to first pet (single pet, or saved pet not found)
                selectedPet = firstPet
                savedPetId = firstPet.id.uuidString
                await loadEventsAndCategories(for: firstPet)
            }
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

        // Cancel any in-flight loading task to prevent race conditions
        loadEventsTask?.cancel()

        selectedPet = pet
        savedPetId = pet?.id.uuidString ?? ""
        events = []
        categories = []
        selectedCategory = nil
        isLoadingEvents = true

        // Capture the selected pet ID to verify it hasn't changed when results arrive
        let expectedPetId = pet?.id

        loadEventsTask = Task {
            if let pet = pet {
                await loadEventsAndCategories(for: pet)
            } else {
                // "All" selected - load events for all pets
                await loadAllPetsEventsAndCategories()
            }

            // Only update loading state if this is still the active request
            if !Task.isCancelled && selectedPet?.id == expectedPetId {
                isLoadingEvents = false
            }
        }
    }

    private func loadEventsAndCategories(for pet: Pet) async {
        do {
            async let eventsTask = dataService.getHealthEvents(for: pet.id)
            async let categoriesTask = dataService.getHealthCategories(for: pet.id)

            let (loadedEvents, loadedCategories) = try await (eventsTask, categoriesTask)

            // Only update state if task wasn't cancelled
            guard !Task.isCancelled else { return }

            events = loadedEvents
            categories = loadedCategories
        } catch {
            guard !Task.isCancelled else { return }
            errorMessage = error.localizedDescription
            showError = true
        }
    }

    private func loadAllPetsEventsAndCategories() async {
        do {
            // Fetch categories once (they're family-wide) using any pet's ID
            let categoriesTask = Task {
                guard let firstPet = pets.first else { return [HealthCategory]() }
                return try await dataService.getHealthCategories(for: firstPet.id)
            }

            // Parallel fetch events for all pets using TaskGroup
            let eventsResults = try await withThrowingTaskGroup(
                of: (petId: UUID, events: [HealthEventWithCategory]).self
            ) { group in
                for pet in pets {
                    group.addTask {
                        let petEvents = try await self.dataService.getHealthEvents(for: pet.id)
                        return (petId: pet.id, events: petEvents)
                    }
                }

                var allResults: [(petId: UUID, events: [HealthEventWithCategory])] = []
                for try await result in group {
                    allResults.append(result)
                }
                return allResults
            }

            // Aggregate events from all pets
            var allEvents: [HealthEventWithCategory] = []
            for result in eventsResults {
                allEvents.append(contentsOf: result.events)
            }

            // Get categories result (already deduplicated since fetched once)
            let loadedCategories = try await categoriesTask.value

            // Only update state if task wasn't cancelled
            guard !Task.isCancelled else { return }

            // Sort all events by date descending
            events = allEvents.sorted { $0.event.occurredAt > $1.event.occurredAt }
            categories = loadedCategories.sorted { $0.name < $1.name }
        } catch {
            guard !Task.isCancelled else { return }
            errorMessage = error.localizedDescription
            showError = true
        }
    }

    private func loadEvents(forceRefresh: Bool = false) async {
        isRefreshing = true
        do {
            if let pet = selectedPet {
                events = try await dataService.getHealthEvents(for: pet.id, forceRefresh: forceRefresh)
                categories = try await dataService.getHealthCategories(for: pet.id, forceRefresh: forceRefresh)
            } else {
                // "All" selected - reload all pets' events
                await loadAllPetsEventsAndCategories()
            }
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
        isRefreshing = false
    }

    private func updateEventInList(_ updatedEvent: HealthEventWithCategory) {
        if let index = events.firstIndex(where: { $0.id == updatedEvent.id }) {
            events[index] = updatedEvent
        }
    }

    private func removeEventFromList(_ eventId: UUID) {
        events.removeAll { $0.id == eventId }
    }
}

// MARK: - Health Event Row

struct HealthEventRow: View {
    let event: HealthEventWithCategory
    var petName: String?

    var body: some View {
        HStack(spacing: 12) {
            // Category icon
            categoryIcon
                .frame(width: 40, height: 40)
                .background(event.category.color.opacity(0.15))
                .clipShape(Circle())

            // Event details
            VStack(alignment: .leading, spacing: 4) {
                Text(event.category.name)
                    .font(.headline)
                    .lineLimit(1)

                // Pet name when showing all pets
                if let petName = petName {
                    Text(petName)
                        .font(.subheadline)
                        .foregroundStyle(Color.accentColor)
                }

                HStack(spacing: 4) {
                    Text(Formatters.shortDate.string(from: event.event.occurredAt))
                        .font(.subheadline)
                        .foregroundStyle(.secondary)

                    if let notes = event.event.notes, !notes.isEmpty {
                        Text("·")
                            .foregroundStyle(.secondary)
                        Text(notes)
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                            .lineLimit(1)
                    }
                }
            }

            Spacer()

            // Photo thumbnail if present (show first photo)
            if let firstPhoto = event.event.photos.first, let url = URL(string: firstPhoto.photoUrl) {
                ZStack(alignment: .bottomTrailing) {
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

                    // Photo count badge if more than 1
                    if event.event.photos.count > 1 {
                        Text("\(event.event.photos.count)")
                            .font(.caption2.weight(.semibold))
                            .foregroundStyle(.white)
                            .padding(.horizontal, 4)
                            .padding(.vertical, 2)
                            .background(Color.black.opacity(0.6))
                            .clipShape(RoundedRectangle(cornerRadius: 4))
                            .offset(x: 2, y: 2)
                    }
                }
                .accessibilityLabel("\(event.event.photos.count) photo\(event.event.photos.count == 1 ? "" : "s")")
            }

            Image(systemName: "chevron.right")
                .font(.system(size: 14, weight: .semibold))
                .foregroundStyle(Color(uiColor: .tertiaryLabel))
        }
        .padding(.horizontal)
        .padding(.vertical, 12)
        .background(Color(uiColor: .secondarySystemGroupedBackground))
    }

    private var categoryIcon: some View {
        Image(systemName: event.category.icon)
            .font(.system(size: 18))
            .foregroundStyle(event.category.color)
    }
}

// MARK: - Preview

#Preview {
    HealthView()
}
