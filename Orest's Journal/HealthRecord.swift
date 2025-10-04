//
//  HealthRecord.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import Foundation

struct HealthRecord: Codable, Identifiable {
    let id: UUID
    let petId: UUID
    let recordedAt: Date
    let ageYears: Double?
    let weightPounds: Double?
    let notes: String?

    enum CodingKeys: String, CodingKey {
        case id
        case petId = "pet_id"
        case recordedAt = "recorded_at"
        case ageYears = "age_years"
        case weightPounds = "weight_pounds"
        case notes
    }
}
