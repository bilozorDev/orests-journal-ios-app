//
//  SmartSearchView.swift
//  Orest's Journal
//
//  Smart search view with Apple Intelligence support (iOS 18.1+) and keyword fallback.
//

import SwiftUI
import FoundationModels
import os.log

private let logger = Logger(subsystem: Bundle.main.bundleIdentifier ?? "com.orests-journal", category: "SmartSearch")

// MARK: - LLM Query Schema (iOS 26+)

/// Structured query representation for LLM-based parsing
@available(iOS 26.0, *)
@Generable
struct ParsedHealthQuery {
    @Guide(description: "The health category being searched for, e.g. 'vomit', 'vet visit', 'vaccination', 'hot spot'. Use lowercase.")
    var category: String?

    @Guide(description: "Number of time units to look back, e.g. 30 for 'last 30 minutes', 6 for 'past 6 months'")
    var timeAmount: Int?

    @Guide(description: "Time unit for timeAmount", .anyOf(["minute", "hour", "day", "week", "month", "year"]))
    var timeUnit: String?

    @Guide(description: "Special time range keyword", .anyOf(["today", "yesterday", "this_week", "this_month", "this_year"]))
    var specialTimeRange: String?

    @Guide(description: "Query intent: 'count' for how many, 'last' for most recent, 'all' for listing all matching")
    var intent: String
}

struct SmartSearchView: View {
    let pets: [Pet]
    var onEventUpdated: ((HealthEventWithCategory) -> Void)?
    var onEventDeleted: ((UUID) -> Void)?

    @Environment(\.dismiss) private var dismiss

    @State private var selectedPet: Pet?
    @State private var query = ""
    @State private var isSearching = false
    @State private var searchResults: [HealthEventWithCategory] = []
    @State private var aiResponse: String?
    @State private var showError = false
    @State private var errorMessage = ""
    @State private var hasSearched = false
    @State private var searchHistory: [SmartSearchHistory] = []
    @State private var navigationPath = NavigationPath()

    private let dataService = DataService.shared
    private let smartSearchManager = SmartSearchManager.shared
    private let authManager = AuthManager.shared

    /// Returns appropriate placeholder text for search field
    private var searchPlaceholderText: String {
        if let pet = selectedPet {
            return "\(pet.name)'s health"
        } else if pets.count > 1 {
            return "your pets' health"
        } else if let first = pets.first {
            return "\(first.name)'s health"
        }
        return "pet health"
    }

    /// Returns the pet name to display for an event (not used in single-pet mode)
    private func petNameForEvent(_ event: HealthEventWithCategory) -> String? {
        // In Smart Search, we always have a selected pet, so no need to show pet name
        return nil
    }

