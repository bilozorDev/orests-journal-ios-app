//
//  LocalMedicationReminderManager.swift
//  Orest's Journal
//
//  Manages local notifications as a fallback for medication reminders.
//  These fire even when offline or if push notifications fail.
//

import Foundation
import UserNotifications

@MainActor
final class LocalMedicationReminderManager {
    static let shared = LocalMedicationReminderManager()

    private let notificationCenter = UNUserNotificationCenter.current()

    /// Identifier prefix for medication reminder notifications
    private let reminderPrefix = "med_reminder_"

    private init() {}

    // MARK: - Public Methods

    /// Schedule local notifications for a medication with reminders enabled
    /// - Parameters:
    ///   - medication: The medication to schedule reminders for
    ///   - petName: The name of the pet (for notification text)
    func scheduleReminders(for medication: Medication, petName: String) async {
        // Only schedule if reminders are enabled and medication is active
        guard medication.remindersEnabled,
              !medication.isArchived,
              medication.isActive,
              let scheduledTimes = medication.scheduledTimes,
              !scheduledTimes.isEmpty else {
            return
        }

        // First cancel any existing reminders for this medication
        await cancelReminders(for: medication.id)

        // Schedule a notification for each scheduled time
        for scheduledTime in scheduledTimes {
            await scheduleNotification(
                medicationId: medication.id,
                scheduleId: scheduledTime.id,
                hour: scheduledTime.scheduledHour,
                minute: scheduledTime.scheduledMinute,
                medicationName: medication.displayName,
                petName: petName
            )
        }
    }

    /// Cancel all local notifications for a medication
    /// - Parameter medicationId: The medication ID to cancel reminders for
    func cancelReminders(for medicationId: UUID) async {
        let prefix = reminderPrefix + medicationId.uuidString

        // Get all pending notifications
        let pendingRequests = await notificationCenter.pendingNotificationRequests()

        // Find notifications matching this medication
        let identifiersToRemove = pendingRequests
            .filter { $0.identifier.hasPrefix(prefix) }
            .map { $0.identifier }

        if !identifiersToRemove.isEmpty {
            notificationCenter.removePendingNotificationRequests(withIdentifiers: identifiersToRemove)
        }
    }

    /// Update reminders for a medication (cancel old and schedule new)
    /// - Parameters:
    ///   - medication: The updated medication
    ///   - petName: The name of the pet
    func updateReminders(for medication: Medication, petName: String) async {
        await cancelReminders(for: medication.id)

        if medication.remindersEnabled && !medication.isArchived {
            await scheduleReminders(for: medication, petName: petName)
        }
    }

    /// Cancel all medication reminders (e.g., on sign out)
    func cancelAllReminders() async {
        let pendingRequests = await notificationCenter.pendingNotificationRequests()

        let identifiersToRemove = pendingRequests
            .filter { $0.identifier.hasPrefix(reminderPrefix) }
            .map { $0.identifier }

        if !identifiersToRemove.isEmpty {
            notificationCenter.removePendingNotificationRequests(withIdentifiers: identifiersToRemove)
        }
    }

    /// Schedule reminders for all medications with reminders enabled
    /// Call this on app launch or after sign in
    /// - Parameter medications: List of medications to schedule
    /// - Parameter petNames: Dictionary mapping pet IDs to pet names
    func scheduleAllReminders(medications: [Medication], petNames: [UUID: String]) async {
        for medication in medications {
            guard let petName = petNames[medication.petId] else { continue }
            await scheduleReminders(for: medication, petName: petName)
        }
    }

    // MARK: - Private Methods

    private func scheduleNotification(
        medicationId: UUID,
        scheduleId: UUID,
        hour: Int,
        minute: Int,
        medicationName: String,
        petName: String
    ) async {
        let content = UNMutableNotificationContent()
        content.title = "Medication Reminder"
        content.body = "Time to give \(petName) their \(medicationName)"
        content.sound = .default
        content.categoryIdentifier = "MEDICATION_REMINDER"
        content.userInfo = [
            "type": "medication_reminder",
            "medication_id": medicationId.uuidString,
            "is_local": true
        ]

        // Create date components trigger for daily repeat
        var dateComponents = DateComponents()
        dateComponents.hour = hour
        dateComponents.minute = minute

        let trigger = UNCalendarNotificationTrigger(
            dateMatching: dateComponents,
            repeats: true
        )

        // Create unique identifier for this specific schedule
        let identifier = "\(reminderPrefix)\(medicationId.uuidString)_\(scheduleId.uuidString)"

        let request = UNNotificationRequest(
            identifier: identifier,
            content: content,
            trigger: trigger
        )

        do {
            try await notificationCenter.add(request)
            #if DEBUG
            print("Scheduled local reminder for \(medicationName) at \(hour):\(String(format: "%02d", minute))")
            #endif
        } catch {
            #if DEBUG
            print("Failed to schedule local reminder: \(error)")
            #endif
        }
    }
}
