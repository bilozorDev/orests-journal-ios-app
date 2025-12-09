//
//  NotificationManager.swift
//  Orest's Journal
//
//  Manages push notification registration and handling.
//

import Foundation
import UserNotifications
import UIKit

@MainActor
@Observable
final class NotificationManager {
    static let shared = NotificationManager()

    var isAuthorized = false
    var deviceToken: String?

    private init() {}

    // MARK: - Public Methods

    /// Request notification permissions and register for push notifications
    func requestAuthorization() async {
        let center = UNUserNotificationCenter.current()

        do {
            let granted = try await center.requestAuthorization(options: [.alert, .sound, .badge])
            isAuthorized = granted

            if granted {
                registerForRemoteNotifications()
            }
        } catch {
            print("Failed to request notification authorization: \(error)")
        }
    }

    /// Check current authorization status
    func checkAuthorizationStatus() async {
        let center = UNUserNotificationCenter.current()
        let settings = await center.notificationSettings()
        isAuthorized = settings.authorizationStatus == .authorized
    }

    /// Register device token with backend
    func registerDeviceTokenWithBackend(_ tokenString: String) async {
        self.deviceToken = tokenString

        // Only register if user is authenticated
        guard AuthManager.shared.isAuthenticated else {
            return
        }

        do {
            let deviceName = UIDevice.current.name
            _ = try await APIClient.shared.registerDeviceToken(token: tokenString, deviceName: deviceName)
        } catch {
            #if DEBUG
            print("Failed to register device token: \(error)")
            #endif
        }
    }

    /// Unregister device token from backend (call on sign out)
    func unregisterDeviceToken() async {
        guard let token = deviceToken else { return }

        do {
            try await APIClient.shared.unregisterDeviceToken(token: token)
        } catch {
            #if DEBUG
            print("Failed to unregister device token: \(error)")
            #endif
        }

        deviceToken = nil
    }

    /// Re-register device token after authentication
    func registerAfterAuthentication() async {
        // Check current authorization status first (doesn't prompt user)
        await checkAuthorizationStatus()

        if let token = deviceToken {
            // Already have a token, just register with backend
            await registerDeviceTokenWithBackend(token)
        } else if isAuthorized {
            // Already authorized, request new token from APNs
            registerForRemoteNotifications()
        } else {
            // Not authorized yet - request permission (prompts user only if status is .notDetermined)
            await requestAuthorization()
        }
    }

    // MARK: - Private Methods

    private func registerForRemoteNotifications() {
        UIApplication.shared.registerForRemoteNotifications()
    }
}

// MARK: - AppDelegate for Push Notifications

class AppDelegate: NSObject, UIApplicationDelegate, UNUserNotificationCenterDelegate {

    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        // Set notification delegate
        UNUserNotificationCenter.current().delegate = self

        // Register background refresh task
        BackgroundTaskManager.shared.registerBackgroundTasks()

        return true
    }

    // Called when APNs successfully registers and provides device token
    func application(
        _ application: UIApplication,
        didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data
    ) {
        let tokenString = deviceToken.map { String(format: "%02.2hhx", $0) }.joined()

        Task { @MainActor in
            await NotificationManager.shared.registerDeviceTokenWithBackend(tokenString)
        }
    }

    // Called when APNs registration fails
    func application(
        _ application: UIApplication,
        didFailToRegisterForRemoteNotificationsWithError error: Error
    ) {
        #if DEBUG
        print("Failed to register for remote notifications: \(error)")
        #endif
    }

    // MARK: - UNUserNotificationCenterDelegate

    // Handle notifications when app is in foreground
    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        willPresent notification: UNNotification,
        withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void
    ) {
        let userInfo = notification.request.content.userInfo

        // Invalidate caches based on notification type
        Task { @MainActor in
            handleCacheInvalidation(userInfo: userInfo)
        }

        // Show notification even when app is in foreground
        completionHandler([.banner, .sound, .badge])
    }

    private func handleCacheInvalidation(userInfo: [AnyHashable: Any]) {
        // Extract notification type from userInfo or nested data
        var notificationType: String?
        var familyId: String?

        if let type = userInfo["type"] as? String {
            notificationType = type
            familyId = userInfo["family_id"] as? String
        } else if let data = userInfo["data"] as? [String: Any],
                  let type = data["type"] as? String {
            notificationType = type
            familyId = data["family_id"] as? String
        }

        // Invalidate family cache when family membership changes
        guard let type = notificationType else { return }

        switch type {
        case "member_joined", "member_removed", "role_changed":
            if let familyId = familyId {
                DataService.shared.invalidateFamilyCache(for: familyId)
                // Also tell the view to refresh when it becomes visible
                NavigationManager.shared.requestTabRefresh(.family)
            }
        default:
            break
        }
    }

    // Handle notification tap
    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        didReceive response: UNNotificationResponse,
        withCompletionHandler completionHandler: @escaping () -> Void
    ) {
        let userInfo = response.notification.request.content.userInfo

        // Invalidate caches based on notification type (in case app was in background)
        Task { @MainActor in
            handleCacheInvalidation(userInfo: userInfo)
        }

        // Handle notification based on type - check both top-level and nested in "data"
        var notificationType: String?
        var notificationData: [AnyHashable: Any] = userInfo

        if let type = userInfo["type"] as? String {
            notificationType = type
        } else if let data = userInfo["data"] as? [String: Any],
                  let type = data["type"] as? String {
            notificationType = type
            // Merge data into notificationData for easier access
            for (key, value) in data {
                notificationData[key] = value
            }
        }

        if let type = notificationType {
            handleNotificationTap(type: type, userInfo: notificationData)
        }

        completionHandler()
    }

    private func handleNotificationTap(type: String, userInfo: [AnyHashable: Any]) {
        switch type {
        case "medication_reminder", "missed_dose":
            // Could navigate to medication detail or record dose screen
            // TODO: Implement medication navigation
            break
        case "member_joined":
            // Use deep link URL - onOpenURL fires after app is fully ready
            if let url = URL(string: "orestsjournal://family?refresh=true") {
                UIApplication.shared.open(url)
            }
        default:
            break
        }
    }
}
