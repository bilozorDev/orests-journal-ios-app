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
    // MARK: - Pets

    func getPets(forceRefresh: Bool) async throws -> [Pet]

    // MARK: - Family

    func getFamilyMembers(for familyId: String, forceRefresh: Bool) async throws -> FamilyDetailResponse

    // MARK: - Cache Invalidation

    func invalidatePetsCache()
    func invalidateFamilyCache(for familyId: String)
    func invalidateAllCaches()
}

// MARK: - Default Parameter Extensions

extension DataServiceProtocol {
    func getPets() async throws -> [Pet] {
        try await getPets(forceRefresh: false)
    }
}
