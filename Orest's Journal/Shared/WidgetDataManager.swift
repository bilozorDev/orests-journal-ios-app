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

enum AppGroup {
    static let identifier = "group.com.notip.orests-journal"

    static var containerURL: URL? {
        FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: identifier)
    }

    static var userDefaults: UserDefaults? {
        UserDefaults(suiteName: identifier)
    }
}

// MARK: - Widget Data Keys

private enum WidgetDataKey {
    static let nextDoses = "widget_next_doses"
    static let lastUpdated = "widget_last_updated"
}

// MARK: - Widget Data Models

/// Simplified medication info for widget display
struct WidgetMedicationInfo: Codable, Identifiable {
    let id: UUID
    let name: String
    let dosage: String?
    let iconName: String
    let petName: String
    let petId: UUID
}

/// A scheduled dose for widget display
struct WidgetDoseInfo: Codable, Identifiable {
    var id: String { "\(medicationId)-\(scheduledTime.timeIntervalSince1970)" }
    let medicationId: UUID
    let medicationName: String
    let dosage: String?
    let iconName: String
    let petName: String
    let scheduledTime: Date
    let isOverdue: Bool

    /// Time until dose (negative if overdue)
    var timeUntil: TimeInterval {
        scheduledTime.timeIntervalSinceNow
    }

    /// Formatted time string
    var formattedTime: String {
        let formatter = DateFormatter()
        formatter.timeStyle = .short
        return formatter.string(from: scheduledTime)
    }

    /// Relative time description (e.g., "in 2h 30m" or "30m ago")
    var relativeTimeDescription: String {
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
struct WidgetData: Codable {
    let nextDoses: [WidgetDoseInfo]
    let lastUpdated: Date

    /// The most urgent upcoming dose
    var primaryDose: WidgetDoseInfo? {
        nextDoses.first
    }

    /// Check if data is stale (older than 15 minutes)
    var isStale: Bool {
        Date().timeIntervalSince(lastUpdated) > 15 * 60
    }
}

// MARK: - Widget Data Manager

final class WidgetDataManager {
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

    // MARK: - Helpers for Main App

    /// Build widget dose info from medication and scheduled time
    static func buildDoseInfo(
        medication: Medication,
        petName: String,
        scheduledTime: Date
    ) -> WidgetDoseInfo {
        WidgetDoseInfo(
            medicationId: medication.id,
            medicationName: medication.name,
            dosage: medication.dosage,
            iconName: medication.medicationType.icon,
            petName: petName,
            scheduledTime: scheduledTime,
            isOverdue: scheduledTime < Date()
        )
    }

    /// Calculate next scheduled times for a medication today/tomorrow
    static func calculateNextDoseTimes(
        for medication: Medication,
        petName: String,
        maxCount: Int = 3
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

        // Check today and tomorrow
        for dayOffset in 0...1 {
            guard let targetDate = calendar.date(byAdding: .day, value: dayOffset, to: now) else {
                continue
            }

            for scheduledTime in scheduledTimes {
                var components = calendar.dateComponents([.year, .month, .day], from: targetDate)
                components.hour = scheduledTime.scheduledHour
                components.minute = scheduledTime.scheduledMinute

                guard let doseTime = calendar.date(from: components) else {
                    continue
                }

                // Include if in the future or within last hour (to show overdue)
                let hourAgo = now.addingTimeInterval(-3600)
                if doseTime > hourAgo {
                    doses.append(buildDoseInfo(
                        medication: medication,
                        petName: petName,
                        scheduledTime: doseTime
                    ))
                }
            }
        }

        // Sort by time and limit
        return doses
            .sorted { $0.scheduledTime < $1.scheduledTime }
            .prefix(maxCount)
            .map { $0 }
    }
}
