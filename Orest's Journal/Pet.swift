//
//  Pet.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import Foundation

struct Pet: Codable, Identifiable, Hashable {
    let id: UUID
    let familyId: UUID
    let name: String
    let kind: String
    let photoUrl: String?
    let currentWeight: Double?
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id
        case familyId = "family_id"
        case name
        case kind
        case photoUrl = "photo_url"
        case currentWeight = "current_weight"
        case createdAt = "created_at"
    }
}
