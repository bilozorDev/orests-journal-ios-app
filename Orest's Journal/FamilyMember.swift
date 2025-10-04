//
//  FamilyMember.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import Foundation

struct FamilyMember: Codable, Identifiable {
    let id: UUID
    let familyId: UUID
    let userId: UUID
    let role: Role
    let joinedAt: Date

    enum Role: String, Codable {
        case owner
        case member
    }

    enum CodingKeys: String, CodingKey {
        case id
        case familyId = "family_id"
        case userId = "user_id"
        case role
        case joinedAt = "joined_at"
    }
}
