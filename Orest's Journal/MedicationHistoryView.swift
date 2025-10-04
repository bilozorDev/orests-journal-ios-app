//
//  MedicationHistoryView.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import SwiftUI

struct MedicationHistoryView: View {
    let medicationId: UUID

    @State private var doses: [PetMedicationDose] = []
    @State private var isLoading = true
    @State private var errorMessage: String?

    var dosesByDate: [Date: [PetMedicationDose]] {
        let calendar = Calendar.current
        let grouped = Dictionary(grouping: doses) { dose in
            calendar.startOfDay(for: dose.givenAt)
        }
        return grouped
    }

    var sortedDates: [Date] {
        dosesByDate.keys.sorted(by: >)
    }

    var body: some View {
        Group {
            if isLoading {
                ProgressView()
            } else if doses.isEmpty {
                VStack(spacing: 16) {
                    Image(systemName: "list.bullet")
                        .font(.system(size: 60))
                        .foregroundColor(.gray)
                    Text("No dose history")
                        .font(.headline)
                        .foregroundColor(.secondary)
                }
            } else {
                List {
                    ForEach(sortedDates, id: \.self) { date in
                        Section(header: Text(formatDate(date))) {
                            if let dayDoses = dosesByDate[date] {
                                ForEach(dayDoses.sorted(by: { $0.givenAt > $1.givenAt })) { dose in
                                    DoseRowView(dose: dose)
                                }
                            }
                        }
                    }
                }
            }
        }
        .navigationTitle("Dose History")
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
            doses = try await SupabaseService.shared.getMedicationDoses(for: medicationId)
        } catch {
            errorMessage = error.localizedDescription
            print("Error loading medication doses: \(error)")
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

struct DoseRowView: View {
    let dose: PetMedicationDose

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Dose given")
                        .font(.headline)
                    Text(formatTime(dose.givenAt))
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }

                Spacer()

                Image(systemName: "checkmark.circle.fill")
                    .font(.title2)
                    .foregroundColor(.green)
            }

            if let notes = dose.notes, !notes.isEmpty {
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
}

#Preview {
    NavigationView {
        MedicationHistoryView(medicationId: UUID())
    }
}
