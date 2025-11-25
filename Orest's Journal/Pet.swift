//
//  Pet.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import Foundation

struct Pet: Codable, Identifiable, Hashable {
    let id: UUID
    let orgId: String  // Family ID
    let name: String
    let kind: String
    let photoUrl: String?
    let currentWeight: Double?
    let createdAt: Date
    let createdBy: String?
}
