//
//  CreateFamilyFlowTests.swift
//  Orest's JournalUITests
//
//  Tests for the create family flow.
//

import XCTest

final class CreateFamilyFlowTests: BaseUITest {

    func testCreateFamilyFlow() async throws {
        // Launch with authenticated user (no family)
        try await launchAppAuthenticated(createFamily: false)

        // Wait for family setup screen
        assertExists(app.staticTexts["Setup Your Family"], timeout: 15)

        // Tap "Create New Family" button
        waitAndTap(app.button(id: "create_family_button"))

        // Verify on create family form
        assertExists(app.navigationBars["Create Family"])

        // Enter family name
        let familyNameField = app.textField(id: "family_name_text_field")
        waitAndType(familyNameField, text: "My Test Family")

        // Submit form
        waitAndTap(app.button(id: "submit_create_family_button"))

        // Verify navigated to add pet screen
        assertExists(app.navigationBars["Add Pet"], timeout: 10)
    }

    func testJoinFamilyFlow() async throws {
        // Launch with authenticated user (no family)
        try await launchAppAuthenticated(createFamily: false)

        // Wait for family setup screen
        assertExists(app.staticTexts["Setup Your Family"], timeout: 15)

        // Tap "Join Existing Family" button
        waitAndTap(app.button(id: "join_family_button"))

        // Verify on join family form
        assertExists(app.navigationBars["Join Family"])

        // Verify invite code field exists
        let inviteCodeField = app.textField(id: "invite_code_text_field")
        assertExists(inviteCodeField)

        // Note: We can't fully test join without a valid invite code
        // But we can verify the UI is correct

        // Go back
        app.buttons["Back"].tap()

        // Verify back on choose screen
        assertExists(app.staticTexts["Setup Your Family"])
    }

    func testBackButtonFromCreateFamily() async throws {
        try await launchAppAuthenticated(createFamily: false)

        assertExists(app.staticTexts["Setup Your Family"], timeout: 15)
        waitAndTap(app.button(id: "create_family_button"))

        // Tap back button
        waitAndTap(app.buttons["Back"])

        // Verify back on choose screen
        assertExists(app.staticTexts["Setup Your Family"])
        assertExists(app.button(id: "create_family_button"))
    }
}
