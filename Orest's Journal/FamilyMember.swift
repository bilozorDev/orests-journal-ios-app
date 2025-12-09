//
//  FamilyMember.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import Foundation

/// Family member model matching API response structure
struct FamilyMember: Codable, Identifiable {
    let id: String
    let orgId: String
    let userId: String
    let role: String
    let joinedAt: Date?
    let email: String?
    let firstName: String?
    let lastName: String?

    var displayName: String {
        Formatters.formatDisplayName(firstName: firstName, lastName: lastName, fallback: email ?? "Unknown")
    }
}
