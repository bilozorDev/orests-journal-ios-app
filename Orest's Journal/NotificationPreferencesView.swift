//
//  NotificationPreferencesView.swift
//  Orest's Journal
//
//  Notification preferences screen for toggling notification categories.
//

import SwiftUI

struct NotificationPreferencesView: View {
    @State private var preferences: NotificationPreferences = .defaults
    @State private var isLoading = true
    @State private var isSaving = false
    @State private var showError = false
    @State private var errorMessage = ""

    var body: some View {
        ScrollView {
            VStack(spacing: 16) {
                if isLoading {
                    ProgressView("Loading preferences...")
                        .frame(maxWidth: .infinity, minHeight: 200)
                } else {
                    // Family Updates Toggle
                    preferenceCard(
                        title: "Family Updates",
                        subtitle: "Members joining, leaving, role changes",
                        icon: "person.2.fill",
                        iconColor: .blue,
                        isOn: Binding(
                            get: { preferences.allFamilyUpdatesEnabled },
                            set: { setAllFamilyPreferences($0) }
                        )
                    )

                    // Pet Updates Toggle
                    preferenceCard(
                        title: "Pet Updates",
                        subtitle: "Pets added, updated, or removed",
                        icon: "pawprint.fill",
                        iconColor: .orange,
                        isOn: Binding(
                            get: { preferences.allPetUpdatesEnabled },
                            set: { setAllPetPreferences($0) }
                        )
                    )
                }
            }
            .padding()
        }
        .background(Color(uiColor: .systemGroupedBackground))
        .navigationTitle("Notifications")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            await loadPreferences()
        }
        .alert("Error", isPresented: $showError) {
            Button("OK") { showError = false }
        } message: {
            Text(errorMessage)
        }
    }

    // MARK: - Preference Card

    private func preferenceCard(
        title: String,
        subtitle: String,
        icon: String,
        iconColor: Color,
        isOn: Binding<Bool>
    ) -> some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .font(.title2)
                .foregroundStyle(iconColor)
                .frame(width: 32)

            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.body)
                    .fontWeight(.medium)
                Text(subtitle)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            Toggle("", isOn: isOn)
                .labelsHidden()
                .disabled(isSaving)
        }
        .padding()
        .background(Color.gray.opacity(0.1))
        .clipShape(.rect(cornerRadius: 12))
    }

    // MARK: - Actions

    private func loadPreferences() async {
        do {
            preferences = try await APIClient.shared.getNotificationPreferences()
        } catch {
            // Use defaults on error - user can still toggle
            preferences = .defaults
        }
        isLoading = false
    }

    private func setAllFamilyPreferences(_ enabled: Bool) {
        Task {
            isSaving = true
            defer { isSaving = false }

            // Update local state immediately for responsiveness
            preferences.familyMemberJoined = enabled
            preferences.familyRoleChanged = enabled
            preferences.familyMemberLeft = enabled
            preferences.familyMemberLeftPromoted = enabled
            preferences.familyAccountDeleted = enabled
            preferences.familyAccountDeletedPromoted = enabled

            do {
                let update = NotificationPreferencesUpdate(
                    familyMemberJoined: enabled,
                    familyRoleChanged: enabled,
                    familyMemberLeft: enabled,
                    familyMemberLeftPromoted: enabled,
                    familyAccountDeleted: enabled,
                    familyAccountDeletedPromoted: enabled
                )
                preferences = try await APIClient.shared.updateNotificationPreferences(update)
            } catch {
                errorMessage = "Failed to save preferences: \(error.localizedDescription)"
                showError = true
                await loadPreferences()
            }
        }
    }

    private func setAllPetPreferences(_ enabled: Bool) {
        Task {
            isSaving = true
            defer { isSaving = false }

            // Update local state immediately for responsiveness
            preferences.petAdded = enabled
            preferences.petUpdated = enabled
            preferences.petDeleted = enabled

            do {
                let update = NotificationPreferencesUpdate(
                    petAdded: enabled,
                    petUpdated: enabled,
                    petDeleted: enabled
                )
                preferences = try await APIClient.shared.updateNotificationPreferences(update)
            } catch {
                errorMessage = "Failed to save preferences: \(error.localizedDescription)"
                showError = true
                await loadPreferences()
            }
        }
    }
}

#Preview {
    NavigationStack {
        NotificationPreferencesView()
    }
}
