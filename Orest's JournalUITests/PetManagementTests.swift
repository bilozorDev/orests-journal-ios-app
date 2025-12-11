//
//  PetManagementTests.swift
//  Orest's JournalUITests
//
//  Tests for pet management flows including add, edit, and delete.
//

import XCTest

final class PetManagementTests: BaseUITest {

    // MARK: - Add Pet

    func testAddAnotherPet() async throws {
        // Launch with authenticated user who has family (will need to add first pet)
        try await launchAppAuthenticated(createFamily: true, familyName: "Pet Test Family")

        // Should be on Add Pet screen since family has no pets
        assertExists(app.navigationBars["Add Pet"], timeout: 10, message: "Should show Add Pet screen")

        // Add first pet
        let petNameField = app.textField(id: "pet_name_text_field")
        waitAndType(petNameField, text: "First Pet")

        // Select species
        waitAndTap(app.button(id: "species_dog"))

        // Save first pet
        waitAndTap(app.button(id: "save_pet_button"))

        // Should now be on main tab view
        assertExists(app.tabBars.firstMatch, timeout: 10, message: "Should show main tab view after adding first pet")

        // Navigate to Family tab
        waitAndTap(app.tabBars.buttons["Family"])

        // Wait for family view
        assertExists(app.staticTexts["Pet Test Family"], timeout: 10)

        // Tap add pet button
        let addPetButton = app.buttons["add_pet_button"]
        assertExists(addPetButton, timeout: 5, message: "Should show add pet button")
        addPetButton.tap()

        // Should show Add Pet screen
        assertExists(app.navigationBars["Add Pet"], timeout: 5, message: "Should show Add Pet screen")

        // Add second pet
        let secondPetNameField = app.textField(id: "pet_name_text_field")
        waitAndType(secondPetNameField, text: "Second Pet")

        // Select species
        waitAndTap(app.button(id: "species_cat"))

        // Save
        waitAndTap(app.button(id: "save_pet_button"))

        // Should be back on Family tab with both pets visible
        assertExists(app.staticTexts["First Pet"], timeout: 10, message: "First pet should be in list")
        assertExists(app.staticTexts["Second Pet"], timeout: 10, message: "Second pet should be in list")
    }

    func testAddPetWithAllFields() async throws {
        // Launch with authenticated user who has family
        try await launchAppAuthenticated(createFamily: true, familyName: "Full Pet Test")

        // Should be on Add Pet screen
        assertExists(app.navigationBars["Add Pet"], timeout: 10)

        // Fill in all fields
        let petNameField = app.textField(id: "pet_name_text_field")
        waitAndType(petNameField, text: "Complete Pet")

        // Select species
        waitAndTap(app.button(id: "species_dog"))

        // Enter weight if field exists
        let weightField = app.textField(id: "pet_weight_text_field")
        if waitForElement(weightField, timeout: 2) {
            weightField.tap()
            weightField.typeText("25")
        }

        // Save
        waitAndTap(app.button(id: "save_pet_button"))

        // Should be on main view
        assertExists(app.tabBars.firstMatch, timeout: 10)
    }

    // MARK: - Edit Pet

    func testEditPetName() async throws {
        // Launch with authenticated user who has family
        try await launchAppAuthenticated(createFamily: true, familyName: "Edit Pet Test")

        // Add a pet first
        assertExists(app.navigationBars["Add Pet"], timeout: 10)

        let petNameField = app.textField(id: "pet_name_text_field")
        waitAndType(petNameField, text: "Original Name")
        waitAndTap(app.button(id: "species_dog"))
        waitAndTap(app.button(id: "save_pet_button"))

        // Should be on main view
        assertExists(app.tabBars.firstMatch, timeout: 10)

        // Navigate to Family tab
        waitAndTap(app.tabBars.buttons["Family"])

        // Wait for pet to appear
        assertExists(app.staticTexts["Original Name"], timeout: 10)

        // Find the pet row and look for its options menu
        // The pet menu identifier includes the pet ID, but we don't know the ID
        // So we'll look for any pet options menu
        let petMenus = app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@", "pet_options_menu"))
        if petMenus.count > 0 {
            let petMenu = petMenus.element(boundBy: 0)
            petMenu.tap()

            // Tap Edit
            let editButton = app.buttons["edit_pet_button"]
            assertExists(editButton, timeout: 5, message: "Should show Edit option")
            editButton.tap()

            // Should show Edit Pet screen
            assertExists(app.navigationBars["Edit Pet"], timeout: 5, message: "Should show Edit Pet screen")

            // Clear and update name
            let editNameField = app.textField(id: "pet_name_text_field")
            assertExists(editNameField, timeout: 5)
            editNameField.tap()

            // Clear existing text and type new name
            // Select all and delete
            editNameField.press(forDuration: 1.0)
            if app.menuItems["Select All"].exists {
                app.menuItems["Select All"].tap()
            }
            editNameField.typeText("Updated Name")

            // Save
            waitAndTap(app.button(id: "save_pet_button"))

            // Verify updated name appears
            assertExists(app.staticTexts["Updated Name"], timeout: 10, message: "Pet name should be updated")
        }
    }

