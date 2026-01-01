//
//  RecordDoseIntent.swift
//  OrestsJournalWidget
//
//  Interactive AppIntent for recording doses directly from the widget.
//  Available on iOS 17+.
//  Uses PendingDose from WidgetDataManager.swift (shared between app and widget).
//

import AppIntents
import WidgetKit
import Foundation

// MARK: - Pending Dose Queue Keys

private enum PendingDoseKey {
    static let queue = "pending_dose_queue"
}

// MARK: - Pending Dose Manager

/// Manages the queue of doses waiting to be recorded
final class PendingDoseManager {
    static let shared = PendingDoseManager()

    private let userDefaults: UserDefaults?
    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()

    private init() {
        userDefaults = UserDefaults(suiteName: "group.com.notip.orests-journal")
        encoder.dateEncodingStrategy = .iso8601
        decoder.dateDecodingStrategy = .iso8601
    }

    /// Add a dose to the pending queue
    func queueDose(_ dose: WidgetPendingDose) {
        var queue = getPendingDoses()

        // Prevent duplicate requests for the same medication within 5 minutes
        let fiveMinutesAgo = Date().addingTimeInterval(-5 * 60)
        queue.removeAll { existing in
            existing.medicationId == dose.medicationId && existing.requestedAt > fiveMinutesAgo
        }

        queue.append(dose)
        savePendingDoses(queue)

        #if DEBUG
        print("📱 [Widget] Queued dose for \(dose.medicationName). Queue size: \(queue.count)")
        #endif
    }

    /// Get all pending doses
    func getPendingDoses() -> [WidgetPendingDose] {
        guard let data = userDefaults?.data(forKey: PendingDoseKey.queue) else {
            return []
        }
        return (try? decoder.decode([WidgetPendingDose].self, from: data)) ?? []
    }

    /// Remove a dose from the queue (after processing)
    func removeDose(_ dose: WidgetPendingDose) {
        var queue = getPendingDoses()
        queue.removeAll { $0.id == dose.id }
        savePendingDoses(queue)
    }

    /// Remove a dose by medication ID (after processing)
    func removeDose(forMedicationId medicationId: UUID) {
        var queue = getPendingDoses()
        queue.removeAll { $0.medicationId == medicationId }
        savePendingDoses(queue)
    }

    /// Clear all pending doses
    func clearAll() {
        userDefaults?.removeObject(forKey: PendingDoseKey.queue)
    }

    /// Clean up old pending doses (older than 1 hour)
    func cleanupOldDoses() {
        var queue = getPendingDoses()
        let oneHourAgo = Date().addingTimeInterval(-3600)
        queue.removeAll { $0.requestedAt < oneHourAgo }
        savePendingDoses(queue)
    }

    private func savePendingDoses(_ doses: [WidgetPendingDose]) {
        if let data = try? encoder.encode(doses) {
            userDefaults?.set(data, forKey: PendingDoseKey.queue)
        }
    }
}

// MARK: - Record Dose Intent

/// AppIntent for recording a dose from the widget
@available(iOS 18.0, *)
struct RecordDoseIntent: AppIntent {
    static var title: LocalizedStringResource = "Record Dose"
    static var description = IntentDescription("Mark a medication dose as given")

    /// Do NOT open the app - show success in widget instead
    static var openAppWhenRun: Bool = false

    @Parameter(title: "Medication ID")
    var medicationId: String

    @Parameter(title: "Medication Name")
    var medicationName: String

    @Parameter(title: "Pet Name")
    var petName: String

    @Parameter(title: "Scheduled For")
    var scheduledFor: Date?

    init() {
        self.medicationId = ""
        self.medicationName = ""
        self.petName = ""
        self.scheduledFor = nil
    }

    nonisolated init(medicationId: UUID, medicationName: String, petName: String, scheduledFor: Date? = nil) {
        self.medicationId = medicationId.uuidString
        self.medicationName = medicationName
        self.petName = petName
        self.scheduledFor = scheduledFor
    }

    func perform() async throws -> some IntentResult {
        guard let medId = UUID(uuidString: medicationId) else {
            throw IntentError.invalidMedicationId
        }

        // Queue the dose for processing by the main app
        let pendingDose = WidgetPendingDose(
            medicationId: medId,
            medicationName: medicationName,
            petName: petName,
            scheduledFor: scheduledFor
        )
        PendingDoseManager.shared.queueDose(pendingDose)

        // Mark dose as given in widget data (optimistic UI)
        WidgetDataManager.shared.markDoseAsGiven(
            medicationId: medId,
            scheduledTime: scheduledFor,
            givenBy: "You"  // Will be updated with actual name when synced
        )

        // Refresh widget to show success state
        WidgetCenter.shared.reloadTimelines(ofKind: "NextDoseWidget")

        #if DEBUG
        print("📱 [Widget] Recorded dose for \(medicationName) - widget updated")
        #endif

        return .result()
    }

    enum IntentError: Swift.Error, CustomLocalizedStringResourceConvertible {
        case invalidMedicationId

        var localizedStringResource: LocalizedStringResource {
            switch self {
            case .invalidMedicationId:
                return "Invalid medication ID"
            }
        }
    }
}

// MARK: - Widget Button

/// A button for recording doses in the widget
@available(iOS 18.0, *)
struct RecordDoseButton: View {
    let dose: WidgetDoseInfo
    let style: ButtonStyle

    enum ButtonStyle {
        case compact  // For small widgets - larger icon
        case standard // For medium/large widgets - icon + text
    }

    var body: some View {
        Button(intent: RecordDoseIntent(
            medicationId: dose.medicationId,
            medicationName: dose.medicationName,
            petName: dose.petName,
            scheduledFor: dose.scheduledTime  // Pass the scheduled time slot
        )) {
            switch style {
            case .compact:
                // Larger touch target for small widget
                ZStack {
                    Circle()
                        .fill(Color.green.opacity(0.2))
                        .frame(width: 44, height: 44)
                    Image(systemName: "checkmark.circle.fill")
                        .font(.system(size: 28, weight: .medium))
                        .foregroundStyle(.green)
                }
            case .standard:
                HStack(spacing: 4) {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.system(size: 16))
                    Text("Give")
                        .font(.subheadline)
                        .fontWeight(.semibold)
                }
                .foregroundStyle(.green)
            }
        }
        .buttonStyle(.plain)
    }
}

// Need to import SwiftUI for the button
import SwiftUI
