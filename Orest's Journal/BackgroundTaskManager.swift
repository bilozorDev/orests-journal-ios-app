//
//  BackgroundTaskManager.swift
//  Orest's Journal
//
//  Manages background app refresh to keep data fresh when app is not in use.
//

import Foundation
import BackgroundTasks

/// Manages BGAppRefresh task registration and execution for background data prefetching.
final class BackgroundTaskManager {
    static let shared = BackgroundTaskManager()

    /// Background task identifier - must match Info.plist BGTaskSchedulerPermittedIdentifiers
    static let backgroundRefreshIdentifier = "com.notip.orests-journal.refresh"

    /// Minimum time between background refreshes (15 minutes is iOS minimum)
    private let minimumRefreshInterval: TimeInterval = 15 * 60

    private init() {}

    // MARK: - Public Methods

    /// Register background tasks with the system. Must be called in application(_:didFinishLaunchingWithOptions:)
    func registerBackgroundTasks() {
        BGTaskScheduler.shared.register(
            forTaskWithIdentifier: Self.backgroundRefreshIdentifier,
            using: nil
        ) { task in
            self.handleAppRefresh(task: task as! BGAppRefreshTask)
        }
        #if DEBUG
        print("BackgroundTaskManager: Registered background refresh task")
        #endif
    }

    /// Schedule the next background refresh. Call when app enters background.
    func scheduleAppRefresh() {
        let request = BGAppRefreshTaskRequest(identifier: Self.backgroundRefreshIdentifier)
        request.earliestBeginDate = Date(timeIntervalSinceNow: minimumRefreshInterval)

        do {
            try BGTaskScheduler.shared.submit(request)
            #if DEBUG
            print("BackgroundTaskManager: Scheduled background refresh for ~\(Int(minimumRefreshInterval/60)) minutes")
            #endif
        } catch {
            #if DEBUG
            print("BackgroundTaskManager: Failed to schedule background refresh: \(error)")
            #endif
        }
    }

    /// Cancel any pending background refresh tasks
    func cancelPendingRefresh() {
        BGTaskScheduler.shared.cancel(taskRequestWithIdentifier: Self.backgroundRefreshIdentifier)
        #if DEBUG
        print("BackgroundTaskManager: Cancelled pending background refresh")
        #endif
    }

    // MARK: - Private Methods

    private func handleAppRefresh(task: BGAppRefreshTask) {
        #if DEBUG
        print("BackgroundTaskManager: Starting background refresh")
        #endif

        // Schedule the next refresh first
        scheduleAppRefresh()

        // Create a task to refresh data
        let refreshTask = Task { @MainActor in
            await DataService.shared.refreshAllDataInBackground()
        }

        // Handle task expiration
        task.expirationHandler = {
            #if DEBUG
            print("BackgroundTaskManager: Background task expired, cancelling")
            #endif
            refreshTask.cancel()
        }

        // Complete the task when refresh finishes
        Task {
            await refreshTask.value
            #if DEBUG
            print("BackgroundTaskManager: Background refresh completed")
            #endif
            task.setTaskCompleted(success: true)
        }
    }
}
