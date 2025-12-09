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
    private let cacheTTL: TimeInterval = 60  // 1 minute
    private let petsCacheTTL: TimeInterval = 300  // 5 minutes

    // Cache stampede prevention flags
    private var petsRefreshInProgress = false
    private var familyRefreshInProgress: Set<String> = []

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

    func invalidateFamilyCache(for familyId: String) {
        familyMembersCache.removeValue(forKey: familyId)
        Task {
            await persistentCache.delete(forKey: .familyMembers(familyId: familyId))
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

    func updatePet(id: UUID, name: String? = nil, kind: String? = nil, photoUrl: String? = nil, currentWeight: Double? = nil, dateOfBirth: Date? = nil) async throws -> Pet {
        let update = PetUpdate(name: name, kind: kind, photoUrl: photoUrl, currentWeight: currentWeight, dateOfBirth: dateOfBirth)
        let result = try await api.updatePet(id: id, update: update)
        invalidatePetsCache()
        return result
    }

    func deletePet(id: UUID) async throws {
        try await api.deletePet(id: id)
        invalidatePetsCache()
    }

    // MARK: - Photo Upload

    func uploadPetPhoto(imageData: Data) async throws -> String {
        return try await api.uploadPetPhoto(imageData: imageData)
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
        invalidateFamilyCache(for: familyId)
        return result
    }

    func removeFamilyMember(familyId: String, userId: String) async throws {
        try await api.removeFamilyMember(familyId: familyId, userId: userId)
        invalidateFamilyCache(for: familyId)
    }

    func updateFamilyName(familyId: String, name: String) async throws -> AppFamily {
        let result = try await api.updateFamilyName(familyId: familyId, name: name)
        invalidateFamilyCache(for: familyId)
        return result
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
