//
//  SupabaseService.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import Foundation
import Supabase
import UIKit

class SupabaseService {
    static let shared = SupabaseService()

    private init() {}

    // MARK: - Family Functions

    func getCurrentUserFamily() async throws -> Family? {
        let userId = try await supabase.auth.session.user.id

        // First get family members for this user
        let familyMembers: [FamilyMember] = try await supabase
            .from("family_members")
            .select()
            .eq("user_id", value: userId.uuidString)
            .limit(1)
            .execute()
            .value

        guard let familyMember = familyMembers.first else {
            return nil
        }

        // Then get the family
        let families: [Family] = try await supabase
            .from("families")
            .select()
            .eq("id", value: familyMember.familyId.uuidString)
            .limit(1)
            .execute()
            .value

        return families.first
    }

    func checkUserFamilyAndPet() async throws -> (hasFamily: Bool, hasPet: Bool) {
        let userId = try await supabase.auth.session.user.id
        print("🔍 Checking family/pet status for user: \(userId.uuidString)")

        // Check if user is in a family
        print("🔍 Querying family_members table...")
        let familyMembers: [FamilyMember] = try await supabase
            .from("family_members")
            .select()
            .eq("user_id", value: userId.uuidString)
            .execute()
            .value

        print("🔍 Found \(familyMembers.count) family memberships")

        guard let familyMember = familyMembers.first else {
            print("🔍 No family membership found")
            return (false, false)
        }

        print("🔍 User is member of family: \(familyMember.familyId.uuidString)")

        // Check if family has pets
        print("🔍 Querying pets table...")
        let pets: [Pet] = try await supabase
            .from("pets")
            .select()
            .eq("family_id", value: familyMember.familyId.uuidString)
            .execute()
            .value

        print("🔍 Found \(pets.count) pets in family")

        return (true, !pets.isEmpty)
    }

    func createFamily(name: String) async throws -> Family {
        let userId = try await supabase.auth.session.user.id

        // Create family
        let newFamily: Family = try await supabase
            .from("families")
            .insert([
                "name": name,
                "created_by": userId.uuidString
            ])
            .select()
            .single()
            .execute()
            .value

        // Add user as owner
        let _: FamilyMember = try await supabase
            .from("family_members")
            .insert([
                "family_id": newFamily.id.uuidString,
                "user_id": userId.uuidString,
                "role": "owner"
            ])
            .select()
            .single()
            .execute()
            .value

        return newFamily
    }

    // MARK: - Pet Functions

    func getFamilyPets(familyId: UUID) async throws -> [Pet] {
        let pets: [Pet] = try await supabase
            .from("pets")
            .select()
            .eq("family_id", value: familyId.uuidString)
            .order("created_at", ascending: false)
            .execute()
            .value

        return pets
    }

    func createPet(
        familyId: UUID,
        name: String,
        kind: String,
        photoUrl: String?,
        currentWeight: Double
    ) async throws -> Pet {
        struct PetInsert: Encodable {
            let familyId: String
            let name: String
            let kind: String
            let photoUrl: String?
            let currentWeight: Double

            enum CodingKeys: String, CodingKey {
                case familyId = "family_id"
                case name
                case kind
                case photoUrl = "photo_url"
                case currentWeight = "current_weight"
            }
        }

        let petInsert = PetInsert(
            familyId: familyId.uuidString,
            name: name,
            kind: kind,
            photoUrl: photoUrl,
            currentWeight: currentWeight
        )

        let pet: Pet = try await supabase
            .from("pets")
            .insert(petInsert)
            .select()
            .single()
            .execute()
            .value

        // Create initial health record
        _ = try await createHealthRecord(
            petId: pet.id,
            ageYears: 0,  // Default to 0 since we don't have DOB
            weightPounds: currentWeight,
            notes: "Initial weight record"
        )

        return pet
    }

    // MARK: - Health Record Functions

