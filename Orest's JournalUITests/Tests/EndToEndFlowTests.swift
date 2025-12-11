//
//  EndToEndFlowTests.swift
//  Orest's JournalUITests
//
//  End-to-end tests covering complete user journeys.
//

import XCTest

final class EndToEndFlowTests: BaseUITest {

    func testCompleteNewUserFlow() async throws {
        // Start with authenticated user (no family, no pets)
        try await launchAppAuthenticated(createFamily: false)

        // Step 1: Family Setup
        assertExists(app.staticTexts["Setup Your Family"], timeout: 15)
        waitAndTap(app.button(id: "create_family_button"))

        waitAndType(app.textField(id: "family_name_text_field"), text: "E2E Test Family")
        waitAndTap(app.button(id: "submit_create_family_button"))

        // Step 2: Add Pet
        assertExists(app.navigationBars["Add Pet"], timeout: 10)

        waitAndType(app.textField(id: "pet_name_text_field"), text: "E2E Pet")
        waitAndType(app.textField(id: "pet_weight_text_field"), text: "25")
        waitAndTap(app.button(id: "save_pet_button"))

        // Step 3: Verify on Main Tab View
        assertExists(app.tabBars.firstMatch, timeout: 10)
    }

    func testNavigateBetweenTabs() async throws {
        // Create a user with family and pet already set up
        // Note: This test assumes the test backend creates family AND pet
        // For now, we'll just test with family
        try await launchAppAuthenticated(createFamily: true, familyName: "Tab Nav Test")

        // If we see add pet screen, add a pet first
        if app.navigationBars["Add Pet"].waitForExistence(timeout: 5) {
            waitAndType(app.textField(id: "pet_name_text_field"), text: "Tab Test Pet")
            waitAndTap(app.button(id: "save_pet_button"))
        }

        // Wait for main tab view
        assertExists(app.tabBars.firstMatch, timeout: 15)

        // Navigate to Family tab
        let familyTab = app.tabBars.buttons["Family"]
        waitAndTap(familyTab)
        assertExists(app.navigationBars["Family"], timeout: 5)

        // Navigate to Settings tab
        let settingsTab = app.tabBars.buttons["Settings"]
        waitAndTap(settingsTab)
        assertExists(app.navigationBars["Settings"], timeout: 5)

        // Navigate back to Home tab
        let homeTab = app.tabBars.buttons["Home"]
        waitAndTap(homeTab)
    }

    func testSignOutFlow() async throws {
        try await launchAppAuthenticated(createFamily: true, familyName: "Sign Out Test")

        // Add a pet first if needed
        if app.navigationBars["Add Pet"].waitForExistence(timeout: 5) {
            waitAndType(app.textField(id: "pet_name_text_field"), text: "Sign Out Pet")
            waitAndTap(app.button(id: "save_pet_button"))
        }

        // Navigate to settings tab
        assertExists(app.tabBars.firstMatch, timeout: 15)
        let settingsTab = app.tabBars.buttons["Settings"]
        waitAndTap(settingsTab)

        // Find and tap sign out button
        let signOutButton = app.button(id: "sign_out_button")

        // Scroll to sign out button if needed
        let scrollView = app.scrollViews.firstMatch
        var attempts = 0
        while !signOutButton.isHittable && attempts < 5 {
            scrollView.swipeUp()
            attempts += 1
        }

        waitAndTap(signOutButton)

        // Verify returned to sign-in screen
        // Note: The sign-in screen shows "Orest's Journal" title
        assertExists(app.staticTexts["Orest's Journal"], timeout: 10)
    }
}
