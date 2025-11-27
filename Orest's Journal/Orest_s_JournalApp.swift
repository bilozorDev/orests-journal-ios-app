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
        }
        .onChange(of: scenePhase) { _, newPhase in
            switch newPhase {
            case .active:
                // Prefetch data when app becomes active
                Task {
                    await DataService.shared.prefetchDataOnForeground()
                }
            case .background:
                // Schedule background refresh when entering background
                BackgroundTaskManager.shared.scheduleAppRefresh()
            default:
                break
            }
        }
    }
}
