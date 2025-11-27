//
//  EditMedicationView.swift
//  Orest's Journal
//
//  Created by Claude on 11/26/25.
//

import SwiftUI

struct EditMedicationView: View {
    @Environment(\.dismiss) var dismiss

    let medication: PetMedication
    var onSave: ((PetMedication) -> Void)?

    @State private var medicationName: String
    @State private var selectedType: MedicationType
    @State private var startDate: Date
    @State private var hasEndDate: Bool
    @State private var endDate: Date
    @State private var timesPerDay: Int
    @State private var notes: String
    @State private var remindersEnabled: Bool
    @State private var scheduledTimes: [Date]
    @State private var isSaving = false
    @State private var errorMessage: String?

    init(medication: PetMedication, onSave: ((PetMedication) -> Void)? = nil) {
        self.medication = medication
        self.onSave = onSave

        _medicationName = State(initialValue: medication.name)
        _selectedType = State(initialValue: medication.medicationType)
        _startDate = State(initialValue: medication.startDate)
        _hasEndDate = State(initialValue: medication.endDate != nil)
        _endDate = State(initialValue: medication.endDate ?? Date())
        _timesPerDay = State(initialValue: medication.timesPerDay)
        _notes = State(initialValue: medication.notes ?? "")
        _remindersEnabled = State(initialValue: medication.remindersEnabled)

        // Convert scheduled times from medication
        if let schedules = medication.scheduledTimes, !schedules.isEmpty {
            _scheduledTimes = State(initialValue: schedules.map { $0.asDate })
        } else {
            // Default times if none set
            var times: [Date] = []
            for i in 0..<medication.timesPerDay {
                times.append(Self.defaultTime(hour: 9 + i * 4))
            }
            _scheduledTimes = State(initialValue: times)
        }
    }

