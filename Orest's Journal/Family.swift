//
//  Family.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import Foundation

struct Family: Codable, Identifiable {
    let id: UUID
    let name: String
    let createdAt: Date
    let createdBy: UUID?

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case createdAt = "created_at"
        case createdBy = "created_by"
    }
}
