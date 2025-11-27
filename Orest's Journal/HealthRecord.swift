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
}

struct HealthRecordCreate: Encodable {
    let weightPounds: Double?
    let ageYears: Double?
    let notes: String?
}
