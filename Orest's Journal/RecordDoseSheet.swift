//
//  RecordDoseSheet.swift
//  Orest's Journal
//
//  Sheet for recording a medication dose with optional notes and time selection.
//

import SwiftUI

struct RecordDoseSheet: View {
    @Environment(\.dismiss) private var dismiss
    @ObservedObject private var offlineQueue = OfflineDoseQueue.shared

    let medication: Medication
    let petName: String
    let orgId: String
    var onDoseRecorded: (() -> Void)?

    @State private var notes: String = ""
    @State private var useCustomTime = false
    @State private var customTime = Date()
    @State private var isSaving = false
    @State private var errorMessage: String?
    @State private var showSuccess = false

    var body: some View {
        NavigationStack {
            Form {
                // Medication info header
                Section {
                    HStack(spacing: 12) {
                        Image(systemName: medication.medicationType.icon)
                            .font(.title2)
                            .foregroundStyle(.white)
                            .frame(width: 44, height: 44)
                            .background(Color.accentColor)
                            .clipShape(Circle())

                        VStack(alignment: .leading, spacing: 2) {
                            Text(medication.displayName)
                                .font(.headline)
                            Text(petName)
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                            if let dosage = medication.dosage, !dosage.isEmpty {
                                Text(dosage)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                    .padding(.vertical, 4)
                }

                // Time selection
                Section(header: Text("When")) {
                    Toggle("Record at different time", isOn: $useCustomTime.animation())

                    if useCustomTime {
                        DatePicker(
                            "Time given",
                            selection: $customTime,
                            in: ...Date(),
                            displayedComponents: [.date, .hourAndMinute]
                        )
                    }
                }

                // Notes
                Section(header: Text("Notes (optional)")) {
                    TextField("Add any notes about this dose...", text: $notes, axis: .vertical)
                        .lineLimit(3...6)
                }

                // Offline indicator
                if !offlineQueue.isOnline {
                    Section {
                        HStack {
                            Image(systemName: "wifi.slash")
                                .foregroundStyle(.orange)
                            Text("You're offline. This dose will be recorded when you're back online.")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }

                // Error message
                if let error = errorMessage {
                    Section {
                        Text(error)
                            .foregroundStyle(.red)
                            .font(.caption)
                    }
                }
            }
            .navigationTitle("Record Dose")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                    .disabled(isSaving)
                }

                ToolbarItem(placement: .confirmationAction) {
                    Button("Record") {
                        Task {
                            await recordDose()
                        }
                    }
                    .disabled(isSaving)
                    .fontWeight(.semibold)
                }
            }
            .interactiveDismissDisabled(isSaving)
            .overlay {
                if showSuccess {
                    successOverlay
                }
            }
        }
    }

    private var successOverlay: some View {
        VStack(spacing: 16) {
            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 60))
                .foregroundStyle(.green)

            Text(offlineQueue.isOnline ? "Dose Recorded" : "Queued for Sync")
                .font(.headline)

            if !offlineQueue.isOnline {
                Text("Will be saved when online")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(32)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 20))
        .transition(.scale.combined(with: .opacity))
    }

    private func recordDose() async {
        isSaving = true
        defer { isSaving = false }
        errorMessage = nil

        do {
            let givenAt = useCustomTime ? customTime : nil
            let notesText = notes.trimmingCharacters(in: .whitespaces).isEmpty ? nil : notes.trimmingCharacters(in: .whitespaces)

            _ = try await DataService.shared.recordDose(
                medicationId: medication.id,
                notes: notesText,
                givenAt: givenAt,
                orgId: orgId
            )

            // Show success feedback
            withAnimation {
                showSuccess = true
            }

            // Haptic feedback
            let generator = UINotificationFeedbackGenerator()
            generator.notificationOccurred(.success)

            // Dismiss after brief delay
            try? await Task.sleep(for: .seconds(1))
            onDoseRecorded?()
            dismiss()

        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
