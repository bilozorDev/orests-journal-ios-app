//
//  AccessibilityIdentifiers.swift
//  Orest's Journal
//
//  Centralized accessibility identifiers for UI testing.
//

import Foundation

/// Centralized accessibility identifiers for UI testing.
/// Use these constants with `.accessibilityIdentifier()` modifier.
enum AccessibilityIdentifier {
    // MARK: - Auth
    static let signInWithAppleButton = "sign_in_with_apple_button"

    // MARK: - Profile Setup
    static let firstNameTextField = "first_name_text_field"
    static let lastNameTextField = "last_name_text_field"
    static let saveProfileButton = "save_profile_button"

    // MARK: - Family Setup
    static let createFamilyButton = "create_family_button"
    static let joinFamilyButton = "join_family_button"
    static let familyNameTextField = "family_name_text_field"
    static let inviteCodeTextField = "invite_code_text_field"
    static let submitCreateFamilyButton = "submit_create_family_button"
    static let submitJoinFamilyButton = "submit_join_family_button"

    // MARK: - Add/Edit Pet
    static let petNameTextField = "pet_name_text_field"
    static let petKindPicker = "pet_kind_picker"
    static let petWeightTextField = "pet_weight_text_field"
    static let petDateOfBirthPicker = "pet_date_of_birth_picker"
    static let savePetButton = "save_pet_button"
    static let saveAndAddAnotherPetButton = "save_and_add_another_pet_button"
    static let cancelPetButton = "cancel_pet_button"

    // MARK: - Pet Photo
    static let photoPickerButton = "photo_picker_button"
    static let removeBackgroundButton = "remove_background_button"
    static let removePhotoButton = "remove_photo_button"

    // MARK: - Tab Bar
    static let homeTab = "home_tab"
    static let foodTab = "food_tab"
    static let medicationTab = "medication_tab"
    static let healthTab = "health_tab"
    static let familyTab = "family_tab"
    static let settingsTab = "settings_tab"

    // MARK: - Settings
    static let signOutButton = "sign_out_button"
    static let editProfileButton = "edit_profile_button"
    static let deleteAccountButton = "delete_account_button"

    // MARK: - Edit Profile
    static let firstNameField = "first_name_field"
    static let lastNameField = "last_name_field"
    static let cancelEditProfileButton = "cancel_edit_profile_button"
    static let saveEditProfileButton = "save_edit_profile_button"

    // MARK: - Delete Account
    static let confirmDeleteAccountButton = "confirm_delete_account_button"
    static let cancelDeleteAccountButton = "cancel_delete_account_button"
    static let backToLoginButton = "back_to_login_button"

    // MARK: - Leave Family
    static let confirmLeaveFamilyButton = "confirm_leave_family_button"
    static let cancelLeaveFamilyButton = "cancel_leave_family_button"

    // MARK: - Admin Picker
    static let adminPickerList = "admin_picker_list"
    static let selectAdminConfirmButton = "select_admin_confirm_button"

    // MARK: - Family Management
    static let editFamilyNameButton = "edit_family_name_button"
    static let inviteMemberButton = "invite_member_button"
    static let leaveFamilyButton = "leave_family_button"
    static let copyInviteCodeButton = "copy_invite_code_button"
    static let shareInviteCodeButton = "share_invite_code_button"

    // MARK: - Family Member Management
    static let memberOptionsMenu = "member_options_menu"
    static let changeRoleButton = "change_role_button"
    static let removeMemberButton = "remove_member_button"
    static let confirmRemoveMemberButton = "confirm_remove_member_button"

    // MARK: - Edit Member Role
    static let rolePickerAdmin = "role_picker_admin"
    static let rolePickerMember = "role_picker_member"
    static let saveRoleButton = "save_role_button"
    static let cancelRoleButton = "cancel_role_button"

    // MARK: - Removed From Family
    static let startOverButton = "start_over_button"

    // MARK: - Pet Management
    static let addPetButton = "add_pet_button"
    static let petOptionsMenu = "pet_options_menu"
    static let editPetButton = "edit_pet_button"
    static let deletePetButton = "delete_pet_button"
    static let confirmDeletePetButton = "confirm_delete_pet_button"
    static let cancelDeletePetButton = "cancel_delete_pet_button"

    // MARK: - Health
    static let healthEventsList = "health_events_list"
    static let healthSearchField = "health_search_field"
    static let addHealthEventButton = "add_health_event_button"
    static let smartSearchButton = "smart_search_button"
    static let healthCategoryField = "health_category_field"
    static let healthNotesField = "health_notes_field"
    static let healthDatePicker = "health_date_picker"
    static let healthNotifyFamilyToggle = "health_notify_family_toggle"
    static let saveHealthEventButton = "save_health_event_button"
    static let cancelHealthEventButton = "cancel_health_event_button"
    static let healthPhotoPickerButton = "health_photo_picker_button"
    static let deleteHealthEventButton = "delete_health_event_button"
    static let confirmDeleteHealthEventButton = "confirm_delete_health_event_button"
}
