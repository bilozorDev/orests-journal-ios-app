//
//  DataService.swift
//  Orest's Journal
//
//  Data service wrapping APIClient for pet management.
//

import Foundation
import UIKit

/// Data service providing high-level methods for pet management.
/// Wraps APIClient and provides family-scoped data access with caching.
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

    private var petsCache: CacheEntry<[Pet]>?
    private var familyMembersCache: [String: CacheEntry<FamilyDetailResponse>] = [:]
    private var calorieGoalCache: [UUID: CacheEntry<CalorieGoal>] = [:]
    private var healthEventsCache: [UUID: CacheEntry<[HealthEventWithCategory]>] = [:]
    private var healthCategoriesCache: [String: CacheEntry<[HealthCategory]>] = [:]  // Keyed by familyId
    private var medicationsCache: [String: CacheEntry<[Medication]>] = [:]  // Keyed by familyId
    private let cacheTTL: TimeInterval = 60  // 1 minute
    private let petsCacheTTL: TimeInterval = 300  // 5 minutes
    private let healthCacheTTL: TimeInterval = 300  // 5 minutes
    private let medicationsCacheTTL: TimeInterval = 300  // 5 minutes

    // Cache stampede prevention flags
    private var petsRefreshInProgress = false
    private var familyRefreshInProgress: Set<String> = []
    private var healthEventsRefreshInProgress: Set<UUID> = []
    private var healthCategoriesRefreshInProgress: Set<String> = []  // By familyId
    private var medicationsRefreshInProgress: Set<String> = []  // By familyId

    private init() {
        // Listen for memory warnings to clear caches
        NotificationCenter.default.addObserver(
            forName: UIApplication.didReceiveMemoryWarningNotification,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            Task { @MainActor [weak self] in
                self?.clearAllCaches()
            }
        }
    }

    /// Clears all cached data (both memory and disk)
    func clearAllCaches() {
        petsCache = nil
        familyMembersCache.removeAll()
        calorieGoalCache.removeAll()
        healthEventsCache.removeAll()
        healthCategoriesCache.removeAll()
        medicationsCache.removeAll()

        Task {
            await persistentCache.clearAll()
        }
    }

    // MARK: - Pets Cache

    private func getCachedPets() -> [Pet]? {
        guard let entry = petsCache,
              Date().timeIntervalSince(entry.timestamp) < petsCacheTTL else {
            return nil
        }
        return entry.data
    }

    private func cachePets(_ data: [Pet]) {
        petsCache = CacheEntry(data: data, timestamp: Date())
    }

    func invalidatePetsCache() {
        petsCache = nil
        Task { await persistentCache.delete(forKey: .pets) }
    }

    func getCachedPetsData() -> [Pet]? {
        return getCachedPets()
    }

    func getCachedPetsFromDisk() async -> [Pet]? {
        let cached: PersistentCacheManager.CachedData<[Pet]>? = await persistentCache.load(forKey: .pets)
        if let cached = cached {
            cachePets(cached.data)
        }
        return cached?.data
    }

    // MARK: - Family Cache

    private func getCachedFamilyMembers(for familyId: String) -> FamilyDetailResponse? {
        guard let entry = familyMembersCache[familyId],
              Date().timeIntervalSince(entry.timestamp) < cacheTTL else {
            return nil
        }
        return entry.data
    }

    private func cacheFamilyMembers(_ data: FamilyDetailResponse, for familyId: String) {
        familyMembersCache[familyId] = CacheEntry(data: data, timestamp: Date())
    }

    func invalidateFamilyCache(for familyId: String) async {
        familyMembersCache.removeValue(forKey: familyId)
        await persistentCache.delete(forKey: .familyMembers(familyId: familyId))
    }

    /// Invalidate all caches (used when user is removed from family)
    func invalidateAllCaches() {
        petsCache = nil
        familyMembersCache.removeAll()
        calorieGoalCache.removeAll()
        healthEventsCache.removeAll()
        healthCategoriesCache.removeAll()
        medicationsCache.removeAll()
        Task {
            await persistentCache.clearAll()
        }
    }

    // MARK: - Pets

    func getPets(forceRefresh: Bool = false) async throws -> [Pet] {
        if !forceRefresh, let cached = getCachedPets() {
            return cached
        }

        if !forceRefresh {
            let diskCached: PersistentCacheManager.CachedData<[Pet]>? = await persistentCache.load(forKey: .pets)
            if let diskCached = diskCached {
                cachePets(diskCached.data)
                if Date().timeIntervalSince(diskCached.timestamp) > petsCacheTTL {
                    // Prevent cache stampede - only one background refresh at a time
                    if !petsRefreshInProgress {
                        petsRefreshInProgress = true
                        Task {
                            defer { Task { @MainActor in self.petsRefreshInProgress = false } }
                            do {
                                try await refreshPetsInBackground()
                            } catch {
                                #if DEBUG
                                print("Background pets refresh failed: \(error)")
                                #endif
                            }
                        }
                    }
                }
                return diskCached.data
            }
        }

        let pets = try await api.getPets()
        cachePets(pets)
        await persistentCache.save(pets, forKey: .pets)
        return pets
    }

    private func refreshPetsInBackground() async throws {
        let oldPets = getCachedPets() ?? []
        let pets = try await api.getPets()
        cachePets(pets)
        await persistentCache.save(pets, forKey: .pets)

        // If pets changed, notify views to refresh
        let oldIds = Set(oldPets.map { $0.id })
        let newIds = Set(pets.map { $0.id })
        if oldIds != newIds {
            NavigationManager.shared.requestTabRefresh(.home)
            NavigationManager.shared.requestTabRefresh(.health)
        }
    }

    func createPet(name: String, kind: String, photoUrl: String?, currentWeight: Double? = nil, dateOfBirth: Date? = nil) async throws -> Pet {
        let pet = PetCreate(name: name, kind: kind, photoUrl: photoUrl, currentWeight: currentWeight, dateOfBirth: dateOfBirth)
        let result = try await api.createPet(pet)
        invalidatePetsCache()
        return result
    }

    func updatePet(id: UUID, name: String? = nil, kind: String? = nil, photoUrl: String? = nil, currentWeight: Double? = nil, dateOfBirth: Date? = nil, clearPhoto: Bool = false) async throws -> Pet {
        // Use empty string to signal photo removal to backend
        let effectivePhotoUrl = clearPhoto ? "" : photoUrl
        let update = PetUpdate(name: name, kind: kind, photoUrl: effectivePhotoUrl, currentWeight: currentWeight, dateOfBirth: dateOfBirth)
        let result = try await api.updatePet(id: id, update: update)
        invalidatePetsCache()
        return result
    }

    func deletePet(id: UUID) async throws {
        try await api.deletePet(id: id)
        invalidatePetsCache()
    }

    // MARK: - Photo Upload

    func uploadPetPhoto(imageData: Data, mimeType: String = "image/jpeg") async throws -> String {
        return try await api.uploadPetPhoto(imageData: imageData, mimeType: mimeType)
    }

    // MARK: - Calorie Goals

    func getCalorieGoal(for petId: UUID) async throws -> CalorieGoal? {
        // Check memory cache first
        if let entry = calorieGoalCache[petId],
           Date().timeIntervalSince(entry.timestamp) < cacheTTL {
            return entry.data
        }

        // Check disk cache
        let diskCached: PersistentCacheManager.CachedData<CalorieGoal>? = await persistentCache.load(forKey: .calorieGoal(petId: petId.uuidString))
        if let diskCached = diskCached {
            calorieGoalCache[petId] = CacheEntry(data: diskCached.data, timestamp: diskCached.timestamp)
            // If stale, refresh from network but return cached data
            if Date().timeIntervalSince(diskCached.timestamp) > cacheTTL {
                Task {
                    if let goal = try? await api.getCalorieGoal(petId: petId) {
                        self.calorieGoalCache[petId] = CacheEntry(data: goal, timestamp: Date())
                        await self.persistentCache.save(goal, forKey: .calorieGoal(petId: petId.uuidString))
                    }
                }
            }
            return diskCached.data
        }

        // Fetch from network
        let goal = try await api.getCalorieGoal(petId: petId)
        if let goal = goal {
            calorieGoalCache[petId] = CacheEntry(data: goal, timestamp: Date())
            await persistentCache.save(goal, forKey: .calorieGoal(petId: petId.uuidString))
        }
        return goal
    }

    func setCalorieGoal(for petId: UUID, dailyCalories: Double, notes: String?) async throws -> CalorieGoal {
        let result = try await api.setCalorieGoal(petId: petId, dailyCalories: dailyCalories, notes: notes)
        calorieGoalCache[petId] = CacheEntry(data: result, timestamp: Date())
        await persistentCache.save(result, forKey: .calorieGoal(petId: petId.uuidString))
        return result
    }

    func invalidateCalorieGoalCache(for petId: UUID) {
        calorieGoalCache.removeValue(forKey: petId)
        Task {
            await persistentCache.delete(forKey: .calorieGoal(petId: petId.uuidString))
        }
    }

    // MARK: - Family Members

    func getFamilyMembers(for familyId: String, forceRefresh: Bool = false) async throws -> FamilyDetailResponse {
        // Check memory cache first
        if !forceRefresh, let cached = getCachedFamilyMembers(for: familyId) {
            return cached
        }

        // Check disk cache if not forcing refresh
        if !forceRefresh {
            let diskCached: PersistentCacheManager.CachedData<FamilyDetailResponse>? = await persistentCache.load(forKey: .familyMembers(familyId: familyId))
            if let diskCached = diskCached {
                cacheFamilyMembers(diskCached.data, for: familyId)
                // If stale, refresh in background (with stampede prevention)
                if Date().timeIntervalSince(diskCached.timestamp) > cacheTTL {
                    if !familyRefreshInProgress.contains(familyId) {
                        familyRefreshInProgress.insert(familyId)
                        Task {
                            defer { Task { @MainActor in self.familyRefreshInProgress.remove(familyId) } }
                            do {
                                try await refreshFamilyMembersInBackground(familyId: familyId)
                            } catch {
                                #if DEBUG
                                print("Background family refresh failed: \(error)")
                                #endif
                            }
                        }
                    }
                }
                return diskCached.data
            }
        }

        // Fetch from network
        let response = try await api.getFamilyDetails(familyId: familyId)
        cacheFamilyMembers(response, for: familyId)
        await persistentCache.save(response, forKey: .familyMembers(familyId: familyId))
        return response
    }

    private func refreshFamilyMembersInBackground(familyId: String) async throws {
        let response = try await api.getFamilyDetails(familyId: familyId)
        cacheFamilyMembers(response, for: familyId)
        await persistentCache.save(response, forKey: .familyMembers(familyId: familyId))
    }

    func updateMemberRole(familyId: String, userId: String, role: String) async throws -> FamilyMember {
        let result = try await api.updateMemberRole(familyId: familyId, userId: userId, role: role)
        await invalidateFamilyCache(for: familyId)
        return result
    }

    func removeFamilyMember(familyId: String, userId: String) async throws {
        try await api.removeFamilyMember(familyId: familyId, userId: userId)
        await invalidateFamilyCache(for: familyId)
    }

    func updateFamilyName(familyId: String, name: String) async throws -> AppFamily {
        let result = try await api.updateFamilyName(familyId: familyId, name: name)
        await invalidateFamilyCache(for: familyId)
        return result
    }

    // MARK: - Health Events

    private func getCachedHealthEvents(for petId: UUID) -> [HealthEventWithCategory]? {
        guard let entry = healthEventsCache[petId],
              Date().timeIntervalSince(entry.timestamp) < healthCacheTTL else {
            return nil
        }
        return entry.data
    }

    private func cacheHealthEvents(_ data: [HealthEventWithCategory], for petId: UUID) {
        healthEventsCache[petId] = CacheEntry(data: data, timestamp: Date())
    }

    private func getCachedHealthCategories(for familyId: String) -> [HealthCategory]? {
        guard let entry = healthCategoriesCache[familyId],
              Date().timeIntervalSince(entry.timestamp) < healthCacheTTL else {
            return nil
        }
        return entry.data
    }

    private func cacheHealthCategories(_ data: [HealthCategory], for familyId: String) {
        healthCategoriesCache[familyId] = CacheEntry(data: data, timestamp: Date())
    }

    func invalidateHealthCache(for petId: UUID, familyId: String? = nil) {
        healthEventsCache.removeValue(forKey: petId)
        Task {
            await persistentCache.delete(forKey: .healthEvents(petId: petId.uuidString))
        }
        // Also invalidate categories if familyId provided
        if let familyId = familyId {
            healthCategoriesCache.removeValue(forKey: familyId)
            Task {
                await persistentCache.delete(forKey: .healthCategories(familyId: familyId))
            }
        }
    }

    /// Invalidate all health caches (used when forceRefresh needed after mutations in All view)
    func invalidateAllHealthCaches() {
        healthEventsCache.removeAll()
        healthCategoriesCache.removeAll()
        Task {
            await persistentCache.deleteAll(matching: .healthEvents(petId: ""))
            await persistentCache.deleteAll(matching: .healthCategories(familyId: ""))
        }
    }

    func getHealthEvents(for petId: UUID, forceRefresh: Bool = false) async throws -> [HealthEventWithCategory] {
        // Check memory cache
        if !forceRefresh, let cached = getCachedHealthEvents(for: petId) {
            return cached
        }

        // Check disk cache
        if !forceRefresh {
            let diskCached: PersistentCacheManager.CachedData<[HealthEventWithCategory]>? = await persistentCache.load(forKey: .healthEvents(petId: petId.uuidString))
            if let diskCached = diskCached {
                cacheHealthEvents(diskCached.data, for: petId)
                // If stale, refresh in background (with stampede prevention)
                if Date().timeIntervalSince(diskCached.timestamp) > healthCacheTTL {
                    if !healthEventsRefreshInProgress.contains(petId) {
                        healthEventsRefreshInProgress.insert(petId)
                        Task {
                            defer { Task { @MainActor in self.healthEventsRefreshInProgress.remove(petId) } }
                            do {
                                try await refreshHealthEventsInBackground(petId: petId)
                            } catch {
                                #if DEBUG
                                print("Background health events refresh failed: \(error)")
                                #endif
                            }
                        }
                    }
                }
                return diskCached.data
            }
        }

        // Fetch from network
        let events = try await api.getHealthEvents(petId: petId)
        cacheHealthEvents(events, for: petId)
        await persistentCache.save(events, forKey: .healthEvents(petId: petId.uuidString))
        return events
    }

    private func refreshHealthEventsInBackground(petId: UUID) async throws {
        let oldEvents = getCachedHealthEvents(for: petId) ?? []
        let events = try await api.getHealthEvents(petId: petId)
        cacheHealthEvents(events, for: petId)
        await persistentCache.save(events, forKey: .healthEvents(petId: petId.uuidString))

        // If events changed, notify views to refresh
        let oldIds = Set(oldEvents.map { $0.id })
        let newIds = Set(events.map { $0.id })
        if oldIds != newIds {
            NavigationManager.shared.requestTabRefresh(.health)
        }
    }

    func getHealthCategories(for petId: UUID, forceRefresh: Bool = false) async throws -> [HealthCategory] {
        // Get familyId from pet (categories are family-wide)
        var pet = petsCache?.data.first(where: { $0.id == petId })
        if pet == nil {
            pet = (try? await getPets())?.first(where: { $0.id == petId })
        }
        guard let pet = pet else {
            // Fallback to API call if pet not in cache
            return try await api.getHealthCategories(petId: petId)
        }
        let familyId = pet.familyId

        // Check memory cache (by familyId, not petId)
        if !forceRefresh, let cached = getCachedHealthCategories(for: familyId) {
            return cached
        }

        // Check disk cache
        if !forceRefresh {
            let diskCached: PersistentCacheManager.CachedData<[HealthCategory]>? = await persistentCache.load(forKey: .healthCategories(familyId: familyId))
            if let diskCached = diskCached {
                cacheHealthCategories(diskCached.data, for: familyId)
                // If stale, refresh in background (with stampede prevention)
                if Date().timeIntervalSince(diskCached.timestamp) > healthCacheTTL {
                    if !healthCategoriesRefreshInProgress.contains(familyId) {
                        healthCategoriesRefreshInProgress.insert(familyId)
                        Task {
                            defer { Task { @MainActor in self.healthCategoriesRefreshInProgress.remove(familyId) } }
                            do {
                                try await refreshHealthCategoriesInBackground(petId: petId, familyId: familyId)
                            } catch {
                                #if DEBUG
                                print("Background health categories refresh failed: \(error)")
                                #endif
                            }
                        }
                    }
                }
                return diskCached.data
            }
        }

        // Fetch from network
        let categories = try await api.getHealthCategories(petId: petId)
        cacheHealthCategories(categories, for: familyId)
        await persistentCache.save(categories, forKey: .healthCategories(familyId: familyId))
        return categories
    }

    private func refreshHealthCategoriesInBackground(petId: UUID, familyId: String) async throws {
        let categories = try await api.getHealthCategories(petId: petId)
        cacheHealthCategories(categories, for: familyId)
        await persistentCache.save(categories, forKey: .healthCategories(familyId: familyId))
    }

    func getHealthEvent(eventId: UUID) async throws -> HealthEventWithCategory {
        return try await api.getHealthEvent(eventId: eventId)
    }

    /// Search health events with filters (not cached - for smart search queries)
    func searchHealthEvents(
        for petId: UUID,
        category: String? = nil,
        since: Date? = nil,
        until: Date? = nil,
        limit: Int = 100
    ) async throws -> [HealthEventWithCategory] {
        return try await api.getHealthEvents(
            petId: petId,
            limit: limit,
            category: category,
            since: since,
            until: until
        )
    }

    func createHealthEvent(petId: UUID, categoryName: String, occurredAt: Date? = nil, notes: String? = nil, notifyFamily: Bool = false) async throws -> HealthEvent {
        let event = HealthEventCreate(categoryName: categoryName, occurredAt: occurredAt, notes: notes, notifyFamily: notifyFamily)
        let result = try await api.createHealthEvent(petId: petId, event: event)
        // Invalidate all health caches to ensure both single-pet and "All" views are fresh
        invalidateAllHealthCaches()
        NavigationManager.shared.requestTabRefresh(.health)
        return result
    }

    func updateHealthEvent(eventId: UUID, petId: UUID, categoryName: String? = nil, occurredAt: Date? = nil, notes: String? = nil) async throws -> HealthEventWithCategory {
        let update = HealthEventUpdate(categoryName: categoryName, occurredAt: occurredAt, notes: notes)
        let result = try await api.updateHealthEvent(eventId: eventId, update: update)
        // Invalidate all health caches to ensure both single-pet and "All" views are fresh
        invalidateAllHealthCaches()
        NavigationManager.shared.requestTabRefresh(.health)
        return result
    }

    func deleteHealthEvent(eventId: UUID, petId: UUID) async throws {
        try await api.deleteHealthEvent(eventId: eventId)
        // Invalidate all health caches to ensure both single-pet and "All" views are fresh
        invalidateAllHealthCaches()
        NavigationManager.shared.requestTabRefresh(.health)
    }

    func uploadHealthEventPhoto(eventId: UUID, petId: UUID, imageData: Data, mimeType: String = "image/jpeg") async throws -> HealthEventPhoto {
        let result = try await api.uploadHealthEventPhoto(eventId: eventId, imageData: imageData, mimeType: mimeType)
        // Invalidate all health caches to ensure "All" view is fresh
        invalidateAllHealthCaches()
        NavigationManager.shared.requestTabRefresh(.health)
        return result
    }

    func deleteHealthEventPhoto(eventId: UUID, photoId: UUID, petId: UUID) async throws {
        try await api.deleteHealthEventPhoto(eventId: eventId, photoId: photoId)
        // Invalidate all health caches to ensure "All" view is fresh
        invalidateAllHealthCaches()
        NavigationManager.shared.requestTabRefresh(.health)
    }

    func searchHealthEvents(
        petId: UUID,
        query: String,
        category: String? = nil,
        since: Date? = nil,
        until: Date? = nil
    ) async throws -> [HealthEventWithCategory] {
        // Search is always fresh, no caching
        return try await api.searchHealthEvents(
            petId: petId,
            query: query,
            category: category,
            since: since,
            until: until
        )
    }

    // MARK: - Medications Cache

    private func getCachedMedications(for familyId: String) -> [Medication]? {
        guard let entry = medicationsCache[familyId],
              Date().timeIntervalSince(entry.timestamp) < medicationsCacheTTL else {
            return nil
        }
        return entry.data
    }

    private func cacheMedications(_ data: [Medication], for familyId: String) {
        medicationsCache[familyId] = CacheEntry(data: data, timestamp: Date())
    }

    func invalidateMedicationsCache(for familyId: String) {
        medicationsCache.removeValue(forKey: familyId)
        Task {
            await persistentCache.delete(forKey: .medications(familyId: familyId))
        }
    }

    /// Invalidate all medication caches (used when mutations affect multiple families)
    func invalidateAllMedicationsCaches() {
        medicationsCache.removeAll()
        Task {
            await persistentCache.deleteAll(matching: .medications(familyId: ""))
        }
    }

    // MARK: - Medications

    func getMedications(for familyId: String, petId: UUID? = nil, includeArchived: Bool = false, forceRefresh: Bool = false) async throws -> [Medication] {
        let familyIdStr = familyId.lowercased()
        guard let familyUUID = UUID(uuidString: familyIdStr) else {
            throw NSError(domain: "DataService", code: 1, userInfo: [NSLocalizedDescriptionKey: "Invalid family ID"])
        }

        // Check memory cache
        if !forceRefresh, petId == nil, let cached = getCachedMedications(for: familyIdStr) {
            return cached
        }

        // Check disk cache (only for full family list, not filtered by pet)
        if !forceRefresh, petId == nil {
            let diskCached: PersistentCacheManager.CachedData<[Medication]>? = await persistentCache.load(forKey: .medications(familyId: familyIdStr))
            if let diskCached = diskCached {
                cacheMedications(diskCached.data, for: familyIdStr)
                // If stale, refresh in background (with stampede prevention)
                if Date().timeIntervalSince(diskCached.timestamp) > medicationsCacheTTL {
                    if !medicationsRefreshInProgress.contains(familyIdStr) {
                        medicationsRefreshInProgress.insert(familyIdStr)
                        Task {
                            defer { Task { @MainActor in self.medicationsRefreshInProgress.remove(familyIdStr) } }
                            do {
                                try await self.refreshMedicationsInBackground(familyId: familyIdStr)
                            } catch {
                                print("Background medications refresh failed: \(error)")
                            }
                        }
                    }
                }
                return diskCached.data
            }
        }

        // Fetch from network
        let response = try await api.getMedications(familyId: familyUUID, petId: petId, includeArchived: includeArchived)
        let medications = response.medications

        // Only cache full family list
        if petId == nil {
            cacheMedications(medications, for: familyIdStr)
            await persistentCache.save(medications, forKey: .medications(familyId: familyIdStr))
        }

        return medications
    }

    private func refreshMedicationsInBackground(familyId: String) async throws {
        let familyIdStr = familyId.lowercased()
        guard let familyUUID = UUID(uuidString: familyIdStr) else { return }
        let oldMeds = getCachedMedications(for: familyIdStr) ?? []
        let response = try await api.getMedications(familyId: familyUUID)
        let medications = response.medications
        cacheMedications(medications, for: familyIdStr)
        await persistentCache.save(medications, forKey: .medications(familyId: familyIdStr))

        // If medications changed, notify views to refresh
        let oldIds = Set(oldMeds.map { $0.id })
        let newIds = Set(medications.map { $0.id })
        if oldIds != newIds {
            NavigationManager.shared.requestTabRefresh(.medication)
        }
    }

    func getMedication(id: UUID) async throws -> Medication {
        return try await api.getMedication(id: id)
    }

    func getActiveMedications(for petId: UUID) async throws -> [Medication] {
        let response = try await api.getActiveMedicationsForPet(petId: petId)
        return response.medications
    }

    func createMedication(_ medication: MedicationCreate, familyId: String) async throws -> Medication {
        let result = try await api.createMedication(medication)
        invalidateMedicationsCache(for: familyId.lowercased())
        NavigationManager.shared.requestTabRefresh(.medication)
        Task { [self] in await syncMedicationsToWidget() }
        return result
    }

    func updateMedication(id: UUID, _ update: MedicationUpdate, familyId: String) async throws -> Medication {
        let result = try await api.updateMedication(id: id, update)
        invalidateMedicationsCache(for: familyId.lowercased())
        NavigationManager.shared.requestTabRefresh(.medication)
        Task { [self] in await syncMedicationsToWidget() }
        return result
    }

    func deleteMedication(id: UUID, familyId: String) async throws -> MedicationDeleteResponse {
        let result = try await api.deleteMedication(id: id)
        invalidateMedicationsCache(for: familyId.lowercased())
        NavigationManager.shared.requestTabRefresh(.medication)
        Task { [self] in await syncMedicationsToWidget() }
        return result
    }

    func uploadMedicationPhoto(medicationId: UUID, imageData: Data, mimeType: String = "image/jpeg", familyId: String) async throws -> MedicationPhoto {
        let result = try await api.uploadMedicationPhoto(medicationId: medicationId, imageData: imageData, mimeType: mimeType)
        invalidateMedicationsCache(for: familyId.lowercased())
        return result
    }

    func deleteMedicationPhoto(medicationId: UUID, photoId: UUID, familyId: String) async throws {
        try await api.deleteMedicationPhoto(medicationId: medicationId, photoId: photoId)
        invalidateMedicationsCache(for: familyId.lowercased())
    }

    // MARK: - Doses

    /// Record a dose for a medication. If offline, queues for later sync.
    /// - Returns: The recorded dose if online, nil if queued for offline sync
    @discardableResult
    func recordDose(
        medicationId: UUID,
        notes: String? = nil,
        givenAt: Date? = nil,
        familyId: String
    ) async throws -> MedicationDose? {
        let offlineQueue = await OfflineDoseQueue.shared

        // Check if online
        if await offlineQueue.isOnline {
            let doseCreate = DoseCreate(
                medicationId: medicationId,
                notes: notes,
                givenAt: givenAt
            )
            let result = try await api.recordDose(doseCreate)
            invalidateMedicationsCache(for: familyId.lowercased())

            // Sync widget after dose recorded
            Task { [self] in
                await syncMedicationsToWidget()
            }

            return result
        } else {
            // Queue for later
            await offlineQueue.queueDose(
                medicationId: medicationId,
                givenAt: givenAt ?? Date(),
                notes: notes,
                familyId: familyId
            )
            return nil
        }
    }

    /// Get dose history for a medication
    func getDosesForMedication(medicationId: UUID, limit: Int = 50, offset: Int = 0) async throws -> [MedicationDose] {
        let response = try await api.getDosesForMedication(medicationId: medicationId, limit: limit, offset: offset)
        return response.doses
    }

    /// Get doses for a medication with pagination info (total count)
    func getDosesForMedicationPaginated(medicationId: UUID, limit: Int = 50, offset: Int = 0) async throws -> DoseListResponse {
        return try await api.getDosesForMedication(medicationId: medicationId, limit: limit, offset: offset)
    }

    /// Get today's doses for a medication
    func getTodaysDoses(medicationId: UUID) async throws -> [MedicationDose] {
        let response = try await api.getTodaysDoses(medicationId: medicationId)
        return response.doses
    }

    /// Get the most recent dose for a medication
    func getLastDose(medicationId: UUID) async throws -> MedicationDose? {
        do {
            return try await api.getLastDose(medicationId: medicationId)
        } catch {
            // 404 means no doses recorded - return nil instead of throwing
            if let apiError = error as? APIError, case .notFound = apiError {
                return nil
            }
            throw error
        }
    }

    /// Get all doses for a pet across all medications
    func getAllDosesForPet(petId: UUID, limit: Int = 50, offset: Int = 0) async throws -> AllDosesListResponse {
        return try await api.getAllDosesForPet(petId: petId, limit: limit, offset: offset)
    }

    /// Update a dose (for correcting time or notes)
    func updateDose(doseId: UUID, givenAt: Date? = nil, notes: String? = nil, familyId: String) async throws -> MedicationDose {
        var update = DoseUpdate()
        update.givenAt = givenAt
        update.notes = notes
        let result = try await api.updateDose(doseId: doseId, update)
        invalidateMedicationsCache(for: familyId.lowercased())
        return result
    }

    /// Delete a dose
    func deleteDose(doseId: UUID, familyId: String) async throws {
        try await api.deleteDose(doseId: doseId)
        invalidateMedicationsCache(for: familyId.lowercased())
    }

    // MARK: - Background Refresh

    func refreshAllDataInBackground() async {
        do {
            _ = try await getPets(forceRefresh: true)
        } catch {
            #if DEBUG
            print("Background refresh failed: \(error)")
            #endif
        }
    }

    func prefetchDataOnForeground() {
        Task {
            _ = try? await getPets(forceRefresh: false)
            // Sync widget data
            await syncMedicationsToWidget()
        }
    }

    // MARK: - Widget Sync

    /// Sync medication data to the widget via App Group
    func syncMedicationsToWidget() async {
        do {
            let pets = try await getPets(forceRefresh: false)
            guard !pets.isEmpty, let familyId = pets.first?.familyId else {
                WidgetDataManager.shared.clearWidgetData()
                return
            }

            // Force refresh to ensure we have latest data with scheduled_times
            let medications = try await getMedications(for: familyId, includeArchived: false, forceRefresh: true)

            #if DEBUG
            print("📱 [Widget] Processing \(medications.count) medications")
            #endif

            // Build dose info for all scheduled medications
            var allDoses: [WidgetDoseInfo] = []

            // Get today's date range for filtering doses
            let calendar = Calendar.current
            let startOfDay = calendar.startOfDay(for: Date())

            // Fetch today's doses for each medication
            var todayDosesCache: [UUID: [WidgetDataManager.RecordedDoseInfo]] = [:]
            for medication in medications {
                if let recentDoses = try? await getDosesForMedication(medicationId: medication.id, limit: 20) {
                    // Filter for today's doses only
                    let todayDoses = recentDoses
                        .filter { $0.givenAt >= startOfDay }
                        .map { WidgetDataManager.RecordedDoseInfo(givenAt: $0.givenAt, givenBy: $0.givenBy) }
                    if !todayDoses.isEmpty {
                        todayDosesCache[medication.id] = todayDoses
                    }
                }
            }

            for medication in medications {
                #if DEBUG
                let hasScheduledTimes = medication.scheduledTimes?.isEmpty == false
                print("📱 [Widget] \(medication.name): asNeeded=\(medication.isAsNeeded), archived=\(medication.isArchived), active=\(medication.isActive), hasScheduledTimes=\(hasScheduledTimes)")
                #endif

                guard !medication.isAsNeeded,
                      !medication.isArchived,
                      medication.isActive else {
                    #if DEBUG
                    print("   ↳ Skipped (failed guard)")
                    #endif
                    continue
                }

                // Find pet name for this medication
                let petName = pets.first { $0.id == medication.petId }?.name ?? "Pet"

                // Get today's doses for this medication
                let todayDoses = todayDosesCache[medication.id] ?? []

                // Calculate today's schedule with given/pending status
                let doses = WidgetDataManager.calculateTodaySchedule(
                    for: medication,
                    petName: petName,
                    todayDoses: todayDoses,
                    maxCount: 5
                )

                #if DEBUG
                print("   ↳ Today's doses: \(todayDoses.count), Generated \(doses.count) schedule entries")
                #endif

                allDoses.append(contentsOf: doses)
            }

            // Sort by scheduled time and take top doses
            let sortedDoses = allDoses
                .sorted { $0.scheduledTime < $1.scheduledTime }
                .prefix(5)
                .map { $0 }

            WidgetDataManager.shared.updateNextDoses(sortedDoses)

            #if DEBUG
            print("📱 [Widget] Synced \(sortedDoses.count) upcoming doses")
            #endif

        } catch {
            #if DEBUG
            print("📱 [Widget] Sync failed: \(error)")
            #endif
        }
    }
}
