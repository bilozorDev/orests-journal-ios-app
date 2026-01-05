//
//  WidgetDataManager.swift
//  Orest's Journal
//
//  Manages shared data between the main app and widget via App Groups.
//  This file should be included in both the main app and widget extension targets.
//

import Foundation
import WidgetKit

// MARK: - App Group Constants

nonisolated enum AppGroup: Sendable {
    static let identifier = "group.com.notip.orests-journal"

    static var containerURL: URL? {
        FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: identifier)
    }

    static var userDefaults: UserDefaults? {
        UserDefaults(suiteName: identifier)
    }
}

// MARK: - Widget Data Keys

nonisolated private enum WidgetDataKey: Sendable {
    static let nextDoses = "widget_next_doses"
    static let lastUpdated = "widget_last_updated"
    static let pendingDoseQueue = "pending_dose_queue"
    static let apiBaseURL = "widget_api_base_url"
    static let needsRefresh = "widget_needs_refresh"  // Signal app to refresh after widget API call
    static let needsReauth = "widget_needs_reauth"  // Signal to show auth required indicator
}

// MARK: - Widget Pending Dose Model (shared between app and widget)

/// A dose waiting to be recorded by the main app (from widget interaction)
/// Named differently from OfflineDoseQueue's PendingDose to avoid conflicts
struct WidgetPendingDose: Codable, Identifiable, Sendable {
    let id: UUID
    let medicationId: UUID
    let medicationName: String
    let petName: String
    let scheduledFor: Date?  // Links dose to specific schedule slot
    let requestedAt: Date

    nonisolated init(medicationId: UUID, medicationName: String, petName: String, scheduledFor: Date? = nil) {
        self.id = UUID()
        self.medicationId = medicationId
        self.medicationName = medicationName
        self.petName = petName
        self.scheduledFor = scheduledFor
        self.requestedAt = Date()
    }
}

// MARK: - Widget Formatters

/// Static formatters to avoid recreating expensive DateFormatter instances
nonisolated private enum WidgetFormatters: Sendable {
    // Use nonisolated(unsafe) for mutable formatter - safe because DateFormatter is thread-safe for formatting
    nonisolated(unsafe) static let shortTime: DateFormatter = {
        let formatter = DateFormatter()
        formatter.timeStyle = .short
        return formatter
    }()
}

// MARK: - Widget Data Models

/// Simplified medication info for widget display
struct WidgetMedicationInfo: Codable, Identifiable, Sendable {
    let id: UUID
    let name: String
    let dosage: String?
    let iconName: String
    let petName: String
    let petId: UUID
}

/// A scheduled dose for widget display
struct WidgetDoseInfo: Codable, Identifiable, Sendable {
    nonisolated var id: String { "\(medicationId)-\(scheduledTime.timeIntervalSince1970)" }
    let medicationId: UUID
    let medicationName: String
    let dosage: String?
    let iconName: String
    let petName: String
    let scheduledTime: Date
    let isOverdue: Bool

    // Completion status
    let isGiven: Bool
    let givenBy: String?
    let givenAt: Date?

    /// Time until dose (negative if overdue)
    nonisolated var timeUntil: TimeInterval {
        scheduledTime.timeIntervalSinceNow
    }

    /// Formatted time string
    nonisolated var formattedTime: String {
        WidgetFormatters.shortTime.string(from: scheduledTime)
    }

    /// Formatted given time string
    nonisolated var formattedGivenTime: String? {
        guard let givenAt else { return nil }
        return WidgetFormatters.shortTime.string(from: givenAt)
    }

    /// Relative time description (e.g., "in 2h 30m" or "30m ago")
    nonisolated var relativeTimeDescription: String {
        // If given, show when it was given
        if isGiven, let givenAt {
            let interval = Date().timeIntervalSince(givenAt)
            let hours = Int(interval) / 3600
            let minutes = (Int(interval) % 3600) / 60

            if hours > 0 {
                return "\(hours)h \(minutes)m ago"
            } else if minutes > 0 {
                return "\(minutes)m ago"
            } else {
                return "just now"
            }
        }

        let interval = timeUntil
        let absInterval = abs(interval)

        let hours = Int(absInterval) / 3600
        let minutes = (Int(absInterval) % 3600) / 60

        var timeString: String
        if hours > 0 {
            timeString = "\(hours)h \(minutes)m"
        } else {
            timeString = "\(minutes)m"
        }

        if interval < 0 {
            return "\(timeString) ago"
        } else {
            return "in \(timeString)"
        }
    }
}

/// Container for all widget data
struct WidgetData: Codable, Sendable {
    let nextDoses: [WidgetDoseInfo]
    let lastUpdated: Date

    /// The most urgent upcoming dose
    nonisolated var primaryDose: WidgetDoseInfo? {
        nextDoses.first
    }

    /// Check if data is stale (older than 15 minutes)
    nonisolated var isStale: Bool {
        Date().timeIntervalSince(lastUpdated) > 15 * 60
    }
}

