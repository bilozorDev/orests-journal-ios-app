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
        if let token = deviceToken {
            await registerDeviceTokenWithBackend(token)
        } else if isAuthorized {
            print("📲 Requesting new device token from APNs...")
            registerForRemoteNotifications()
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
        let userInfo = response.notification.request.content.userInfo

        // Handle notification based on type
        if let type = userInfo["type"] as? String {
            handleNotificationTap(type: type, userInfo: userInfo)
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
        default:
            break
        }
    }
}
