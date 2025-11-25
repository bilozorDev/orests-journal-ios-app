//
//  FamilyMember.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import Foundation

/// APIClient uses automatic snake_case conversion
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
}
