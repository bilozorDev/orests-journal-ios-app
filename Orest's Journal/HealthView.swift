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
    @State private var eventPetMap: [UUID: UUID] = [:]  // Maps event ID to pet ID for "All" view

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
            .navigationTitle("Health")
            .toolbar {
                if !pets.isEmpty {
                    ToolbarItem(placement: .topBarTrailing) {
                        Button {
                            showAddEvent = true
                        } label: {
                            Image(systemName: "plus")
                        }
                        .accessibilityIdentifier(AccessibilityIdentifier.addHealthEventButton)
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
                        .foregroundColor(selectedPet == nil ? .accentColor : .primary)
                        .clipShape(Capsule())
                    }
                    .buttonStyle(.plain)
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

    // MARK: - Search Bar

    private var searchBar: some View {
        HStack(spacing: 12) {
            HStack {
                Image(systemName: "magnifyingglass")
                    .foregroundColor(.secondary)
                TextField("Search health events", text: $searchText)
                    .textFieldStyle(.plain)
                    .accessibilityIdentifier(AccessibilityIdentifier.healthSearchField)
                if !searchText.isEmpty {
                    Button {
                        searchText = ""
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundColor(.secondary)
                    }
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
                    .foregroundColor(.accentColor)
                    .frame(width: 40, height: 40)
                    .background(Color(uiColor: .secondarySystemGroupedBackground))
                    .clipShape(RoundedRectangle(cornerRadius: 10))
            }
            .accessibilityIdentifier(AccessibilityIdentifier.smartSearchButton)
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
                        .foregroundColor(selectedCategory == nil ? .white : .primary)
                        .clipShape(Capsule())
                }
                .buttonStyle(.plain)

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
                            .foregroundColor(selectedCategory?.id == category.id ? .white : .primary)
                            .clipShape(Capsule())
                    }
                    .buttonStyle(.plain)
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
                        HealthEventRow(
                            event: eventWithCategory,
                            petName: selectedPet == nil ? petName(for: eventWithCategory) : nil
                        )
                        .contentShape(Rectangle())
                        .onTapGesture {
                            navigationPath.append(HealthDestination.eventDetail(eventWithCategory))
                        }
                    }
                } header: {
                    HStack {
                        Text(sectionTitle(for: section))
                            .font(.subheadline)
                            .fontWeight(.semibold)
                            .foregroundColor(.secondary)
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
                .foregroundColor(.secondary)
            Text("No Pets")
                .font(.title2)
                .fontWeight(.semibold)
            Text("Add a pet to start tracking health events")
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var emptyEventsView: some View {
        VStack(spacing: 16) {
            Image(systemName: "heart.text.square")
                .font(.system(size: 48))
                .foregroundColor(.secondary)
            Text("No Health Events")
                .font(.title2)
                .fontWeight(.semibold)
            Text("Tap + to record a health event")
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)

            Button {
                showAddEvent = true
            } label: {
                Label("Add Health Event", systemImage: "plus")
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

    private var filteredEvents: [HealthEventWithCategory] {
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

        return result
    }

    private var groupedEvents: [DateSection: [HealthEventWithCategory]] {
        Dictionary(grouping: filteredEvents) { event in
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
            errorMessage = error.localizedDescription
            showError = true
        }
        isLoading = false
    }

    private func selectPet(_ pet: Pet?) {
        guard pet?.id != selectedPet?.id else { return }
        selectedPet = pet
        savedPetId = pet?.id.uuidString ?? ""
        events = []
        categories = []
        selectedCategory = nil
        isLoadingEvents = true
        Task {
            if let pet = pet {
                await loadEventsAndCategories(for: pet)
            } else {
                // "All" selected - load events for all pets
                await loadAllPetsEventsAndCategories()
            }
            isLoadingEvents = false
        }
    }

    private func loadEventsAndCategories(for pet: Pet) async {
        do {
            async let eventsTask = dataService.getHealthEvents(for: pet.id)
            async let categoriesTask = dataService.getHealthCategories(for: pet.id)

            let (loadedEvents, loadedCategories) = try await (eventsTask, categoriesTask)
            events = loadedEvents
            categories = loadedCategories
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
    }

    private func loadAllPetsEventsAndCategories() async {
        do {
            var allEvents: [HealthEventWithCategory] = []
            var allCategories: [HealthCategory] = []
            var seenCategoryIds = Set<UUID>()
            var newEventPetMap: [UUID: UUID] = [:]

            for pet in pets {
                let petEvents = try await dataService.getHealthEvents(for: pet.id)
                let petCategories = try await dataService.getHealthCategories(for: pet.id)

                // Track which pet each event belongs to
                for event in petEvents {
                    newEventPetMap[event.id] = pet.id
                }
                allEvents.append(contentsOf: petEvents)

                // Deduplicate categories (they're family-wide but fetched per-pet)
                for category in petCategories {
                    if !seenCategoryIds.contains(category.id) {
                        seenCategoryIds.insert(category.id)
                        allCategories.append(category)
                    }
                }
            }

            // Sort all events by date descending
            events = allEvents.sorted { $0.event.occurredAt > $1.event.occurredAt }
            categories = allCategories.sorted { $0.name < $1.name }
            eventPetMap = newEventPetMap
        } catch {
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
                .background(categoryColor.opacity(0.15))
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
                        .foregroundColor(.accentColor)
                }

                HStack(spacing: 4) {
                    Text(Formatters.shortDate.string(from: event.event.occurredAt))
                        .font(.subheadline)
                        .foregroundColor(.secondary)

                    if let notes = event.event.notes, !notes.isEmpty {
                        Text("·")
                            .foregroundColor(.secondary)
                        Text(notes)
                            .font(.subheadline)
                            .foregroundColor(.secondary)
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
                            .foregroundColor(.white)
                            .padding(.horizontal, 4)
                            .padding(.vertical, 2)
                            .background(Color.black.opacity(0.6))
                            .clipShape(RoundedRectangle(cornerRadius: 4))
                            .offset(x: 2, y: 2)
                    }
                }
            }

            Image(systemName: "chevron.right")
                .font(.system(size: 14, weight: .semibold))
                .foregroundColor(Color(uiColor: .tertiaryLabel))
        }
        .padding(.horizontal)
        .padding(.vertical, 12)
        .background(Color(uiColor: .secondarySystemGroupedBackground))
    }

    private var categoryIcon: some View {
        Image(systemName: iconName(for: event.category.nameNormalized))
            .font(.system(size: 18))
            .foregroundColor(categoryColor)
    }

    private var categoryColor: Color {
        // Hash category name to get consistent color
        let hash = event.category.nameNormalized.hashValue
        let colors: [Color] = [.red, .orange, .yellow, .green, .blue, .purple, .pink]
        return colors[abs(hash) % colors.count]
    }

    private func iconName(for category: String) -> String {
        // Common health event types with appropriate icons
        switch category {
        case "vet visit", "vet", "veterinary":
            return "stethoscope"
        case "vaccination", "vaccine", "shot":
            return "syringe"
        case "medication", "medicine":
            return "pills"
        case "surgery", "operation":
            return "scissors"
        case "blood work", "blood test", "lab work":
            return "drop"
        case "weight", "weigh-in":
            return "scalemass"
        case "dental", "teeth", "dental cleaning":
            return "mouth"
        case "grooming", "bath":
            return "scissors.badge.ellipsis"
        case "allergy", "allergic reaction":
            return "exclamationmark.triangle"
        case "injury", "wound", "hurt":
            return "bandage"
        case "vomiting", "sick", "illness":
            return "facemask"
        case "diarrhea", "digestive":
            return "stomach"
        default:
            return "heart.text.square"
        }
    }
}

// MARK: - Preview

#Preview {
    HealthView()
}
