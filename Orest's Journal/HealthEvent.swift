//
//  HealthEvent.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import Foundation

struct HealthEvent: Codable, Identifiable, Hashable {
    let id: UUID
    let categoryId: UUID
    let occurredAt: Date
    let notes: String?
    let createdAt: Date
    let createdBy: UUID?

    enum CodingKeys: String, CodingKey {
        case id
        case categoryId = "category_id"
        case occurredAt = "occurred_at"
        case notes
        case createdAt = "created_at"
        case createdBy = "created_by"
    }
}

struct HealthEventWithCategory: Identifiable, Hashable {
    let event: HealthEvent
    let category: HealthCategory

    var id: UUID { event.id }
}
