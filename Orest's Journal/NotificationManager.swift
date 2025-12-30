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
        // Skip notification permissions in UI test mode
        guard !ProcessInfo.processInfo.arguments.contains("--uitesting") else {
            return
        }

        let center = UNUserNotificationCenter.current()

        do {
            let granted = try await center.requestAuthorization(options: [.alert, .sound, .badge])
            isAuthorized = granted

            if granted {
                registerForRemoteNotifications()
            }
        } catch {
            #if DEBUG
            print("Failed to request notification authorization: \(error)")
            #endif
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

    // Configure scene delegate for quick actions
    func application(
        _ application: UIApplication,
        configurationForConnecting connectingSceneSession: UISceneSession,
        options: UIScene.ConnectionOptions
    ) -> UISceneConfiguration {
        let config = UISceneConfiguration(name: nil, sessionRole: connectingSceneSession.role)
        config.delegateClass = SceneDelegate.self
        return config
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

        // Extract notification type
        var notificationType: String?
        if let type = userInfo["type"] as? String {
            notificationType = type
        } else if let data = userInfo["data"] as? [String: Any],
                  let type = data["type"] as? String {
            notificationType = type
        }

        // Invalidate caches based on notification type
        Task { @MainActor in
            await handleCacheInvalidation(userInfo: userInfo)
        }

        // Skip banner for member_removed (UI handles it with full-screen view)
        if notificationType == "member_removed" {
            completionHandler([])
        } else {
            completionHandler([.banner, .sound, .badge])
        }
    }

    private func handleCacheInvalidation(userInfo: [AnyHashable: Any]) async {
        // Extract notification type from userInfo or nested data
        var notificationType: String?
        var familyId: String?
        var familyName: String?

        if let type = userInfo["type"] as? String {
            notificationType = type
            familyId = userInfo["family_id"] as? String
            familyName = userInfo["family_name"] as? String
        } else if let data = userInfo["data"] as? [String: Any],
                  let type = data["type"] as? String {
            notificationType = type
            familyId = data["family_id"] as? String
            familyName = data["family_name"] as? String
        }

        // Handle notifications based on type
        guard let type = notificationType else { return }

        switch type {
        case "member_removed":
            // User was removed from the family - show removal screen
            AuthManager.shared.handleRemovedFromFamily(familyName: familyName)
        case "member_joined", "role_changed", "member_left", "member_left_promoted", "account_deleted", "account_deleted_promoted":
            // All family membership changes should refresh the family members list
            if let familyId = familyId {
                await DataService.shared.invalidateFamilyCache(for: familyId)
                // Also tell the view to refresh when it becomes visible
                NavigationManager.shared.requestFamilyRefresh()
            }
        case "pet_added", "pet_updated", "pet_deleted":
            // Pet changes from other family members - refresh pets list
            DataService.shared.invalidatePetsCache()
            NavigationManager.shared.requestFamilyRefresh()
        case "medication_created", "medication_updated", "medication_archived", "dose_administered":
            // Medication changes from other family members - refresh medications list
            DataService.shared.invalidateAllMedicationsCaches()
            NavigationManager.shared.requestTabRefresh(.medication)
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
            await handleCacheInvalidation(userInfo: userInfo)
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
            // Navigate to medication tab for reminders
            Task { @MainActor in
                NavigationManager.shared.selectedTab = .medication
            }
        case "medication_created", "medication_updated", "medication_archived", "dose_administered":
            // Navigate to medication tab for CRUD and dose notifications
            Task { @MainActor in
                NavigationManager.shared.selectedTab = .medication
                NavigationManager.shared.requestTabRefresh(.medication)
            }
        case "member_joined", "role_changed", "member_left", "member_left_promoted", "account_deleted", "account_deleted_promoted":
            // Use deep link URL - onOpenURL fires after app is fully ready
            if let url = URL(string: "orestsjournal://family?refresh=true") {
                UIApplication.shared.open(url)
            }
        case "pet_added", "pet_updated", "pet_deleted":
            // Navigate to family tab where pets are displayed
            if let url = URL(string: "orestsjournal://family?refresh=true") {
                UIApplication.shared.open(url)
            }
        default:
            break
        }
    }
}
