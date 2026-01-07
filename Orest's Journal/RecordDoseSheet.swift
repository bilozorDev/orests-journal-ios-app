//
//  RecordDoseSheet.swift
//  Orest's Journal
//
//  Sheet for recording a medication dose with optional notes and time selection.
//

import SwiftUI

struct RecordDoseSheet: View {
    @Environment(\.dismiss) private var dismiss
    private var offlineQueue: OfflineDoseQueue { OfflineDoseQueue.shared }

    let medication: Medication
    let petName: String
    let familyId: String
    var onDoseRecorded: (() -> Void)?

    @State private var notes: String = ""
    @State private var useCustomTime = false
    @State private var customTime = Date()
    @State private var isSaving = false
    @State private var errorMessage: String?
    @State private var showSuccess = false
    @State private var showDuplicateWarning = false
    @State private var lastDoseTime: Date?

    /// Time window in seconds to consider as duplicate dose (5 minutes)
    private let duplicateThresholdSeconds: TimeInterval = 5 * 60

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
            .alert("Recent Dose Detected", isPresented: $showDuplicateWarning) {
                Button("Cancel", role: .cancel) {}
                Button("Record Anyway") {
                    Task {
                        await performDoseRecording()
                    }
                }
            } message: {
                if let lastTime = lastDoseTime {
                    let minutes = Int(Date().timeIntervalSince(lastTime) / 60)
                    Text("A dose was recorded \(minutes < 1 ? "less than a minute" : "\(minutes) minute\(minutes == 1 ? "" : "s")") ago. Are you sure you want to record another dose?")
                } else {
                    Text("A dose was recorded recently. Are you sure you want to record another dose?")
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

    /// Check for recent dose and record if safe, or show warning
    private func recordDose() async {
        isSaving = true
        errorMessage = nil

        // Check for recent dose
        do {
            if let lastDose = try await DataService.shared.getLastDose(medicationId: medication.id) {
                let timeSinceLastDose = Date().timeIntervalSince(lastDose.givenAt)

                if timeSinceLastDose < duplicateThresholdSeconds {
                    // Show warning dialog
                    lastDoseTime = lastDose.givenAt
                    isSaving = false
                    showDuplicateWarning = true
                    return
                }
            }
        } catch {
            // If we can't check last dose, proceed anyway (fail open)
            #if DEBUG
            print("Failed to check last dose: \(error)")
            #endif
        }

        // No recent dose, proceed with recording
        await performDoseRecording()
    }

    /// Actually perform the dose recording
    private func performDoseRecording() async {
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
                familyId: familyId
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
