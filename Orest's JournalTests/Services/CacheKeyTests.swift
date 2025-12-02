//
//  CacheKeyTests.swift
//  Orest's JournalTests
//
//  Unit tests for PersistentCacheManager.CacheKey enum.
//

import XCTest
@testable import Orest_s_Journal

final class CacheKeyTests: XCTestCase {

    // MARK: - Dashboard Cache Key Tests

    func testDashboardCacheKeyFileName() {
        let petId = UUID(uuidString: "550e8400-e29b-41d4-a716-446655440000")!
        let key = PersistentCacheManager.CacheKey.dashboard(petId: petId)

        XCTAssertEqual(key.fileName, "dashboard_550E8400-E29B-41D4-A716-446655440000.json")
    }

    func testDashboardCacheKeyUniqueness() {
        let petId1 = UUID()
        let petId2 = UUID()

        let key1 = PersistentCacheManager.CacheKey.dashboard(petId: petId1)
        let key2 = PersistentCacheManager.CacheKey.dashboard(petId: petId2)

        XCTAssertNotEqual(key1.fileName, key2.fileName)
    }

    // MARK: - Foods Cache Key Tests

    func testFoodsCacheKeyActiveOnly() {
        let key = PersistentCacheManager.CacheKey.foods(includeArchived: false)
        XCTAssertEqual(key.fileName, "foods_active.json")
    }

    func testFoodsCacheKeyIncludeArchived() {
        let key = PersistentCacheManager.CacheKey.foods(includeArchived: true)
        XCTAssertEqual(key.fileName, "foods_all.json")
    }

    // MARK: - Medications Cache Key Tests

    func testMedicationsCacheKeyWithPetId() {
        let petId = UUID(uuidString: "550e8400-e29b-41d4-a716-446655440000")!
        let key = PersistentCacheManager.CacheKey.medications(petId: petId)

        XCTAssertEqual(key.fileName, "medications_550E8400-E29B-41D4-A716-446655440000.json")
    }

    func testMedicationsCacheKeyAllPets() {
        let key = PersistentCacheManager.CacheKey.medications(petId: nil)
        XCTAssertEqual(key.fileName, "medications_all.json")
    }

    // MARK: - Feeding History Cache Key Tests

    func testFeedingHistoryCacheKeyFileName() {
        let petId = UUID(uuidString: "550e8400-e29b-41d4-a716-446655440000")!
        let key = PersistentCacheManager.CacheKey.feedingHistory(petId: petId)

        XCTAssertEqual(key.fileName, "feeding_history_550E8400-E29B-41D4-A716-446655440000.json")
    }

    // MARK: - Medication History Cache Key Tests

    func testMedicationHistoryCacheKeyFileName() {
        let petId = UUID(uuidString: "550e8400-e29b-41d4-a716-446655440000")!
        let key = PersistentCacheManager.CacheKey.medicationHistory(petId: petId)

        XCTAssertEqual(key.fileName, "medication_history_550E8400-E29B-41D4-A716-446655440000.json")
    }

    // MARK: - Family Members Cache Key Tests

    func testFamilyMembersCacheKeyFileName() {
        let key = PersistentCacheManager.CacheKey.familyMembers(familyId: "family-123")
        XCTAssertEqual(key.fileName, "family_members_family-123.json")
    }

    func testFamilyMembersCacheKeyWithUUID() {
        let familyId = UUID().uuidString
        let key = PersistentCacheManager.CacheKey.familyMembers(familyId: familyId)

        XCTAssertTrue(key.fileName.hasPrefix("family_members_"))
        XCTAssertTrue(key.fileName.hasSuffix(".json"))
        XCTAssertTrue(key.fileName.contains(familyId))
    }

    // MARK: - Pets Cache Key Tests

    func testPetsCacheKeyFileName() {
        let key = PersistentCacheManager.CacheKey.pets
        XCTAssertEqual(key.fileName, "pets.json")
    }

    // MARK: - File Name Format Tests

    func testAllCacheKeysHaveJsonExtension() {
        let petId = UUID()
        let keys: [PersistentCacheManager.CacheKey] = [
            .dashboard(petId: petId),
            .foods(includeArchived: false),
            .foods(includeArchived: true),
            .medications(petId: petId),
            .medications(petId: nil),
            .feedingHistory(petId: petId),
            .medicationHistory(petId: petId),
            .familyMembers(familyId: "test"),
            .pets
        ]

        for key in keys {
            XCTAssertTrue(key.fileName.hasSuffix(".json"), "Cache key \(key) should have .json extension")
        }
    }

    func testCacheKeyFileNamesAreUnique() {
        let petId = UUID()
        let keys: [PersistentCacheManager.CacheKey] = [
            .dashboard(petId: petId),
            .foods(includeArchived: false),
            .foods(includeArchived: true),
            .medications(petId: petId),
            .medications(petId: nil),
            .feedingHistory(petId: petId),
            .medicationHistory(petId: petId),
            .familyMembers(familyId: "test"),
            .pets
        ]

        var fileNames = Set<String>()
        for key in keys {
            XCTAssertFalse(fileNames.contains(key.fileName), "Duplicate file name: \(key.fileName)")
            fileNames.insert(key.fileName)
        }
    }
}
