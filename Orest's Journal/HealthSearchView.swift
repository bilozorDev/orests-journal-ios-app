//
//  HealthSearchView.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import SwiftUI

struct HealthSearchView: View {
    @State private var searchQuery = ""
    @State private var searchResults: [HealthSearchResult] = []
    @State private var isSearching = false
    @State private var errorMessage: String?
    @State private var selectedPet: Pet?
    @State private var pets: [Pet] = []

    var body: some View {
        NavigationView {
            VStack(spacing: 0) {
                // Title at very top
                HStack {
                    Text("Search Health Journal")
                        .font(.largeTitle)
                        .fontWeight(.bold)
                    Spacer()
                }
                .padding(.horizontal)
                .padding(.top)
                .padding(.bottom, 8)

            // Search bar
            VStack(spacing: 12) {
                    HStack {
                        Image(systemName: "magnifyingglass")
                            .foregroundColor(.secondary)

                        TextField("Search health events...", text: $searchQuery)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                            .onSubmit {
                                performSearch()
                            }

                        if !searchQuery.isEmpty {
                            Button(action: {
                                searchQuery = ""
                                searchResults = []
                            }) {
                                Image(systemName: "xmark.circle.fill")
                                    .foregroundColor(.secondary)
                            }
                        }
                    }
                    .padding(12)
                    .background(Color(.systemGray6))
                    .cornerRadius(10)

                    // Pet filter
                    if !pets.isEmpty {
                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack(spacing: 8) {
                                Button(action: {
                                    selectedPet = nil
                                    if !searchQuery.isEmpty {
                                        performSearch()
                                    }
                                }) {
                                    Text("All Pets")
                                        .font(.subheadline)
                                        .padding(.horizontal, 12)
                                        .padding(.vertical, 6)
                                        .background(selectedPet == nil ? Color.blue : Color(.systemGray6))
                                        .foregroundColor(selectedPet == nil ? .white : .primary)
                                        .cornerRadius(16)
                                }

                                ForEach(pets) { pet in
                                    Button(action: {
                                        selectedPet = pet
                                        if !searchQuery.isEmpty {
                                            performSearch()
                                        }
                                    }) {
                                        Text(pet.name)
                                            .font(.subheadline)
                                            .padding(.horizontal, 12)
                                            .padding(.vertical, 6)
                                            .background(selectedPet?.id == pet.id ? Color.blue : Color(.systemGray6))
                                            .foregroundColor(selectedPet?.id == pet.id ? .white : .primary)
                                            .cornerRadius(16)
                                    }
                                }
                            }
                        }
                    }
            }
            .padding()

            Divider()

            // Results
            if isSearching {
                VStack {
                    Spacer()
                    ProgressView("Searching...")
                    Spacer()
                }
            } else if let error = errorMessage {
                VStack {
                    Spacer()
                    Text("Error")
                        .font(.headline)
                        .padding(.bottom, 4)
                    Text(error)
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                    Spacer()
                }
                .padding()
            } else if searchQuery.isEmpty {
                VStack {
                    Spacer()
                    Image(systemName: "magnifyingglass")
                        .font(.system(size: 60))
                        .foregroundColor(.secondary)
                        .padding(.bottom, 16)
                    Text("Search Health Events")
                        .font(.headline)
                        .padding(.bottom, 4)
                    Text("Try: \"first asthma attack\" or \"recent vomit\"")
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                    Spacer()
                }
                .padding()
            } else if searchResults.isEmpty {
                VStack {
                    Spacer()
                    Image(systemName: "exclamationmark.magnifyingglass")
                        .font(.system(size: 60))
                        .foregroundColor(.secondary)
                        .padding(.bottom, 16)
                    Text("No Results Found")
                        .font(.headline)
                        .padding(.bottom, 4)
                    Text("No health events found matching '\(searchQuery)'")
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                    Spacer()
                }
                .padding()
            } else {
                List {
                    Section {
                        ForEach(searchResults) { result in
                            HealthSearchResultRow(result: result)
                        }
                    } header: {
                        Text("\(searchResults.count) result\(searchResults.count == 1 ? "" : "s") for '\(searchQuery)'")
                    }
                }
                .listStyle(.insetGrouped)
            }
        }
        .navigationBarHidden(true)
        .task {
            await loadPets()
        }
        }
    }

    private func loadPets() async {
        do {
            guard let family = try await SupabaseService.shared.getCurrentUserFamily() else {
                return
            }
            pets = try await SupabaseService.shared.getFamilyPets(familyId: family.id)
        } catch {
            print("Error loading pets: \(error)")
        }
    }

    private func performSearch() {
        guard !searchQuery.trimmingCharacters(in: .whitespaces).isEmpty else {
            return
        }

        Task {
            isSearching = true
            errorMessage = nil

            do {
                // Parse the query to detect intent
                let parsedQuery = SearchQueryParser.parse(searchQuery)

                // Perform the search
                let results = try await SupabaseService.shared.searchHealthEvents(
                    query: parsedQuery.cleanedQuery.isEmpty ? parsedQuery.originalQuery : parsedQuery.cleanedQuery,
                    petId: selectedPet?.id,
                    intent: parsedQuery.intent,
                    matchThreshold: 0.65, // Slightly lower threshold for better recall
                    matchCount: 20
                )

                // Take only the first result if intent is .first or .last
                if parsedQuery.intent == .first || parsedQuery.intent == .last {
                    searchResults = Array(results.prefix(1))
                } else {
                    searchResults = results
                }
            } catch {
                errorMessage = error.localizedDescription
                searchResults = []
            }

            isSearching = false
        }
    }
}

struct HealthSearchResultRow: View {
    let result: HealthSearchResult

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            // Category and pet
            HStack {
                Text(result.categoryName)
                    .font(.headline)

                Spacer()

                Text(result.petName)
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.blue.opacity(0.1))
                    .cornerRadius(8)
            }

            // Date
            Text(result.occurredAt.formatted(date: .abbreviated, time: .shortened))
                .font(.subheadline)
                .foregroundColor(.secondary)

            // Notes (if any)
            if let notes = result.notes, !notes.isEmpty {
                Text(notes)
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .lineLimit(2)
            }

            // Created by and similarity
            HStack {
                Text("Logged by \(result.createdByEmail)")
                    .font(.caption2)
                    .foregroundColor(.secondary)

                Spacer()

                Text("\(Int(result.similarity * 100))% match")
                    .font(.caption2)
                    .foregroundColor(.blue)
            }
        }
        .padding(.vertical, 4)
    }
}

#Preview {
    HealthSearchView()
}
