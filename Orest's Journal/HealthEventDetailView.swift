//
//  HealthEventDetailView.swift
//  Orest's Journal
//
//  Detail view for viewing and managing a single health event.
//

import SwiftUI

struct HealthEventDetailView: View {
    @State var event: HealthEventWithCategory
    let pet: Pet
    let onUpdate: (HealthEventWithCategory) -> Void
    let onDelete: () -> Void

    @Environment(\.dismiss) private var dismiss

    @State private var showEditSheet = false
    @State private var showDeleteConfirmation = false
    @State private var showFullScreenPhoto = false
    @State private var selectedPhotoIndex = 0
    @State private var isDeleting = false
    @State private var showError = false
    @State private var errorMessage = ""

    private let dataService = DataService.shared

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                // Header with category
                headerSection

                // Date
                dateSection

                // Photos if present
                if !event.event.photos.isEmpty {
                    photosSection
                }

                // Notes
                if let notes = event.event.notes, !notes.isEmpty {
                    notesSection(notes: notes)
                }

                // Metadata
                metadataSection
            }
            .padding()
        }
        .background(Color(uiColor: .systemGroupedBackground))
        .navigationTitle("Health Event")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Menu {
                    Button {
                        showEditSheet = true
                    } label: {
                        Label("Edit", systemImage: "pencil")
                    }

                    Button(role: .destructive) {
                        showDeleteConfirmation = true
                    } label: {
                        Label("Delete", systemImage: "trash")
                    }
                } label: {
                    Image(systemName: "ellipsis.circle")
                }
                .accessibilityLabel("More actions")
                .accessibilityHint("Edit or delete this event")
            }
        }
        .sheet(isPresented: $showEditSheet) {
            AddHealthEventView(
                pet: pet,
                existingEvent: event
            ) { _ in
                // Refresh the event after editing
                Task {
                    await refreshEvent()
                }
            }
        }
        .fullScreenCover(isPresented: $showFullScreenPhoto) {
            FullScreenPhotoGalleryView(
                photos: event.event.photos,
                initialIndex: selectedPhotoIndex
            )
        }
        .confirmationDialog(
            "Delete Health Event",
            isPresented: $showDeleteConfirmation,
            titleVisibility: .visible
        ) {
            Button("Delete", role: .destructive) {
                Task {
                    await deleteEvent()
                }
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("Are you sure you want to delete this health event? This action cannot be undone.")
        }
        .alert("Error", isPresented: $showError) {
            Button("OK") {}
        } message: {
            Text(errorMessage)
        }
        .overlay {
            if isDeleting {
                Color.black.opacity(0.3)
                    .ignoresSafeArea()
                ProgressView("Deleting...")
                    .padding()
                    .background(Color(uiColor: .systemBackground))
                    .cornerRadius(10)
            }
        }
    }

    // MARK: - Sections

    private var headerSection: some View {
        HStack(spacing: 16) {
            Image(systemName: categoryIcon)
                .font(.system(size: 24))
                .foregroundColor(categoryColor)
                .frame(width: 56, height: 56)
                .background(categoryColor.opacity(0.15))
                .clipShape(Circle())

            VStack(alignment: .leading, spacing: 4) {
                Text(event.category.name)
                    .font(.title2)
                    .fontWeight(.semibold)
                Text("Health Event")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }

            Spacer()
        }
        .padding()
        .background(Color(uiColor: .secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private var dateSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("Date & Time", systemImage: "calendar")
                .font(.subheadline)
                .foregroundColor(.secondary)

            Text(formattedDate)
                .font(.body)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(Color(uiColor: .secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private var photosSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("Photos (\(event.event.photos.count))", systemImage: "photo")
                .font(.subheadline)
                .foregroundColor(.secondary)

            if event.event.photos.count == 1 {
                // Single photo - show larger
                singlePhotoView(event.event.photos[0], index: 0)
            } else {
                // Multiple photos - show grid
                photoGrid
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(Color(uiColor: .secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private func singlePhotoView(_ photo: HealthEventPhoto, index: Int) -> some View {
        Button {
            selectedPhotoIndex = index
            showFullScreenPhoto = true
        } label: {
            AsyncImage(url: URL(string: photo.photoUrl)) { image in
                image
                    .resizable()
                    .scaledToFill()
            } placeholder: {
                Rectangle()
                    .fill(Color(uiColor: .tertiarySystemGroupedBackground))
                    .overlay {
                        ProgressView()
                    }
            }
            .frame(maxWidth: .infinity)
            .frame(height: 200)
            .clipShape(RoundedRectangle(cornerRadius: 12))
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Photo")
        .accessibilityHint("Double tap to view full screen")
    }

    private var photoGrid: some View {
        let columns = [
            GridItem(.flexible(), spacing: 8),
            GridItem(.flexible(), spacing: 8)
        ]

        return LazyVGrid(columns: columns, spacing: 8) {
            ForEach(Array(event.event.photos.enumerated()), id: \.element.id) { index, photo in
                Button {
                    selectedPhotoIndex = index
                    showFullScreenPhoto = true
                } label: {
                    AsyncImage(url: URL(string: photo.photoUrl)) { image in
                        image
                            .resizable()
                            .scaledToFill()
                    } placeholder: {
                        Rectangle()
                            .fill(Color(uiColor: .tertiarySystemGroupedBackground))
                            .overlay {
                                ProgressView()
                            }
                    }
                    .frame(height: 120)
                    .clipShape(RoundedRectangle(cornerRadius: 8))
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Photo \(index + 1) of \(event.event.photos.count)")
                .accessibilityHint("Double tap to view full screen")
            }
        }
    }

    private func notesSection(notes: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("Notes", systemImage: "note.text")
                .font(.subheadline)
                .foregroundColor(.secondary)

            Text(notes)
                .font(.body)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(Color(uiColor: .secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private var metadataSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("Details", systemImage: "info.circle")
                .font(.subheadline)
                .foregroundColor(.secondary)

            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text("Created")
                        .foregroundColor(.secondary)
                    Spacer()
                    Text(Formatters.shortDate.string(from: event.event.createdAt))
                }
                .font(.subheadline)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(Color(uiColor: .secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    // MARK: - Helpers

    private var formattedDate: String {
        Formatters.fullDateTime.string(from: event.event.occurredAt)
    }

    private var categoryIcon: String {
        event.category.icon
    }

    private var categoryColor: Color {
        event.category.color
    }

    // MARK: - Actions

    private func refreshEvent() async {
        do {
            let updated = try await dataService.getHealthEvent(eventId: event.id)
            event = updated
            onUpdate(updated)
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
    }

    private func deleteEvent() async {
        isDeleting = true
        do {
            try await dataService.deleteHealthEvent(eventId: event.id, petId: pet.id)
            onDelete()
            dismiss()
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
        isDeleting = false
    }
}

// MARK: - Full Screen Photo Gallery View

struct FullScreenPhotoGalleryView: View {
    let photos: [HealthEventPhoto]
    let initialIndex: Int

    @Environment(\.dismiss) private var dismiss
    @State private var currentIndex: Int

    init(photos: [HealthEventPhoto], initialIndex: Int) {
        self.photos = photos
        self.initialIndex = initialIndex
        self._currentIndex = State(initialValue: initialIndex)
    }

    var body: some View {
        NavigationStack {
            ZStack {
                Color.black.ignoresSafeArea()

                TabView(selection: $currentIndex) {
                    ForEach(Array(photos.enumerated()), id: \.element.id) { index, photo in
                        AsyncImage(url: URL(string: photo.photoUrl)) { image in
                            image
                                .resizable()
                                .scaledToFit()
                        } placeholder: {
                            ProgressView()
                                .tint(.white)
                        }
                        .tag(index)
                        .accessibilityLabel("Photo \(index + 1) of \(photos.count)")
                    }
                }
                .tabViewStyle(.page(indexDisplayMode: photos.count > 1 ? .automatic : .never))
            }
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    if photos.count > 1 {
                        Text("\(currentIndex + 1) / \(photos.count)")
                            .foregroundStyle(.white.opacity(0.7))
                            .font(.subheadline)
                            .accessibilityLabel("Photo \(currentIndex + 1) of \(photos.count)")
                    }
                }

                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        dismiss()
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .font(.title2)
                            .foregroundStyle(.white.opacity(0.7))
                    }
                    .accessibilityLabel("Close")
                }
            }
        }
    }
}

// MARK: - Preview

#Preview {
    NavigationStack {
        HealthEventDetailView(
            event: HealthEventWithCategory(
                event: HealthEvent(
                    id: UUID(),
                    petId: UUID(),
                    categoryId: UUID(),
                    occurredAt: Date(),
                    notes: "Annual checkup, all tests came back normal. Vet recommended continuing current diet.",
                    photos: [],
                    createdAt: Date(),
                    createdBy: nil
                ),
                category: HealthCategory(
                    id: UUID(),
                    orgId: UUID(),
                    name: "Vet Visit",
                    nameNormalized: "vet visit",
                    createdAt: Date(),
                    createdBy: nil
                )
            ),
            pet: Pet(
                id: UUID(),
                orgId: UUID().uuidString,
                name: "Max",
                kind: "dog",
                photoUrl: nil,
                currentWeight: nil,
                dateOfBirth: nil,
                isArchived: false,
                createdAt: Date(),
                createdBy: nil
            ),
            onUpdate: { _ in },
            onDelete: {}
        )
    }
}
