//
//  FamilyManagementView.swift
//  Orest's Journal
//
//  Created by Claude on 11/26/25.
//

import SwiftUI
import PhotosUI

// MARK: - Family Management View

struct FamilyManagementView: View {
    private var authManager = AuthManager.shared
    @State private var familyMembers: [FamilyMemberResponse] = []
    @State private var pets: [Pet] = []
    @State private var isLoading = false
    @State private var hasLoaded = false
    @State private var errorMessage: String?

    // Sheet states
    @State private var showInviteSheet = false
    @State private var showAddPet = false
    @State private var showEditFamilyName = false
    @State private var petToEdit: Pet?
    @State private var petToDelete: Pet?
    @State private var memberToEdit: FamilyMemberResponse?
    @State private var memberToRemove: FamilyMemberResponse?

    // Alert states
    @State private var showDeletePetConfirmation = false
    @State private var showRemoveMemberConfirmation = false
    @State private var showDeleteResultAlert = false
    @State private var deleteResultMessage = ""

    // Archived pets
    @State private var showArchivedPets = false

    var activePets: [Pet] {
        pets.filter { !($0.isArchived ?? false) }
    }

    var archivedPets: [Pet] {
        pets.filter { $0.isArchived ?? false }
    }

    var isAdmin: Bool {
        authManager.currentFamily?.role == "admin"
    }

