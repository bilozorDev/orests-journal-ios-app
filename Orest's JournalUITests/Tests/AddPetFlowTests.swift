//
//  AddPetFlowTests.swift
//  Orest's JournalUITests
//
//  Tests for the add pet flow.
//

import XCTest

final class AddPetFlowTests: BaseUITest {

    func testAddPetFlow() async throws {
        // Launch with authenticated user and family (no pets yet)
        try await launchAppAuthenticated(createFamily: true, familyName: "Pet Test Family")

        // Wait for add pet screen (shown when family has no pets)
        assertExists(app.navigationBars["Add Pet"], timeout: 15)

        // Fill in pet name
        let petNameField = app.textField(id: "pet_name_text_field")
        waitAndType(petNameField, text: "Buddy")

        // The kind picker defaults to "Dog", so we don't need to change it

        // Enter weight
        let weightField = app.textField(id: "pet_weight_text_field")
        waitAndType(weightField, text: "25")

        // Tap save button
        waitAndTap(app.button(id: "save_pet_button"))

        // Verify navigated to main tab view
        assertExists(app.tabBars.firstMatch, timeout: 10)
    }

    func testAddPetRequiresName() async throws {
        try await launchAppAuthenticated(createFamily: true, familyName: "Validation Test Family")

        assertExists(app.navigationBars["Add Pet"], timeout: 15)

        // Only enter weight (no name)
        let weightField = app.textField(id: "pet_weight_text_field")
        waitAndType(weightField, text: "15")

        // Dismiss keyboard
        app.tap()

        // Save button should exist but be disabled when name is empty
        let saveButton = app.button(id: "save_pet_button")
        assertExists(saveButton)

        // Button should not be enabled (we can't easily check disabled state in XCUITest,
        // but tapping it should not navigate away)
        saveButton.tap()

        // Should still be on add pet screen
        assertExists(app.navigationBars["Add Pet"])
    }

    func testSaveAndAddAnotherPet() async throws {
        try await launchAppAuthenticated(createFamily: true, familyName: "Multi-Pet Family")

        assertExists(app.navigationBars["Add Pet"], timeout: 15)

        // Add first pet
        waitAndType(app.textField(id: "pet_name_text_field"), text: "Pet One")

        // Tap "Save & Add Another"
        waitAndTap(app.button(id: "save_and_add_another_pet_button"))

        // Wait for success toast and form to clear
        sleep(3)

        // Verify still on add pet screen
        assertExists(app.navigationBars["Add Pet"])
    }
}
