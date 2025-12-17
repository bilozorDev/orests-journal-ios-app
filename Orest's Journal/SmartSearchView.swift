//
//  SmartSearchView.swift
//  Orest's Journal
//
//  Smart search view with Apple Intelligence support (iOS 18.1+) and keyword fallback.
//

import SwiftUI

struct SmartSearchView: View {
    let pet: Pet

    @Environment(\.dismiss) private var dismiss

    @State private var query = ""
    @State private var isSearching = false
    @State private var searchResults: [HealthEventWithCategory] = []
    @State private var aiResponse: String?
    @State private var showError = false
    @State private var errorMessage = ""
    @State private var hasSearched = false

    private let dataService = DataService.shared
    private let smartSearchManager = SmartSearchManager.shared

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // AI availability banner
                if !smartSearchManager.isAvailable {
                    unavailableBanner
                }

                // Search input
                searchInput

                // Results
                resultsContent
            }
            .background(Color(uiColor: .systemGroupedBackground))
            .navigationTitle("Smart Search")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Done") {
                        dismiss()
                    }
                }
            }
            .task {
                await smartSearchManager.checkAvailability()
            }
        }
    }

    // MARK: - Unavailable Banner

    private var unavailableBanner: some View {
        HStack(spacing: 12) {
            Image(systemName: "sparkles")
                .font(.title2)
                .foregroundColor(.orange)

            VStack(alignment: .leading, spacing: 2) {
                Text("Smart Search Limited")
                    .font(.subheadline)
                    .fontWeight(.semibold)

                Text(smartSearchManager.unavailableReason)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            Spacer()
        }
        .padding()
        .background(Color.orange.opacity(0.1))
    }

    // MARK: - Search Input

    private var searchInput: some View {
        VStack(spacing: 12) {
            HStack {
                Image(systemName: smartSearchManager.isAvailable ? "sparkles" : "magnifyingglass")
                    .foregroundColor(smartSearchManager.isAvailable ? .accentColor : .secondary)

                TextField(
                    smartSearchManager.isAvailable
                        ? "Ask about \(pet.name)'s health..."
                        : "Search health events...",
                    text: $query
                )
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
                            .foregroundColor(.secondary)
                    }
                }
            }
            .padding(12)
            .background(Color(uiColor: .secondarySystemGroupedBackground))
            .clipShape(RoundedRectangle(cornerRadius: 10))

            // Example queries
            if !hasSearched && smartSearchManager.isAvailable {
                exampleQueries
            }
        }
        .padding()
    }

    private var exampleQueries: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Try asking:")
                .font(.caption)
                .foregroundColor(.secondary)

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
                                .foregroundColor(.accentColor)
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
                        .foregroundColor(.secondary)
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
            Image(systemName: smartSearchManager.isAvailable ? "sparkles" : "magnifyingglass")
                .font(.system(size: 48))
                .foregroundColor(.secondary)

            Text(smartSearchManager.isAvailable
                ? "Ask anything about \(pet.name)'s health"
                : "Search \(pet.name)'s health events")
                .font(.headline)

            Text(smartSearchManager.isAvailable
                ? "Use natural language to search and get insights"
                : "Enter keywords to find health events")
                .font(.subheadline)
                .foregroundColor(.secondary)
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
                            .foregroundColor(.accentColor)
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
                            .padding(.horizontal)

                        ForEach(searchResults) { event in
                            SmartSearchResultRow(event: event)
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
                .foregroundColor(.secondary)

            Text("No Results")
                .font(.headline)

            Text("Try a different search term")
                .font(.subheadline)
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var resultsList: some View {
        ScrollView {
            LazyVStack(spacing: 0) {
                ForEach(searchResults) { event in
                    SmartSearchResultRow(event: event)
                }
            }
            .padding(.vertical)
        }
    }

    // MARK: - Search

    private func performSearch() async {
        let trimmedQuery = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedQuery.isEmpty else { return }

        isSearching = true
        hasSearched = true
        aiResponse = nil
        searchResults = []

        do {
            if smartSearchManager.isAvailable {
                // Get all events for AI analysis
                let allEvents = try await dataService.getHealthEvents(for: pet.id)
                // Use smart search
                let (response, relevantEvents) = await smartSearchManager.search(
                    query: trimmedQuery,
                    events: allEvents,
                    petName: pet.name
                )
                aiResponse = response
                searchResults = relevantEvents
            } else {
                // Fallback to keyword search
                searchResults = try await dataService.searchHealthEvents(
                    petId: pet.id,
                    query: trimmedQuery
                )
            }
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }

        isSearching = false
    }
}

// MARK: - Smart Search Result Row

struct SmartSearchResultRow: View {
    let event: HealthEventWithCategory

    var body: some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                Text(event.category.name)
                    .font(.headline)

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

