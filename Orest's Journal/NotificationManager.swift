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
        print("📱 Device token received: \(tokenString.prefix(20))...")

        // Only register if user is authenticated
        guard AuthManager.shared.isAuthenticated else {
            print("⏳ User not authenticated, will register token after login")
            return
        }

        do {
            let deviceName = UIDevice.current.name
            print("📤 Registering device token with backend...")
            let _ = try await APIClient.shared.registerDeviceToken(token: tokenString, deviceName: deviceName)
            print("✅ Device token registered with backend successfully")
        } catch {
            print("❌ Failed to register device token: \(error)")
        }
    }

    /// Unregister device token from backend (call on sign out)
    func unregisterDeviceToken() async {
        guard let token = deviceToken else { return }

        do {
            try await APIClient.shared.unregisterDeviceToken(token: token)
            print("Device token unregistered from backend")
        } catch {
            print("Failed to unregister device token: \(error)")
        }

        deviceToken = nil
    }

    /// Re-register device token after authentication
    func registerAfterAuthentication() async {
        print("🔐 registerAfterAuthentication called - deviceToken: \(deviceToken != nil ? "exists" : "nil"), isAuthorized: \(isAuthorized)")

        // Check current authorization status first (doesn't prompt user)
        await checkAuthorizationStatus()

        if let token = deviceToken {
            // Already have a token, just register with backend
            await registerDeviceTokenWithBackend(token)
        } else if isAuthorized {
            // Already authorized, request new token from APNs
            print("📲 Requesting new device token from APNs...")
            registerForRemoteNotifications()
        } else {
            // Not authorized yet - request permission (prompts user only if status is .notDetermined)
            print("🔔 Requesting notification authorization...")
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
        print("🚀 [AppDelegate] didFinishLaunchingWithOptions")

        // Set notification delegate
        UNUserNotificationCenter.current().delegate = self
        print("🚀 [AppDelegate] Set UNUserNotificationCenter delegate")

        // Register background refresh task
        BackgroundTaskManager.shared.registerBackgroundTasks()

        // Check if launched from notification
        if let notificationResponse = launchOptions?[.remoteNotification] as? [AnyHashable: Any] {
            print("🚀 [AppDelegate] Launched from notification: \(notificationResponse)")
        }

        return true
    }

    // Called when APNs successfully registers and provides device token
    func application(
        _ application: UIApplication,
        didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data
    ) {
        let tokenString = deviceToken.map { String(format: "%02.2hhx", $0) }.joined()
        print("Device token: \(tokenString)")

        Task { @MainActor in
            await NotificationManager.shared.registerDeviceTokenWithBackend(tokenString)
        }
    }

    // Called when APNs registration fails
    func application(
        _ application: UIApplication,
        didFailToRegisterForRemoteNotificationsWithError error: Error
    ) {
        print("❌ Failed to register for remote notifications: \(error.localizedDescription)")
        print("❌ Error details: \(error)")
    }

    // MARK: - UNUserNotificationCenterDelegate

    // Handle notifications when app is in foreground
    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        willPresent notification: UNNotification,
        withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void
    ) {
        // Show notification even when app is in foreground
        completionHandler([.banner, .sound, .badge])
    }

    // Handle notification tap
    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        didReceive response: UNNotificationResponse,
        withCompletionHandler completionHandler: @escaping () -> Void
    ) {
        print("🔔 [AppDelegate] didReceive notification response")
        let userInfo = response.notification.request.content.userInfo
        print("🔔 [AppDelegate] userInfo: \(userInfo)")

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
            print("🔔 [AppDelegate] Found type: \(type), calling handleNotificationTap")
            handleNotificationTap(type: type, userInfo: notificationData)
        } else {
            print("🔔 [AppDelegate] No 'type' found in userInfo")
        }

        completionHandler()
    }

    private func handleNotificationTap(type: String, userInfo: [AnyHashable: Any]) {
        switch type {
        case "medication_reminder", "missed_dose":
            // Could navigate to medication detail or record dose screen
            if let medicationId = userInfo["medication_id"] as? String,
               let petId = userInfo["pet_id"] as? String {
                print("Notification tapped - medication: \(medicationId), pet: \(petId)")
                // TODO: Post notification to navigate to medication or record dose
            }
        case "member_joined":
            // Use deep link URL - onOpenURL fires after app is fully ready
            print("🔔 [Notification] member_joined tapped, opening deep link...")
            if let url = URL(string: "orestsjournal://family?refresh=true") {
                print("🔔 [Notification] Opening URL: \(url)")
                UIApplication.shared.open(url) { success in
                    print("🔔 [Notification] URL open result: \(success)")
                }
            } else {
                print("🔔 [Notification] Failed to create URL")
            }
        default:
            break
        }
    }
}
