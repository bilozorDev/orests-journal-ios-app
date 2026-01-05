//
//  PendingDoseProcessor.swift
//  Orest's Journal
//
//  Processes doses queued from widget interactions.
//  Uses PendingDose from WidgetDataManager.swift (shared between app and widget).
//

import Foundation

// MARK: - Pending Dose Queue Keys

private enum PendingDoseKey {
    static let queue = "pending_dose_queue"
}

// MARK: - Pending Dose Processor

@MainActor
final class PendingDoseProcessor {
    static let shared = PendingDoseProcessor()

    private let userDefaults: UserDefaults?
    private let decoder = JSONDecoder()
    private let encoder = JSONEncoder()

    private var isProcessing = false

    private init() {
        userDefaults = UserDefaults(suiteName: "group.com.notip.orests-journal")
        decoder.dateDecodingStrategy = .iso8601
        encoder.dateEncodingStrategy = .iso8601
    }

    // MARK: - Public Methods

    /// Process any pending doses from the widget
    /// Should be called when the app becomes active
    func processPendingDoses() async {
        guard !isProcessing else { return }
        isProcessing = true
        defer { isProcessing = false }

        // Clean up old doses first
        cleanupOldDoses()

        let pendingDoses = getPendingDoses()
        guard !pendingDoses.isEmpty else { return }

        #if DEBUG
        print("📱 [PendingDose] Processing \(pendingDoses.count) pending doses")
        #endif

        // Get family ID for API calls
        guard let familyId = AuthManager.shared.currentFamily?.id else {
            #if DEBUG
            print("⚠️ [PendingDose] No family ID available, keeping doses in queue")
            #endif
            return
        }

        for dose in pendingDoses {
            await processDose(dose, familyId: familyId)
        }
    }

    /// Process a specific pending dose (called from deep link handling)
    /// Returns the medication name if dose was successfully recorded
    @discardableResult
    func processDoseForMedication(_ medicationId: UUID) async -> String? {
        guard let familyId = AuthManager.shared.currentFamily?.id else {
            #if DEBUG
            print("⚠️ [PendingDose] No family ID available")
            #endif
            return nil
        }

        let pendingDoses = getPendingDoses()
        #if DEBUG
        print("📱 [PendingDose] Looking for medication \(medicationId) in \(pendingDoses.count) pending doses")
        for dose in pendingDoses {
            print("   - \(dose.medicationName): \(dose.medicationId)")
        }
        #endif

        guard let dose = pendingDoses.first(where: { $0.medicationId == medicationId }) else {
            #if DEBUG
            print("⚠️ [PendingDose] No pending dose found for medication \(medicationId)")
            #endif
            return nil
        }

        let success = await processDose(dose, familyId: familyId)
        return success ? dose.medicationName : nil
    }

    // MARK: - Private Methods

    /// Process a dose and return whether it was successful
    private func processDose(_ dose: WidgetPendingDose, familyId: String) async -> Bool {
        #if DEBUG
        print("📱 [PendingDose] Recording dose for \(dose.medicationName), scheduledFor: \(String(describing: dose.scheduledFor))")
        #endif

        do {
            _ = try await DataService.shared.recordDose(
                medicationId: dose.medicationId,
                notes: "Recorded from widget",
                givenAt: nil,
                scheduledFor: dose.scheduledFor,
                familyId: familyId
            )

            // Remove from queue on success
            removeDose(dose)

            #if DEBUG
            print("✅ [PendingDose] Successfully recorded dose for \(dose.medicationName)")
            #endif
            return true
        } catch {
            #if DEBUG
            print("❌ [PendingDose] Failed to record dose: \(error)")
            #endif

            // If the dose is old (>10 min), remove it anyway
            if Date().timeIntervalSince(dose.requestedAt) > 600 {
                removeDose(dose)
            }
            return false
        }
    }

    private func getPendingDoses() -> [WidgetPendingDose] {
        guard let data = userDefaults?.data(forKey: PendingDoseKey.queue) else {
            return []
        }
        return (try? decoder.decode([WidgetPendingDose].self, from: data)) ?? []
    }

    private func removeDose(_ dose: WidgetPendingDose) {
        var queue = getPendingDoses()
        queue.removeAll { $0.id == dose.id }
        savePendingDoses(queue)
    }

    private func savePendingDoses(_ doses: [WidgetPendingDose]) {
        if let data = try? encoder.encode(doses) {
            userDefaults?.set(data, forKey: PendingDoseKey.queue)
        }
    }

    private func cleanupOldDoses() {
        var queue = getPendingDoses()
        let oneHourAgo = Date().addingTimeInterval(-3600)
        let oldCount = queue.count
        queue.removeAll { $0.requestedAt < oneHourAgo }
        if queue.count != oldCount {
            savePendingDoses(queue)
            #if DEBUG
            print("🧹 [PendingDose] Cleaned up \(oldCount - queue.count) old pending doses")
            #endif
        }
    }
}
