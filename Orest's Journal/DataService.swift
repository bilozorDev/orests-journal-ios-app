//
//  DataService.swift
//  Orest's Journal
//
//  Data service wrapping APIClient for pet health management.
//

import Foundation
import UIKit

/// Data service providing high-level methods for pet health management.
/// Wraps APIClient and provides organization-scoped data access with caching.
/// Uses a two-tier cache (memory + disk) with stale-while-revalidate pattern.
@MainActor
final class DataService {
    static let shared = DataService()

    private let api = APIClient.shared
    private let persistentCache = PersistentCacheManager.shared

    // MARK: - Cache

    private struct CacheEntry<T> {
        let data: T
        let timestamp: Date
    }

    private var dashboardCache: [UUID: CacheEntry<DashboardData>] = [:]
    private var feedingHistoryCache: [UUID: CacheEntry<FeedingListResponse>] = [:]
    private var foodsCache: [Bool: CacheEntry<[PetFood]>] = [:]  // Key: includeArchived flag
    private var medicationsCache: [UUID: CacheEntry<[PetMedication]>] = [:]  // Key: petId (nil stored as UUID())
    private let cacheTTL: TimeInterval = 60  // 1 minute
    private let foodsCacheTTL: TimeInterval = 300  // 5 minutes (foods change rarely)
    private let medicationsCacheTTL: TimeInterval = 60  // 1 minute

    private init() {
        // Listen for memory warnings to clear caches
        NotificationCenter.default.addObserver(
            forName: UIApplication.didReceiveMemoryWarningNotification,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            self?.clearAllCaches()
        }
    }

    /// Clears all cached data (both memory and disk)
    func clearAllCaches() {
        dashboardCache.removeAll()
        feedingHistoryCache.removeAll()
        foodsCache.removeAll()
        familyMembersCache.removeAll()
        medicationsCache.removeAll()
        petsCache = nil

        // Clear disk cache
        Task {
            await persistentCache.clearAll()
        }
    }

    // MARK: - Pets Cache

    private var petsCache: CacheEntry<[Pet]>?
    private let petsCacheTTL: TimeInterval = 300  // 5 minutes

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

    /// Invalidates dashboard cache for a specific pet or all pets (memory + disk)
    func invalidateDashboardCache(for petId: UUID? = nil) {
        if let petId = petId {
            dashboardCache.removeValue(forKey: petId)
            Task { await persistentCache.delete(forKey: .dashboard(petId: petId)) }
        } else {
            dashboardCache.removeAll()
            // Note: Don't clear all disk dashboard caches here, just memory
        }
    }

    /// Returns cached dashboard data if available from memory (synchronous)
    func getCachedDashboardData(for petId: UUID) -> DashboardData? {
        return getCachedDashboard(for: petId)
    }

    /// Returns cached dashboard data from disk if available (async)
    func getCachedDashboardDataFromDisk(for petId: UUID) async -> DashboardData? {
        let cached: PersistentCacheManager.CachedData<DashboardData>? = await persistentCache.load(forKey: .dashboard(petId: petId))
        if let cached = cached {
            // Also populate memory cache
            cacheDashboard(cached.data, for: petId)
        }
        return cached?.data
    }

    /// Returns cached feeding history if still valid, nil otherwise
    private func getCachedFeedingHistory(for petId: UUID) -> FeedingListResponse? {
        guard let entry = feedingHistoryCache[petId],
              Date().timeIntervalSince(entry.timestamp) < cacheTTL else {
            return nil
        }
        return entry.data
    }

    /// Stores feeding history in cache with current timestamp
    private func cacheFeedingHistory(_ data: FeedingListResponse, for petId: UUID) {
        feedingHistoryCache[petId] = CacheEntry(data: data, timestamp: Date())
    }

    /// Invalidates feeding history cache for a specific pet (memory + disk)
    func invalidateFeedingHistoryCache(for petId: UUID) {
        feedingHistoryCache.removeValue(forKey: petId)
        Task { await persistentCache.delete(forKey: .feedingHistory(petId: petId)) }
    }

    /// Returns true if there's valid cached feeding history for a pet
    func hasCachedFeedingHistory(for petId: UUID) -> Bool {
        return getCachedFeedingHistory(for: petId) != nil
    }

    /// Returns cached feeding history data if available (synchronous)
    func getCachedFeedingHistoryData(for petId: UUID) -> FeedingListResponse? {
        return getCachedFeedingHistory(for: petId)
    }

