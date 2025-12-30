//
//  Pet.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import Foundation

struct Pet: Codable, Identifiable, Hashable {
    let id: UUID
    let familyId: String
    let name: String
    let kind: String
    let photoUrl: String?
    let currentWeight: Double?
    let dateOfBirth: Date?
    let isArchived: Bool?
    let createdAt: Date
    let createdBy: String?
}

struct PetDeleteResponse: Codable {
    let deleted: Bool
    let archived: Bool
    let message: String
}
