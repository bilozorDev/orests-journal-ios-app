//
//  OfflineDoseQueue.swift
//  Orest's Journal
//
//  Manages offline dose recording with automatic sync when network is available.
//

import Foundation
import Network

/// A pending dose that hasn't been synced to the server yet
struct PendingDose: Codable, Identifiable, Sendable {
    let id: UUID
    let medicationId: UUID
    let givenAt: Date
    let notes: String?
    let scheduledFor: Date?  // Links dose to specific schedule slot
    let familyId: String
    let queuedAt: Date

    init(medicationId: UUID, givenAt: Date = Date(), notes: String? = nil, scheduledFor: Date? = nil, familyId: String) {
        self.id = UUID()
        self.medicationId = medicationId
        self.givenAt = givenAt
        self.notes = notes
        self.scheduledFor = scheduledFor
        self.familyId = familyId
        self.queuedAt = Date()
    }
}

/// Manages offline dose queue with persistence and automatic sync
@MainActor
@Observable
final class OfflineDoseQueue {
    static let shared = OfflineDoseQueue()

    private(set) var pendingDoses: [PendingDose] = []
    private(set) var isOnline = true
    private(set) var isSyncing = false

    private let monitor = NWPathMonitor()
    private let monitorQueue = DispatchQueue(label: "com.orestsjournal.networkmonitor")
    private let userDefaultsKey = "pendingDoses"

    private var syncTask: Task<Void, Never>?

    private init() {
        loadFromDisk()
        startNetworkMonitoring()
    }

    // MARK: - Network Monitoring

    private func startNetworkMonitoring() {
        monitor.pathUpdateHandler = { [weak self] path in
            // Capture network status before entering MainActor to avoid data races
            let newOnlineStatus = path.status == .satisfied

            Task { @MainActor [weak self] in
                guard let self else { return }
                let wasOffline = !self.isOnline
                self.isOnline = newOnlineStatus

                // Sync when coming back online
                if wasOffline && newOnlineStatus {
                    self.syncPendingDoses()
                }
            }
        }
        monitor.start(queue: monitorQueue)
    }

    // MARK: - Queue Management

    /// Queue a dose for later sync (when offline)
    func queueDose(medicationId: UUID, givenAt: Date = Date(), notes: String? = nil, scheduledFor: Date? = nil, familyId: String) {
        let pendingDose = PendingDose(
            medicationId: medicationId,
            givenAt: givenAt,
            notes: notes,
            scheduledFor: scheduledFor,
            familyId: familyId
        )
        pendingDoses.append(pendingDose)
        saveToDisk()
    }

    /// Get count of pending doses
    var pendingCount: Int {
        pendingDoses.count
    }

    /// Check if there are any pending doses
    var hasPendingDoses: Bool {
        !pendingDoses.isEmpty
    }

    /// Get pending doses for a specific medication
    func pendingDoses(for medicationId: UUID) -> [PendingDose] {
        pendingDoses.filter { $0.medicationId == medicationId }
    }

    // MARK: - Sync

    /// Attempt to sync all pending doses to the server
    func syncPendingDoses() {
        guard !isSyncing, !pendingDoses.isEmpty, isOnline else { return }

        syncTask?.cancel()
        syncTask = Task {
            await performSync()
        }
    }

    private func performSync() async {
        guard !pendingDoses.isEmpty else { return }

        isSyncing = true
        defer { isSyncing = false }

        // Create a snapshot to avoid race conditions if array is modified during iteration
        let dosesToSync = pendingDoses
        var successfullySubmitted: Set<UUID> = []
        var familyIdsToInvalidate: Set<String> = []

        for dose in dosesToSync {
            // Check if task was cancelled
            if Task.isCancelled { break }

            do {
                let doseCreate = DoseCreate(
                    medicationId: dose.medicationId,
                    notes: dose.notes,
                    givenAt: dose.givenAt,
                    scheduledFor: dose.scheduledFor
                )
                _ = try await APIClient.shared.recordDose(doseCreate)
                successfullySubmitted.insert(dose.id)
                familyIdsToInvalidate.insert(dose.familyId.lowercased())
            } catch {
                // If we get an auth error or server error, stop syncing
                // If it's just this dose failing (e.g., medication deleted), continue
                print("Failed to sync dose \(dose.id): \(error)")

                // For now, continue with other doses
                continue
            }
        }

        // Remove successfully submitted doses and invalidate caches
        if !successfullySubmitted.isEmpty {
            pendingDoses.removeAll { successfullySubmitted.contains($0.id) }
            saveToDisk()

            // Invalidate medication caches for affected families
            for familyId in familyIdsToInvalidate {
                DataService.shared.invalidateMedicationsCache(for: familyId)
            }
        }
    }

    // MARK: - Persistence

    private func saveToDisk() {
        do {
            let data = try JSONEncoder().encode(pendingDoses)
            UserDefaults.standard.set(data, forKey: userDefaultsKey)
        } catch {
            print("Failed to save pending doses: \(error)")
        }
    }

    private func loadFromDisk() {
        guard let data = UserDefaults.standard.data(forKey: userDefaultsKey) else { return }
        do {
            pendingDoses = try JSONDecoder().decode([PendingDose].self, from: data)
        } catch {
            print("Failed to load pending doses: \(error)")
            pendingDoses = []
        }
    }

    /// Remove a pending dose (e.g., if user deletes it before sync)
    func removePendingDose(id: UUID) {
        pendingDoses.removeAll { $0.id == id }
        saveToDisk()
    }

    /// Clear all pending doses
    func clearAll() {
        pendingDoses.removeAll()
        saveToDisk()
    }
}
