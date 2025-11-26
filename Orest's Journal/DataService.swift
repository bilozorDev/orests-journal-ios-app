//
//  DataService.swift
//  Orest's Journal
//
//  Data service wrapping APIClient for pet health management.
//

import Foundation

/// Data service providing high-level methods for pet health management.
/// Wraps APIClient and provides organization-scoped data access with caching.
@MainActor
final class DataService {
    static let shared = DataService()

    private let api = APIClient.shared

    // MARK: - Cache

    private struct CacheEntry<T> {
        let data: T
        let timestamp: Date
    }

    private var dashboardCache: [UUID: CacheEntry<DashboardData>] = [:]
    private let cacheTTL: TimeInterval = 60  // 1 minute

    private init() {}

    /// Returns cached data if still valid, nil otherwise
    private func getCachedDashboard(for petId: UUID) -> DashboardData? {
        guard let entry = dashboardCache[petId],
              Date().timeIntervalSince(entry.timestamp) < cacheTTL else {
            return nil
        }
        return entry.data
    }

    /// Stores data in cache with current timestamp
    private func cacheDashboard(_ data: DashboardData, for petId: UUID) {
        dashboardCache[petId] = CacheEntry(data: data, timestamp: Date())
    }

    /// Invalidates dashboard cache for a specific pet or all pets
    func invalidateDashboardCache(for petId: UUID? = nil) {
        if let petId = petId {
            dashboardCache.removeValue(forKey: petId)
        } else {
            dashboardCache.removeAll()
        }
    }

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

    func getFoods(includeArchived: Bool = false) async throws -> [PetFood] {
        return try await api.getFoods(includeArchived: includeArchived)
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

    func updateFood(
        id: UUID,
        name: String? = nil,
        category: FoodCategory? = nil,
        caloriesPerKg: Double? = nil,
        containerSize: Double? = nil,
        containerSizeUnit: ContainerUnit? = nil,
        imageUrl: String? = nil
    ) async throws -> PetFood {
        let update = FoodUpdate(
            name: name,
            category: category?.rawValue,
            caloriesPerKg: caloriesPerKg,
            containerSize: containerSize,
            containerSizeUnit: containerSizeUnit?.rawValue,
            imageUrl: imageUrl
        )
        return try await api.updateFood(id: id, update: update)
    }

    func deleteFood(id: UUID) async throws -> FoodDeleteResponse {
        return try await api.deleteFood(id: id)
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
        let result = try await api.createFeeding(feeding)
        invalidateDashboardCache(for: petId)
        return result
    }

    func getTodayFeedings(for petId: UUID) async throws -> [PetFeeding] {
        let response = try await api.getTodayFeedings(petId: petId)
        return response.feedings
    }

    func getTodayCalories(for petId: UUID) async throws -> Double {
        let response = try await api.getTodayFeedings(petId: petId)
        return response.totalCalories
    }

    /// Returns both today's feedings and total calories in a single API call
    func getTodayFeedingsWithCalories(for petId: UUID) async throws -> (feedings: [PetFeeding], totalCalories: Double) {
        let response = try await api.getTodayFeedings(petId: petId)
        return (feedings: response.feedings, totalCalories: response.totalCalories)
    }

    func getFeedingHistory(for petId: UUID, limit: Int = 50) async throws -> [PetFeeding] {
        return try await api.getFeedingHistory(petId: petId, limit: limit)
    }

    func updateFeeding(
        id: UUID,
        amount: Double? = nil,
        amountUnit: ContainerUnit? = nil,
        calories: Double? = nil,
        notes: String? = nil,
        fedAt: Date? = nil,
        petId: UUID? = nil
    ) async throws -> PetFeeding {
        let update = FeedingUpdate(
            amount: amount,
            amountUnit: amountUnit?.rawValue,
            calories: calories,
            notes: notes,
            fedAt: fedAt
        )
        let result = try await api.updateFeeding(id: id, update: update)
        if let petId = petId {
            invalidateDashboardCache(for: petId)
        }
        return result
    }

    func deleteFeeding(id: UUID, petId: UUID? = nil) async throws {
        try await api.deleteFeeding(id: id)
        if let petId = petId {
            invalidateDashboardCache(for: petId)
        }
    }

    // MARK: - Calorie Goal Functions

    func getActiveCalorieGoal(for petId: UUID) async throws -> CalorieGoal? {
        return try await api.getCalorieGoal(petId: petId)
    }

    func setCalorieGoal(for petId: UUID, dailyCalories: Double, notes: String? = nil) async throws -> CalorieGoal {
        let result = try await api.setCalorieGoal(petId: petId, dailyCalories: dailyCalories, notes: notes)
        invalidateDashboardCache(for: petId)
        return result
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
        let result = try await api.createMedication(medication)
        invalidateDashboardCache(for: petId)
        return result
    }

    func deleteMedication(id: UUID, petId: UUID? = nil) async throws {
        try await api.deleteMedication(id: id)
        if let petId = petId {
            invalidateDashboardCache(for: petId)
        }
    }

    // MARK: - Dose Functions

    func recordDose(medicationId: UUID, petId: UUID? = nil, notes: String? = nil) async throws -> PetMedicationDose {
        let dose = DoseCreate(
            medicationId: medicationId,
            notes: notes,
            givenAt: nil
        )
        let result = try await api.recordDose(dose)
        if let petId = petId {
            invalidateDashboardCache(for: petId)
        }
        return result
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

    // MARK: - Dashboard Functions

    /// Get all dashboard data for a pet in a single call with caching
    func getDashboardData(for petId: UUID, forceRefresh: Bool = false) async throws -> DashboardData {
        // Return cached data if available and not forcing refresh
        if !forceRefresh, let cached = getCachedDashboard(for: petId) {
            return cached
        }

        // Fetch from API
        let data = try await api.getDashboardData(petId: petId)
        cacheDashboard(data, for: petId)
        return data
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
