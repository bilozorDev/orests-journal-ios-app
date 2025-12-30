//
//  DoseHistoryView.swift
//  Orest's Journal
//
//  Full history of doses for a medication, grouped by date with edit/delete support.
//

import SwiftUI

struct DoseHistoryView: View {
    let medication: Medication
    let petName: String
    let familyId: String

    @State private var doses: [MedicationDose] = []
    @State private var groupedDosesCache: [(String, [MedicationDose])] = []
    @State private var isLoading = true
    @State private var isLoadingMore = false
    @State private var errorMessage: String?
    @State private var selectedDose: MedicationDose?
    @State private var doseToDelete: MedicationDose?
    @State private var showDeleteConfirmation = false

    // Pagination
    @State private var totalDoses = 0
    @State private var currentOffset = 0
    private let pageSize = 50

    private var hasMoreDoses: Bool {
        doses.count < totalDoses
    }

    var body: some View {
        Group {
            if isLoading {
                ProgressView()
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if let error = errorMessage {
                ContentUnavailableView {
                    Label("Error", systemImage: "exclamationmark.triangle")
                } description: {
                    Text(error)
                }
            } else if doses.isEmpty {
                ContentUnavailableView {
                    Label("No Doses Recorded", systemImage: "pills")
                } description: {
                    Text("No doses have been recorded for \(medication.name) yet.")
                }
            } else {
                doseList
            }
        }
        .navigationTitle("Dose History")
        .navigationBarTitleDisplayMode(.inline)
        .refreshable {
            await loadDoses(reset: true)
        }
        .task {
            await loadDoses(reset: true)
        }
        .sheet(item: $selectedDose) { dose in
            EditDoseSheet(
                dose: dose,
                medicationName: medication.name,
                familyId: familyId,
                onDoseUpdated: {
                    Task { await loadDoses(reset: true) }
                }
            )
        }
        .confirmationDialog(
            "Delete Dose",
            isPresented: $showDeleteConfirmation,
            presenting: doseToDelete
        ) { dose in
            Button("Delete", role: .destructive) {
                Task { await deleteDose(dose) }
            }
            Button("Cancel", role: .cancel) {}
        } message: { dose in
            Text("Are you sure you want to delete this dose recorded on \(dose.formattedDateTime)?")
        }
    }

    private var doseList: some View {
        List {
            ForEach(groupedDosesCache, id: \.0) { section in
                Section(header: Text(section.0)) {
                    ForEach(section.1) { dose in
                        DoseRow(dose: dose)
                            .contentShape(Rectangle())
                            .onTapGesture {
                                selectedDose = dose
                            }
                            .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                                Button(role: .destructive) {
                                    doseToDelete = dose
                                    showDeleteConfirmation = true
                                } label: {
                                    Label("Delete", systemImage: "trash")
                                }
                            }
                    }
                }
            }

            // Load more section
            if hasMoreDoses {
                Section {
                    HStack {
                        Spacer()
                        if isLoadingMore {
                            ProgressView()
                                .padding(.vertical, 8)
                        } else {
                            Button {
                                Task { await loadMoreDoses() }
                            } label: {
                                Text("Load More (\(doses.count) of \(totalDoses))")
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                            }
                            .padding(.vertical, 8)
                        }
                        Spacer()
                    }
                }
                .onAppear {
                    // Auto-load more when this section appears
                    Task { await loadMoreDoses() }
                }
            }
        }
        .listStyle(.insetGrouped)
    }

    /// Updates the cached grouped doses array
    private func updateGroupedDosesCache() {
        let calendar = Calendar.current
        let now = Date()
        let today = calendar.startOfDay(for: now)
        let yesterday = calendar.date(byAdding: .day, value: -1, to: today)!
        let weekAgo = calendar.date(byAdding: .day, value: -7, to: today)!

        var groups: [String: [MedicationDose]] = [:]

        for dose in doses {
            let doseDay = calendar.startOfDay(for: dose.givenAt)
            let sectionName: String

            if doseDay == today {
                sectionName = "Today"
            } else if doseDay == yesterday {
                sectionName = "Yesterday"
            } else if doseDay > weekAgo {
                sectionName = "This Week"
            } else {
                sectionName = Formatters.monthYear.string(from: dose.givenAt)
            }

            groups[sectionName, default: []].append(dose)
        }

        // Define section order
        let sectionOrder = ["Today", "Yesterday", "This Week"]

        groupedDosesCache = groups.sorted { lhs, rhs in
            let lhsIndex = sectionOrder.firstIndex(of: lhs.key) ?? Int.max
            let rhsIndex = sectionOrder.firstIndex(of: rhs.key) ?? Int.max

            if lhsIndex != Int.max && rhsIndex != Int.max {
                return lhsIndex < rhsIndex
            } else if lhsIndex != Int.max {
                return true
            } else if rhsIndex != Int.max {
                return false
            } else {
                // Both are month sections - sort by date descending
                return lhs.value.first?.givenAt ?? .distantPast > rhs.value.first?.givenAt ?? .distantPast
            }
        }
    }

    private func loadDoses(reset: Bool) async {
        if reset {
            isLoading = doses.isEmpty
            currentOffset = 0
        }
        errorMessage = nil

        do {
            let response = try await DataService.shared.getDosesForMedicationPaginated(
                medicationId: medication.id,
                limit: pageSize,
                offset: 0
            )
            doses = response.doses
            totalDoses = response.total
            currentOffset = response.doses.count
            updateGroupedDosesCache()
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    private func loadMoreDoses() async {
        guard !isLoadingMore, hasMoreDoses else { return }

        isLoadingMore = true
        defer { isLoadingMore = false }

        do {
            let response = try await DataService.shared.getDosesForMedicationPaginated(
                medicationId: medication.id,
                limit: pageSize,
                offset: currentOffset
            )
            doses.append(contentsOf: response.doses)
            currentOffset += response.doses.count
            updateGroupedDosesCache()
        } catch {
            // Silently fail for pagination - user can retry
            #if DEBUG
            print("Failed to load more doses: \(error)")
            #endif
        }
    }

    private func deleteDose(_ dose: MedicationDose) async {
        do {
            try await DataService.shared.deleteDose(doseId: dose.id, familyId: familyId)
            doses.removeAll { $0.id == dose.id }
            totalDoses -= 1
            updateGroupedDosesCache()
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

// MARK: - Dose Row

private struct DoseRow: View {
    let dose: MedicationDose

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            // Time
            VStack(alignment: .leading, spacing: 2) {
                Text(dose.formattedTime)
                    .font(.headline)
                Text(dose.givenBy)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            // Notes preview if exists
            if let notes = dose.notes, !notes.isEmpty {
                Text(notes)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
                    .frame(maxWidth: 150, alignment: .trailing)
            }

            Image(systemName: "chevron.right")
                .font(.caption)
                .foregroundStyle(.tertiary)
        }
        .padding(.vertical, 4)
        .accessibilityElement(children: .combine)
        .accessibilityLabel(accessibilityLabel)
        .accessibilityHint("Double tap to edit this dose")
    }

    private var accessibilityLabel: String {
        var label = "Dose given at \(dose.formattedTime) by \(dose.givenBy)"
        if let notes = dose.notes, !notes.isEmpty {
            label += ". Notes: \(notes)"
        }
        return label
    }
}
