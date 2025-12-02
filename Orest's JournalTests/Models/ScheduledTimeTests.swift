//
//  ScheduledTimeTests.swift
//  Orest's JournalTests
//
//  Unit tests for ScheduledTime and ScheduledTimeCreate models.
//

import XCTest
@testable import Orest_s_Journal

final class ScheduledTimeTests: XCTestCase {

    // MARK: - ScheduledTime Decoding Tests

    func testDecodingScheduledTimeFromJSON() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "medication_id": "660e8400-e29b-41d4-a716-446655440001",
            "scheduled_hour": 8,
            "scheduled_minute": 30
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase

        let time = try decoder.decode(ScheduledTime.self, from: json)

        XCTAssertEqual(time.id, UUID(uuidString: "550e8400-e29b-41d4-a716-446655440000"))
        XCTAssertEqual(time.medicationId, UUID(uuidString: "660e8400-e29b-41d4-a716-446655440001"))
        XCTAssertEqual(time.scheduledHour, 8)
        XCTAssertEqual(time.scheduledMinute, 30)
    }

    func testDecodingScheduledTimeWithZeroMinute() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "medication_id": "660e8400-e29b-41d4-a716-446655440001",
            "scheduled_hour": 14,
            "scheduled_minute": 0
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase

        let time = try decoder.decode(ScheduledTime.self, from: json)

        XCTAssertEqual(time.scheduledHour, 14)
        XCTAssertEqual(time.scheduledMinute, 0)
    }

    // MARK: - Display Time Tests

    func testDisplayTimeMorning() {
        let time = ScheduledTime(
            id: UUID(),
            medicationId: UUID(),
            scheduledHour: 8,
            scheduledMinute: 0
        )

        XCTAssertEqual(time.displayTime, "8 AM")
    }

    func testDisplayTimeMorningWithMinutes() {
        let time = ScheduledTime(
            id: UUID(),
            medicationId: UUID(),
            scheduledHour: 8,
            scheduledMinute: 30
        )

        XCTAssertEqual(time.displayTime, "8:30 AM")
    }

    func testDisplayTimeNoon() {
        let time = ScheduledTime(
            id: UUID(),
            medicationId: UUID(),
            scheduledHour: 12,
            scheduledMinute: 0
        )

        XCTAssertEqual(time.displayTime, "12 PM")
    }

    func testDisplayTimeAfternoon() {
        let time = ScheduledTime(
            id: UUID(),
            medicationId: UUID(),
            scheduledHour: 14,
            scheduledMinute: 0
        )

        XCTAssertEqual(time.displayTime, "2 PM")
    }

    func testDisplayTimeAfternoonWithMinutes() {
        let time = ScheduledTime(
            id: UUID(),
            medicationId: UUID(),
            scheduledHour: 14,
            scheduledMinute: 45
        )

        XCTAssertEqual(time.displayTime, "2:45 PM")
    }

    func testDisplayTimeEvening() {
        let time = ScheduledTime(
            id: UUID(),
            medicationId: UUID(),
            scheduledHour: 20,
            scheduledMinute: 0
        )

        XCTAssertEqual(time.displayTime, "8 PM")
    }

    func testDisplayTimeMidnight() {
        let time = ScheduledTime(
            id: UUID(),
            medicationId: UUID(),
            scheduledHour: 0,
            scheduledMinute: 0
        )

        XCTAssertEqual(time.displayTime, "12 AM")
    }

    func testDisplayTimeWithLeadingZeroMinutes() {
        let time = ScheduledTime(
            id: UUID(),
            medicationId: UUID(),
            scheduledHour: 9,
            scheduledMinute: 5
        )

        XCTAssertEqual(time.displayTime, "9:05 AM")
    }

    // MARK: - asDate Tests

    func testAsDateHourAndMinute() {
        let time = ScheduledTime(
            id: UUID(),
            medicationId: UUID(),
            scheduledHour: 14,
            scheduledMinute: 30
        )

        let date = time.asDate
        let components = Calendar.current.dateComponents([.hour, .minute], from: date)

        XCTAssertEqual(components.hour, 14)
        XCTAssertEqual(components.minute, 30)
    }

    func testAsDateIsToday() {
        let time = ScheduledTime(
            id: UUID(),
            medicationId: UUID(),
            scheduledHour: 10,
            scheduledMinute: 0
        )

        let date = time.asDate
        XCTAssertTrue(Calendar.current.isDateInToday(date))
    }

    // MARK: - Identifiable Tests

    func testScheduledTimeIdentifiable() {
        let uuid = UUID()
        let time = ScheduledTime(
            id: uuid,
            medicationId: UUID(),
            scheduledHour: 8,
            scheduledMinute: 0
        )

        XCTAssertEqual(time.id, uuid)
    }

    // MARK: - Hashable Tests

    func testScheduledTimeHashable() {
        let id = UUID()
        let medId = UUID()

        let time1 = ScheduledTime(id: id, medicationId: medId, scheduledHour: 8, scheduledMinute: 30)
        let time2 = ScheduledTime(id: id, medicationId: medId, scheduledHour: 8, scheduledMinute: 30)

        XCTAssertEqual(time1.hashValue, time2.hashValue)

        var set = Set<ScheduledTime>()
        set.insert(time1)
        XCTAssertTrue(set.contains(time1))
    }

    // MARK: - ScheduledTimeCreate Tests

    func testScheduledTimeCreateWithHourAndMinute() {
        let create = ScheduledTimeCreate(hour: 14, minute: 30)

        XCTAssertEqual(create.hour, 14)
        XCTAssertEqual(create.minute, 30)
    }

    func testScheduledTimeCreateWithHourOnly() {
        let create = ScheduledTimeCreate(hour: 8)

        XCTAssertEqual(create.hour, 8)
        XCTAssertEqual(create.minute, 0)
    }

    func testScheduledTimeCreateFromDate() {
        var components = DateComponents()
        components.hour = 15
        components.minute = 45
        let date = Calendar.current.date(from: components)!

        let create = ScheduledTimeCreate(from: date)

        XCTAssertEqual(create.hour, 15)
        XCTAssertEqual(create.minute, 45)
    }

    func testScheduledTimeCreateEncoding() throws {
        let create = ScheduledTimeCreate(hour: 10, minute: 15)

        let encoder = JSONEncoder()
        let data = try encoder.encode(create)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["hour"] as? Int, 10)
        XCTAssertEqual(jsonObject["minute"] as? Int, 15)
    }

    func testScheduledTimeCreateDecoding() throws {
        let json = """
        {
            "hour": 9,
            "minute": 30
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        let create = try decoder.decode(ScheduledTimeCreate.self, from: json)

        XCTAssertEqual(create.hour, 9)
        XCTAssertEqual(create.minute, 30)
    }

    func testScheduledTimeCreateHashable() {
        let create1 = ScheduledTimeCreate(hour: 8, minute: 30)
        let create2 = ScheduledTimeCreate(hour: 8, minute: 30)
        let create3 = ScheduledTimeCreate(hour: 9, minute: 30)

        XCTAssertEqual(create1.hashValue, create2.hashValue)
        XCTAssertNotEqual(create1.hashValue, create3.hashValue)

        var set = Set<ScheduledTimeCreate>()
        set.insert(create1)
        XCTAssertTrue(set.contains(create1))
        XCTAssertTrue(set.contains(create2)) // Same values
        XCTAssertFalse(set.contains(create3))
    }

    // MARK: - Edge Case Tests

    func testBoundaryHours() {
        // Test 0 (midnight), 12 (noon), 23 (11 PM)
        let midnight = ScheduledTime(id: UUID(), medicationId: UUID(), scheduledHour: 0, scheduledMinute: 0)
        XCTAssertEqual(midnight.displayTime, "12 AM")

        let noon = ScheduledTime(id: UUID(), medicationId: UUID(), scheduledHour: 12, scheduledMinute: 0)
        XCTAssertEqual(noon.displayTime, "12 PM")

        let elevenPM = ScheduledTime(id: UUID(), medicationId: UUID(), scheduledHour: 23, scheduledMinute: 0)
        XCTAssertEqual(elevenPM.displayTime, "11 PM")
    }

    func testBoundaryMinutes() {
        let time59 = ScheduledTime(id: UUID(), medicationId: UUID(), scheduledHour: 10, scheduledMinute: 59)
        XCTAssertEqual(time59.displayTime, "10:59 AM")
    }
}
