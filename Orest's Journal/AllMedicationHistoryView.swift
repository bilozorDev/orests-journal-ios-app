//
//  AllMedicationHistoryView.swift
//  Orest's Journal
//
//  Created by Claude on 11/26/25.
//

import SwiftUI

struct AllMedicationHistoryView: View {
    @State private var pets: [Pet] = []
    @State private var selectedPet: Pet?
    @State private var doses: [AllMedicationDose] = []
    @State private var isLoading = false
    @State private var isLoadingMore = false
    @State private var totalCount: Int = 0
    @State private var errorMessage: String?
    @State private var doseToEdit: AllMedicationDose?
    @State private var doseToDelete: AllMedicationDose?
    @State private var showDeleteConfirmation = false

    private let pageSize = 50

    var hasMore: Bool {
        doses.count < totalCount
    }

    var dosesByDate: [Date: [AllMedicationDose]] {
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
        VStack(spacing: 0) {
            // Pet picker
            if pets.count > 1 {
                Picker("Pet", selection: $selectedPet) {
                    ForEach(pets) { pet in
                        Text(pet.name).tag(pet as Pet?)
                    }
                }
                .pickerStyle(SegmentedPickerStyle())
                .padding()
                .onChange(of: selectedPet) { _, newPet in
                    doses = []
                    totalCount = 0
                    // Try to load from cache first for instant display
                    if let pet = newPet,
                       let cached = DataService.shared.getCachedMedicationHistoryData(for: pet.id) {
                        doses = cached.doses
                        totalCount = cached.total
                    }
                    Task { await loadData() }
                }
            }

            // Content
            Group {
                if isLoading {
                    Spacer()
                    ProgressView()
                    Spacer()
                } else if selectedPet == nil {
                    Spacer()
                    VStack(spacing: 16) {
                        Image(systemName: "pills")
                            .font(.system(size: 60))
                            .foregroundColor(.gray)
                        Text("Select a pet to view history")
                            .font(.headline)
                            .foregroundColor(.secondary)
                    }
                    Spacer()
                } else if doses.isEmpty {
                    Spacer()
                    VStack(spacing: 16) {
                        Image(systemName: "list.bullet")
                            .font(.system(size: 60))
                            .foregroundColor(.gray)
                        Text("No medication history")
                            .font(.headline)
                            .foregroundColor(.secondary)
                    }
                    Spacer()
                } else {
                    List {
                        ForEach(sortedDates, id: \.self) { date in
                            Section(header: Text(formatDate(date))) {
                                if let dayDoses = dosesByDate[date] {
                                    ForEach(dayDoses.sorted(by: { $0.givenAt > $1.givenAt })) { dose in
                                        DoseHistoryRowView(dose: dose)
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
        }
        .navigationTitle("Medication History")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear {
            // Load from cache synchronously for instant display
            if let pet = selectedPet, doses.isEmpty {
                if let cached = DataService.shared.getCachedMedicationHistoryData(for: pet.id) {
                    doses = cached.doses
                    totalCount = cached.total
                }
            }
        }
        .task {
            await loadPets()
        }
        .refreshable {
            await loadData(forceRefresh: true)
        }
        .sheet(item: $doseToEdit) { dose in
            EditDoseFromHistoryView(dose: dose) { updatedDose in
                if let index = doses.firstIndex(where: { $0.id == updatedDose.id }) {
                    // Update with new values
                    doses[index] = AllMedicationDose(
                        id: updatedDose.id,
                        medicationId: doses[index].medicationId,
                        medicationName: doses[index].medicationName,
                        petId: doses[index].petId,
                        givenAt: updatedDose.givenAt,
                        givenBy: updatedDose.givenBy,
                        notes: updatedDose.notes,
                        createdAt: doses[index].createdAt
                    )
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
                Text("Are you sure you want to delete the \(dose.medicationName) dose from \(formatTime(dose.givenAt))?")
            } else {
                Text("Are you sure you want to delete this dose?")
            }
        }
    }

    private func loadPets() async {
        do {
            pets = try await DataService.shared.getPets()
            if let firstPet = pets.first {
                selectedPet = firstPet
                await loadData()
            }
        } catch {
            errorMessage = error.localizedDescription
            print("Error loading pets: \(error)")
        }
    }

    private func loadData(forceRefresh: Bool = false) async {
        guard let pet = selectedPet else { return }

        // Only show loading indicator if no cached data
        let hasCachedData = !doses.isEmpty
        if !hasCachedData {
            isLoading = true
        }

        do {
            let response = try await DataService.shared.getAllDoses(petId: pet.id, limit: pageSize, offset: 0, forceRefresh: forceRefresh)
            doses = response.doses
            totalCount = response.total
        } catch let error as NSError where error.domain == NSURLErrorDomain && error.code == NSURLErrorCancelled {
            print("Dose history load cancelled (this is normal during navigation)")
        } catch {
            errorMessage = error.localizedDescription
            print("Error loading dose history: \(error)")
        }
        isLoading = false
    }

    private func loadMore() async {
        guard let pet = selectedPet else { return }

        isLoadingMore = true
        do {
            let response = try await DataService.shared.getAllDoses(
                petId: pet.id,
                limit: pageSize,
                offset: doses.count
            )
            doses.append(contentsOf: response.doses)
        } catch {
            errorMessage = error.localizedDescription
            print("Error loading more doses: \(error)")
        }
        isLoadingMore = false
    }

    private func deleteDose(_ dose: AllMedicationDose) async {
        do {
            try await DataService.shared.deleteDose(id: dose.id, petId: dose.petId)
            doseToDelete = nil
            doses.removeAll { $0.id == dose.id }
        } catch {
            errorMessage = error.localizedDescription
            print("Error deleting dose: \(error)")
        }
    }

    private func formatTime(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.timeStyle = .short
        return formatter.string(from: date)
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

struct DoseHistoryRowView: View {
    let dose: AllMedicationDose

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(dose.medicationName)
                        .font(.headline)
                    Text(formatTime(dose.givenAt))
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }

                Spacer()

                VStack(alignment: .trailing, spacing: 4) {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(.green)
                        .font(.title2)
                    Text(dose.givenBy)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
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

// MARK: - Edit Dose From History View

struct EditDoseFromHistoryView: View {
    @Environment(\.dismiss) var dismiss

    let dose: AllMedicationDose
    var onSave: ((PetMedicationDose) -> Void)?

    @State private var selectedDate: Date
    @State private var selectedHour: Int
    @State private var selectedMinute: Int
    @State private var notes: String
    @State private var isSaving = false
    @State private var errorMessage: String?

    init(dose: AllMedicationDose, onSave: ((PetMedicationDose) -> Void)? = nil) {
        self.dose = dose
        self.onSave = onSave

        let components = Calendar.current.dateComponents([.hour, .minute], from: dose.givenAt)
        _selectedDate = State(initialValue: dose.givenAt)
        _selectedHour = State(initialValue: components.hour ?? 0)
        _selectedMinute = State(initialValue: components.minute ?? 0)
        _notes = State(initialValue: dose.notes ?? "")
    }

    var body: some View {
        NavigationView {
            Form {
                Section("Medication") {
                    Text(dose.medicationName)
                        .foregroundColor(.primary)
                }

                Section("Time Given") {
                    DatePicker("Date", selection: $selectedDate, displayedComponents: .date)

                    HStack {
                        Text("Time")
                        Spacer()
                        Picker("Hour", selection: $selectedHour) {
                            ForEach(0..<24, id: \.self) { hour in
                                Text(formatHour(hour)).tag(hour)
                            }
                        }
                        .pickerStyle(.wheel)
                        .frame(width: 80)
                        .clipped()

                        Text(":")

                        Picker("Minute", selection: $selectedMinute) {
                            ForEach(0..<60, id: \.self) { minute in
                                Text(String(format: "%02d", minute)).tag(minute)
                            }
                        }
                        .pickerStyle(.wheel)
                        .frame(width: 60)
                        .clipped()
                    }
                }

                Section("Notes (Optional)") {
                    TextEditor(text: $notes)
                        .frame(height: 80)
                }

                if let error = errorMessage {
                    Section {
                        Text(error)
                            .foregroundColor(.red)
                            .font(.caption)
                    }
                }

                Section {
                    if isSaving {
                        HStack {
                            Spacer()
                            ProgressView()
                            Spacer()
                        }
                    } else {
                        Button(action: saveChanges) {
                            Text("Save Changes")
                                .frame(maxWidth: .infinity)
                                .foregroundColor(.blue)
                        }
                        .disabled(!hasChanges)
                    }
                }
            }
            .navigationTitle("Edit Dose")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
            }
        }
    }

    private var hasChanges: Bool {
        let originalComponents = Calendar.current.dateComponents([.hour, .minute], from: dose.givenAt)
        let originalDate = Calendar.current.startOfDay(for: dose.givenAt)
        let newDate = Calendar.current.startOfDay(for: selectedDate)

        return originalDate != newDate ||
               originalComponents.hour != selectedHour ||
               originalComponents.minute != selectedMinute ||
               notes != (dose.notes ?? "")
    }

    private func formatHour(_ hour: Int) -> String {
        let displayHour = hour % 12 == 0 ? 12 : hour % 12
        let period = hour < 12 ? "AM" : "PM"
        return "\(displayHour) \(period)"
    }

    private func saveChanges() {
        Task {
            isSaving = true
            errorMessage = nil

            do {
                // Combine date and time
                var components = Calendar.current.dateComponents([.year, .month, .day], from: selectedDate)
                components.hour = selectedHour
                components.minute = selectedMinute
                let newGivenAt = Calendar.current.date(from: components) ?? selectedDate

                let result = try await DataService.shared.updateDose(
                    id: dose.id,
                    givenAt: newGivenAt,
                    notes: notes.isEmpty ? nil : notes,
                    petId: dose.petId
                )

                onSave?(result)
                dismiss()
            } catch {
                errorMessage = error.localizedDescription
                isSaving = false
            }
        }
    }
}

#Preview {
    NavigationView {
        AllMedicationHistoryView()
    }
}
