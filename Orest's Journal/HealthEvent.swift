//
//  HealthEvent.swift
//  Orest's Journal
//
//  Created by Claude on 12/11/25.
//

import Foundation

// MARK: - Health Category

struct HealthCategory: Codable, Identifiable, Hashable {
    let id: UUID
    let orgId: UUID
    let name: String
    let nameNormalized: String
    let createdAt: Date
    let createdBy: UUID?

    // Custom decoder for backwards compatibility with cached data that has petId
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(UUID.self, forKey: .id)
        // Try orgId first, fall back to petId for cached data
        if let orgId = try container.decodeIfPresent(UUID.self, forKey: .orgId) {
            self.orgId = orgId
        } else if let petId = try container.decodeIfPresent(UUID.self, forKey: .petId) {
            // Backwards compatibility: use petId as orgId (they were equivalent before)
            self.orgId = petId
        } else {
            throw DecodingError.keyNotFound(CodingKeys.orgId, DecodingError.Context(codingPath: container.codingPath, debugDescription: "Neither orgId nor petId found"))
        }
        name = try container.decode(String.self, forKey: .name)
        nameNormalized = try container.decode(String.self, forKey: .nameNormalized)
        createdAt = try container.decode(Date.self, forKey: .createdAt)
        createdBy = try container.decodeIfPresent(UUID.self, forKey: .createdBy)
    }

    // Memberwise initializer
    init(id: UUID, orgId: UUID, name: String, nameNormalized: String, createdAt: Date, createdBy: UUID?) {
        self.id = id
        self.orgId = orgId
        self.name = name
        self.nameNormalized = nameNormalized
        self.createdAt = createdAt
        self.createdBy = createdBy
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(id, forKey: .id)
        try container.encode(orgId, forKey: .orgId)
        try container.encode(name, forKey: .name)
        try container.encode(nameNormalized, forKey: .nameNormalized)
        try container.encode(createdAt, forKey: .createdAt)
        try container.encodeIfPresent(createdBy, forKey: .createdBy)
    }

    private enum CodingKeys: String, CodingKey {
        case id, orgId, petId, name, nameNormalized, createdAt, createdBy
    }
}

// MARK: - Health Event Photo

struct HealthEventPhoto: Codable, Identifiable, Hashable {
    let id: UUID
    let photoUrl: String
    let sortOrder: Int
    let createdAt: Date
}

// MARK: - Health Event

struct HealthEvent: Codable, Identifiable, Hashable {
    let id: UUID
    let petId: UUID?
    let categoryId: UUID
    let occurredAt: Date
    let durationMinutes: Int?
    let notes: String?
    let photos: [HealthEventPhoto]
    let createdAt: Date
    let createdBy: UUID?

    // Custom decoder to handle backwards compatibility with cached data missing 'photos', 'petId', or 'durationMinutes'
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(UUID.self, forKey: .id)
        petId = try container.decodeIfPresent(UUID.self, forKey: .petId)
        categoryId = try container.decode(UUID.self, forKey: .categoryId)
        occurredAt = try container.decode(Date.self, forKey: .occurredAt)
        durationMinutes = try container.decodeIfPresent(Int.self, forKey: .durationMinutes)
        notes = try container.decodeIfPresent(String.self, forKey: .notes)
        photos = try container.decodeIfPresent([HealthEventPhoto].self, forKey: .photos) ?? []
        createdAt = try container.decode(Date.self, forKey: .createdAt)
        createdBy = try container.decodeIfPresent(UUID.self, forKey: .createdBy)
    }

    // Memberwise initializer for creating instances directly
    init(id: UUID, petId: UUID?, categoryId: UUID, occurredAt: Date, durationMinutes: Int? = nil, notes: String?, photos: [HealthEventPhoto], createdAt: Date, createdBy: UUID?) {
        self.id = id
        self.petId = petId
        self.categoryId = categoryId
        self.occurredAt = occurredAt
        self.durationMinutes = durationMinutes
        self.notes = notes
        self.photos = photos
        self.createdAt = createdAt
        self.createdBy = createdBy
    }
}

// MARK: - Combined Response (event + category)

struct HealthEventWithCategory: Codable, Identifiable, Hashable {
    let event: HealthEvent
    let category: HealthCategory

    var id: UUID { event.id }
}

// MARK: - List Response

struct HealthEventListResponse: Codable {
    let events: [HealthEventWithCategory]
}

// MARK: - Create/Update DTOs

struct HealthEventCreate: Encodable {
    let categoryName: String
    let occurredAt: Date?
    let durationMinutes: Int?
    let notes: String?
    let notifyFamily: Bool

    init(categoryName: String, occurredAt: Date? = nil, durationMinutes: Int? = nil, notes: String? = nil, notifyFamily: Bool = false) {
        self.categoryName = categoryName
        self.occurredAt = occurredAt
        self.durationMinutes = durationMinutes
        self.notes = notes
        self.notifyFamily = notifyFamily
    }
}

struct HealthEventUpdate: Encodable {
    var categoryName: String?
    var occurredAt: Date?
    var durationMinutes: Int?
    var notes: String?
}