    /// Returns cached foods if still valid, nil otherwise
    private func getCachedFoods(includeArchived: Bool) -> [PetFood]? {
        guard let entry = foodsCache[includeArchived],
              Date().timeIntervalSince(entry.timestamp) < foodsCacheTTL else {
            return nil
        }
        return entry.data
    }

    /// Stores foods in cache with current timestamp
    private func cacheFoods(_ foods: [PetFood], includeArchived: Bool) {
        foodsCache[includeArchived] = CacheEntry(data: foods, timestamp: Date())
    }

    /// Invalidates foods cache (memory + disk)
    func invalidateFoodsCache() {
        foodsCache.removeAll()
        Task {
            await persistentCache.delete(forKey: .foods(includeArchived: true))
            await persistentCache.delete(forKey: .foods(includeArchived: false))
        }
    }

    /// Returns true if there's valid cached foods
    func hasCachedFoods(includeArchived: Bool = false) -> Bool {
        return getCachedFoods(includeArchived: includeArchived) != nil
    }

    /// Returns cached foods data if available (synchronous)
    func getCachedFoodsData(includeArchived: Bool = false) -> [PetFood]? {
        return getCachedFoods(includeArchived: includeArchived)
    }

    // MARK: - Medications Cache

    /// Returns cached medications if still valid, nil otherwise
    private func getCachedMedications(for petId: UUID?) -> [PetMedication]? {
        let cacheKey = petId ?? UUID(uuidString: "00000000-0000-0000-0000-000000000000")!
        guard let entry = medicationsCache[cacheKey],
              Date().timeIntervalSince(entry.timestamp) < medicationsCacheTTL else {
            return nil
        }
        return entry.data
    }

    /// Stores medications in cache with current timestamp
    private func cacheMedications(_ medications: [PetMedication], for petId: UUID?) {
        let cacheKey = petId ?? UUID(uuidString: "00000000-0000-0000-0000-000000000000")!
        medicationsCache[cacheKey] = CacheEntry(data: medications, timestamp: Date())
    }

    /// Invalidates medications cache for a specific pet or all pets (memory + disk)
    func invalidateMedicationsCache(for petId: UUID? = nil) {
        if let petId = petId {
            medicationsCache.removeValue(forKey: petId)
            Task { await persistentCache.delete(forKey: .medications(petId: petId)) }
        } else {
            medicationsCache.removeAll()
            Task { await persistentCache.delete(forKey: .medications(petId: nil)) }
        }
    }

    /// Returns true if there's valid cached medications for a pet
    func hasCachedMedications(for petId: UUID? = nil) -> Bool {
        return getCachedMedications(for: petId) != nil
    }

    /// Returns cached medications data if available (synchronous)
    func getCachedMedicationsData(for petId: UUID? = nil) -> [PetMedication]? {
        return getCachedMedications(for: petId)
    }

    // MARK: - Pet Functions

    func getPets(forceRefresh: Bool = false) async throws -> [Pet] {
        // Check memory cache first
        if !forceRefresh, let cached = petsCache,
           Date().timeIntervalSince(cached.timestamp) < petsCacheTTL {
            return cached.data
        }

        // Check disk cache for instant display
        if !forceRefresh {
            let diskCached: PersistentCacheManager.CachedData<[Pet]>? = await persistentCache.load(forKey: .pets)
            if let diskCached = diskCached {
                // Update memory cache
                petsCache = CacheEntry(data: diskCached.data, timestamp: diskCached.timestamp)

                // If disk cache is stale (past memory TTL), refresh in background
                if Date().timeIntervalSince(diskCached.timestamp) > petsCacheTTL {
                    Task {
                        try? await refreshPetsInBackground()
                    }
                }
                return diskCached.data
            }
        }

        // Fetch from network
        let pets = try await api.getPets()

        // Update both caches
        petsCache = CacheEntry(data: pets, timestamp: Date())
        await persistentCache.save(pets, forKey: .pets)

        return pets
    }

    /// Refresh pets in background without throwing
    private func refreshPetsInBackground() async throws {
        let pets = try await api.getPets()
        petsCache = CacheEntry(data: pets, timestamp: Date())
        await persistentCache.save(pets, forKey: .pets)
    }

