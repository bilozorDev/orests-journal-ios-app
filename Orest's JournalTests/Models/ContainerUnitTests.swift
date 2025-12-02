//
//  ContainerUnitTests.swift
//  Orest's JournalTests
//
//  Unit tests for ContainerUnit enum and conversions.
//

import XCTest
@testable import Orest_s_Journal

final class ContainerUnitTests: XCTestCase {

    // MARK: - Raw Value Tests

    func testRawValues() {
        XCTAssertEqual(ContainerUnit.grams.rawValue, "g")
        XCTAssertEqual(ContainerUnit.ounces.rawValue, "oz")
        XCTAssertEqual(ContainerUnit.kilograms.rawValue, "kg")
        XCTAssertEqual(ContainerUnit.pounds.rawValue, "lb")
    }

    func testInitFromRawValue() {
        XCTAssertEqual(ContainerUnit(rawValue: "g"), .grams)
        XCTAssertEqual(ContainerUnit(rawValue: "oz"), .ounces)
        XCTAssertEqual(ContainerUnit(rawValue: "kg"), .kilograms)
        XCTAssertEqual(ContainerUnit(rawValue: "lb"), .pounds)
        XCTAssertNil(ContainerUnit(rawValue: "invalid"))
        XCTAssertNil(ContainerUnit(rawValue: ""))
    }

    // MARK: - Display Name Tests

    func testDisplayNames() {
        XCTAssertEqual(ContainerUnit.grams.displayName, "Grams (g)")
        XCTAssertEqual(ContainerUnit.ounces.displayName, "Ounces (oz)")
        XCTAssertEqual(ContainerUnit.kilograms.displayName, "Kilograms (kg)")
        XCTAssertEqual(ContainerUnit.pounds.displayName, "Pounds (lb)")
    }

    // MARK: - Abbreviation Tests

    func testAbbreviations() {
        XCTAssertEqual(ContainerUnit.grams.abbreviation, "g")
        XCTAssertEqual(ContainerUnit.ounces.abbreviation, "oz")
        XCTAssertEqual(ContainerUnit.kilograms.abbreviation, "kg")
        XCTAssertEqual(ContainerUnit.pounds.abbreviation, "lb")
    }

    // MARK: - Grams Conversion Tests

    func testGramsToGrams() {
        let result = ContainerUnit.grams.toGrams(100)
        XCTAssertEqual(result, 100, accuracy: 0.001)
    }

    func testGramsIdentity() {
        // Converting grams to grams should be identity
        for value in [0.0, 1.0, 50.0, 100.0, 1000.0] {
            XCTAssertEqual(ContainerUnit.grams.toGrams(value), value, accuracy: 0.001)
        }
    }

    func testOuncesToGrams() {
        // 1 oz = 28.3495 g
        let result = ContainerUnit.ounces.toGrams(1)
        XCTAssertEqual(result, 28.3495, accuracy: 0.001)
    }

    func testOuncesToGramsMultiple() {
        // 10 oz should be 283.495 g
        let result = ContainerUnit.ounces.toGrams(10)
        XCTAssertEqual(result, 283.495, accuracy: 0.001)
    }

    func testKilogramsToGrams() {
        // 1 kg = 1000 g
        let result = ContainerUnit.kilograms.toGrams(1)
        XCTAssertEqual(result, 1000, accuracy: 0.001)
    }

    func testKilogramsToGramsFractional() {
        // 0.5 kg = 500 g
        let result = ContainerUnit.kilograms.toGrams(0.5)
        XCTAssertEqual(result, 500, accuracy: 0.001)
    }

    func testPoundsToGrams() {
        // 1 lb = 453.592 g
        let result = ContainerUnit.pounds.toGrams(1)
        XCTAssertEqual(result, 453.592, accuracy: 0.001)
    }

    func testPoundsToGramsMultiple() {
        // 5 lb should be 2267.96 g
        let result = ContainerUnit.pounds.toGrams(5)
        XCTAssertEqual(result, 2267.96, accuracy: 0.01)
    }

    func testZeroConversion() {
        // Zero should convert to zero for all units
        XCTAssertEqual(ContainerUnit.grams.toGrams(0), 0)
        XCTAssertEqual(ContainerUnit.ounces.toGrams(0), 0)
        XCTAssertEqual(ContainerUnit.kilograms.toGrams(0), 0)
        XCTAssertEqual(ContainerUnit.pounds.toGrams(0), 0)
    }

    // MARK: - CaseIterable Tests

    func testAllCases() {
        let allCases = ContainerUnit.allCases
        XCTAssertEqual(allCases.count, 4)
        XCTAssertTrue(allCases.contains(.grams))
        XCTAssertTrue(allCases.contains(.ounces))
        XCTAssertTrue(allCases.contains(.kilograms))
        XCTAssertTrue(allCases.contains(.pounds))
    }

    // MARK: - Codable Tests

    func testEncodingDecoding() throws {
        let encoder = JSONEncoder()
        let decoder = JSONDecoder()

        for unit in ContainerUnit.allCases {
            let data = try encoder.encode(unit)
            let decoded = try decoder.decode(ContainerUnit.self, from: data)
            XCTAssertEqual(decoded, unit)
        }
    }

    func testDecodingFromString() throws {
        let json = "\"g\"".data(using: .utf8)!
        let decoder = JSONDecoder()
        let unit = try decoder.decode(ContainerUnit.self, from: json)
        XCTAssertEqual(unit, .grams)
    }

    // MARK: - Practical Conversion Tests

    func testTypicalFoodPortions() {
        // Test common feeding amounts

        // 100g dry food
        XCTAssertEqual(ContainerUnit.grams.toGrams(100), 100, accuracy: 0.001)

        // 3oz wet food
        let wetFoodGrams = ContainerUnit.ounces.toGrams(3)
        XCTAssertEqual(wetFoodGrams, 85.0485, accuracy: 0.001)

        // 0.25 kg bag portion
        let bagPortion = ContainerUnit.kilograms.toGrams(0.25)
        XCTAssertEqual(bagPortion, 250, accuracy: 0.001)

        // 0.5 lb food
        let halfPound = ContainerUnit.pounds.toGrams(0.5)
        XCTAssertEqual(halfPound, 226.796, accuracy: 0.001)
    }
}
