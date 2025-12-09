//
//  Orest_s_JournalApp.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import SwiftUI

@main
struct Orest_s_JournalApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @Environment(\.scenePhase) private var scenePhase

    var body: some Scene {
        WindowGroup {
            ContentView()
                .onOpenURL { url in
                    handleDeepLink(url)
                }
        }
        .onChange(of: scenePhase) { _, newPhase in
            switch newPhase {
            case .active:
                // Prefetch data when app becomes active
                DataService.shared.prefetchDataOnForeground()
            case .background:
                // Schedule background refresh when entering background
                BackgroundTaskManager.shared.scheduleAppRefresh()
            default:
                break
            }
        }
    }

    private func handleDeepLink(_ url: URL) {
        print("🔗 [DeepLink] Received URL: \(url)")
        print("🔗 [DeepLink] Scheme: \(url.scheme ?? "nil"), Host: \(url.host ?? "nil")")
        print("🔗 [DeepLink] Auth status: \(AuthManager.shared.isAuthenticated), Family: \(AuthManager.shared.currentFamily?.id ?? "nil")")

        guard url.scheme == "orestsjournal" else {
            print("🔗 [DeepLink] Wrong scheme, ignoring")
            return
        }

        switch url.host {
        case "family":
            print("🔗 [DeepLink] Handling family deep link...")
            // Invalidate cache and navigate to family
            if let familyId = AuthManager.shared.currentFamily?.id {
                print("🔗 [DeepLink] Invalidating cache for family: \(familyId)")
                DataService.shared.invalidateFamilyCache(for: familyId)
            }
            print("🔗 [DeepLink] Navigating to family management...")
            NavigationManager.shared.navigate(to: .familyManagement)
        default:
            print("🔗 [DeepLink] Unknown host: \(url.host ?? "nil")")
            break
        }
    }
}
