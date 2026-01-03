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

    init() {
        // Check for test authentication token (UI testing mode)
        AuthManager.shared.checkForTestAuth()

        // Sync API base URL to App Group for widget access
        WidgetDataManager.shared.setAPIBaseURL(APIConfiguration.baseURL)
    }

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
                // Check if widget recorded a dose - if so, force refresh
                let widgetRecordedDose = WidgetDataManager.shared.checkAndClearNeedsRefresh()

                // Prefetch data when app becomes active
                DataService.shared.prefetchDataOnForeground(forceRefresh: widgetRecordedDose)

                // Process any pending doses from widget interactions (fallback queue)
                Task {
                    await PendingDoseProcessor.shared.processPendingDoses()
                }
            case .background:
                // Schedule background refresh when entering background
                BackgroundTaskManager.shared.scheduleAppRefresh()
            default:
                break
            }
        }
    }

    private func handleDeepLink(_ url: URL) {
        #if DEBUG
        print("🔗 [DeepLink] Received URL: \(url)")
        print("🔗 [DeepLink] Scheme: \(url.scheme ?? "nil"), Host: \(url.host ?? "nil")")
        print("🔗 [DeepLink] Auth status: \(AuthManager.shared.isAuthenticated), Family: \(AuthManager.shared.currentFamily?.id ?? "nil")")
        #endif

        guard url.scheme == "orestsjournal" else {
            return
        }

        switch url.host {
        case "family":
            // Invalidate cache and navigate to family
            Task { @MainActor in
                if let familyId = AuthManager.shared.currentFamily?.id {
                    await DataService.shared.invalidateFamilyCache(for: familyId)
                }
                NavigationManager.shared.navigate(to: .familyManagement)
            }
        case "medication":
            // Navigate to specific medication: orestsjournal://medication/{id}
            let pathComponents = url.pathComponents.filter { $0 != "/" }
            if let medicationIdString = pathComponents.first,
               let medicationId = UUID(uuidString: medicationIdString) {
                Task { @MainActor in
                    #if DEBUG
                    print("🔗 [DeepLink] Processing medication deep link for: \(medicationId)")
                    #endif

                    // Process any pending dose from widget for this medication
                    if let medicationName = await PendingDoseProcessor.shared.processDoseForMedication(medicationId) {
                        // Dose was recorded - set flag for confirmation UI
                        #if DEBUG
                        print("✅ [DeepLink] Dose recorded for \(medicationName), setting confirmation flag")
                        #endif
                        NavigationManager.shared.widgetDoseRecorded = (medicationId, medicationName)
                    } else {
                        #if DEBUG
                        print("⚠️ [DeepLink] No pending dose found for medication \(medicationId)")
                        #endif
                    }
                    DataService.shared.invalidateAllMedicationsCaches()
                    NavigationManager.shared.requestTabRefresh(.medication)
                    NavigationManager.shared.navigate(to: .medicationDetail(medicationId: medicationId))
                }
            } else {
                // No specific medication, just go to medications tab
                Task { @MainActor in
                    NavigationManager.shared.navigate(to: .medications)
                }
            }
        case "medications":
            // Navigate to medications tab: orestsjournal://medications
            Task { @MainActor in
                NavigationManager.shared.navigate(to: .medications)
            }
        default:
            break
        }
    }
}
