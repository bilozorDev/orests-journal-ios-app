//
//  FamilyManagementView.swift
//  Orest's Journal
//
//  Created by Claude on 11/26/25.
//

import SwiftUI
import PhotosUI

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
        NavigationStack {
            ScrollView {
                VStack(spacing: 20) {
                    // Family Info Section
                    familyInfoSection

                    // Family Members Section
                    familyMembersSection

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
    }

    // MARK: - Family Info Section

    private var familyInfoSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Family")
                .font(.headline)
                .foregroundColor(.secondary)

            if let family = authManager.currentFamily {
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Image(systemName: "house.circle.fill")
                            .font(.title2)
                            .foregroundColor(.green)

                        VStack(alignment: .leading, spacing: 4) {
                            Text(family.name)
                                .font(.body)
                                .fontWeight(.medium)

                            Text("Role: \(family.role.capitalized)")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }

                        Spacer()
                    }
                    .padding()
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(Color.gray.opacity(0.1))
                    .cornerRadius(12)

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
                    .padding(.top, 4)

                    Text("Share this code to invite family members")
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }
            }
        }
    }

    // MARK: - Family Members Section

    private var familyMembersSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Members")
                .font(.headline)
                .foregroundColor(.secondary)

            if familyMembers.isEmpty {
                VStack(spacing: 8) {
                    Image(systemName: "person.2.circle")
                        .font(.system(size: 40))
                        .foregroundColor(.gray)
                    Text("No family members")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 20)
                .background(Color.gray.opacity(0.1))
                .cornerRadius(12)
            } else {
                VStack(spacing: 8) {
                    ForEach(familyMembers) { member in
                        memberRow(member)
                    }
                }
            }
        }
    }

    private func memberRow(_ member: FamilyMemberResponse) -> some View {
        let isCurrentUser = member.userId == authManager.userId

        return HStack(spacing: 12) {
            Image(systemName: "person.circle.fill")
                .font(.title2)
                .foregroundColor(member.role == "admin" ? .orange : .blue)

            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(member.displayName)
                        .font(.body)
                        .fontWeight(.medium)

                    if isCurrentUser {
                        Text("(You)")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }

                HStack(spacing: 8) {
                    Text(member.role.capitalized)
                        .font(.caption)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 2)
                        .background(member.role == "admin" ? Color.orange.opacity(0.2) : Color.blue.opacity(0.2))
                        .foregroundColor(member.role == "admin" ? .orange : .blue)
                        .cornerRadius(4)

                    if let joinedAt = member.joinedAt {
                        Text("Joined \(formatDate(joinedAt))")
                            .font(.caption)
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
        .padding()
        .background(Color.gray.opacity(0.1))
        .cornerRadius(12)
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
        isLoading = true
        errorMessage = nil

        do {
            async let petsTask = DataService.shared.getPets(forceRefresh: forceRefresh)
            async let membersTask = loadFamilyMembers()

            pets = try await petsTask
            familyMembers = try await membersTask
            hasLoaded = true
        } catch let error as NSError where error.domain == NSURLErrorDomain && error.code == NSURLErrorCancelled {
            print("Family data load cancelled (this is normal during navigation)")
        } catch {
            errorMessage = error.localizedDescription
            print("Error loading family data: \(error)")
        }

        isLoading = false
    }

    private func loadFamilyMembers() async throws -> [FamilyMemberResponse] {
        guard let familyId = authManager.currentFamily?.id else {
            return []
        }
        return try await DataService.shared.getFamilyMembers(familyId: familyId)
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
            try await DataService.shared.removeFamilyMember(familyId: familyId, memberUserId: member.userId)
            memberToRemove = nil
            familyMembers.removeAll { $0.userId == member.userId }
        } catch {
            errorMessage = error.localizedDescription
            print("Error removing member: \(error)")
        }
    }

    // MARK: - Helpers

    private func formatDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateStyle = .short
        return formatter.string(from: date)
    }

    private func formatWeight(_ weight: Double) -> String {
        let formatter = NumberFormatter()
        formatter.minimumFractionDigits = 0
        formatter.maximumFractionDigits = 1
        return formatter.string(from: NSNumber(value: weight)) ?? "\(weight)"
    }
}

#Preview {
    FamilyManagementView()
}
