//
//  NavigationManager.swift
//  Orest's Journal
//
//  Manages app-wide navigation state for deep linking and push notification handling.
//

import Foundation

/// Tab identifiers for the main tab view
enum Tab: Int {
    case home = 0
    case food = 1
    case medication = 2
    case health = 3
    case family = 4
    case settings = 5
}

enum AppDestination: Equatable {
    case familyManagement
}

@MainActor
@Observable
final class NavigationManager {
    static let shared = NavigationManager()

    var selectedTab: Tab = .home
    var pendingDestination: AppDestination?
    private(set) var tabsNeedingRefresh: Set<Tab> = []

    private init() {}

    func navigate(to destination: AppDestination) {
        print("🧭 [Navigation] navigate(to: \(destination))")
        switch destination {
        case .familyManagement:
            selectedTab = .family
            tabsNeedingRefresh.insert(.family)
            print("🧭 [Navigation] Set selectedTab=.family, tabsNeedingRefresh=\(tabsNeedingRefresh)")
        }
        pendingDestination = destination
    }

    func markTabRefreshed(_ tab: Tab) {
        tabsNeedingRefresh.remove(tab)
    }

    func clearPendingDestination() {
        pendingDestination = nil
    }

    func reset() {
        selectedTab = .home
        pendingDestination = nil
        tabsNeedingRefresh.removeAll()
    }
}
