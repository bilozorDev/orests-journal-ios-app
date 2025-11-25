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
    let createdBy: String?
}

struct HealthEventWithCategory: Codable, Identifiable, Hashable {
    let event: HealthEvent
    let category: HealthCategory

    var id: UUID { event.id }
}
