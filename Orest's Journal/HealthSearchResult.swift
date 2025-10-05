//
//  HealthSearchResult.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import Foundation

struct HealthSearchResult: Codable, Identifiable, Hashable {
    let eventId: UUID
    let categoryId: UUID
    let categoryName: String
    let occurredAt: Date
    let notes: String?
    let petId: UUID
    let petName: String
    let createdById: UUID?
    let createdByEmail: String
    let similarity: Double

    var id: UUID { eventId }

    enum CodingKeys: String, CodingKey {
        case eventId = "event_id"
        case categoryId = "category_id"
        case categoryName = "category_name"
        case occurredAt = "occurred_at"
        case notes
        case petId = "pet_id"
        case petName = "pet_name"
        case createdById = "created_by_id"
        case createdByEmail = "created_by_email"
        case similarity
    }
}

// Response from the embed-search-query Edge Function
struct EmbeddingResponse: Codable {
    let success: Bool
    let query: String?
    let embedding: [Double]?
    let dimensions: Int?
    let error: String?
}
