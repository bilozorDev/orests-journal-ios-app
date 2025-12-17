//
//  DataService.swift
//  Orest's Journal
//
//  Data service wrapping APIClient for pet management.
//

import Foundation
import UIKit

/// Data service providing high-level methods for pet management.
/// Wraps APIClient and provides organization-scoped data access with caching.
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
    private var healthCategoriesCache: [UUID: CacheEntry<[HealthCategory]>] = [:]
    private let cacheTTL: TimeInterval = 60  // 1 minute
    private let petsCacheTTL: TimeInterval = 300  // 5 minutes
    private let healthCacheTTL: TimeInterval = 300  // 5 minutes

    // Cache stampede prevention flags
    private var petsRefreshInProgress = false
    private var familyRefreshInProgress: Set<String> = []
    private var healthEventsRefreshInProgress: Set<UUID> = []

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
                                print("Background pets refresh failed: \(error)")
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
        let pets = try await api.getPets()
        cachePets(pets)
        await persistentCache.save(pets, forKey: .pets)
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
                                print("Background family refresh failed: \(error)")
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

    private func getCachedHealthCategories(for petId: UUID) -> [HealthCategory]? {
        guard let entry = healthCategoriesCache[petId],
              Date().timeIntervalSince(entry.timestamp) < healthCacheTTL else {
            return nil
        }
        return entry.data
    }

    private func cacheHealthCategories(_ data: [HealthCategory], for petId: UUID) {
        healthCategoriesCache[petId] = CacheEntry(data: data, timestamp: Date())
    }

    func invalidateHealthCache(for petId: UUID) {
        healthEventsCache.removeValue(forKey: petId)
        healthCategoriesCache.removeValue(forKey: petId)
        Task {
            await persistentCache.delete(forKey: .healthEvents(petId: petId.uuidString))
            await persistentCache.delete(forKey: .healthCategories(petId: petId.uuidString))
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
                                print("Background health events refresh failed: \(error)")
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
        let events = try await api.getHealthEvents(petId: petId)
        cacheHealthEvents(events, for: petId)
        await persistentCache.save(events, forKey: .healthEvents(petId: petId.uuidString))
    }

    func getHealthCategories(for petId: UUID, forceRefresh: Bool = false) async throws -> [HealthCategory] {
        // Check memory cache
        if !forceRefresh, let cached = getCachedHealthCategories(for: petId) {
            return cached
        }

        // Check disk cache
        if !forceRefresh {
            let diskCached: PersistentCacheManager.CachedData<[HealthCategory]>? = await persistentCache.load(forKey: .healthCategories(petId: petId.uuidString))
            if let diskCached = diskCached {
                cacheHealthCategories(diskCached.data, for: petId)
                return diskCached.data
            }
        }

        // Fetch from network
        let categories = try await api.getHealthCategories(petId: petId)
        cacheHealthCategories(categories, for: petId)
        await persistentCache.save(categories, forKey: .healthCategories(petId: petId.uuidString))
        return categories
    }

    func getHealthEvent(eventId: UUID) async throws -> HealthEventWithCategory {
        return try await api.getHealthEvent(eventId: eventId)
    }

    func createHealthEvent(petId: UUID, categoryName: String, occurredAt: Date? = nil, notes: String? = nil, notifyFamily: Bool = false) async throws -> HealthEvent {
        let event = HealthEventCreate(categoryName: categoryName, occurredAt: occurredAt, notes: notes, notifyFamily: notifyFamily)
        let result = try await api.createHealthEvent(petId: petId, event: event)
        invalidateHealthCache(for: petId)
        NavigationManager.shared.requestTabRefresh(.health)
        return result
    }

    func updateHealthEvent(eventId: UUID, petId: UUID, categoryName: String? = nil, occurredAt: Date? = nil, notes: String? = nil) async throws -> HealthEventWithCategory {
        let update = HealthEventUpdate(categoryName: categoryName, occurredAt: occurredAt, notes: notes)
        let result = try await api.updateHealthEvent(eventId: eventId, update: update)
        invalidateHealthCache(for: petId)
        NavigationManager.shared.requestTabRefresh(.health)
        return result
    }

    func deleteHealthEvent(eventId: UUID, petId: UUID) async throws {
        try await api.deleteHealthEvent(eventId: eventId)
        invalidateHealthCache(for: petId)
        NavigationManager.shared.requestTabRefresh(.health)
    }

    func uploadHealthEventPhoto(eventId: UUID, petId: UUID, imageData: Data, mimeType: String = "image/jpeg") async throws -> HealthEventPhoto {
        let result = try await api.uploadHealthEventPhoto(eventId: eventId, imageData: imageData, mimeType: mimeType)
        invalidateHealthCache(for: petId)
        NavigationManager.shared.requestTabRefresh(.health)
        return result
    }

    func deleteHealthEventPhoto(eventId: UUID, photoId: UUID, petId: UUID) async throws {
        try await api.deleteHealthEventPhoto(eventId: eventId, photoId: photoId)
        invalidateHealthCache(for: petId)
        NavigationManager.shared.requestTabRefresh(.health)
    }

    func searchHealthEvents(petId: UUID, query: String, category: String? = nil) async throws -> [HealthEventWithCategory] {
        // Search is always fresh, no caching
        return try await api.searchHealthEvents(petId: petId, query: query, category: category)
    }

    // MARK: - Background Refresh

    func refreshAllDataInBackground() async {
        do {
            _ = try await getPets(forceRefresh: true)
        } catch {
            print("Background refresh failed: \(error)")
        }
    }

    func prefetchDataOnForeground() {
        Task {
            _ = try? await getPets(forceRefresh: false)
        }
    }
}