    var body: some View {
        ScrollView {
            VStack(spacing: 20) {
                // Household Section (combined family info + members)
                householdSection

                // Pets Section
                petsSection

                // Archived Pets Section
                if !archivedPets.isEmpty {
                    archivedPetsSection
                }

                Spacer()
            }
            .padding()
        }
        .overlay {
            if isLoading && !hasLoaded {
                ProgressView("Loading...")
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(Color(uiColor: .systemBackground))
            }
        }
        .navigationTitle("Family")
        .navigationBarTitleDisplayMode(.inline)
        .sheet(isPresented: $showInviteSheet) {
            InviteShareSheet(inviteCode: authManager.currentFamily?.inviteCode ?? "")
        }
        .sheet(isPresented: $showAddPet) {
            AddEditPetView(mode: .add) { newPet in
                pets.append(newPet)
            }
        }
        .sheet(item: $petToEdit) { pet in
            AddEditPetView(mode: .edit(pet)) { updatedPet in
                if let index = pets.firstIndex(where: { $0.id == updatedPet.id }) {
                    pets[index] = updatedPet
                }
            }
        }
        .sheet(item: $memberToEdit) { member in
            EditMemberRoleSheet(member: member) { updatedMember in
                if let index = familyMembers.firstIndex(where: { $0.userId == updatedMember.userId }) {
                    familyMembers[index] = updatedMember
                }
            }
        }
        .sheet(isPresented: $showEditFamilyName) {
            if let family = authManager.currentFamily {
                EditFamilyNameSheet(
                    familyId: family.id,
                    currentName: family.name
                )
            }
        }
        .alert("Delete Pet", isPresented: $showDeletePetConfirmation) {
            Button("Cancel", role: .cancel) {
                petToDelete = nil
            }
            Button("Delete", role: .destructive) {
                if let pet = petToDelete {
                    Task {
                        await deletePet(pet)
                    }
                }
            }
        } message: {
            Text("Are you sure you want to delete \"\(petToDelete?.name ?? "")\"? This action cannot be undone.")
        }
        .alert("Remove Member", isPresented: $showRemoveMemberConfirmation) {
            Button("Cancel", role: .cancel) {
                memberToRemove = nil
            }
            Button("Remove", role: .destructive) {
                if let member = memberToRemove {
                    Task {
                        await removeMember(member)
                    }
                }
            }
        } message: {
            let memberName = memberToRemove?.displayName ?? "this member"
            Text("Are you sure you want to remove \(memberName) from the family?")
        }
        .alert("Pet Archived", isPresented: $showDeleteResultAlert) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(deleteResultMessage)
        }
        .task {
            guard !hasLoaded else { return }
            await loadData()
        }
        .refreshable {
            await loadData(forceRefresh: true)
        }
    }

    // MARK: - Household Section (combined family info + members)

    private var householdSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Household")
                .font(.headline)
                .foregroundColor(.secondary)

            if let family = authManager.currentFamily {
                VStack(spacing: 0) {
                    // Family name row with edit button (admin only)
                    HStack {
                        Image(systemName: "house.circle.fill")
                            .font(.title2)
                            .foregroundColor(.green)

                        Text(family.name)
                            .font(.body)
                            .fontWeight(.medium)

                        Spacer()

                        if isAdmin {
                            Button(action: {
                                showEditFamilyName = true
                            }) {
                                Image(systemName: "pencil")
                                    .foregroundColor(.blue)
                            }
                        }
                    }
                    .padding()
                    .background(Color.gray.opacity(0.1))
                    .cornerRadius(12, corners: familyMembers.isEmpty ? .allCorners : [.topLeft, .topRight])

                    // Members list inline (indented to show hierarchy)
                    if !familyMembers.isEmpty {
                        VStack(spacing: 0) {
                            ForEach(Array(familyMembers.enumerated()), id: \.element.id) { index, member in
                                VStack(spacing: 0) {
                                    if index > 0 {
                                        Divider()
                                            .padding(.leading, 68)
                                    }
                                    memberRowCompact(member)
                                }
                            }
                        }
                        .padding(.leading, 16)
                        .background(Color.gray.opacity(0.1))
                        .cornerRadius(12, corners: [.bottomLeft, .bottomRight])
                    }

                    // Invite code section
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Invite Code")
                            .font(.caption)
                            .foregroundColor(.secondary)

                        HStack {
                            Text(family.inviteCode)
                                .font(.system(.body, design: .monospaced))
                                .fontWeight(.semibold)

                            Spacer()

                            Button(action: {
                                UIPasteboard.general.string = family.inviteCode
                            }) {
                                Image(systemName: "doc.on.doc")
                                    .foregroundColor(.blue)
                            }

                            Button(action: {
                                showInviteSheet = true
                            }) {
                                Image(systemName: "square.and.arrow.up")
                                    .foregroundColor(.blue)
                            }
                        }
                        .padding()
                        .background(Color.blue.opacity(0.1))
                        .cornerRadius(8)
                    }
                    .padding(.top, 12)

                    Text("Share this code to invite family members")
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }
            }
        }
    }

    private func memberRowCompact(_ member: FamilyMemberResponse) -> some View {
        let isCurrentUser = member.userId == authManager.userId

        return HStack(spacing: 12) {
            Image(systemName: "person.circle.fill")
                .font(.title3)
                .foregroundColor(member.role == "admin" ? .orange : .blue)

            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 4) {
                    Text(member.displayName)
                        .font(.subheadline)
                        .fontWeight(.medium)

                    if isCurrentUser {
                        Text("(You)")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }

                HStack(spacing: 6) {
                    Text(member.role.capitalized)
                        .font(.caption2)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(member.role == "admin" ? Color.orange.opacity(0.2) : Color.blue.opacity(0.2))
                        .foregroundColor(member.role == "admin" ? .orange : .blue)
                        .cornerRadius(4)

                    if let joinedAt = member.joinedAt {
                        Text("Joined \(formatDate(joinedAt))")
                            .font(.caption2)
                            .foregroundColor(.secondary)
                    }
                }
            }

            Spacer()

            if isAdmin && !isCurrentUser {
                Menu {
                    Button(action: {
                        memberToEdit = member
                    }) {
                        Label("Change Role", systemImage: "person.badge.key")
                    }

                    Button(role: .destructive, action: {
                        memberToRemove = member
                        showRemoveMemberConfirmation = true
                    }) {
                        Label("Remove", systemImage: "person.badge.minus")
                    }
                } label: {
                    Image(systemName: "ellipsis.circle")
                        .foregroundColor(.gray)
                }
            }
        }
        .padding(.horizontal)
        .padding(.vertical, 10)
    }

    // MARK: - Pets Section

    private var petsSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Pets")
                    .font(.headline)
                    .foregroundColor(.secondary)

                Spacer()

                Button(action: {
                    showAddPet = true
                }) {
                    Image(systemName: "plus.circle.fill")
                        .font(.title3)
                        .foregroundColor(.blue)
                }
            }

            if activePets.isEmpty {
                VStack(spacing: 8) {
                    Image(systemName: "pawprint.circle")
                        .font(.system(size: 40))
                        .foregroundColor(.gray)
                    Text("No pets in family")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                    Button("Add Pet") {
                        showAddPet = true
                    }
                    .buttonStyle(.borderedProminent)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 20)
                .background(Color.gray.opacity(0.1))
                .cornerRadius(12)
            } else {
                VStack(spacing: 12) {
                    ForEach(activePets) { pet in
                        petRow(pet)
                    }
                }
            }
        }
    }

    private func petRow(_ pet: Pet) -> some View {
        HStack(spacing: 12) {
            // Pet Photo
            if let photoUrl = pet.photoUrl, let url = URL(string: photoUrl) {
                AsyncImage(url: url) { image in
                    image
                        .resizable()
                        .scaledToFill()
                } placeholder: {
                    Rectangle()
                        .fill(Color.gray.opacity(0.2))
                        .overlay(ProgressView())
                }
                .frame(width: 60, height: 60)
                .clipShape(Circle())
            } else {
                Circle()
                    .fill(Color.gray.opacity(0.2))
                    .frame(width: 60, height: 60)
                    .overlay(
                        Image(systemName: "pawprint.fill")
                            .foregroundColor(.gray)
                    )
            }

            // Pet Info
            VStack(alignment: .leading, spacing: 4) {
                Text(pet.name)
                    .font(.body)
                    .fontWeight(.medium)

                Text(pet.kind)
                    .font(.subheadline)
                    .foregroundColor(.secondary)

                if let weight = pet.currentWeight {
                    Text("\(formatWeight(weight)) lbs")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }

                if let dob = pet.dateOfBirth {
                    Text(formatAge(from: dob))
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }

            Spacer()

            Menu {
                Button(action: {
                    petToEdit = pet
                }) {
                    Label("Edit", systemImage: "pencil")
                }

                Button(role: .destructive, action: {
                    petToDelete = pet
                    showDeletePetConfirmation = true
                }) {
                    Label("Delete", systemImage: "trash")
                }
            } label: {
                Image(systemName: "ellipsis.circle")
                    .foregroundColor(.gray)
            }
        }
        .padding()
        .background(Color.gray.opacity(0.1))
        .cornerRadius(12)
    }

    // MARK: - Archived Pets Section

    private var archivedPetsSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Button(action: {
                withAnimation {
                    showArchivedPets.toggle()
                }
            }) {
                HStack {
                    Text("Archived Pets (\(archivedPets.count))")
                        .font(.headline)
                        .foregroundColor(.secondary)

                    Spacer()

                    Image(systemName: showArchivedPets ? "chevron.up" : "chevron.down")
                        .foregroundColor(.secondary)
                }
            }
            .buttonStyle(.plain)

            if showArchivedPets {
                VStack(spacing: 12) {
                    ForEach(archivedPets) { pet in
                        petRow(pet)
                            .opacity(0.6)
                    }
                }
            }
        }
    }

    // MARK: - Actions

    private func loadData(forceRefresh: Bool = false) async {
        // Only show loading indicator on initial load, not on pull-to-refresh
        if !hasLoaded {
            isLoading = true
        }
        errorMessage = nil

        // Load pets
        do {
            pets = try await DataService.shared.getPets(forceRefresh: forceRefresh)
        } catch is CancellationError {
            // Cancelled during navigation - ignore
        } catch let error as NSError where error.domain == NSURLErrorDomain && error.code == NSURLErrorCancelled {
            // Network request cancelled - ignore
        } catch {
            print("Error loading pets: \(error)")
        }

        // Load family members (separate try block so one failure doesn't stop the other)
        do {
            familyMembers = try await loadFamilyMembers(forceRefresh: forceRefresh)
        } catch is CancellationError {
            // Cancelled during navigation - ignore
        } catch let error as NSError where error.domain == NSURLErrorDomain && error.code == NSURLErrorCancelled {
            // Network request cancelled - ignore
        } catch {
            errorMessage = error.localizedDescription
            print("Error loading family members: \(error)")
        }

        hasLoaded = true
        isLoading = false
    }

    private func loadFamilyMembers(forceRefresh: Bool = false) async throws -> [FamilyMemberResponse] {
        guard let currentFamily = authManager.currentFamily else {
            return []
        }
        let response = try await DataService.shared.getFamilyMembers(for: currentFamily.id, forceRefresh: forceRefresh)

        // Update authManager with fresh family data (preserve role from current family)
        let updatedFamily = AppFamily(
            id: response.id,
            name: response.name,
            inviteCode: response.inviteCode,
            role: currentFamily.role
        )
        authManager.updateCurrentFamily(updatedFamily)

        return response.members
    }

    private func deletePet(_ pet: Pet) async {
        do {
            let response = try await DataService.shared.deletePet(id: pet.id)
            petToDelete = nil

            if response.archived && !response.deleted {
                // Pet was archived, update local state
                if let index = pets.firstIndex(where: { $0.id == pet.id }) {
                    let existingPet = pets[index]
                    // Create a new pet with isArchived = true
                    pets[index] = Pet(
                        id: existingPet.id,
                        orgId: existingPet.orgId,
                        name: existingPet.name,
                        kind: existingPet.kind,
                        photoUrl: existingPet.photoUrl,
                        currentWeight: existingPet.currentWeight,
                        dateOfBirth: existingPet.dateOfBirth,
                        isArchived: true,
                        createdAt: existingPet.createdAt,
                        createdBy: existingPet.createdBy
                    )
                }
                deleteResultMessage = response.message
                showDeleteResultAlert = true
            } else {
                // Pet was actually deleted
                pets.removeAll { $0.id == pet.id }
            }
        } catch {
            errorMessage = error.localizedDescription
            print("Error deleting pet: \(error)")
        }
    }

    private func removeMember(_ member: FamilyMemberResponse) async {
        guard let familyId = authManager.currentFamily?.id else { return }

        do {
            try await DataService.shared.removeFamilyMember(familyId: familyId, userId: member.userId)
            memberToRemove = nil
            familyMembers.removeAll { $0.userId == member.userId }
        } catch {
            errorMessage = error.localizedDescription
            print("Error removing member: \(error)")
        }
    }

    // MARK: - Helpers

    private func formatDate(_ date: Date) -> String {
        Formatters.shortDate.string(from: date)
    }

    private func formatWeight(_ weight: Double) -> String {
        Formatters.weight.string(from: NSNumber(value: weight)) ?? "\(weight)"
    }

    private func formatAge(from dateOfBirth: Date) -> String {
        let calendar = Calendar.current
        let now = Date()
        let components = calendar.dateComponents([.year, .month], from: dateOfBirth, to: now)

        if let years = components.year, years > 0 {
            if let months = components.month, months > 0 {
                return "\(years) yr\(years == 1 ? "" : "s"), \(months) mo"
            }
            return "\(years) year\(years == 1 ? "" : "s") old"
        } else if let months = components.month, months > 0 {
            return "\(months) month\(months == 1 ? "" : "s") old"
        }
        return "Less than 1 month old"
    }
}

#Preview {
    FamilyManagementView()
}
