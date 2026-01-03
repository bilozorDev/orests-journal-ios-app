
//
//  RecordDoseIntent.swift
//  OrestsJournalWidget
//
//  Interactive AppIntent for recording doses directly from the widget.
//  Available on iOS 17+.
//  Makes actual API call to record dose immediately so family members get notified.
//

import AppIntents
import WidgetKit
import Foundation
import Security

// MARK: - Shared Keychain Manager

/// Manages credentials shared between the main app and widget extension
/// using Keychain access groups for secure storage.
/// All methods are nonisolated to allow access from widget AppIntents.
nonisolated enum SharedKeychainManager: Sendable {
    // Shared access group - must match in both app and widget entitlements
    private static let accessGroup = "group.com.notip.orests-journal"
    private static let service = "com.notip.orests-journal.shared"

    enum Key: String, Sendable {
        case authToken = "shared_auth_token"
        case familyId = "shared_family_id"
    }

    /// Save a credential to the shared Keychain
    nonisolated static func save(_ value: String, for key: Key) {
        guard let data = value.data(using: .utf8) else { return }

        let searchQuery: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key.rawValue,
            kSecAttrAccessGroup as String: accessGroup,
        ]

        SecItemDelete(searchQuery as CFDictionary)

        let addQuery: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key.rawValue,
            kSecAttrAccessGroup as String: accessGroup,
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlock,
        ]

        SecItemAdd(addQuery as CFDictionary, nil)
    }

    /// Retrieve a credential from the shared Keychain
    nonisolated static func get(_ key: Key) -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key.rawValue,
            kSecAttrAccessGroup as String: accessGroup,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne,
        ]

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)

        guard status == errSecSuccess,
              let data = result as? Data,
              let string = String(data: data, encoding: .utf8) else {
            return nil
        }

        return string
    }

    /// Delete a credential from the shared Keychain
    nonisolated static func delete(_ key: Key) {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key.rawValue,
            kSecAttrAccessGroup as String: accessGroup,
        ]

        SecItemDelete(query as CFDictionary)
    }

    /// Delete all shared credentials (e.g., on logout)
    nonisolated static func deleteAll() {
        delete(.authToken)
        delete(.familyId)
    }
}

// MARK: - Widget API Configuration

private enum WidgetAPIConfig {
    /// Get the API base URL from App Group (synced from main app)
    static var baseURL: String? {
        WidgetDataManager.shared.getAPIBaseURL()
    }
}

// MARK: - Pending Dose Queue Keys

nonisolated private enum PendingDoseKey: Sendable {
    static let queue = "pending_dose_queue"
}

// MARK: - Pending Dose Manager

