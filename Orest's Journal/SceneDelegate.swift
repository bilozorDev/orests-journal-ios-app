//
//  SceneDelegate.swift
//  Orest's Journal
//
//  Handles Home Screen Quick Actions (3D Touch / long-press app icon menu).
//

import UIKit

/// Quick action types matching Info.plist UIApplicationShortcutItemType values
enum QuickAction: String {
    case recordDose = "com.notip.orests-journal.recordDose"
    case viewMedications = "com.notip.orests-journal.viewMedications"

    /// Convert to navigation destination
    var destination: AppDestination {
        switch self {
        case .recordDose:
            return .recordDose
        case .viewMedications:
            return .medications
        }
    }
}

class SceneDelegate: NSObject, UIWindowSceneDelegate {

    /// Called when app launches from a quick action (app was not running)
    func scene(
        _ scene: UIScene,
        willConnectTo session: UISceneSession,
        options connectionOptions: UIScene.ConnectionOptions
    ) {
        if let shortcutItem = connectionOptions.shortcutItem {
            handleShortcutItem(shortcutItem)
        }
    }

    /// Called when app is in background and user selects a quick action
    func windowScene(
        _ windowScene: UIWindowScene,
        performActionFor shortcutItem: UIApplicationShortcutItem,
        completionHandler: @escaping (Bool) -> Void
    ) {
        let handled = handleShortcutItem(shortcutItem)
        completionHandler(handled)
    }

    @discardableResult
    private func handleShortcutItem(_ shortcutItem: UIApplicationShortcutItem) -> Bool {
        guard let action = QuickAction(rawValue: shortcutItem.type) else {
            #if DEBUG
            print("⚡️ [QuickAction] Unknown shortcut type: \(shortcutItem.type)")
            #endif
            return false
        }

        #if DEBUG
        print("⚡️ [QuickAction] Handling: \(action)")
        #endif

        // Navigate on main actor
        Task { @MainActor in
            NavigationManager.shared.navigate(to: action.destination)
        }

        return true
    }
}
