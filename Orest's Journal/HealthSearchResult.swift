//
//  HealthSearchResult.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import Foundation

/// APIClient uses automatic snake_case conversion
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
}

// Response from the embed-search-query Edge Function
struct EmbeddingResponse: Codable {
    let success: Bool
    let query: String?
    let embedding: [Double]?
    let dimensions: Int?
    let error: String?
}
