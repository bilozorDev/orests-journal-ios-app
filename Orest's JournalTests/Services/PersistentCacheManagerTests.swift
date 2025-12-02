//
//  PersistentCacheManagerTests.swift
//  Orest's JournalTests
//
//  Unit tests for PersistentCacheManager CacheKey file name generation.
//

import XCTest
@testable import Orest_s_Journal

final class PersistentCacheManagerTests: XCTestCase {

    // MARK: - CacheKey File Name Tests

    func testDashboardCacheKeyFileName() {
        let petId = UUID(uuidString: "550e8400-e29b-41d4-a716-446655440000")!
        let key = PersistentCacheManager.CacheKey.dashboard(petId: petId)

        XCTAssertEqual(key.fileName, "dashboard_550E8400-E29B-41D4-A716-446655440000.json")
    }

    func testFoodsCacheKeyFileNameActiveOnly() {
        let key = PersistentCacheManager.CacheKey.foods(includeArchived: false)

        XCTAssertEqual(key.fileName, "foods_active.json")
    }

    func testFoodsCacheKeyFileNameIncludingArchived() {
        let key = PersistentCacheManager.CacheKey.foods(includeArchived: true)

        XCTAssertEqual(key.fileName, "foods_all.json")
    }

    func testMedicationsCacheKeyFileNameForPet() {
        let petId = UUID(uuidString: "660e8400-e29b-41d4-a716-446655440001")!
        let key = PersistentCacheManager.CacheKey.medications(petId: petId)

        XCTAssertEqual(key.fileName, "medications_660E8400-E29B-41D4-A716-446655440001.json")
    }

    func testMedicationsCacheKeyFileNameForAll() {
        let key = PersistentCacheManager.CacheKey.medications(petId: nil)

        XCTAssertEqual(key.fileName, "medications_all.json")
    }

    func testFeedingHistoryCacheKeyFileName() {
        let petId = UUID(uuidString: "770e8400-e29b-41d4-a716-446655440002")!
        let key = PersistentCacheManager.CacheKey.feedingHistory(petId: petId)

        XCTAssertEqual(key.fileName, "feeding_history_770E8400-E29B-41D4-A716-446655440002.json")
    }

    func testMedicationHistoryCacheKeyFileName() {
        let petId = UUID(uuidString: "880e8400-e29b-41d4-a716-446655440003")!
        let key = PersistentCacheManager.CacheKey.medicationHistory(petId: petId)

        XCTAssertEqual(key.fileName, "medication_history_880E8400-E29B-41D4-A716-446655440003.json")
    }

    func testFamilyMembersCacheKeyFileName() {
        let familyId = "family-123"
        let key = PersistentCacheManager.CacheKey.familyMembers(familyId: familyId)

        XCTAssertEqual(key.fileName, "family_members_family-123.json")
    }

    func testPetsCacheKeyFileName() {
        let key = PersistentCacheManager.CacheKey.pets

        XCTAssertEqual(key.fileName, "pets.json")
    }

    // MARK: - CacheKey Uniqueness Tests

    func testDifferentPetIdProducesDifferentFileName() {
        let petId1 = UUID(uuidString: "550e8400-e29b-41d4-a716-446655440000")!
        let petId2 = UUID(uuidString: "660e8400-e29b-41d4-a716-446655440001")!

        let key1 = PersistentCacheManager.CacheKey.dashboard(petId: petId1)
        let key2 = PersistentCacheManager.CacheKey.dashboard(petId: petId2)

        XCTAssertNotEqual(key1.fileName, key2.fileName)
    }

    func testSamePetIdProducesSameFileName() {
        let petId = UUID(uuidString: "550e8400-e29b-41d4-a716-446655440000")!

        let key1 = PersistentCacheManager.CacheKey.dashboard(petId: petId)
        let key2 = PersistentCacheManager.CacheKey.dashboard(petId: petId)

        XCTAssertEqual(key1.fileName, key2.fileName)
    }

    func testDifferentCacheTypesProduceDifferentFileNames() {
        let petId = UUID(uuidString: "550e8400-e29b-41d4-a716-446655440000")!

        let dashboardKey = PersistentCacheManager.CacheKey.dashboard(petId: petId)
        let feedingKey = PersistentCacheManager.CacheKey.feedingHistory(petId: petId)
        let medicationKey = PersistentCacheManager.CacheKey.medicationHistory(petId: petId)

        XCTAssertNotEqual(dashboardKey.fileName, feedingKey.fileName)
        XCTAssertNotEqual(feedingKey.fileName, medicationKey.fileName)
        XCTAssertNotEqual(dashboardKey.fileName, medicationKey.fileName)
    }

    // MARK: - File Name Format Tests

    func testAllFileNamesEndWithJson() {
        let petId = UUID()
        let keys: [PersistentCacheManager.CacheKey] = [
            .dashboard(petId: petId),
            .foods(includeArchived: true),
            .foods(includeArchived: false),
            .medications(petId: petId),
            .medications(petId: nil),
            .feedingHistory(petId: petId),
            .medicationHistory(petId: petId),
            .familyMembers(familyId: "test"),
            .pets
        ]

        for key in keys {
            XCTAssertTrue(key.fileName.hasSuffix(".json"), "File name should end with .json: \(key.fileName)")
        }
    }

    func testFileNamesContainNoInvalidCharacters() {
        let petId = UUID()
        let keys: [PersistentCacheManager.CacheKey] = [
            .dashboard(petId: petId),
            .foods(includeArchived: true),
            .medications(petId: petId),
            .feedingHistory(petId: petId),
            .medicationHistory(petId: petId),
            .familyMembers(familyId: "family-123"),
            .pets
        ]

        let invalidChars = CharacterSet(charactersIn: "/\\:*?\"<>|")

        for key in keys {
            let fileName = key.fileName
            XCTAssertNil(fileName.rangeOfCharacter(from: invalidChars), "File name contains invalid characters: \(fileName)")
        }
    }
}
