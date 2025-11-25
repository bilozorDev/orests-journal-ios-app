//
//  DataService.swift
//  Orest's Journal
//
//  Data service wrapping APIClient for pet health management.
//

import Foundation

/// Data service providing high-level methods for pet health management.
/// Wraps APIClient and provides organization-scoped data access.
@MainActor
final class DataService {
    static let shared = DataService()

    private let api = APIClient.shared

    private init() {}

    // MARK: - Pet Functions

    func getPets() async throws -> [Pet] {
        return try await api.getPets()
    }

    func createPet(
        name: String,
        kind: String,
        photoUrl: String?,
        currentWeight: Double?
    ) async throws -> Pet {
        let pet = PetCreate(
            name: name,
            kind: kind,
            photoUrl: photoUrl,
            currentWeight: currentWeight
        )
        return try await api.createPet(pet)
    }

    func updatePet(id: UUID, name: String?, kind: String?, photoUrl: String?, currentWeight: Double?) async throws -> Pet {
        let update = PetUpdate(
            name: name,
            kind: kind,
            photoUrl: photoUrl,
            currentWeight: currentWeight
        )
        return try await api.updatePet(id: id, update: update)
    }

    func deletePet(id: UUID) async throws {
        try await api.deletePet(id: id)
    }

    // MARK: - Food Functions

    func getFoods() async throws -> [PetFood] {
        return try await api.getFoods()
    }

    func createFood(
        name: String,
        category: FoodCategory,
        caloriesPerKg: Double,
        containerSize: Double,
        containerSizeUnit: ContainerUnit,
        imageUrl: String?
    ) async throws -> PetFood {
        let food = FoodCreate(
            name: name,
            category: category.rawValue,
            caloriesPerKg: caloriesPerKg,
            containerSize: containerSize,
            containerSizeUnit: containerSizeUnit.rawValue,
            imageUrl: imageUrl
        )
        return try await api.createFood(food)
    }

    func deleteFood(id: UUID) async throws {
        try await api.deleteFood(id: id)
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
        let feeding = FeedingCreate(
            petId: petId,
            foodId: foodId,
            amount: amount,
            amountUnit: amountUnit.rawValue,
            calories: calories,
            notes: notes,
            fedAt: nil
        )
        return try await api.createFeeding(feeding)
    }

    func getTodayFeedings(for petId: UUID) async throws -> [PetFeeding] {
        let response = try await api.getTodayFeedings(petId: petId)
        return response.feedings
    }

    func getTodayCalories(for petId: UUID) async throws -> Double {
        let response = try await api.getTodayFeedings(petId: petId)
        return response.totalCalories
    }

    func getFeedingHistory(for petId: UUID, limit: Int = 50) async throws -> [PetFeeding] {
        return try await api.getFeedingHistory(petId: petId, limit: limit)
    }

    // MARK: - Calorie Goal Functions

    func getActiveCalorieGoal(for petId: UUID) async throws -> CalorieGoal? {
        return try await api.getCalorieGoal(petId: petId)
    }

    func setCalorieGoal(for petId: UUID, dailyCalories: Double, notes: String? = nil) async throws -> CalorieGoal {
        return try await api.setCalorieGoal(petId: petId, dailyCalories: dailyCalories, notes: notes)
    }

    // MARK: - Medication Functions

    func getMedications(petId: UUID? = nil, activeOnly: Bool = false) async throws -> [PetMedication] {
        return try await api.getMedications(petId: petId, activeOnly: activeOnly)
    }

    func getActiveMedications(for petId: UUID) async throws -> [PetMedication] {
        return try await api.getActiveMedications(petId: petId)
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
        let medication = MedicationCreate(
            petId: petId,
            name: name,
            medicationType: medicationType.rawValue,
            startDate: startDate,
            endDate: endDate,
            timesPerDay: timesPerDay,
            notes: notes
        )
        return try await api.createMedication(medication)
    }

    func deleteMedication(id: UUID) async throws {
        try await api.deleteMedication(id: id)
    }

    // MARK: - Dose Functions

    func recordDose(medicationId: UUID, notes: String? = nil) async throws -> PetMedicationDose {
        let dose = DoseCreate(
            medicationId: medicationId,
            notes: notes,
            givenAt: nil
        )
        return try await api.recordDose(dose)
    }

    func getTodayDoses(for medicationId: UUID) async throws -> [PetMedicationDose] {
        return try await api.getTodayDoses(medicationId: medicationId)
    }

    func getLastDose(for medicationId: UUID) async throws -> PetMedicationDose? {
        return try await api.getLastDose(medicationId: medicationId)
    }

    func getDoses(for medicationId: UUID, limit: Int = 50) async throws -> [PetMedicationDose] {
        return try await api.getDoses(medicationId: medicationId, limit: limit)
    }

    // MARK: - Health Journal Functions

    func getHealthCategories(for petId: UUID) async throws -> [HealthCategory] {
        return try await api.getHealthCategories(petId: petId)
    }

    func createHealthEvent(
        petId: UUID,
        categoryName: String,
        occurredAt: Date = Date(),
        notes: String?
    ) async throws -> HealthEvent {
        let event = HealthEventCreate(
            categoryName: categoryName,
            occurredAt: occurredAt,
            notes: notes
        )
        return try await api.createHealthEvent(petId: petId, event: event)
    }

    func getHealthEvents(for petId: UUID, limit: Int = 100) async throws -> [HealthEventWithCategory] {
        return try await api.getHealthEvents(petId: petId, limit: limit)
    }

    func deleteHealthEvent(id: UUID) async throws {
        try await api.deleteHealthEvent(id: id)
    }

    // MARK: - Helper Functions

    func getUserEmail(for userId: String?) async -> String {
        // Check if this is the current user
        // For now, return a generic label
        if let userId = userId, userId == AuthManager.shared.userId {
            return AuthManager.shared.userEmail ?? "You"
        }
        return "Family Member"
    }
}