            if !event.event.photos.isEmpty {
                HStack(spacing: 2) {
                    Image(systemName: "photo")
                        .foregroundColor(.secondary)
                    if event.event.photos.count > 1 {
                        Text("\(event.event.photos.count)")
                            .font(.caption2)
                            .foregroundColor(.secondary)
                    }
                }
            }
        }
        .padding()
        .background(Color(uiColor: .secondarySystemGroupedBackground))
    }
}

// MARK: - Smart Search Manager

@Observable
class SmartSearchManager {
    static let shared = SmartSearchManager()

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

    @MainActor
    func checkAvailability() async {
        // Check if running on iOS 18.1+ where Apple Intelligence is available
        if #available(iOS 18.1, *) {
            // In a real implementation, we would check:
            // 1. Device model (iPhone 15 Pro+, M-series iPad/Mac)
            // 2. Apple Intelligence enabled in Settings
            // 3. Model download status
            //
            // For now, we check device capability using ProcessInfo
            let isEligibleDevice = checkDeviceEligibility()

            if isEligibleDevice {
                availability = .available
            } else {
                availability = .deviceNotEligible
            }
        } else {
            availability = .deviceNotEligible
        }
    }

    private func checkDeviceEligibility() -> Bool {
        // Check for A17 Pro or later (iPhone 15 Pro+) or M-series chips
        // This is a simplified check - in production you'd use more robust detection
        var systemInfo = utsname()
        uname(&systemInfo)
        let modelCode = withUnsafePointer(to: &systemInfo.machine) {
            $0.withMemoryRebound(to: CChar.self, capacity: 1) {
                String(validatingUTF8: $0)
            }
        }

        guard let model = modelCode else { return false }

        // iPhone 15 Pro and Pro Max (iPhone16,1 and iPhone16,2)
        // iPhone 16 series (iPhone17,*)
        // iPad with M-series (iPad14,* with M chips)
        let eligiblePrefixes = ["iPhone16,1", "iPhone16,2", "iPhone17,", "iPad14,", "iPad15,", "iPad16,"]

        return eligiblePrefixes.contains { model.hasPrefix($0) }
    }

    @MainActor
    func search(
        query: String,
        events: [HealthEventWithCategory],
        petName: String
    ) async -> (response: String?, relevantEvents: [HealthEventWithCategory]) {
        // For iOS 18.1+, we would use Apple Intelligence here
        // For now, we provide a smart keyword-based response

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

        // Time filtering
        if query.contains("this year") {
            let startOfYear = calendar.date(from: calendar.dateComponents([.year], from: now))!
            filtered = filtered.filter { $0.event.occurredAt >= startOfYear }
        } else if query.contains("last month") || query.contains("past month") {
            let oneMonthAgo = calendar.date(byAdding: .month, value: -1, to: now)!
            filtered = filtered.filter { $0.event.occurredAt >= oneMonthAgo }
        } else if query.contains("last 3 months") || query.contains("past 3 months") {
            let threeMonthsAgo = calendar.date(byAdding: .month, value: -3, to: now)!
            filtered = filtered.filter { $0.event.occurredAt >= threeMonthsAgo }
        } else if query.contains("last 6 months") || query.contains("past 6 months") {
            let sixMonthsAgo = calendar.date(byAdding: .month, value: -6, to: now)!
            filtered = filtered.filter { $0.event.occurredAt >= sixMonthsAgo }
        }

        // Category filtering
        let categoryKeywords = ["vet", "vaccination", "vaccine", "blood", "dental", "grooming", "medication", "surgery", "allergy", "sick", "injury"]
        for keyword in categoryKeywords {
            if query.contains(keyword) {
                filtered = filtered.filter { $0.category.nameNormalized.contains(keyword) }
                break
            }
        }

        // Text search in notes
        let searchTerms = query.components(separatedBy: .whitespaces)
            .filter { $0.count > 2 }
            .filter { !["how", "many", "the", "was", "last", "when", "this", "year", "month", "show", "all"].contains($0) }

        if !searchTerms.isEmpty {
            filtered = filtered.filter { event in
                searchTerms.contains { term in
                    event.category.nameNormalized.contains(term) ||
                    (event.event.notes?.lowercased().contains(term) ?? false)
                }
            }
        }

        return filtered.sorted { $0.event.occurredAt > $1.event.occurredAt }
    }

    private func extractTimeRange(from query: String) -> String {
        if query.contains("this year") {
            return " this year"
        } else if query.contains("last month") || query.contains("past month") {
            return " in the last month"
        } else if query.contains("last 3 months") || query.contains("past 3 months") {
            return " in the last 3 months"
        } else if query.contains("last 6 months") || query.contains("past 6 months") {
            return " in the last 6 months"
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
            "illness": "illness"
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
    )
}