    /// Returns cached pets from disk if available
    func getCachedPetsFromDisk() async -> [Pet]? {
        let cached: PersistentCacheManager.CachedData<[Pet]>? = await persistentCache.load(forKey: .pets)
        if let cached = cached {
            petsCache = CacheEntry(data: cached.data, timestamp: cached.timestamp)
        }
        return cached?.data
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

    func getFoods(includeArchived: Bool = false, forceRefresh: Bool = false) async throws -> [PetFood] {
        // Check memory cache first
        if !forceRefresh, let cached = getCachedFoods(includeArchived: includeArchived) {
            return cached
        }

        // Check disk cache for instant display
        if !forceRefresh {
            let diskCached: PersistentCacheManager.CachedData<[PetFood]>? = await persistentCache.load(forKey: .foods(includeArchived: includeArchived))
            if let diskCached = diskCached {
                // Update memory cache
                cacheFoods(diskCached.data, includeArchived: includeArchived)

                // If disk cache is stale (past memory TTL), refresh in background
                if Date().timeIntervalSince(diskCached.timestamp) > foodsCacheTTL {
                    Task {
                        try? await refreshFoodsInBackground(includeArchived: includeArchived)
                    }
                }
                return diskCached.data
            }
        }

        // Fetch from network
        let foods = try await api.getFoods(includeArchived: includeArchived)

        // Update both caches
        cacheFoods(foods, includeArchived: includeArchived)
        await persistentCache.save(foods, forKey: .foods(includeArchived: includeArchived))

        return foods
    }

    /// Refresh foods in background without throwing
    private func refreshFoodsInBackground(includeArchived: Bool) async throws {
        let foods = try await api.getFoods(includeArchived: includeArchived)
        cacheFoods(foods, includeArchived: includeArchived)
        await persistentCache.save(foods, forKey: .foods(includeArchived: includeArchived))
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
        let result = try await api.createFood(food)
        invalidateFoodsCache()
        return result
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
        let result = try await api.updateFood(id: id, update: update)
        invalidateFoodsCache()
        return result
    }

    func deleteFood(id: UUID) async throws -> FoodDeleteResponse {
        let result = try await api.deleteFood(id: id)
        invalidateFoodsCache()
        return result
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
        invalidateFeedingHistoryCache(for: petId)
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

    func getFeedingHistory(for petId: UUID, limit: Int = 50, offset: Int = 0, forceRefresh: Bool = false) async throws -> FeedingListResponse {
        // Only cache first page (offset=0)
        if offset == 0 {
            // Check memory cache first
            if !forceRefresh, let cached = getCachedFeedingHistory(for: petId) {
                return cached
            }

            // Check disk cache for instant display
            if !forceRefresh {
                let diskCached: PersistentCacheManager.CachedData<FeedingListResponse>? = await persistentCache.load(forKey: .feedingHistory(petId: petId))
                if let diskCached = diskCached {
                    // Update memory cache
                    cacheFeedingHistory(diskCached.data, for: petId)

                    // If disk cache is stale, refresh in background
                    if Date().timeIntervalSince(diskCached.timestamp) > cacheTTL {
                        Task {
                            try? await refreshFeedingHistoryInBackground(for: petId, limit: limit)
                        }
                    }
                    return diskCached.data
                }
            }
        }

        // Fetch from network
        let response = try await api.getFeedingHistory(petId: petId, limit: limit, offset: offset)

        // Only cache first page
        if offset == 0 {
            cacheFeedingHistory(response, for: petId)
            await persistentCache.save(response, forKey: .feedingHistory(petId: petId))
        }

        return response
    }

    /// Refresh feeding history in background without throwing
    private func refreshFeedingHistoryInBackground(for petId: UUID, limit: Int) async throws {
        let response = try await api.getFeedingHistory(petId: petId, limit: limit, offset: 0)
        cacheFeedingHistory(response, for: petId)
        await persistentCache.save(response, forKey: .feedingHistory(petId: petId))
    }

    func updateFeeding(
        id: UUID,
        amount: Double? = nil,
        amountUnit: ContainerUnit? = nil,
        calories: Double? = nil,
        notes: String? = nil,
        fedAt: Date? = nil,
        fedBy: UUID? = nil,
        petId: UUID? = nil
    ) async throws -> PetFeeding {
        let update = FeedingUpdate(
            amount: amount,
            amountUnit: amountUnit?.rawValue,
            calories: calories,
            notes: notes,
            fedAt: fedAt,
            fedBy: fedBy
        )
        let result = try await api.updateFeeding(id: id, update: update)
        if let petId = petId {
            invalidateDashboardCache(for: petId)
            invalidateFeedingHistoryCache(for: petId)
        }
        return result
    }

    func deleteFeeding(id: UUID, petId: UUID? = nil) async throws {
        try await api.deleteFeeding(id: id)
        if let petId = petId {
            invalidateDashboardCache(for: petId)
            invalidateFeedingHistoryCache(for: petId)
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

    func getMedications(petId: UUID? = nil, activeOnly: Bool = false, forceRefresh: Bool = false) async throws -> [PetMedication] {
        // Only cache non-activeOnly requests (activeOnly is time-sensitive)
        if !activeOnly {
            // Check memory cache first
            if !forceRefresh, let cached = getCachedMedications(for: petId) {
                return cached
            }

            // Check disk cache for instant display
            if !forceRefresh {
                let diskCached: PersistentCacheManager.CachedData<[PetMedication]>? = await persistentCache.load(forKey: .medications(petId: petId))
                if let diskCached = diskCached {
                    // Update memory cache
                    cacheMedications(diskCached.data, for: petId)

                    // If disk cache is stale, refresh in background
                    if Date().timeIntervalSince(diskCached.timestamp) > medicationsCacheTTL {
                        Task {
                            try? await refreshMedicationsInBackground(petId: petId)
                        }
                    }
                    return diskCached.data
                }
            }
        }

        // Fetch from network
        let medications = try await api.getMedications(petId: petId, activeOnly: activeOnly)

        // Only cache non-activeOnly results
        if !activeOnly {
            cacheMedications(medications, for: petId)
            await persistentCache.save(medications, forKey: .medications(petId: petId))
        }

        return medications
    }

    /// Refresh medications in background without throwing
    private func refreshMedicationsInBackground(petId: UUID?) async throws {
        let medications = try await api.getMedications(petId: petId, activeOnly: false)
        cacheMedications(medications, for: petId)
        await persistentCache.save(medications, forKey: .medications(petId: petId))
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
        notes: String?,
        remindersEnabled: Bool = false,
        scheduledTimes: [ScheduledTimeCreate]? = nil
    ) async throws -> PetMedication {
        let medication = MedicationCreate(
            petId: petId,
            name: name,
            medicationType: medicationType.rawValue,
            startDate: startDate,
            endDate: endDate,
            timesPerDay: timesPerDay,
            notes: notes,
            remindersEnabled: remindersEnabled ? true : nil,
            timezone: remindersEnabled ? TimeZone.current.identifier : nil,
            scheduledTimes: remindersEnabled ? scheduledTimes : nil
        )
        let result = try await api.createMedication(medication)
        invalidateDashboardCache(for: petId)
        invalidateMedicationsCache(for: petId)
        return result
    }

    func deleteMedication(id: UUID, petId: UUID? = nil) async throws {
        try await api.deleteMedication(id: id)
        if let petId = petId {
            invalidateDashboardCache(for: petId)
            invalidateMedicationsCache(for: petId)
        } else {
            invalidateMedicationsCache()
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

    func updateDose(
        id: UUID,
        givenAt: Date? = nil,
        givenBy: UUID? = nil,
        notes: String? = nil,
        petId: UUID? = nil
    ) async throws -> PetMedicationDose {
        let update = DoseUpdate(
            givenAt: givenAt,
            givenBy: givenBy,
            notes: notes
        )
        let result = try await api.updateDose(id: id, update: update)
        if let petId = petId {
            invalidateDashboardCache(for: petId)
        }
        return result
    }

    func deleteDose(id: UUID, petId: UUID? = nil) async throws {
        try await api.deleteDose(id: id)
        if let petId = petId {
            invalidateDashboardCache(for: petId)
        }
    }

    // MARK: - Family Functions

    private var familyMembersCache: [String: CacheEntry<[FamilyMemberResponse]>] = [:]
    private let familyMembersCacheTTL: TimeInterval = 300  // 5 minutes

    func getFamilyMembers(familyId: String, forceRefresh: Bool = false) async throws -> [FamilyMemberResponse] {
        // Check memory cache first
        if !forceRefresh,
           let entry = familyMembersCache[familyId],
           Date().timeIntervalSince(entry.timestamp) < familyMembersCacheTTL {
            return entry.data
        }

        // Check disk cache for instant display
        if !forceRefresh {
            let diskCached: PersistentCacheManager.CachedData<[FamilyMemberResponse]>? = await persistentCache.load(forKey: .familyMembers(familyId: familyId))
            if let diskCached = diskCached {
                // Update memory cache
                familyMembersCache[familyId] = CacheEntry(data: diskCached.data, timestamp: diskCached.timestamp)

                // If disk cache is stale, refresh in background
                if Date().timeIntervalSince(diskCached.timestamp) > familyMembersCacheTTL {
                    Task {
                        try? await refreshFamilyMembersInBackground(familyId: familyId)
                    }
                }
                return diskCached.data
            }
        }

        // Fetch from API
        let response = try await api.getFamilyMembers(familyId: familyId)
        familyMembersCache[familyId] = CacheEntry(data: response.members, timestamp: Date())
        await persistentCache.save(response.members, forKey: .familyMembers(familyId: familyId))
        return response.members
    }

    /// Refresh family members in background without throwing
    private func refreshFamilyMembersInBackground(familyId: String) async throws {
        let response = try await api.getFamilyMembers(familyId: familyId)
        familyMembersCache[familyId] = CacheEntry(data: response.members, timestamp: Date())
        await persistentCache.save(response.members, forKey: .familyMembers(familyId: familyId))
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
        // Check memory cache first
        if !forceRefresh, let cached = getCachedDashboard(for: petId) {
            return cached
        }

        // Check disk cache for instant display
        if !forceRefresh {
            let diskCached: PersistentCacheManager.CachedData<DashboardData>? = await persistentCache.load(forKey: .dashboard(petId: petId))
            if let diskCached = diskCached {
                // Update memory cache
                cacheDashboard(diskCached.data, for: petId)

                // If disk cache is stale, refresh in background
                if Date().timeIntervalSince(diskCached.timestamp) > cacheTTL {
                    Task {
                        try? await refreshDashboardInBackground(for: petId)
                    }
                }
                return diskCached.data
            }
        }

        // Fetch from API
        let data = try await api.getDashboardData(petId: petId)
        cacheDashboard(data, for: petId)
        await persistentCache.save(data, forKey: .dashboard(petId: petId))
        return data
    }

    /// Refresh dashboard in background without throwing
    private func refreshDashboardInBackground(for petId: UUID) async throws {
        let data = try await api.getDashboardData(petId: petId)
        cacheDashboard(data, for: petId)
        await persistentCache.save(data, forKey: .dashboard(petId: petId))
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

    // MARK: - Background Refresh

    /// Refresh all data in the background (called by BGAppRefresh)
    func refreshAllDataInBackground() async {
        guard AuthManager.shared.isAuthenticated else {
            print("DataService: Not authenticated, skipping background refresh")
            return
        }

        print("DataService: Starting background refresh")

        do {
            // Refresh pets first (needed to know which dashboards to refresh)
            let pets = try await getPets(forceRefresh: true)
            print("DataService: Refreshed \(pets.count) pets")

            // Refresh foods (family-wide)
            let foods = try await getFoods(forceRefresh: true)
            print("DataService: Refreshed \(foods.count) foods")

            // Refresh medications (family-wide)
            let medications = try await getMedications(forceRefresh: true)
            print("DataService: Refreshed \(medications.count) medications")

            // Refresh family members if we have a family ID
            if let familyId = AuthManager.shared.familyId {
                let members = try await getFamilyMembers(familyId: familyId, forceRefresh: true)
                print("DataService: Refreshed \(members.count) family members")
            }

            // Refresh dashboard for each pet
            for pet in pets {
                let _ = try await getDashboardData(for: pet.id, forceRefresh: true)
                print("DataService: Refreshed dashboard for \(pet.name)")
            }

            print("DataService: Background refresh completed successfully")
        } catch {
            print("DataService: Background refresh failed: \(error)")
        }
    }

    /// Prefetch data when app enters foreground (lightweight refresh)
    func prefetchDataOnForeground() async {
        guard AuthManager.shared.isAuthenticated else { return }

        print("DataService: Prefetching data on foreground")

        // These calls will return disk cache instantly if available,
        // and trigger background refresh if stale
        async let _ = try? getFoods()
        async let _ = try? getMedications()

        // Wait for both to complete their cache checks
        _ = await ((), ())
    }
}
