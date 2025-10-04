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
    @State private var isLoading = true
    @State private var errorMessage: String?

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
                                }
                            }
                        }
                    }
                }
            }
        }
        .navigationTitle("Feeding History")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            await loadData()
        }
        .refreshable {
            await loadData()
        }
    }

    private func loadData() async {
        isLoading = true
        do {
            feedings = try await SupabaseService.shared.getFeedingHistory(for: petId)

            // Load all unique foods
            let foodIds = Set(feedings.map { $0.foodId })
            guard let family = try await SupabaseService.shared.getCurrentUserFamily() else {
                return
            }
            let allFoods = try await SupabaseService.shared.getFamilyFoods(familyId: family.id)
            foods = Dictionary(uniqueKeysWithValues: allFoods.map { ($0.id, $0) })
        } catch {
            errorMessage = error.localizedDescription
            print("Error loading feeding history: \(error)")
        }
        isLoading = false
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