    var body: some View {
        NavigationView {
            Form {
                Section("Medication Information") {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Medicine Name *")
                            .font(.caption)
                            .foregroundColor(.secondary)
                        TextField("Enter medicine name", text: $medicationName)
                    }

                    Picker("Type", selection: $selectedType) {
                        ForEach(MedicationType.allCases, id: \.self) { type in
                            Text(type.displayName).tag(type)
                        }
                    }
                }

                Section("Schedule") {
                    DatePicker("Start Date", selection: $startDate, displayedComponents: .date)

                    Toggle("Has End Date", isOn: $hasEndDate)

                    if hasEndDate {
                        DatePicker("End Date", selection: $endDate, displayedComponents: .date)
                    }

                    HStack {
                        Text("Times per day")
                        Spacer()
                        HStack(spacing: 12) {
                            Button(action: {
                                if timesPerDay > 1 {
                                    timesPerDay -= 1
                                    updateScheduledTimesCount()
                                }
                            }) {
                                Image(systemName: "minus.circle.fill")
                                    .foregroundColor(timesPerDay > 1 ? .blue : .gray)
                            }
                            .buttonStyle(.plain)
                            .disabled(timesPerDay <= 1)

                            Text("\(timesPerDay)")
                                .frame(minWidth: 30)

                            Button(action: {
                                if timesPerDay < 10 {
                                    timesPerDay += 1
                                    updateScheduledTimesCount()
                                }
                            }) {
                                Image(systemName: "plus.circle.fill")
                                    .foregroundColor(timesPerDay < 10 ? .blue : .gray)
                            }
                            .buttonStyle(.plain)
                            .disabled(timesPerDay >= 10)
                        }
                    }
                }

                Section {
                    Toggle("Enable Reminders", isOn: $remindersEnabled)

                    if remindersEnabled {
                        ForEach(0..<timesPerDay, id: \.self) { index in
                            DatePicker(
                                "Dose \(index + 1)",
                                selection: binding(for: index),
                                displayedComponents: .hourAndMinute
                            )
                        }
                    }
                } header: {
                    Text("Reminders")
                } footer: {
                    if remindersEnabled {
                        Text("You'll receive notifications at these times to give the medication.")
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
                        Button(action: saveMedication) {
                            Text("Save Changes")
                                .frame(maxWidth: .infinity)
                                .foregroundColor(.blue)
                        }
                        .disabled(!isFormValid || !hasChanges)
                    }
                }
            }
            .navigationTitle("Edit Medication")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
            }
            .onChange(of: remindersEnabled) { _, enabled in
                if enabled {
                    requestNotificationPermission()
                }
            }
        }
    }

    private var isFormValid: Bool {
        let nameValid = !medicationName.isEmpty
        let dateValid = !hasEndDate || endDate >= startDate
        return nameValid && dateValid
    }

    private var hasChanges: Bool {
        if medicationName != medication.name { return true }
        if selectedType != medication.medicationType { return true }
        if !Calendar.current.isDate(startDate, inSameDayAs: medication.startDate) { return true }
        if hasEndDate != (medication.endDate != nil) { return true }
        if hasEndDate, let origEnd = medication.endDate, !Calendar.current.isDate(endDate, inSameDayAs: origEnd) { return true }
        if timesPerDay != medication.timesPerDay { return true }
        if notes != (medication.notes ?? "") { return true }
        if remindersEnabled != medication.remindersEnabled { return true }

        // Check scheduled times changes if reminders enabled
        if remindersEnabled {
            if let origTimes = medication.scheduledTimes {
                if origTimes.count != scheduledTimes.count { return true }
                for (i, time) in scheduledTimes.enumerated() {
                    if i < origTimes.count {
                        let origComponents = (origTimes[i].scheduledHour, origTimes[i].scheduledMinute)
                        let newComponents = Calendar.current.dateComponents([.hour, .minute], from: time)
                        if origComponents.0 != newComponents.hour || origComponents.1 != newComponents.minute {
                            return true
                        }
                    }
                }
            } else if !scheduledTimes.isEmpty {
                return true
            }
        }

        return false
    }

    private func binding(for index: Int) -> Binding<Date> {
        Binding(
            get: {
                if index < scheduledTimes.count {
                    return scheduledTimes[index]
                }
                return Self.defaultTime(hour: 9 + index * 4)
            },
            set: { newValue in
                while scheduledTimes.count <= index {
                    scheduledTimes.append(Self.defaultTime(hour: 9 + scheduledTimes.count * 4))
                }
                scheduledTimes[index] = newValue
            }
        )
    }

    private func updateScheduledTimesCount() {
        // Ensure we have enough scheduled times
        while scheduledTimes.count < timesPerDay {
            let hour = 9 + scheduledTimes.count * 4
            scheduledTimes.append(Self.defaultTime(hour: min(hour, 21)))
        }
        // Remove excess times
        if scheduledTimes.count > timesPerDay {
            scheduledTimes = Array(scheduledTimes.prefix(timesPerDay))
        }
    }

    private static func defaultTime(hour: Int) -> Date {
        var components = Calendar.current.dateComponents([.year, .month, .day], from: Date())
        components.hour = hour
        components.minute = 0
        return Calendar.current.date(from: components) ?? Date()
    }

    private func requestNotificationPermission() {
        Task {
            await NotificationManager.shared.requestAuthorization()
        }
    }

    private func saveMedication() {
        Task {
            isSaving = true
            errorMessage = nil

            do {
                // Convert scheduled times to ScheduledTimeCreate
                let schedules: [ScheduledTimeCreate]? = remindersEnabled ? scheduledTimes.prefix(timesPerDay).map { date in
                    ScheduledTimeCreate(from: date)
                } : nil

                let result = try await DataService.shared.updateMedication(
                    id: medication.id,
                    name: medicationName,
                    medicationType: selectedType,
                    startDate: startDate,
                    endDate: hasEndDate ? endDate : nil,
                    timesPerDay: timesPerDay,
                    notes: notes.isEmpty ? nil : notes,
                    remindersEnabled: remindersEnabled,
                    scheduledTimes: schedules,
                    petId: medication.petId
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
    let sampleMedication = PetMedication(
        id: UUID(),
        petId: UUID(),
        name: "Sample Medication",
        medicationType: .pill,
        startDate: Date(),
        endDate: nil,
        timesPerDay: 2,
        notes: nil,
        remindersEnabled: false,
        timezone: TimeZone.current.identifier,
        isArchived: false,
        createdAt: Date(),
        createdBy: nil,
        scheduledTimes: nil
    )
    EditMedicationView(medication: sampleMedication)
}
