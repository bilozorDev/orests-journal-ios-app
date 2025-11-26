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
    @State private var medication: PetMedication?
    @State private var isLoading = false
    @State private var hasLoaded = false
    @State private var errorMessage: String?
    @State private var doseToEdit: PetMedicationDose?
    @State private var doseToDelete: PetMedicationDose?
    @State private var showDeleteConfirmation = false

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
            if doses.isEmpty && hasLoaded {
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
                                        .contentShape(Rectangle())
                                        .onTapGesture {
                                            doseToEdit = dose
                                        }
                                        .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                                            Button(role: .destructive) {
                                                doseToDelete = dose
                                                showDeleteConfirmation = true
                                            } label: {
                                                Label("Delete", systemImage: "trash")
                                            }

                                            Button {
                                                doseToEdit = dose
                                            } label: {
                                                Label("Edit", systemImage: "pencil")
                                            }
                                            .tint(.blue)
                                        }
                                }
                            }
                        }
                    }
                }
            }
        }
        .overlay {
            if isLoading && !hasLoaded {
                ProgressView()
            }
        }
        .navigationTitle(medication?.name ?? "Dose History")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            guard !hasLoaded else { return }
            await loadData()
        }
        .refreshable {
            await loadData()
        }
        .sheet(item: $doseToEdit) { dose in
            EditDoseView(dose: dose, medication: medication, petId: medication?.petId) { updatedDose in
                if let index = doses.firstIndex(where: { $0.id == updatedDose.id }) {
                    doses[index] = updatedDose
                }
            }
        }
        .alert("Delete Dose", isPresented: $showDeleteConfirmation) {
            Button("Cancel", role: .cancel) {
                doseToDelete = nil
            }
            Button("Delete", role: .destructive) {
                if let dose = doseToDelete {
                    Task {
                        await deleteDose(dose)
                    }
                }
            }
        } message: {
            if let dose = doseToDelete {
                Text("Are you sure you want to delete the dose from \(formatTime(dose.givenAt))?")
            } else {
                Text("Are you sure you want to delete this dose?")
            }
        }
    }

    private func loadData() async {
        isLoading = true
        do {
            // Load medication info for the title and petId
            let medications = try await DataService.shared.getMedications()
            medication = medications.first { $0.id == medicationId }

            doses = try await DataService.shared.getDoses(for: medicationId)
            hasLoaded = true
        } catch let error as NSError where error.domain == NSURLErrorDomain && error.code == NSURLErrorCancelled {
            print("Medication history load cancelled (this is normal during navigation)")
        } catch {
            errorMessage = error.localizedDescription
            print("Error loading medication doses: \(error)")
        }
        isLoading = false
    }

    private func deleteDose(_ dose: PetMedicationDose) async {
        do {
            try await DataService.shared.deleteDose(id: dose.id, petId: medication?.petId)
            doseToDelete = nil
            doses.removeAll { $0.id == dose.id }
        } catch {
            errorMessage = error.localizedDescription
            print("Error deleting dose: \(error)")
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

    private func formatTime(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.timeStyle = .short
        return formatter.string(from: date)
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
                    HStack(spacing: 4) {
                        Text(formatTime(dose.givenAt))
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                        Text("by \(dose.givenBy)")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }
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
