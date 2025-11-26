//
//  FeedingHistoryView.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import SwiftUI

struct FeedingHistoryView: View {
    let petId: UUID

    @State private var feedings: [PetFeeding] = []
    @State private var foods: [UUID: PetFood] = [:]
    @State private var isLoading = false
    @State private var isLoadingMore = false
    @State private var totalCount: Int = 0
    @State private var errorMessage: String?
    @State private var feedingToEdit: PetFeeding?
    @State private var feedingToDelete: PetFeeding?
    @State private var showDeleteConfirmation = false

    private let pageSize = 50

    var hasMore: Bool {
        feedings.count < totalCount
    }

    var feedingsByDate: [Date: [PetFeeding]] {
        let calendar = Calendar.current
        let grouped = Dictionary(grouping: feedings) { feeding in
            calendar.startOfDay(for: feeding.fedAt)
        }
        return grouped
    }

    var sortedDates: [Date] {
        feedingsByDate.keys.sorted(by: >)
    }

    var body: some View {
        Group {
            if isLoading {
                ProgressView()
            } else if feedings.isEmpty {
                VStack(spacing: 16) {
                    Image(systemName: "list.bullet")
                        .font(.system(size: 60))
                        .foregroundColor(.gray)
                    Text("No feeding history")
                        .font(.headline)
                        .foregroundColor(.secondary)
                }
            } else {
                List {
                    ForEach(sortedDates, id: \.self) { date in
                        Section(header: Text(formatDate(date))) {
                            if let dayFeedings = feedingsByDate[date] {
                                ForEach(dayFeedings.sorted(by: { $0.fedAt > $1.fedAt })) { feeding in
                                    FeedingRowView(feeding: feeding, food: foods[feeding.foodId])
                                        .contentShape(Rectangle())
                                        .onTapGesture {
                                            feedingToEdit = feeding
                                        }
                                        .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                                            Button(role: .destructive) {
                                                feedingToDelete = feeding
                                                showDeleteConfirmation = true
                                            } label: {
                                                Label("Delete", systemImage: "trash")
                                            }

                                            Button {
                                                feedingToEdit = feeding
                                            } label: {
                                                Label("Edit", systemImage: "pencil")
                                            }
                                            .tint(.blue)
                                        }
                                }
                            }
                        }
                    }

                    // Load More button
                    if hasMore {
                        Section {
                            Button(action: {
                                Task { await loadMore() }
                            }) {
                                HStack {
                                    Spacer()
                                    if isLoadingMore {
                                        ProgressView()
                                            .progressViewStyle(CircularProgressViewStyle())
                                    } else {
                                        Text("Load More")
                                    }
                                    Spacer()
                                }
                            }
                            .disabled(isLoadingMore)
                        }
                    }
                }
            }
        }
        .navigationTitle("Feeding History")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear {
            // Populate from cache synchronously for instant display
            if let cached = DataService.shared.getCachedFeedingHistoryData(for: petId) {
                feedings = cached.feedings
                totalCount = cached.total
            }
        }
        .task {
            await loadData()
        }
        .refreshable {
            await loadData(forceRefresh: true)
        }
        .sheet(item: $feedingToEdit) { feeding in
            EditFeedingView(feeding: feeding, food: foods[feeding.foodId]) { updatedFeeding in
                if let index = feedings.firstIndex(where: { $0.id == updatedFeeding.id }) {
                    feedings[index] = updatedFeeding
                }
            }
        }
        .alert("Delete Feeding", isPresented: $showDeleteConfirmation) {
            Button("Cancel", role: .cancel) {
                feedingToDelete = nil
            }
            Button("Delete", role: .destructive) {
                if let feeding = feedingToDelete {
                    Task {
                        await deleteFeeding(feeding)
                    }
                }
            }
        } message: {
            if let feeding = feedingToDelete, let food = foods[feeding.foodId] {
                Text("Are you sure you want to delete the \(food.name) feeding from \(formatTime(feeding.fedAt))?")
            } else {
                Text("Are you sure you want to delete this feeding?")
            }
        }
    }

    private func formatTime(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.timeStyle = .short
        return formatter.string(from: date)
    }

    private func loadData(forceRefresh: Bool = false) async {
        // Only show loading indicator if no cached data
        let hasCachedData = DataService.shared.hasCachedFeedingHistory(for: petId)
        if !hasCachedData {
            isLoading = true
        }
        do {
            let response = try await DataService.shared.getFeedingHistory(for: petId, limit: pageSize, forceRefresh: forceRefresh)
            feedings = response.feedings
            totalCount = response.total

            // Load all foods (including archived for historical display)
            let allFoods = try await DataService.shared.getFoods(includeArchived: true)
            foods = Dictionary(uniqueKeysWithValues: allFoods.map { ($0.id, $0) })
        } catch let error as NSError where error.domain == NSURLErrorDomain && error.code == NSURLErrorCancelled {
            print("Feeding history load cancelled (this is normal during navigation)")
        } catch {
            errorMessage = error.localizedDescription
            print("Error loading feeding history: \(error)")
        }
        isLoading = false
    }

    private func loadMore() async {
        isLoadingMore = true
        do {
            let response = try await DataService.shared.getFeedingHistory(
                for: petId,
                limit: pageSize,
                offset: feedings.count
            )
            feedings.append(contentsOf: response.feedings)
        } catch {
            errorMessage = error.localizedDescription
            print("Error loading more feedings: \(error)")
        }
        isLoadingMore = false
    }

    private func deleteFeeding(_ feeding: PetFeeding) async {
        do {
            try await DataService.shared.deleteFeeding(id: feeding.id, petId: petId)
            feedingToDelete = nil
            feedings.removeAll { $0.id == feeding.id }
        } catch {
            errorMessage = error.localizedDescription
            print("Error deleting feeding: \(error)")
        }
    }

    private func formatDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .none

        if Calendar.current.isDateInToday(date) {
            return "Today"
        } else if Calendar.current.isDateInYesterday(date) {
            return "Yesterday"
        } else {
            return formatter.string(from: date)
        }
    }
}

struct FeedingRowView: View {
    let feeding: PetFeeding
    let food: PetFood?

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(food?.name ?? "Unknown Food")
                        .font(.headline)
                    Text(formatTime(feeding.fedAt))
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }

                Spacer()

                VStack(alignment: .trailing, spacing: 4) {
                    Text("\(Int(feeding.calories)) cal")
                        .font(.headline)
                        .foregroundColor(.blue)
                    Text("\(formatAmount(feeding.amount)) \(feeding.amountUnit.abbreviation)")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
            }

            if let notes = feeding.notes, !notes.isEmpty {
                Text(notes)
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .padding(.top, 4)
            }
        }
        .padding(.vertical, 4)
    }

    private func formatTime(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.timeStyle = .short
        return formatter.string(from: date)
    }

    private func formatAmount(_ value: Double) -> String {
        let formatter = NumberFormatter()
        formatter.minimumFractionDigits = 0
        formatter.maximumFractionDigits = 2
        return formatter.string(from: NSNumber(value: value)) ?? "\(value)"
    }
}