    var body: some View {
        NavigationStack(path: $navigationPath) {
            Group {
                if smartSearchManager.isAvailable {
                    availableContent
                } else {
                    unavailableContent
                }
            }
            .background(Color(uiColor: .systemGroupedBackground))
            .navigationTitle("Smart Search (Beta)")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Done") {
                        dismiss()
                    }
                }
            }
            .navigationDestination(for: HealthDestination.self) { destination in
                switch destination {
                case .eventDetail(let event):
                    if let pet = selectedPet {
                        HealthEventDetailView(
                            event: event,
                            pet: pet,
                            onUpdate: { updatedEvent in
                                updateEventInResults(updatedEvent)
                                onEventUpdated?(updatedEvent)
                            },
                            onDelete: {
                                removeEventFromResults(event.id)
                                onEventDeleted?(event.id)
                            }
                        )
                    } else {
                        // Fallback view when pet is unexpectedly nil
                        ContentUnavailableView(
                            "Pet Not Found",
                            systemImage: "exclamationmark.triangle",
                            description: Text("Unable to load pet information for this event.")
                        )
                    }
                }
            }
            .task {
                await smartSearchManager.checkAvailability()
                if let familyId = authManager.familyId {
                    searchHistory = smartSearchManager.loadSearchHistory(for: familyId)
                }
                // Always default to first pet (no "All" option in Smart Search)
                if selectedPet == nil {
                    selectedPet = pets.first
                }
            }
        }
    }

    // MARK: - Event Updates

    private func updateEventInResults(_ updatedEvent: HealthEventWithCategory) {
        if let index = searchResults.firstIndex(where: { $0.id == updatedEvent.id }) {
            searchResults[index] = updatedEvent
        }
    }

    private func removeEventFromResults(_ eventId: UUID) {
        searchResults.removeAll { $0.id == eventId }
        // Navigate back to search results (guard against empty path)
        if !navigationPath.isEmpty {
            navigationPath.removeLast()
        }
    }

    // MARK: - Available Content (AI is available)

    private var availableContent: some View {
        VStack(spacing: 0) {
            // Pet selector (only show if multiple pets)
            if pets.count > 1 {
                petSelector
            }

            // Explanation text
            explanationBanner

            // Search input
            searchInput

            // Results
            resultsContent
        }
    }

    // MARK: - Pet Selector

    private var petSelector: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
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
                                    Image(systemName: "pawprint.fill")
                                        .foregroundStyle(.secondary)
                                }
                                .frame(width: 28, height: 28)
                                .clipShape(Circle())
                            } else {
                                Image(systemName: "pawprint.fill")
                                    .font(.system(size: 14))
                                    .frame(width: 28, height: 28)
                            }
                            Text(pet.name)
                                .font(.subheadline)
                                .fontWeight(selectedPet?.id == pet.id ? .semibold : .regular)
                        }
                        .padding(.horizontal, 12)
                        .padding(.vertical, 8)
                        .background(selectedPet?.id == pet.id ? Color.accentColor.opacity(0.15) : Color(uiColor: .secondarySystemGroupedBackground))
                        .foregroundStyle(selectedPet?.id == pet.id ? .accentColor : .primary)
                        .clipShape(Capsule())
                        .overlay {
                            Capsule()
                                .strokeBorder(selectedPet?.id == pet.id ? Color.accentColor : Color.clear, lineWidth: 2)
                        }
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Select \(pet.name)")
                    .accessibilityAddTraits(selectedPet?.id == pet.id ? .isSelected : [])
                }
            }
            .padding(.horizontal)
            .padding(.vertical, 12)
        }
        .background(Color(uiColor: .secondarySystemGroupedBackground))
    }

    private func selectPet(_ pet: Pet?) {
        selectedPet = pet
        // Clear previous search results when switching pets
        if hasSearched {
            searchResults = []
            aiResponse = nil
            hasSearched = false
        }
    }

    // MARK: - Unavailable Content (No AI)

    private var unavailableContent: some View {
        VStack(spacing: 24) {
            Spacer()

            Image(systemName: "sparkles.slash")
                .font(.system(size: 56))
                .foregroundStyle(.secondary)

            VStack(spacing: 8) {
                Text("AI Search Unavailable")
                    .font(.title2)
                    .fontWeight(.semibold)

                Text("Smart Search is only available with Apple Intelligence (iPhone 15 Pro or newer, iOS 18.1+).")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 32)
            }

            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Explanation Banner

    private var explanationBanner: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 12) {
                Image(systemName: "sparkles")
                    .font(.title3)
                    .foregroundStyle(.accentColor)

                Text("Ask questions in natural language, like \"how many vet visits this year?\"")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            Text("AI can make mistakes. Verify important information.")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.accentColor.opacity(0.08))
    }

    // MARK: - Search Input

    private var searchInput: some View {
        VStack(spacing: 12) {
            HStack {
                Image(systemName: "sparkles")
                    .foregroundStyle(.accentColor)

                TextField("Ask about \(searchPlaceholderText)...", text: $query)
                    .textFieldStyle(.plain)
                    .submitLabel(.search)
                    .onSubmit {
                        Task {
                            await performSearch()
                        }
                    }

                if !query.isEmpty {
                    Button {
                        query = ""
                        searchResults = []
                        aiResponse = nil
                        hasSearched = false
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundStyle(.secondary)
                    }
                    .accessibilityLabel("Clear search")
                }
            }
            .padding(12)
            .background(Color(uiColor: .secondarySystemGroupedBackground))
            .clipShape(RoundedRectangle(cornerRadius: 10))

            // Search history
            if !searchHistory.isEmpty && !hasSearched {
                searchHistorySection
            }

            // Example queries
            if !hasSearched {
                exampleQueries
            }
        }
        .padding()
    }

    // MARK: - Search History Section

    private var searchHistorySection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Recent Searches")
                .font(.caption)
                .foregroundStyle(.secondary)

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(searchHistory) { item in
                        Button {
                            query = item.query
                            Task {
                                await performSearch()
                            }
                        } label: {
                            Text(item.query)
                                .font(.caption)
                                .lineLimit(1)
                                .padding(.horizontal, 12)
                                .padding(.vertical, 6)
                                .background(Color(uiColor: .secondarySystemGroupedBackground))
                                .foregroundStyle(.primary)
                                .clipShape(Capsule())
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
        }
    }

    private var exampleQueries: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Try asking:")
                .font(.caption)
                .foregroundStyle(.secondary)

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(exampleQueryList, id: \.self) { example in
                        Button {
                            query = example
                            Task {
                                await performSearch()
                            }
                        } label: {
                            Text(example)
                                .font(.caption)
                                .padding(.horizontal, 12)
                                .padding(.vertical, 6)
                                .background(Color.accentColor.opacity(0.1))
                                .foregroundStyle(.accentColor)
                                .clipShape(Capsule())
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
        }
    }

    private var exampleQueryList: [String] {
        [
            "How many vet visits this year?",
            "When was the last vaccination?",
            "Any health issues last month?",
            "Show all blood work results"
        ]
    }

    // MARK: - Results Content

    private var resultsContent: some View {
        Group {
            if isSearching {
                VStack(spacing: 16) {
                    ProgressView()
                    Text("Searching...")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if !hasSearched {
                emptyState
            } else if let response = aiResponse {
                aiResponseView(response: response)
            } else if searchResults.isEmpty {
                noResultsView
            } else {
                resultsList
            }
        }
    }

    private var emptyState: some View {
        VStack(spacing: 16) {
            Image(systemName: "sparkles")
                .font(.system(size: 48))
                .foregroundStyle(.secondary)

            Text("Ask anything about \(searchPlaceholderText)")
                .font(.headline)

            Text("Use natural language to search and get insights")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func aiResponseView(response: String) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                // AI Response card
                VStack(alignment: .leading, spacing: 12) {
                    HStack {
                        Image(systemName: "sparkles")
                            .foregroundStyle(.accentColor)
                        Text("Answer")
                            .font(.headline)
                        Spacer()
                    }

                    Text(response)
                        .font(.body)
                }
                .padding()
                .background(Color(uiColor: .secondarySystemGroupedBackground))
                .clipShape(RoundedRectangle(cornerRadius: 12))

                // Related events
                if !searchResults.isEmpty {
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Related Events")
                            .font(.headline)

                        VStack(spacing: 8) {
                            ForEach(searchResults) { event in
                                Button {
                                    navigationPath.append(HealthDestination.eventDetail(event))
                                } label: {
                                    SmartSearchResultRow(event: event, petName: petNameForEvent(event))
                                }
                                .buttonStyle(.plain)
                                .accessibilityLabel("\(event.category.name) on \(Formatters.shortDate.string(from: event.event.occurredAt))")
                                .accessibilityHint("Double tap to view details")
                            }
                        }
                    }
                }
            }
            .padding()
        }
    }

    private var noResultsView: some View {
        VStack(spacing: 16) {
            Image(systemName: "magnifyingglass")
                .font(.system(size: 48))
                .foregroundStyle(.secondary)

            Text("No Results")
                .font(.headline)

            Text("Try a different search term")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var resultsList: some View {
        ScrollView {
            LazyVStack(spacing: 8) {
                ForEach(searchResults) { event in
                    Button {
                        navigationPath.append(HealthDestination.eventDetail(event))
                    } label: {
                        SmartSearchResultRow(event: event, petName: petNameForEvent(event))
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("\(event.category.name) on \(Formatters.shortDate.string(from: event.event.occurredAt))")
                    .accessibilityHint("Double tap to view details")
                }
            }
            .padding()
        }
    }

    // MARK: - Search

    private func performSearch() async {
        let trimmedQuery = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedQuery.isEmpty else { return }
        guard let pet = selectedPet else { return }

        isSearching = true
        hasSearched = true
        aiResponse = nil
        searchResults = []

        // Use smart search with LLM parsing (iOS 26+) or regex fallback
        let (response, relevantEvents) = await smartSearchManager.search(
            query: trimmedQuery,
            petId: pet.id,
            petName: pet.name,
            dataService: dataService
        )
        aiResponse = response
        searchResults = relevantEvents

        // Save to search history
        if let familyId = authManager.familyId {
            smartSearchManager.saveSearch(trimmedQuery, familyId: familyId)
            searchHistory = smartSearchManager.loadSearchHistory(for: familyId)
        }

        isSearching = false
    }
}

// MARK: - Smart Search Result Row

struct SmartSearchResultRow: View {
    let event: HealthEventWithCategory
    var petName: String?

    var body: some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                Text(event.category.name)
                    .font(.headline)

                // Pet name when showing all pets
                if let petName = petName {
                    Text(petName)
                        .font(.subheadline)
                        .foregroundStyle(.accentColor)
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

            if !event.event.photos.isEmpty {
                HStack(spacing: 2) {
                    Image(systemName: "photo")
                        .foregroundStyle(.secondary)
                    if event.event.photos.count > 1 {
                        Text("\(event.event.photos.count)")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }
            }

            Image(systemName: "chevron.right")
                .font(.system(size: 14, weight: .semibold))
                .foregroundStyle(Color(uiColor: .tertiaryLabel))
        }
        .padding()
        .background(Color(uiColor: .secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 10))
    }
}

// MARK: - Search History Model

struct SmartSearchHistory: Codable, Identifiable {
    let id: UUID
    let query: String
    let timestamp: Date

    init(query: String) {
        self.id = UUID()
        self.query = query
        self.timestamp = Date()
    }
}

// MARK: - Smart Search Manager

@Observable
class SmartSearchManager {
    static let shared = SmartSearchManager()

    private let maxHistoryCount = 5
    private let historyKeyPrefix = "smart_search_history_"

    enum Availability {
        case available
        case notEnabled
        case deviceNotEligible
        case notReady
    }

    private(set) var availability: Availability = .deviceNotEligible

    var isAvailable: Bool {
        availability == .available
    }

    var unavailableReason: String {
        switch availability {
        case .available:
            return ""
        case .notEnabled:
            return "Enable Apple Intelligence in Settings"
        case .deviceNotEligible:
            return "Requires iPhone 15 Pro or newer"
        case .notReady:
            return "Apple Intelligence is setting up..."
        }
    }

    private init() {}

    // MARK: - Search History

    func loadSearchHistory(for familyId: String) -> [SmartSearchHistory] {
        let key = historyKeyPrefix + familyId
        guard let data = UserDefaults.standard.data(forKey: key) else {
            return []
        }

        do {
            let history = try JSONDecoder().decode([SmartSearchHistory].self, from: data)
            return history
        } catch {
            logger.warning("Failed to decode search history: \(error.localizedDescription, privacy: .public)")
            return []
        }
    }

    func saveSearch(_ query: String, familyId: String) {
        let trimmedQuery = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedQuery.isEmpty else { return }

        var history = loadSearchHistory(for: familyId)

        // Remove duplicate if exists
        history.removeAll { $0.query.lowercased() == trimmedQuery.lowercased() }

        // Add new entry at the beginning
        let newEntry = SmartSearchHistory(query: trimmedQuery)
        history.insert(newEntry, at: 0)

        // Keep only the most recent entries
        if history.count > maxHistoryCount {
            history = Array(history.prefix(maxHistoryCount))
        }

        // Save to UserDefaults
        let key = historyKeyPrefix + familyId
        do {
            let data = try JSONEncoder().encode(history)
            UserDefaults.standard.set(data, forKey: key)
        } catch {
            logger.warning("Failed to encode search history: \(error.localizedDescription, privacy: .public)")
        }
    }

    @MainActor
    func checkAvailability() async {
        // iOS 26+: Use Foundation Models framework for proper availability check
        if #available(iOS 26.0, *) {
            switch SystemLanguageModel.default.availability {
            case .available:
                availability = .available
            case .unavailable(let reason):
                switch reason {
                case .appleIntelligenceNotEnabled:
                    availability = .notEnabled
                case .deviceNotEligible:
                    availability = .deviceNotEligible
                case .modelNotReady:
                    availability = .notReady
                @unknown default:
                    availability = .deviceNotEligible
                }
            @unknown default:
                availability = .deviceNotEligible
            }
        } else if #available(iOS 18.1, *) {
            // iOS 18.1 - 25.x: Apple Intelligence available, use device model check
            if checkDeviceEligibility() {
                availability = .available
            } else {
                availability = .deviceNotEligible
            }
        } else {
            // iOS < 18.1: Apple Intelligence not available
            availability = .deviceNotEligible
        }
    }

    /// Manual device eligibility check for iOS 18.1 - 25.x
    private func checkDeviceEligibility() -> Bool {
        var systemInfo = utsname()
        uname(&systemInfo)
        let modelCode = withUnsafePointer(to: &systemInfo.machine) {
            $0.withMemoryRebound(to: CChar.self, capacity: 1) {
                String(validatingUTF8: $0)
            }
        }

        guard let model = modelCode else { return false }

        // iPhone 15 Pro/Pro Max: iPhone16,1 and iPhone16,2
        // iPhone 16 series: iPhone17,*
        // iPhone 17 series: iPhone18,*
        // Future iPhones: iPhone19,*, iPhone20,*
        // M-series iPads: iPad14,* and newer
        let eligiblePrefixes = [
            "iPhone16,1", "iPhone16,2",
            "iPhone17,", "iPhone18,", "iPhone19,", "iPhone20,",
            "iPad14,", "iPad15,", "iPad16,", "iPad17,", "iPad18,"
        ]

        return eligiblePrefixes.contains { model.hasPrefix($0) }
    }

    // MARK: - LLM Query Parsing (iOS 26+)

    /// Parse a natural language query using on-device LLM
    @available(iOS 26.0, *)
    @MainActor
    func parseQueryWithLLM(_ query: String, petName: String) async throws -> ParsedHealthQuery {
        let session = LanguageModelSession(instructions: """
            You are a query parser for a pet health tracking app. Extract structured data from health queries.

            IMPORTANT RULES:
            1. ALWAYS extract the health category if mentioned (vomit, vet visit, vaccination, hot spot, diarrhea, etc.)
            2. ALWAYS extract time information if mentioned (e.g. "last 30 minutes" = timeAmount:30, timeUnit:"minute")
            3. For "how many" questions, intent is "count"
            4. For "when was the last" questions, intent is "last"
            5. Otherwise, intent is "all"

            Examples:
            Query: "how many times did \(petName) vomit in the last 30 minutes"
            Result: category="vomit", timeAmount=30, timeUnit="minute", intent="count"

            Query: "when was the last vet visit"
            Result: category="vet visit", timeAmount=nil, timeUnit=nil, intent="last"

            Query: "show all vaccinations this year"
            Result: category="vaccination", specialTimeRange="this_year", intent="all"

            Query: "any hot spots today"
            Result: category="hot spot", specialTimeRange="today", intent="all"

            Query: "vomit events from the last 2 hours"
            Result: category="vomit", timeAmount=2, timeUnit="hour", intent="all"
            """)

        let response = try await session.respond(
            to: query,
            generating: ParsedHealthQuery.self
        )

        return response.content
    }

    /// Convert parsed query to a cutoff date for filtering
    func buildTimeFilter(from timeAmount: Int?, timeUnit: String?, specialTimeRange: String?) -> Date? {
        let calendar = Calendar.current
        let now = Date()

        // Handle special time ranges first
        if let special = specialTimeRange {
            switch special {
            case "today":
                return calendar.startOfDay(for: now)
            case "yesterday":
                guard let yesterday = calendar.date(byAdding: .day, value: -1, to: now) else { return nil }
                return calendar.startOfDay(for: yesterday)
            case "this_week":
                return calendar.date(from: calendar.dateComponents([.yearForWeekOfYear, .weekOfYear], from: now))
            case "this_month":
                return calendar.date(from: calendar.dateComponents([.year, .month], from: now))
            case "this_year":
                return calendar.date(from: calendar.dateComponents([.year], from: now))
            default:
                return nil
            }
        }

        // Handle numeric time ranges
        guard let amount = timeAmount, let unit = timeUnit else { return nil }

        let component: Calendar.Component
        switch unit {
        case "minute": component = .minute
        case "hour": component = .hour
        case "day": component = .day
        case "week": component = .weekOfYear
        case "month": component = .month
        case "year": component = .year
        default: return nil
        }

        return calendar.date(byAdding: component, value: -amount, to: now)
    }

    /// Main search method with LLM parsing (iOS 26+) and backend filtering
    /// Falls back to regex + local filtering on older iOS versions
    @MainActor
    func search(
        query: String,
        petId: UUID,
        petName: String,
        dataService: DataService
    ) async -> (response: String?, relevantEvents: [HealthEventWithCategory]) {
        // iOS 26+: Try LLM parsing + backend filtering
        if #available(iOS 26.0, *), availability == .available {
            do {
                let parsed = try await parseQueryWithLLM(query, petName: petName)
                logger.debug("LLM parsed query: category=\(parsed.category ?? "nil", privacy: .public), intent=\(parsed.intent, privacy: .public)")
                return await searchWithParsedQuery(
                    parsed,
                    petId: petId,
                    petName: petName,
                    dataService: dataService
                )
            } catch {
                logger.warning("LLM parsing failed, falling back to regex: \(error.localizedDescription, privacy: .public)")
                // Fall through to regex fallback
            }
        } else {
            logger.info("LLM not available, using regex fallback")
        }

        // Fallback: Load all events and filter locally with regex
        do {
            let allEvents = try await dataService.getHealthEvents(for: petId)
            return await searchWithRegex(query: query, events: allEvents, petName: petName)
        } catch {
            logger.error("Failed to load events for search: \(error.localizedDescription, privacy: .public)")
            return (response: "Failed to search events.", relevantEvents: [])
        }
    }

    /// Process search with LLM-parsed query using backend filtering
    @available(iOS 26.0, *)
    @MainActor
    private func searchWithParsedQuery(
        _ parsed: ParsedHealthQuery,
        petId: UUID,
        petName: String,
        dataService: DataService
    ) async -> (response: String?, relevantEvents: [HealthEventWithCategory]) {
        // Build time filter from parsed query
        let since = buildTimeFilter(
            from: parsed.timeAmount,
            timeUnit: parsed.timeUnit,
            specialTimeRange: parsed.specialTimeRange
        )

        // Fetch filtered events from backend
        logger.debug("Calling backend search with category=\(parsed.category ?? "nil", privacy: .public)")
        do {
            let events = try await dataService.searchHealthEvents(
                for: petId,
                category: parsed.category,
                since: since,
                limit: 100
            )
            logger.debug("Backend returned \(events.count, privacy: .public) events")

            // Generate response based on intent
            let response = generateResponse(
                intent: parsed.intent,
                category: parsed.category,
                events: events,
                petName: petName,
                parsed: parsed
            )

            // For "last" intent, only return the most recent event
            let resultEvents: [HealthEventWithCategory]
            if parsed.intent == "last", let first = events.first {
                resultEvents = [first]
            } else {
                resultEvents = events
            }

            return (response, resultEvents)
        } catch {
            logger.error("Backend search failed: \(error.localizedDescription, privacy: .public)")
            return (response: "Failed to search events.", relevantEvents: [])
        }
    }

    /// Generate natural language response based on search results
    @available(iOS 26.0, *)
    private func generateResponse(
        intent: String,
        category: String?,
        events: [HealthEventWithCategory],
        petName: String,
        parsed: ParsedHealthQuery
    ) -> String {
        let timeRange = formatTimeRange(from: parsed)
        let categoryName = category ?? "health"

        switch intent {
        case "count":
            return "\(petName) had \(events.count) \(categoryName) event\(events.count == 1 ? "" : "s")\(timeRange)."

        case "last":
            if let mostRecent = events.first {
                let dateStr = Formatters.shortDate.string(from: mostRecent.event.occurredAt)
                return "The last \(mostRecent.category.name.lowercased()) was on \(dateStr)."
            } else {
                return "No \(categoryName) events found\(timeRange)."
            }

        default: // "all" or other
            if events.isEmpty {
                return "No \(categoryName) events found\(timeRange)."
            } else {
                return "Found \(events.count) \(categoryName) event\(events.count == 1 ? "" : "s")\(timeRange)."
            }
        }
    }

    /// Format time range for response text from parsed query
    @available(iOS 26.0, *)
    private func formatTimeRange(from parsed: ParsedHealthQuery) -> String {
        if let special = parsed.specialTimeRange {
            switch special {
            case "today": return " today"
            case "yesterday": return " yesterday"
            case "this_week": return " this week"
            case "this_month": return " this month"
            case "this_year": return " this year"
            default: return ""
            }
        }

        if let amount = parsed.timeAmount, let unit = parsed.timeUnit {
            let plural = amount == 1 ? "" : "s"
            return " in the last \(amount) \(unit)\(plural)"
        }

        return ""
    }

    /// Legacy regex-based search for iOS < 26 or as fallback
    @MainActor
    func searchWithRegex(
        query: String,
        events: [HealthEventWithCategory],
        petName: String
    ) async -> (response: String?, relevantEvents: [HealthEventWithCategory]) {
        let lowercaseQuery = query.lowercased()

        // Parse query intent
        var relevantEvents: [HealthEventWithCategory] = []
        var response: String?

        // Count queries
        if lowercaseQuery.contains("how many") || lowercaseQuery.contains("count") {
            let filteredEvents = filterEventsByQuery(events: events, query: lowercaseQuery)
            relevantEvents = filteredEvents

            let timeRange = extractTimeRange(from: lowercaseQuery)
            let categoryName = extractCategory(from: lowercaseQuery)

            if let category = categoryName {
                response = "\(petName) had \(filteredEvents.count) \(category) event\(filteredEvents.count == 1 ? "" : "s")\(timeRange)."
            } else {
                response = "\(petName) had \(filteredEvents.count) health event\(filteredEvents.count == 1 ? "" : "s")\(timeRange)."
            }
        }
        // Last/recent queries
        else if lowercaseQuery.contains("last") || lowercaseQuery.contains("recent") || lowercaseQuery.contains("when was") {
            let filteredEvents = filterEventsByQuery(events: events, query: lowercaseQuery)
            if let mostRecent = filteredEvents.first {
                relevantEvents = [mostRecent]
                let dateStr = Formatters.shortDate.string(from: mostRecent.event.occurredAt)
                response = "The last \(mostRecent.category.name.lowercased()) was on \(dateStr)."
            } else {
                response = "No matching events found."
            }
        }
        // General search
        else {
            relevantEvents = filterEventsByQuery(events: events, query: lowercaseQuery)
            if relevantEvents.isEmpty {
                response = "No health events found matching your search."
            } else {
                response = "Found \(relevantEvents.count) health event\(relevantEvents.count == 1 ? "" : "s") matching your search."
            }
        }

        return (response, relevantEvents)
    }

    private func filterEventsByQuery(events: [HealthEventWithCategory], query: String) -> [HealthEventWithCategory] {
        let calendar = Calendar.current
        let now = Date()

        var filtered = events

        // Time filtering - check specific time ranges first
        if let timeFilter = extractTimeFilter(from: query, calendar: calendar, now: now) {
            filtered = filtered.filter { $0.event.occurredAt >= timeFilter }
        }

        // Extract search terms (excluding stopwords)
        let stopwords = Set(["how", "many", "the", "was", "last", "when", "this", "year", "month", "show", "all", "times", "did", "have", "has", "any", "does"])
        let searchTerms = query.components(separatedBy: .whitespaces)
            .map { $0.lowercased() }
            .filter { $0.count > 2 && !stopwords.contains($0) }

        // If we have search terms, filter by category name or notes
        if !searchTerms.isEmpty {
            filtered = filtered.filter { event in
                let categoryName = event.category.nameNormalized
                let notes = event.event.notes?.lowercased() ?? ""

                return searchTerms.contains { term in
                    // Fuzzy match: check both directions and partial matches
                    fuzzyMatch(term: term, against: categoryName) ||
                    fuzzyMatch(term: term, against: notes)
                }
            }
        }

        return filtered.sorted { $0.event.occurredAt > $1.event.occurredAt }
    }

    /// Fuzzy matching - handles typos and partial matches
    private func fuzzyMatch(term: String, against text: String) -> Bool {
        // Direct contains (either direction)
        if text.contains(term) || term.contains(text) {
            return true
        }

        // Check if term shares significant prefix (handles typos like vomit/vommit)
        let minLength = min(term.count, 4)
        if term.count >= 3 {
            let termPrefix = String(term.prefix(minLength))
            if text.contains(termPrefix) {
                return true
            }
        }

        // Check words in text for partial match
        let words = text.components(separatedBy: .whitespaces)
        for word in words {
            if word.count >= 3 && term.count >= 3 {
                // Check if first 3+ chars match (handles vomit/vommit)
                let wordPrefix = String(word.prefix(min(word.count, 4)))
                let termPrefix = String(term.prefix(min(term.count, 4)))
                if wordPrefix == termPrefix {
                    return true
                }
            }
        }

        return false
    }

    /// Extracts a time filter cutoff date from the query
    private func extractTimeFilter(from query: String, calendar: Calendar, now: Date) -> Date? {
        // Check for "last X minutes/hours/days/weeks/months"
        let patterns: [(regex: String, unit: Calendar.Component)] = [
            (#"last\s+(\d+)\s*min"#, .minute),
            (#"past\s+(\d+)\s*min"#, .minute),
            (#"last\s+(\d+)\s*hour"#, .hour),
            (#"past\s+(\d+)\s*hour"#, .hour),
            (#"last\s+(\d+)\s*day"#, .day),
            (#"past\s+(\d+)\s*day"#, .day),
            (#"last\s+(\d+)\s*week"#, .weekOfYear),
            (#"past\s+(\d+)\s*week"#, .weekOfYear),
            (#"last\s+(\d+)\s*month"#, .month),
            (#"past\s+(\d+)\s*month"#, .month)
        ]

        for (pattern, unit) in patterns {
            if let regex = try? NSRegularExpression(pattern: pattern, options: .caseInsensitive) {
                let range = NSRange(query.startIndex..., in: query)
                if let match = regex.firstMatch(in: query, options: [], range: range),
                   let numberRange = Range(match.range(at: 1), in: query),
                   let number = Int(query[numberRange]) {
                    return calendar.date(byAdding: unit, value: -number, to: now)
                }
            }
        }

        // Fixed time ranges
        if query.contains("today") {
            return calendar.startOfDay(for: now)
        } else if query.contains("yesterday") {
            guard let yesterday = calendar.date(byAdding: .day, value: -1, to: now) else { return nil }
            return calendar.startOfDay(for: yesterday)
        } else if query.contains("this week") {
            return calendar.date(from: calendar.dateComponents([.yearForWeekOfYear, .weekOfYear], from: now))
        } else if query.contains("this month") {
            return calendar.date(from: calendar.dateComponents([.year, .month], from: now))
        } else if query.contains("this year") {
            return calendar.date(from: calendar.dateComponents([.year], from: now))
        } else if query.contains("last month") || query.contains("past month") {
            return calendar.date(byAdding: .month, value: -1, to: now)
        } else if query.contains("last week") || query.contains("past week") {
            return calendar.date(byAdding: .weekOfYear, value: -1, to: now)
        }

        return nil
    }

    private func extractTimeRange(from query: String) -> String {
        // Check for "last X minutes/hours/days"
        let patterns: [(regex: String, singular: String, plural: String)] = [
            (#"last\s+(\d+)\s*min"#, "minute", "minutes"),
            (#"past\s+(\d+)\s*min"#, "minute", "minutes"),
            (#"last\s+(\d+)\s*hour"#, "hour", "hours"),
            (#"past\s+(\d+)\s*hour"#, "hour", "hours"),
            (#"last\s+(\d+)\s*day"#, "day", "days"),
            (#"past\s+(\d+)\s*day"#, "day", "days"),
            (#"last\s+(\d+)\s*week"#, "week", "weeks"),
            (#"past\s+(\d+)\s*week"#, "week", "weeks")
        ]

        for (pattern, singular, plural) in patterns {
            if let regex = try? NSRegularExpression(pattern: pattern, options: .caseInsensitive) {
                let range = NSRange(query.startIndex..., in: query)
                if let match = regex.firstMatch(in: query, options: [], range: range),
                   let numberRange = Range(match.range(at: 1), in: query),
                   let number = Int(query[numberRange]) {
                    return " in the last \(number) \(number == 1 ? singular : plural)"
                }
            }
        }

        if query.contains("today") {
            return " today"
        } else if query.contains("yesterday") {
            return " yesterday"
        } else if query.contains("this week") {
            return " this week"
        } else if query.contains("this month") {
            return " this month"
        } else if query.contains("this year") {
            return " this year"
        } else if query.contains("last month") || query.contains("past month") {
            return " in the last month"
        } else if query.contains("last 3 months") || query.contains("past 3 months") {
            return " in the last 3 months"
        } else if query.contains("last 6 months") || query.contains("past 6 months") {
            return " in the last 6 months"
        } else if query.contains("last week") || query.contains("past week") {
            return " in the last week"
        }
        return ""
    }

    private func extractCategory(from query: String) -> String? {
        let categories = [
            "vet visit": "vet visit",
            "vet": "vet",
            "vaccination": "vaccination",
            "vaccine": "vaccination",
            "blood work": "blood work",
            "blood test": "blood work",
            "dental": "dental",
            "grooming": "grooming",
            "medication": "medication",
            "surgery": "surgery",
            "allergy": "allergy",
            "sick": "illness",
            "illness": "illness",
            "vomit": "vomit",
            "vomm": "vomit",
            "threw up": "vomit",
            "diarrhea": "diarrhea",
            "injury": "injury",
            "wound": "injury",
            "hot spot": "hot spot",
            "rash": "skin issue",
            "ear": "ear issue",
            "eye": "eye issue"
        ]

        for (keyword, category) in categories {
            if query.contains(keyword) {
                return category
            }
        }

        return nil
    }
}

// MARK: - Preview

#Preview {
    SmartSearchView(
        pets: [
            Pet(
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
            ),
            Pet(
                id: UUID(),
                orgId: UUID().uuidString,
                name: "Bella",
                kind: "cat",
                photoUrl: nil,
                currentWeight: nil,
                dateOfBirth: nil,
                isArchived: false,
                createdAt: Date(),
                createdBy: nil
            )
        ]
    )
}