// MARK: - Widget Data Manager

nonisolated final class WidgetDataManager: @unchecked Sendable {
    static let shared = WidgetDataManager()

    private let userDefaults: UserDefaults?
    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()

    private init() {
        userDefaults = AppGroup.userDefaults
        encoder.dateEncodingStrategy = .iso8601
        decoder.dateDecodingStrategy = .iso8601

        #if DEBUG
        if userDefaults == nil {
            print("⚠️ [Widget] App Group UserDefaults is nil! Check App Group configuration.")
        } else {
            print("✅ [Widget] App Group UserDefaults initialized: \(AppGroup.identifier)")
        }
        #endif
    }

    // MARK: - Read Data (for Widget)

    /// Get the current widget data
    func getWidgetData() -> WidgetData? {
        guard let data = userDefaults?.data(forKey: WidgetDataKey.nextDoses) else {
            return nil
        }
        return try? decoder.decode(WidgetData.self, from: data)
    }

    // MARK: - Write Data (from Main App)

    /// Update widget data with upcoming doses
    func updateNextDoses(_ doses: [WidgetDoseInfo]) {
        #if DEBUG
        print("📱 [Widget] updateNextDoses called with \(doses.count) doses")
        for dose in doses {
            print("   - \(dose.medicationName) for \(dose.petName) at \(dose.formattedTime)")
        }
        #endif

        guard userDefaults != nil else {
            #if DEBUG
            print("⚠️ [Widget] Cannot save - userDefaults is nil")
            #endif
            return
        }

        let widgetData = WidgetData(nextDoses: doses, lastUpdated: Date())

        if let data = try? encoder.encode(widgetData) {
            userDefaults?.set(data, forKey: WidgetDataKey.nextDoses)
            #if DEBUG
            print("✅ [Widget] Saved \(data.count) bytes to App Group")
            #endif
        } else {
            #if DEBUG
            print("❌ [Widget] Failed to encode widget data")
            #endif
        }

        // Trigger widget refresh
        WidgetCenter.shared.reloadTimelines(ofKind: "NextDoseWidget")
    }

    /// Clear all widget data (e.g., on logout)
    func clearWidgetData() {
        userDefaults?.removeObject(forKey: WidgetDataKey.nextDoses)
        WidgetCenter.shared.reloadTimelines(ofKind: "NextDoseWidget")
    }

    // MARK: - API Configuration (for Widget API calls)

    /// Set the API base URL (called from main app on launch)
    func setAPIBaseURL(_ url: String) {
        userDefaults?.set(url, forKey: WidgetDataKey.apiBaseURL)
        #if DEBUG
        print("✅ [Widget] API base URL set: \(url)")
        #endif
    }

    /// Get the API base URL (called from widget intent)
    /// Marked nonisolated to allow access from widget AppIntent
    nonisolated func getAPIBaseURL() -> String? {
        AppGroup.userDefaults?.string(forKey: WidgetDataKey.apiBaseURL)
    }

    // MARK: - Widget-to-App Refresh Signal

    /// Mark that a dose was recorded from widget and app should refresh (called from widget)
    nonisolated func setNeedsRefresh() {
        AppGroup.userDefaults?.set(true, forKey: WidgetDataKey.needsRefresh)
        #if DEBUG
        print("📱 [Widget] Set needs refresh flag")
        #endif
    }

    /// Check if app needs to refresh after widget action (called from app)
    nonisolated func checkAndClearNeedsRefresh() -> Bool {
        let needsRefresh = AppGroup.userDefaults?.bool(forKey: WidgetDataKey.needsRefresh) ?? false
        if needsRefresh {
            AppGroup.userDefaults?.set(false, forKey: WidgetDataKey.needsRefresh)
            #if DEBUG
            print("📱 [App] Clearing needs refresh flag - will refresh data")
            #endif
        }
        return needsRefresh
    }

    // MARK: - Auth Status for Widget

    /// Mark that the widget encountered an auth error (called from widget intent)
    nonisolated func setNeedsReauth() {
        AppGroup.userDefaults?.set(true, forKey: WidgetDataKey.needsReauth)
        #if DEBUG
        print("📱 [Widget] Set needs reauth flag")
        #endif
    }

    /// Check if widget is showing auth error state (called from widget provider)
    nonisolated func getNeedsReauth() -> Bool {
        AppGroup.userDefaults?.bool(forKey: WidgetDataKey.needsReauth) ?? false
    }

    /// Clear the reauth flag when user logs in (called from app after successful auth)
    nonisolated func clearNeedsReauth() {
        AppGroup.userDefaults?.set(false, forKey: WidgetDataKey.needsReauth)
        WidgetCenter.shared.reloadTimelines(ofKind: "NextDoseWidget")
        #if DEBUG
        print("📱 [App] Cleared needs reauth flag")
        #endif
    }

    // MARK: - Optimistic UI Update (from Widget Intent)

    /// Mark a dose as given in widget data (optimistic UI update).
    /// Called from RecordDoseIntent when user taps "Give" in widget.
    /// The actual API call happens when the main app processes the pending queue.
    func markDoseAsGiven(medicationId: UUID, scheduledTime: Date?, givenBy: String) {
        guard let widgetData = getWidgetData() else {
            #if DEBUG
            print("⚠️ [Widget] Cannot mark dose - no widget data")
            #endif
            return
        }

        let now = Date()
        let updatedDoses = widgetData.nextDoses.map { dose -> WidgetDoseInfo in
            // Match by medication ID and scheduled time
            let matchesMedication = dose.medicationId == medicationId

            // Match scheduled time if provided, otherwise match closest pending dose
            let matchesTime: Bool
            if let scheduledTime = scheduledTime {
                let calendar = Calendar.current
                matchesTime = calendar.isDate(dose.scheduledTime, equalTo: scheduledTime, toGranularity: .minute)
            } else {
                // No specific time - match first pending dose for this medication
                matchesTime = !dose.isGiven
            }

            if matchesMedication && matchesTime && !dose.isGiven {
                // Return updated dose marked as given
                return WidgetDoseInfo(
                    medicationId: dose.medicationId,
                    medicationName: dose.medicationName,
                    dosage: dose.dosage,
                    iconName: dose.iconName,
                    petName: dose.petName,
                    scheduledTime: dose.scheduledTime,
                    isOverdue: false,
                    isGiven: true,
                    givenBy: givenBy,
                    givenAt: now
                )
            }
            return dose
        }

        // Save updated data
        let updatedWidgetData = WidgetData(nextDoses: updatedDoses, lastUpdated: Date())
        if let data = try? encoder.encode(updatedWidgetData) {
            userDefaults?.set(data, forKey: WidgetDataKey.nextDoses)
            #if DEBUG
            print("✅ [Widget] Marked dose as given for medication \(medicationId)")
            #endif
        }
    }

    // MARK: - Helpers for Main App

    /// Information about a recorded dose for matching with scheduled times
    struct RecordedDoseInfo {
        let givenAt: Date
        let givenBy: String
        let scheduledFor: Date?  // The schedule slot this dose was for
    }

    /// Build widget dose info from medication and scheduled time
    static func buildDoseInfo(
        medication: Medication,
        petName: String,
        scheduledTime: Date,
        recordedDose: RecordedDoseInfo? = nil
    ) -> WidgetDoseInfo {
        let isGiven = recordedDose != nil
        let isOverdue = !isGiven && scheduledTime < Date()

        return WidgetDoseInfo(
            medicationId: medication.id,
            medicationName: medication.displayName,
            dosage: medication.dosage,
            iconName: medication.medicationType.icon,
            petName: petName,
            scheduledTime: scheduledTime,
            isOverdue: isOverdue,
            isGiven: isGiven,
            givenBy: recordedDose?.givenBy,
            givenAt: recordedDose?.givenAt
        )
    }

    /// Calculate scheduled times for a medication today, marking given doses
    /// - Parameters:
    ///   - medication: The medication to calculate doses for
    ///   - petName: Name of the pet
    ///   - todayDoses: Doses recorded today for this medication
    ///   - maxCount: Maximum number of doses to return
    static func calculateTodaySchedule(
        for medication: Medication,
        petName: String,
        todayDoses: [RecordedDoseInfo] = [],
        maxCount: Int = 5
    ) -> [WidgetDoseInfo] {
        guard !medication.isAsNeeded,
              !medication.isArchived,
              medication.isActive,
              let scheduledTimes = medication.scheduledTimes,
              !scheduledTimes.isEmpty else {
            return []
        }

        let calendar = Calendar.current
        let now = Date()
        var doses: [WidgetDoseInfo] = []

        // Sort scheduled times chronologically
        let sortedScheduledTimes = scheduledTimes.sorted {
            ($0.scheduledHour, $0.scheduledMinute) < ($1.scheduledHour, $1.scheduledMinute)
        }

        for scheduledTime in sortedScheduledTimes {
            var components = calendar.dateComponents([.year, .month, .day], from: now)
            components.hour = scheduledTime.scheduledHour
            components.minute = scheduledTime.scheduledMinute

            guard let doseTime = calendar.date(from: components) else {
                continue
            }

            // Find dose with matching scheduledFor
            let matchingDose = todayDoses.first { dose in
                guard let scheduledFor = dose.scheduledFor else { return false }
                return calendar.isDate(scheduledFor, equalTo: doseTime, toGranularity: .minute)
            }

            // Include doses from 6 hours ago onwards
            let sixHoursAgo = now.addingTimeInterval(-6 * 3600)
            if doseTime > sixHoursAgo {
                doses.append(buildDoseInfo(
                    medication: medication,
                    petName: petName,
                    scheduledTime: doseTime,
                    recordedDose: matchingDose
                ))
            }
        }

        // Sort by time and limit
        return doses
            .sorted { $0.scheduledTime < $1.scheduledTime }
            .prefix(maxCount)
            .map { $0 }
    }
}
