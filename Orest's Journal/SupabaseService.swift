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
        caloriesPerKg: Double,
        containerSize: Double,
        containerSizeUnit: ContainerUnit,
        imageUrl: String?
    ) async throws -> PetFood {
        struct FoodInsert: Encodable {
            let familyId: String
            let name: String
            let category: String
            let caloriesPerKg: Double
            let containerSize: Double
            let containerSizeUnit: String
            let imageUrl: String?
            let createdBy: String

            enum CodingKeys: String, CodingKey {
                case familyId = "family_id"
                case name
                case category
                case caloriesPerKg = "calories_per_kg"
                case containerSize = "container_size"
                case containerSizeUnit = "container_size_unit"
                case imageUrl = "image_url"
                case createdBy = "created_by"
            }
        }

        let userId = try await supabase.auth.session.user.id

        let foodInsert = FoodInsert(
            familyId: familyId.uuidString,
            name: name,
            category: category.rawValue,
            caloriesPerKg: caloriesPerKg,
            containerSize: containerSize,
            containerSizeUnit: containerSizeUnit.rawValue,
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

    func deleteFood(_ foodId: UUID) async throws {
        try await supabase
            .from("pet_foods")
            .delete()
            .eq("id", value: foodId.uuidString)
            .execute()
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

    // MARK: - Feeding Functions

    func createFeeding(
        petId: UUID,
        foodId: UUID,
        amount: Double,
        amountUnit: ContainerUnit,
        calories: Double,
        notes: String? = nil
    ) async throws -> PetFeeding {
        struct FeedingInsert: Encodable {
            let petId: String
            let foodId: String
            let fedBy: String
            let amount: Double
            let amountUnit: String
            let calories: Double
            let notes: String?

            enum CodingKeys: String, CodingKey {
                case petId = "pet_id"
                case foodId = "food_id"
                case fedBy = "fed_by"
                case amount
                case amountUnit = "amount_unit"
                case calories
                case notes
            }
        }

        let userId = try await supabase.auth.session.user.id

        let feedingInsert = FeedingInsert(
            petId: petId.uuidString,
            foodId: foodId.uuidString,
            fedBy: userId.uuidString,
            amount: amount,
            amountUnit: amountUnit.rawValue,
            calories: calories,
            notes: notes
        )

        let feeding: PetFeeding = try await supabase
            .from("pet_feedings")
            .insert(feedingInsert)
            .select()
            .single()
            .execute()
            .value

        return feeding
    }

    func getTodayCalories(for petId: UUID) async throws -> Double {
        let calendar = Calendar.current
        let today = calendar.startOfDay(for: Date())
        let tomorrow = calendar.date(byAdding: .day, value: 1, to: today)!

        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]

        let feedings: [PetFeeding] = try await supabase
            .from("pet_feedings")
            .select()
            .eq("pet_id", value: petId.uuidString)
            .gte("fed_at", value: formatter.string(from: today))
            .lt("fed_at", value: formatter.string(from: tomorrow))
            .execute()
            .value

        return feedings.reduce(0) { $0 + $1.calories }
    }

    func getTodayFeedings(for petId: UUID) async throws -> [PetFeeding] {
        let calendar = Calendar.current
        let today = calendar.startOfDay(for: Date())
        let tomorrow = calendar.date(byAdding: .day, value: 1, to: today)!

        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]

        let feedings: [PetFeeding] = try await supabase
            .from("pet_feedings")
            .select()
            .eq("pet_id", value: petId.uuidString)
            .gte("fed_at", value: formatter.string(from: today))
            .lt("fed_at", value: formatter.string(from: tomorrow))
            .order("fed_at", ascending: false)
            .execute()
            .value

        return feedings
    }

    func getFeedingHistory(for petId: UUID, limit: Int = 50) async throws -> [PetFeeding] {
        let feedings: [PetFeeding] = try await supabase
            .from("pet_feedings")
            .select()
            .eq("pet_id", value: petId.uuidString)
            .order("fed_at", ascending: false)
            .limit(limit)
            .execute()
            .value

        return feedings
    }

    // MARK: - Calorie Goal Functions

    func getActiveCalorieGoal(for petId: UUID) async throws -> CalorieGoal? {
        let today = Date()
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        let todayString = formatter.string(from: today)

        let goals: [CalorieGoal] = try await supabase
            .from("pet_calorie_goals")
            .select()
            .eq("pet_id", value: petId.uuidString)
            .lte("effective_from", value: todayString)
            .or("effective_until.is.null,effective_until.gte.\(todayString)")
            .order("effective_from", ascending: false)
            .limit(1)
            .execute()
            .value

        return goals.first
    }

    func setCalorieGoal(
        for petId: UUID,
        dailyCalories: Double,
        effectiveFrom: Date = Date(),
        notes: String? = nil
    ) async throws -> CalorieGoal {
        struct GoalInsert: Encodable {
            let petId: String
            let dailyCalories: Double
            let notes: String?
            let createdBy: String

            enum CodingKeys: String, CodingKey {
                case petId = "pet_id"
                case dailyCalories = "daily_calories"
                case notes
                case createdBy = "created_by"
            }
        }

        let userId = try await supabase.auth.session.user.id

        let goalInsert = GoalInsert(
            petId: petId.uuidString,
            dailyCalories: dailyCalories,
            notes: notes,
            createdBy: userId.uuidString
        )

        let goal: CalorieGoal = try await supabase
            .from("pet_calorie_goals")
            .insert(goalInsert)
            .select()
            .single()
            .execute()
            .value

        return goal
    }

    // MARK: - Medication Functions

    func getFamilyMedications(familyId: UUID) async throws -> [PetMedication] {
        // Get all pets for the family
        let pets = try await getFamilyPets(familyId: familyId)
        let petIds = pets.map { $0.id.uuidString }

        guard !petIds.isEmpty else {
            return []
        }

        let medications: [PetMedication] = try await supabase
            .from("pet_medications")
            .select()
            .in("pet_id", values: petIds)
            .order("created_at", ascending: false)
            .execute()
            .value

        return medications
    }

    func getActiveMedications(for petId: UUID) async throws -> [PetMedication] {
        let today = Calendar.current.startOfDay(for: Date())
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        let todayString = formatter.string(from: today)

        let medications: [PetMedication] = try await supabase
            .from("pet_medications")
            .select()
            .eq("pet_id", value: petId.uuidString)
            .lte("start_date", value: todayString)
            .or("end_date.is.null,end_date.gte.\(todayString)")
            .order("created_at", ascending: false)
            .execute()
            .value

        return medications
    }

    func createMedication(
        petId: UUID,
        name: String,
        medicationType: MedicationType,
        startDate: Date,
        endDate: Date?,
        timesPerDay: Int,
        notes: String?
    ) async throws -> PetMedication {
        struct MedicationInsert: Encodable {
            let petId: String
            let name: String
            let medicationType: String
            let startDate: String
            let endDate: String?
            let timesPerDay: Int
            let notes: String?
            let createdBy: String

            enum CodingKeys: String, CodingKey {
                case petId = "pet_id"
                case name
                case medicationType = "medication_type"
                case startDate = "start_date"
                case endDate = "end_date"
                case timesPerDay = "times_per_day"
                case notes
                case createdBy = "created_by"
            }
        }

        let userId = try await supabase.auth.session.user.id
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]

        let medicationInsert = MedicationInsert(
            petId: petId.uuidString,
            name: name,
            medicationType: medicationType.rawValue,
            startDate: formatter.string(from: startDate),
            endDate: endDate.map { formatter.string(from: $0) },
            timesPerDay: timesPerDay,
            notes: notes,
            createdBy: userId.uuidString
        )

        let medication: PetMedication = try await supabase
            .from("pet_medications")
            .insert(medicationInsert)
            .select()
            .single()
            .execute()
            .value

        return medication
    }

    func recordDose(
        medicationId: UUID,
        notes: String? = nil
    ) async throws -> PetMedicationDose {
        struct DoseInsert: Encodable {
            let medicationId: String
            let givenBy: String
            let notes: String?

            enum CodingKeys: String, CodingKey {
                case medicationId = "medication_id"
                case givenBy = "given_by"
                case notes
            }
        }

        let userId = try await supabase.auth.session.user.id

        let doseInsert = DoseInsert(
            medicationId: medicationId.uuidString,
            givenBy: userId.uuidString,
            notes: notes
        )

        let dose: PetMedicationDose = try await supabase
            .from("pet_medication_doses")
            .insert(doseInsert)
            .select()
            .single()
            .execute()
            .value

        return dose
    }

    func getMedicationDoses(for medicationId: UUID, limit: Int = 50) async throws -> [PetMedicationDose] {
        let doses: [PetMedicationDose] = try await supabase
            .from("pet_medication_doses")
            .select()
            .eq("medication_id", value: medicationId.uuidString)
            .order("given_at", ascending: false)
            .limit(limit)
            .execute()
            .value

        return doses
    }

    func getLastDose(for medicationId: UUID) async throws -> PetMedicationDose? {
        let doses: [PetMedicationDose] = try await supabase
            .from("pet_medication_doses")
            .select()
            .eq("medication_id", value: medicationId.uuidString)
            .order("given_at", ascending: false)
            .limit(1)
            .execute()
            .value

        return doses.first
    }

    func getDosesToday(for medicationId: UUID) async throws -> [PetMedicationDose] {
        // Get start of today in UTC
        let calendar = Calendar.current
        let startOfToday = calendar.startOfDay(for: Date())

        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let todayString = formatter.string(from: startOfToday)

        let doses: [PetMedicationDose] = try await supabase
            .from("pet_medication_doses")
            .select()
            .eq("medication_id", value: medicationId.uuidString)
            .gte("given_at", value: todayString)
            .order("given_at", ascending: false)
            .execute()
            .value

        return doses
    }

    func deleteMedication(_ medicationId: UUID) async throws {
        try await supabase
            .from("pet_medications")
            .delete()
            .eq("id", value: medicationId.uuidString)
            .execute()
    }

    // MARK: - Health Journal Functions

    func getHealthCategories(for petId: UUID) async throws -> [HealthCategory] {
        let categories: [HealthCategory] = try await supabase
            .from("pet_health_categories")
            .select()
            .eq("pet_id", value: petId.uuidString)
            .order("name", ascending: true)
            .execute()
            .value

        return categories
    }

    func getOrCreateHealthCategory(petId: UUID, name: String) async throws -> HealthCategory {
        let normalized = name.lowercased().trimmingCharacters(in: .whitespaces)

        // Try to find existing category (case-insensitive)
        let existing: [HealthCategory] = try await supabase
            .from("pet_health_categories")
            .select()
            .eq("pet_id", value: petId.uuidString)
            .eq("name_normalized", value: normalized)
            .limit(1)
            .execute()
            .value

        if let category = existing.first {
            return category
        }

        // Create new category
        struct CategoryInsert: Encodable {
            let petId: String
            let name: String
            let nameNormalized: String
            let createdBy: String

            enum CodingKeys: String, CodingKey {
                case petId = "pet_id"
                case name
                case nameNormalized = "name_normalized"
                case createdBy = "created_by"
            }
        }

        let userId = try await supabase.auth.session.user.id

        let categoryInsert = CategoryInsert(
            petId: petId.uuidString,
            name: name.trimmingCharacters(in: .whitespaces),
            nameNormalized: normalized,
            createdBy: userId.uuidString
        )

        let category: HealthCategory = try await supabase
            .from("pet_health_categories")
            .insert(categoryInsert)
            .select()
            .single()
            .execute()
            .value

        return category
    }

    func createHealthEvent(
        petId: UUID,
        categoryName: String,
        occurredAt: Date = Date(),
        notes: String?
    ) async throws -> HealthEvent {
        // Get or create category
        let category = try await getOrCreateHealthCategory(petId: petId, name: categoryName)

        // Create event
        struct EventInsert: Encodable {
            let categoryId: String
            let occurredAt: String
            let notes: String?
            let createdBy: String

            enum CodingKeys: String, CodingKey {
                case categoryId = "category_id"
                case occurredAt = "occurred_at"
                case notes
                case createdBy = "created_by"
            }
        }

        let userId = try await supabase.auth.session.user.id
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]

        let eventInsert = EventInsert(
            categoryId: category.id.uuidString,
            occurredAt: formatter.string(from: occurredAt),
            notes: notes?.isEmpty == false ? notes : nil,
            createdBy: userId.uuidString
        )

        let event: HealthEvent = try await supabase
            .from("pet_health_events")
            .insert(eventInsert)
            .select()
            .single()
            .execute()
            .value

        return event
    }

    func getHealthEvents(for petId: UUID, limit: Int = 100) async throws -> [HealthEventWithCategory] {
        // Get all categories for this pet
        let categories = try await getHealthCategories(for: petId)
        let categoryIds = categories.map { $0.id.uuidString }

        guard !categoryIds.isEmpty else {
            return []
        }

        // Get events for these categories
        let events: [HealthEvent] = try await supabase
            .from("pet_health_events")
            .select()
            .in("category_id", values: categoryIds)
            .order("occurred_at", ascending: false)
            .limit(limit)
            .execute()
            .value

        // Create category lookup
        let categoryDict = Dictionary(uniqueKeysWithValues: categories.map { ($0.id, $0) })

        // Combine events with categories
        let eventsWithCategories = events.compactMap { event -> HealthEventWithCategory? in
            guard let category = categoryDict[event.categoryId] else { return nil }
            return HealthEventWithCategory(event: event, category: category)
        }

        return eventsWithCategories
    }

    func deleteHealthEvent(_ eventId: UUID) async throws {
        try await supabase
            .from("pet_health_events")
            .delete()
            .eq("id", value: eventId.uuidString)
            .execute()
    }

    // MARK: - Helper Functions

    private func calculateAge(from dateOfBirth: Date) -> Double {
        let calendar = Calendar.current
        let components = calendar.dateComponents([.year, .month], from: dateOfBirth, to: Date())
        let years = Double(components.year ?? 0)
        let months = Double(components.month ?? 0)
        return years + (months / 12.0)
    }

    func getUserEmail(for userId: UUID?) async -> String {
        guard let userId = userId else {
            return "Unknown"
        }

        // Check if this is the current user
        if let currentUser = try? await supabase.auth.session.user,
           currentUser.id == userId {
            return currentUser.email ?? "Unknown"
        }

        // For other family members, we would need a user_profiles table
        // For now, just return a generic label
        return "Family Member"
    }
}
