//
//  DataServiceProtocol.swift
//  Orest's Journal
//
//  Protocol abstraction for DataService to enable testing with mock implementations.
//

import Foundation

/// Protocol defining the data service interface for business logic operations.
/// Conforming to this protocol allows for dependency injection and mock implementations in tests.
protocol DataServiceProtocol {
    // MARK: - Dashboard

    func getDashboard(for petId: String, forceRefresh: Bool) async throws -> DashboardData

    // MARK: - Pets

    func getPets(forceRefresh: Bool) async throws -> [Pet]

    // MARK: - Foods

    func getFoods(includeArchived: Bool, forceRefresh: Bool) async throws -> [PetFood]

    // MARK: - Feedings

    func getFeedingHistory(for petId: String, forceRefresh: Bool) async throws -> FeedingListResponse

    // MARK: - Medications

    func getMedications(for petId: String?, forceRefresh: Bool) async throws -> [PetMedication]
    func getMedicationHistory(for petId: String, forceRefresh: Bool) async throws -> AllDosesListResponse

    // MARK: - Family

    func getFamilyMembers(for familyId: String, forceRefresh: Bool) async throws -> FamilyDetailResponse

    // MARK: - Cache Invalidation

    func invalidateDashboardCache(for petId: String)
    func invalidatePetsCache()
    func invalidateFoodsCache()
    func invalidateFeedingHistoryCache(for petId: String)
    func invalidateMedicationsCache()
    func invalidateMedicationHistoryCache(for petId: String)
    func invalidateFamilyCache(for familyId: String)
    func invalidateAllCaches()
}

// MARK: - Default Parameter Extensions

extension DataServiceProtocol {
    func getDashboard(for petId: String) async throws -> DashboardData {
        try await getDashboard(for: petId, forceRefresh: false)
    }

    func getPets() async throws -> [Pet] {
        try await getPets(forceRefresh: false)
    }

    func getFoods(includeArchived: Bool = false) async throws -> [PetFood] {
        try await getFoods(includeArchived: includeArchived, forceRefresh: false)
    }

    func getMedications(for petId: String? = nil) async throws -> [PetMedication] {
        try await getMedications(for: petId, forceRefresh: false)
    }
}