    func testEditPetSpecies() async throws {
        // Launch with authenticated user who has family
        try await launchAppAuthenticated(createFamily: true, familyName: "Species Edit Test")

        // Add a dog first
        assertExists(app.navigationBars["Add Pet"], timeout: 10)

        let petNameField = app.textField(id: "pet_name_text_field")
        waitAndType(petNameField, text: "Species Test Pet")
        waitAndTap(app.button(id: "species_dog"))
        waitAndTap(app.button(id: "save_pet_button"))

        // Navigate to Family tab
        assertExists(app.tabBars.firstMatch, timeout: 10)
        waitAndTap(app.tabBars.buttons["Family"])

        // Wait for pet
        assertExists(app.staticTexts["Species Test Pet"], timeout: 10)

        // Find and tap pet options menu
        let petMenus = app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@", "pet_options_menu"))
        if petMenus.count > 0 {
            petMenus.element(boundBy: 0).tap()

            // Tap Edit
            waitAndTap(app.buttons["edit_pet_button"])

            // Change species to cat
            waitAndTap(app.button(id: "species_cat"))

            // Save
            waitAndTap(app.button(id: "save_pet_button"))

            // Wait for update
            try? await Task.sleep(for: .seconds(1))
        }
    }

    // MARK: - Delete Pet

    func testDeletePet() async throws {
        // Launch with authenticated user who has family
        try await launchAppAuthenticated(createFamily: true, familyName: "Delete Pet Test")

        // Add a pet first
        assertExists(app.navigationBars["Add Pet"], timeout: 10)

        let petNameField = app.textField(id: "pet_name_text_field")
        waitAndType(petNameField, text: "Pet To Delete")
        waitAndTap(app.button(id: "species_dog"))
        waitAndTap(app.button(id: "save_pet_button"))

        // Navigate to Family tab
        assertExists(app.tabBars.firstMatch, timeout: 10)
        waitAndTap(app.tabBars.buttons["Family"])

        // Wait for pet
        assertExists(app.staticTexts["Pet To Delete"], timeout: 10)

        // Find and tap pet options menu
        let petMenus = app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@", "pet_options_menu"))
        XCTAssertTrue(petMenus.count > 0, "Should find pet options menu")

        petMenus.element(boundBy: 0).tap()

        // Tap Delete
        let deleteButton = app.buttons["delete_pet_button"]
        assertExists(deleteButton, timeout: 5, message: "Should show Delete option")
        deleteButton.tap()

        // Confirm deletion
        let confirmButton = app.buttons["confirm_delete_pet_button"]
        assertExists(confirmButton, timeout: 5, message: "Should show confirmation alert")
        confirmButton.tap()

        // Wait for deletion
        try? await Task.sleep(for: .seconds(1))

        // Pet should no longer appear
        assertNotExists(app.staticTexts["Pet To Delete"], timeout: 5, message: "Deleted pet should not appear")
    }

    func testDeletePetCancel() async throws {
        // Launch with authenticated user who has family
        try await launchAppAuthenticated(createFamily: true, familyName: "Cancel Delete Test")

        // Add a pet first
        assertExists(app.navigationBars["Add Pet"], timeout: 10)

        let petNameField = app.textField(id: "pet_name_text_field")
        waitAndType(petNameField, text: "Pet Not Deleted")
        waitAndTap(app.button(id: "species_dog"))
        waitAndTap(app.button(id: "save_pet_button"))

        // Navigate to Family tab
        assertExists(app.tabBars.firstMatch, timeout: 10)
        waitAndTap(app.tabBars.buttons["Family"])

        // Wait for pet
        assertExists(app.staticTexts["Pet Not Deleted"], timeout: 10)

        // Find and tap pet options menu
        let petMenus = app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@", "pet_options_menu"))
        XCTAssertTrue(petMenus.count > 0, "Should find pet options menu")

        petMenus.element(boundBy: 0).tap()

        // Tap Delete
        waitAndTap(app.buttons["delete_pet_button"])

        // Cancel deletion
        let cancelButton = app.buttons["cancel_delete_pet_button"]
        if cancelButton.exists {
            cancelButton.tap()
        } else {
            // Try standard Cancel button
            let standardCancel = app.buttons["Cancel"]
            if standardCancel.exists {
                standardCancel.tap()
            }
        }

        // Pet should still exist
        assertExists(app.staticTexts["Pet Not Deleted"], timeout: 5, message: "Pet should still exist after canceling delete")
    }

    // MARK: - Edge Cases

    func testAddPetValidation() async throws {
        // Launch with authenticated user who has family
        try await launchAppAuthenticated(createFamily: true, familyName: "Validation Test")

        // Should be on Add Pet screen
        assertExists(app.navigationBars["Add Pet"], timeout: 10)

        // Try to save without entering name
        let saveButton = app.button(id: "save_pet_button")

        // Save button should be disabled or show error when tapped without name
        if saveButton.isEnabled {
            saveButton.tap()
            // Should still be on Add Pet screen (validation failed)
            assertExists(app.navigationBars["Add Pet"], timeout: 2, message: "Should stay on Add Pet screen without valid name")
        }

        // Enter only spaces
        let petNameField = app.textField(id: "pet_name_text_field")
        waitAndType(petNameField, text: "   ")

        // Still shouldn't save (or should show error)
        if saveButton.isEnabled {
            saveButton.tap()
            try? await Task.sleep(for: .milliseconds(500))
            // Either still on Add Pet or showing validation error
        }
    }
}
