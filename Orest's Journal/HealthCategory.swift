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
    let createdBy: String?
}
