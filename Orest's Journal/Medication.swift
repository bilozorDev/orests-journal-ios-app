//
//  Medication.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import Foundation

enum MedicationType: String, Codable, CaseIterable {
    case drops
    case pill
    case inhaler
    case shot
    case liquid
    case tablet
    case capsule
    case topical

    var displayName: String {
        switch self {
        case .drops: return "Drops"
        case .pill: return "Pill"
        case .inhaler: return "Inhaler"
        case .shot: return "Shot"
        case .liquid: return "Liquid"
        case .tablet: return "Tablet"
        case .capsule: return "Capsule"
        case .topical: return "Topical"
        }
    }
}

struct PetMedication: Codable, Identifiable, Hashable {
    let id: UUID
    let petId: UUID
    let name: String
    let medicationType: MedicationType
    let startDate: Date
    let endDate: Date?
    let timesPerDay: Int
    let notes: String?
    let createdAt: Date
    let createdBy: UUID?

    enum CodingKeys: String, CodingKey {
        case id
        case petId = "pet_id"
        case name
        case medicationType = "medication_type"
        case startDate = "start_date"
        case endDate = "end_date"
        case timesPerDay = "times_per_day"
        case notes
        case createdAt = "created_at"
        case createdBy = "created_by"
    }

    var isActive: Bool {
        let today = Calendar.current.startOfDay(for: Date())
        let start = Calendar.current.startOfDay(for: startDate)

        guard today >= start else { return false }

        if let end = endDate {
            let endDay = Calendar.current.startOfDay(for: end)
            return today <= endDay
        }

        return true
    }
}

struct PetMedicationDose: Codable, Identifiable {
    let id: UUID
    let medicationId: UUID
    let givenAt: Date
    let givenBy: UUID
    let notes: String?
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id
        case medicationId = "medication_id"
        case givenAt = "given_at"
        case givenBy = "given_by"
        case notes
        case createdAt = "created_at"
    }
}
