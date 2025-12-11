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
    case settings = 4
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
    var familyRefreshTrigger: Int = 0

    private init() {}

    func navigate(to destination: AppDestination) {
        switch destination {
        case .familyManagement:
            selectedTab = .settings
            familyRefreshTrigger += 1
        }
        pendingDestination = destination
    }

    func markTabRefreshed(_ tab: Tab) {
        tabsNeedingRefresh.remove(tab)
    }

    func requestTabRefresh(_ tab: Tab) {
        tabsNeedingRefresh.insert(tab)
    }

    func requestFamilyRefresh() {
        familyRefreshTrigger += 1
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
