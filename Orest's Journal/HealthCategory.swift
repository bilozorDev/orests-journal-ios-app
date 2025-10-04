//
//  HealthCategory.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import Foundation

struct HealthCategory: Codable, Identifiable, Hashable {
    let id: UUID
    let petId: UUID
    let name: String
    let nameNormalized: String
    let createdAt: Date
    let createdBy: UUID?

    enum CodingKeys: String, CodingKey {
        case id
        case petId = "pet_id"
        case name
        case nameNormalized = "name_normalized"
        case createdAt = "created_at"
        case createdBy = "created_by"
    }
}