/// Manages the queue of doses waiting to be recorded
/// Thread-safe for access from widget AppIntents
nonisolated final class PendingDoseManager: @unchecked Sendable {
    static let shared = PendingDoseManager()

    private let userDefaults: UserDefaults?
    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()

    init() {
        userDefaults = UserDefaults(suiteName: "group.com.notip.orests-journal")
        encoder.dateEncodingStrategy = .iso8601
        decoder.dateDecodingStrategy = .iso8601
    }

    /// Add a dose to the pending queue
    nonisolated func queueDose(_ dose: WidgetPendingDose) {
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
    nonisolated func getPendingDoses() -> [WidgetPendingDose] {
        guard let data = userDefaults?.data(forKey: PendingDoseKey.queue) else {
            return []
        }
        return (try? decoder.decode([WidgetPendingDose].self, from: data)) ?? []
    }

    /// Remove a dose from the queue (after processing)
    nonisolated func removeDose(_ dose: WidgetPendingDose) {
        var queue = getPendingDoses()
        queue.removeAll { $0.id == dose.id }
        savePendingDoses(queue)
    }

    /// Remove a dose by medication ID (after processing)
    nonisolated func removeDose(forMedicationId medicationId: UUID) {
        var queue = getPendingDoses()
        queue.removeAll { $0.medicationId == medicationId }
        savePendingDoses(queue)
    }

    /// Clear all pending doses
    nonisolated func clearAll() {
        userDefaults?.removeObject(forKey: PendingDoseKey.queue)
    }

    /// Clean up old pending doses (older than 1 hour)
    nonisolated func cleanupOldDoses() {
        var queue = getPendingDoses()
        let oneHourAgo = Date().addingTimeInterval(-3600)
        queue.removeAll { $0.requestedAt < oneHourAgo }
        savePendingDoses(queue)
    }

    nonisolated private func savePendingDoses(_ doses: [WidgetPendingDose]) {
        if let data = try? encoder.encode(doses) {
            userDefaults?.set(data, forKey: PendingDoseKey.queue)
        }
    }
}

// MARK: - Widget API Client

/// Lightweight API client for making authenticated requests from the widget
private enum WidgetAPIClient {
    /// Record a dose via API
    static func recordDose(
        medicationId: UUID,
        familyId: String,
        authToken: String,
        notes: String?,
        scheduledFor: Date?
    ) async throws {
        guard let baseURL = WidgetAPIConfig.baseURL else {
            throw WidgetAPIError.noAPIURL
        }

        guard let url = URL(string: "\(baseURL)/doses?family_id=\(familyId)") else {
            throw WidgetAPIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("Bearer \(authToken)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 15  // Widgets have limited execution time

        // Build request body
        var body: [String: Any] = [
            "medication_id": medicationId.uuidString.lowercased()
        ]
        if let notes = notes {
            body["notes"] = notes
        }
        if let scheduledFor = scheduledFor {
            let formatter = ISO8601DateFormatter()
            formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            body["scheduled_for"] = formatter.string(from: scheduledFor)
        }

        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw WidgetAPIError.invalidResponse
        }

        switch httpResponse.statusCode {
        case 200...299:
            #if DEBUG
            print("✅ [Widget API] Dose recorded successfully")
            #endif
            return
        case 401:
            throw WidgetAPIError.unauthorized
        default:
            let message = String(data: data, encoding: .utf8) ?? "Unknown error"
            #if DEBUG
            print("❌ [Widget API] Error \(httpResponse.statusCode): \(message)")
            #endif
            throw WidgetAPIError.httpError(statusCode: httpResponse.statusCode, message: message)
        }
    }

    enum WidgetAPIError: Error, LocalizedError {
        case invalidURL
        case invalidResponse
        case unauthorized
        case httpError(statusCode: Int, message: String)
        case noCredentials
        case noAPIURL

        var errorDescription: String? {
            switch self {
            case .invalidURL:
                return "Invalid URL"
            case .invalidResponse:
                return "Invalid response"
            case .unauthorized:
                return "Please open the app to re-authenticate"
            case .httpError(let code, let message):
                return "Error \(code): \(message)"
            case .noCredentials:
                return "Please open the app to sign in"
            case .noAPIURL:
                return "Please open the app first"
            }
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

        // Get credentials from shared keychain
        let authToken = SharedKeychainManager.get(.authToken)
        let familyId = SharedKeychainManager.get(.familyId)

        guard let authToken, let familyId else {
            #if DEBUG
            print("⚠️ [Widget] No credentials - falling back to queue")
            #endif
            // Fall back to queuing for later if no credentials
            await queueAndUpdateWidget(medId: medId)
            return .result()
        }

        #if DEBUG
        print("📱 [Widget] Recording dose for \(medicationName) via API...")
        #endif

        do {
            // Make actual API call to record the dose
            try await WidgetAPIClient.recordDose(
                medicationId: medId,
                familyId: familyId,
                authToken: authToken,
                notes: "Recorded from widget",
                scheduledFor: scheduledFor
            )

            // Update widget data to show success
            await MainActor.run {
                WidgetDataManager.shared.markDoseAsGiven(
                    medicationId: medId,
                    scheduledTime: scheduledFor,
                    givenBy: "You"
                )
            }

            // Signal app to refresh when opened (dose was recorded via API)
            WidgetDataManager.shared.setNeedsRefresh()

            // Refresh widget to show success state
            WidgetCenter.shared.reloadTimelines(ofKind: "NextDoseWidget")

            #if DEBUG
            print("✅ [Widget] Dose recorded and widget updated")
            #endif

            return .result()

        } catch WidgetAPIClient.WidgetAPIError.unauthorized {
            // Token expired - queue for later and suggest opening app
            #if DEBUG
            print("⚠️ [Widget] Auth expired - queuing dose")
            #endif
            await queueAndUpdateWidget(medId: medId)
            return .result()

        } catch {
            // Network error or other failure - queue for later
            #if DEBUG
            print("⚠️ [Widget] API failed: \(error) - queuing dose")
            #endif
            await queueAndUpdateWidget(medId: medId)
            return .result()
        }
    }

    /// Queue the dose and update widget optimistically
    private func queueAndUpdateWidget(medId: UUID) async {
        let pendingDose = WidgetPendingDose(
            medicationId: medId,
            medicationName: medicationName,
            petName: petName,
            scheduledFor: scheduledFor
        )
        PendingDoseManager.shared.queueDose(pendingDose)

        // Still update widget optimistically
        await MainActor.run {
            WidgetDataManager.shared.markDoseAsGiven(
                medicationId: medId,
                scheduledTime: scheduledFor,
                givenBy: "You"
            )
        }

        WidgetCenter.shared.reloadTimelines(ofKind: "NextDoseWidget")
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
