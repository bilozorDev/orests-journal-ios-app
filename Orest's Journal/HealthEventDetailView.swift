//
//  HealthEventDetailView.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import SwiftUI

struct HealthEventDetailView: View {
    let eventWithCategory: HealthEventWithCategory
    let petId: UUID

    @Environment(\.dismiss) var dismiss

    @State private var petName: String = ""
    @State private var createdByEmail: String = ""
    @State private var isLoading = true
    @State private var showDeleteConfirmation = false
    @State private var isDeleting = false
    @State private var errorMessage: String?

    var body: some View {
        Group {
            if isLoading {
                ProgressView()
            } else {
                ScrollView {
                    VStack(alignment: .leading, spacing: 24) {
                        // Event Category Header
                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                Image(systemName: "heart.circle.fill")
                                    .font(.system(size: 40))
                                    .foregroundColor(.red.opacity(0.7))

                                VStack(alignment: .leading, spacing: 4) {
                                    Text(eventWithCategory.category.name)
                                        .font(.title2)
                                        .fontWeight(.bold)

                                    Text(petName)
                                        .font(.subheadline)
                                        .foregroundColor(.secondary)
                                }

                                Spacer()
                            }
                        }
                        .padding()
                        .background(Color.red.opacity(0.1))
                        .cornerRadius(12)

                        // Event Details Section
                        VStack(alignment: .leading, spacing: 16) {
                            Text("Event Details")
                                .font(.headline)
                                .foregroundColor(.secondary)

                            VStack(spacing: 12) {
                                DetailRow(
                                    icon: "calendar",
                                    label: "Date",
                                    value: formatDate(eventWithCategory.event.occurredAt)
                                )

                                DetailRow(
                                    icon: "clock",
                                    label: "Time",
                                    value: formatTime(eventWithCategory.event.occurredAt)
                                )
                            }
                        }

                        // Notes Section
                        if let notes = eventWithCategory.event.notes, !notes.isEmpty {
                            VStack(alignment: .leading, spacing: 12) {
                                Text("Notes")
                                    .font(.headline)
                                    .foregroundColor(.secondary)

                                Text(notes)
                                    .font(.body)
                                    .padding()
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                    .background(Color.gray.opacity(0.1))
                                    .cornerRadius(8)
                            }
                        }

                        // Metadata Section
                        VStack(alignment: .leading, spacing: 16) {
                            Text("Record Information")
                                .font(.headline)
                                .foregroundColor(.secondary)

                            VStack(spacing: 12) {
                                DetailRow(
                                    icon: "person.circle",
                                    label: "Logged by",
                                    value: createdByEmail
                                )

                                DetailRow(
                                    icon: "clock.arrow.circlepath",
                                    label: "Logged at",
                                    value: formatDateTime(eventWithCategory.event.createdAt)
                                )
                            }
                        }

                        // Delete Button
                        Button(role: .destructive, action: {
                            showDeleteConfirmation = true
                        }) {
                            HStack {
                                Image(systemName: "trash")
                                Text("Delete Event")
                            }
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color.red.opacity(0.1))
                            .foregroundColor(.red)
                            .cornerRadius(12)
                        }
                        .disabled(isDeleting)

                        if let error = errorMessage {
                            Text(error)
                                .foregroundColor(.red)
                                .font(.caption)
                        }
                    }
                    .padding()
                }
            }
        }
        .navigationTitle("Health Event")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            await loadData()
        }
        .alert("Delete Event", isPresented: $showDeleteConfirmation) {
            Button("Cancel", role: .cancel) {}
            Button("Delete", role: .destructive) {
                Task {
                    await deleteEvent()
                }
            }
        } message: {
            Text("Are you sure you want to delete this health event? This action cannot be undone.")
        }
    }

    private func loadData() async {
        isLoading = true

        // Load pet name
        do {
            let pets = try await SupabaseService.shared.getFamilyPets(
                familyId: (try await SupabaseService.shared.getCurrentUserFamily())?.id ?? UUID()
            )
            petName = pets.first(where: { $0.id == petId })?.name ?? "Unknown Pet"
        } catch {
            petName = "Unknown Pet"
            print("Error loading pet: \(error)")
        }

        // Load creator email
        createdByEmail = await SupabaseService.shared.getUserEmail(for: eventWithCategory.event.createdBy)

        isLoading = false
    }

    private func deleteEvent() async {
        isDeleting = true
        errorMessage = nil

        do {
            try await SupabaseService.shared.deleteHealthEvent(eventWithCategory.event.id)
            dismiss()
        } catch {
            errorMessage = "Failed to delete event: \(error.localizedDescription)"
            print("Error deleting event: \(error)")
        }

        isDeleting = false
    }

    private func formatDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .none

        if Calendar.current.isDateInToday(date) {
            return "Today"
        } else if Calendar.current.isDateInYesterday(date) {
            return "Yesterday"
        } else {
            return formatter.string(from: date)
        }
    }

    private func formatTime(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.timeStyle = .short
        return formatter.string(from: date)
    }

    private func formatDateTime(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        return formatter.string(from: date)
    }
}

struct DetailRow: View {
    let icon: String
    let label: String
    let value: String

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .font(.title3)
                .foregroundColor(.blue)
                .frame(width: 24)

            VStack(alignment: .leading, spacing: 2) {
                Text(label)
                    .font(.caption)
                    .foregroundColor(.secondary)
                Text(value)
                    .font(.body)
            }

            Spacer()
        }
        .padding()
        .background(Color.gray.opacity(0.05))
        .cornerRadius(8)
    }
}

#Preview {
    NavigationView {
        HealthEventDetailView(
            eventWithCategory: HealthEventWithCategory(
                event: HealthEvent(
                    id: UUID(),
                    categoryId: UUID(),
                    occurredAt: Date(),
                    notes: "This is a test note about the health event",
                    createdAt: Date(),
                    createdBy: UUID()
                ),
                category: HealthCategory(
                    id: UUID(),
                    petId: UUID(),
                    name: "Asthma Attack",
                    nameNormalized: "asthma attack",
                    createdAt: Date(),
                    createdBy: UUID()
                )
            ),
            petId: UUID()
        )
    }
}