    func createHealthRecord(
        petId: UUID,
        ageYears: Double,
        weightPounds: Double,
        notes: String?
    ) async throws -> HealthRecord {
        struct HealthRecordInsert: Encodable {
            let petId: String
            let ageYears: Double
            let weightPounds: Double
            let notes: String?

            enum CodingKeys: String, CodingKey {
                case petId = "pet_id"
                case ageYears = "age_years"
                case weightPounds = "weight_pounds"
                case notes
            }
        }

        let recordInsert = HealthRecordInsert(
            petId: petId.uuidString,
            ageYears: ageYears,
            weightPounds: weightPounds,
            notes: notes
        )

        let record: HealthRecord = try await supabase
            .from("health_records")
            .insert(recordInsert)
            .select()
            .single()
            .execute()
            .value

        return record
    }

    func getHealthRecords(for petId: UUID) async throws -> [HealthRecord] {
        let records: [HealthRecord] = try await supabase
            .from("health_records")
            .select()
            .eq("pet_id", value: petId.uuidString)
            .order("recorded_at", ascending: false)
            .execute()
            .value

        return records
    }

    // MARK: - Food Functions

    func getFamilyFoods(familyId: UUID) async throws -> [PetFood] {
        let foods: [PetFood] = try await supabase
            .from("pet_foods")
            .select()
            .eq("family_id", value: familyId.uuidString)
            .order("created_at", ascending: false)
            .execute()
            .value

        return foods
    }

    func createFood(
        familyId: UUID,
        name: String,
        category: FoodCategory,
        caloriesPerContainer: Double,
        containerSizeGrams: Double,
        imageUrl: String?
    ) async throws -> PetFood {
        struct FoodInsert: Encodable {
            let familyId: String
            let name: String
            let category: String
            let caloriesPerContainer: Double
            let containerSizeGrams: Double
            let imageUrl: String?
            let createdBy: String

            enum CodingKeys: String, CodingKey {
                case familyId = "family_id"
                case name
                case category
                case caloriesPerContainer = "calories_per_container"
                case containerSizeGrams = "container_size_grams"
                case imageUrl = "image_url"
                case createdBy = "created_by"
            }
        }

        let userId = try await supabase.auth.session.user.id

        let foodInsert = FoodInsert(
            familyId: familyId.uuidString,
            name: name,
            category: category.rawValue,
            caloriesPerContainer: caloriesPerContainer,
            containerSizeGrams: containerSizeGrams,
            imageUrl: imageUrl,
            createdBy: userId.uuidString
        )

        let food: PetFood = try await supabase
            .from("pet_foods")
            .insert(foodInsert)
            .select()
            .single()
            .execute()
            .value

        return food
    }

    // MARK: - Storage Functions

    func uploadPetPhoto(_ image: UIImage) async throws -> String {
        guard let imageData = image.jpegData(compressionQuality: 0.7) else {
            throw NSError(domain: "SupabaseService", code: 400, userInfo: [NSLocalizedDescriptionKey: "Failed to convert image to data"])
        }

        let fileName = "\(UUID().uuidString).jpg"
        let filePath = fileName

        try await supabase.storage
            .from("pet-photos")
            .upload(
                filePath,
                data: imageData,
                options: FileOptions(contentType: "image/jpeg")
            )

        let publicURL = try supabase.storage
            .from("pet-photos")
            .getPublicURL(path: filePath)

        return publicURL.absoluteString
    }

    func uploadFoodImage(_ image: UIImage) async throws -> String {
        guard let imageData = image.jpegData(compressionQuality: 0.7) else {
            throw NSError(domain: "SupabaseService", code: 400, userInfo: [NSLocalizedDescriptionKey: "Failed to convert image to data"])
        }

        let fileName = "\(UUID().uuidString).jpg"
        let filePath = fileName

        try await supabase.storage
            .from("food-images")
            .upload(
                filePath,
                data: imageData,
                options: FileOptions(contentType: "image/jpeg")
            )

        let publicURL = try supabase.storage
            .from("food-images")
            .getPublicURL(path: filePath)

        return publicURL.absoluteString
    }

    // MARK: - Helper Functions

    private func calculateAge(from dateOfBirth: Date) -> Double {
        let calendar = Calendar.current
        let components = calendar.dateComponents([.year, .month], from: dateOfBirth, to: Date())
        let years = Double(components.year ?? 0)
        let months = Double(components.month ?? 0)
        return years + (months / 12.0)
    }
}
