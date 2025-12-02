//
//  PetMedicationDoseTests.swift
//  Orest's JournalTests
//
//  Unit tests for PetMedicationDose and AllMedicationDose models.
//

import XCTest
@testable import Orest_s_Journal

final class PetMedicationDoseTests: XCTestCase {

    // MARK: - PetMedicationDose Decoding Tests

    func testDecodingPetMedicationDoseFromJSON() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "medication_id": "660e8400-e29b-41d4-a716-446655440001",
            "given_at": "2024-01-15T08:30:00Z",
            "given_by": "user@example.com",
            "notes": "Given with food",
            "created_at": "2024-01-15T08:30:05Z"
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let dose = try decoder.decode(PetMedicationDose.self, from: json)

        XCTAssertEqual(dose.id, UUID(uuidString: "550e8400-e29b-41d4-a716-446655440000"))
        XCTAssertEqual(dose.medicationId, UUID(uuidString: "660e8400-e29b-41d4-a716-446655440001"))
        XCTAssertEqual(dose.givenBy, "user@example.com")
        XCTAssertEqual(dose.notes, "Given with food")
    }

    func testDecodingPetMedicationDoseWithNullNotes() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "medication_id": "660e8400-e29b-41d4-a716-446655440001",
            "given_at": "2024-01-15T08:30:00Z",
            "given_by": "admin@example.com",
            "notes": null,
            "created_at": "2024-01-15T08:30:05Z"
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let dose = try decoder.decode(PetMedicationDose.self, from: json)

        XCTAssertNil(dose.notes)
        XCTAssertEqual(dose.givenBy, "admin@example.com")
    }

    // MARK: - PetMedicationDose Encoding Tests

    func testEncodingPetMedicationDose() throws {
        let dose = PetMedicationDose(
            id: UUID(uuidString: "550e8400-e29b-41d4-a716-446655440000")!,
            medicationId: UUID(uuidString: "660e8400-e29b-41d4-a716-446655440001")!,
            givenAt: Date(timeIntervalSince1970: 1705307400),
            givenBy: "test@example.com",
            notes: "Test notes",
            createdAt: Date(timeIntervalSince1970: 1705307405)
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.dateEncodingStrategy = .iso8601

        let data = try encoder.encode(dose)
        let jsonObject = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(jsonObject["given_by"] as? String, "test@example.com")
        XCTAssertEqual(jsonObject["notes"] as? String, "Test notes")
    }

    // MARK: - PetMedicationDose Identifiable Tests

    func testPetMedicationDoseIdentifiable() {
        let uuid = UUID()
        let dose = PetMedicationDose(
            id: uuid,
            medicationId: UUID(),
            givenAt: Date(),
            givenBy: "user@example.com",
            notes: nil,
            createdAt: Date()
        )

        XCTAssertEqual(dose.id, uuid)
    }

    // MARK: - Round-Trip Tests

    func testPetMedicationDoseRoundTrip() throws {
        let original = PetMedicationDose(
            id: UUID(),
            medicationId: UUID(),
            givenAt: Date(timeIntervalSince1970: 1705307400),
            givenBy: "round_trip@example.com",
            notes: "Round trip test",
            createdAt: Date(timeIntervalSince1970: 1705307405)
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.dateEncodingStrategy = .iso8601

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let data = try encoder.encode(original)
        let decoded = try decoder.decode(PetMedicationDose.self, from: data)

        XCTAssertEqual(decoded.id, original.id)
        XCTAssertEqual(decoded.medicationId, original.medicationId)
        XCTAssertEqual(decoded.givenBy, original.givenBy)
        XCTAssertEqual(decoded.notes, original.notes)
    }

    // MARK: - AllMedicationDose Tests

    func testDecodingAllMedicationDoseFromJSON() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "medication_id": "660e8400-e29b-41d4-a716-446655440001",
            "medication_name": "Antibiotics",
            "pet_id": "770e8400-e29b-41d4-a716-446655440002",
            "given_at": "2024-01-15T08:30:00Z",
            "given_by": "user@example.com",
            "notes": "Morning dose",
            "created_at": "2024-01-15T08:30:05Z"
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let dose = try decoder.decode(AllMedicationDose.self, from: json)

        XCTAssertEqual(dose.id, UUID(uuidString: "550e8400-e29b-41d4-a716-446655440000"))
        XCTAssertEqual(dose.medicationId, UUID(uuidString: "660e8400-e29b-41d4-a716-446655440001"))
        XCTAssertEqual(dose.medicationName, "Antibiotics")
        XCTAssertEqual(dose.petId, UUID(uuidString: "770e8400-e29b-41d4-a716-446655440002"))
        XCTAssertEqual(dose.givenBy, "user@example.com")
        XCTAssertEqual(dose.notes, "Morning dose")
    }

    func testDecodingAllMedicationDoseWithNullNotes() throws {
        let json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "medication_id": "660e8400-e29b-41d4-a716-446655440001",
            "medication_name": "Pain Relief",
            "pet_id": "770e8400-e29b-41d4-a716-446655440002",
            "given_at": "2024-01-15T08:30:00Z",
            "given_by": "admin@example.com",
            "notes": null,
            "created_at": "2024-01-15T08:30:05Z"
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let dose = try decoder.decode(AllMedicationDose.self, from: json)

        XCTAssertNil(dose.notes)
        XCTAssertEqual(dose.medicationName, "Pain Relief")
    }

    func testAllMedicationDoseIdentifiable() {
        let uuid = UUID()
        let dose = AllMedicationDose(
            id: uuid,
            medicationId: UUID(),
            medicationName: "Test Med",
            petId: UUID(),
            givenAt: Date(),
            givenBy: "user@example.com",
            notes: nil,
            createdAt: Date()
        )

        XCTAssertEqual(dose.id, uuid)
    }

    // MARK: - AllDosesListResponse Tests

    func testDecodingAllDosesListResponse() throws {
        let json = """
        {
            "doses": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "medication_id": "660e8400-e29b-41d4-a716-446655440001",
                    "medication_name": "Antibiotics",
                    "pet_id": "770e8400-e29b-41d4-a716-446655440002",
                    "given_at": "2024-01-15T08:30:00Z",
                    "given_by": "user@example.com",
                    "notes": null,
                    "created_at": "2024-01-15T08:30:05Z"
                },
                {
                    "id": "880e8400-e29b-41d4-a716-446655440003",
                    "medication_id": "660e8400-e29b-41d4-a716-446655440001",
                    "medication_name": "Antibiotics",
                    "pet_id": "770e8400-e29b-41d4-a716-446655440002",
                    "given_at": "2024-01-15T20:30:00Z",
                    "given_by": "user@example.com",
                    "notes": "Evening dose",
                    "created_at": "2024-01-15T20:30:05Z"
                }
            ],
            "total": 2
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let response = try decoder.decode(AllDosesListResponse.self, from: json)

        XCTAssertEqual(response.doses.count, 2)
        XCTAssertEqual(response.total, 2)
        XCTAssertEqual(response.doses[0].medicationName, "Antibiotics")
        XCTAssertEqual(response.doses[1].notes, "Evening dose")
    }

    func testDecodingEmptyDosesListResponse() throws {
        let json = """
        {
            "doses": [],
            "total": 0
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601

        let response = try decoder.decode(AllDosesListResponse.self, from: json)

        XCTAssertEqual(response.doses.count, 0)
        XCTAssertEqual(response.total, 0)
    }
}
