//
//  PetFood.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import Foundation

enum FoodCategory: String, Codable, CaseIterable {
    case dry
    case wet
    case snack

    var displayName: String {
        switch self {
        case .dry: return "Dry"
        case .wet: return "Wet"
        case .snack: return "Snack"
        }
    }
}

struct PetFood: Codable, Identifiable {
    let id: UUID
    let familyId: UUID
    let name: String
    let category: FoodCategory
    let caloriesPerContainer: Double
    let containerSizeGrams: Double
    let imageUrl: String?
    let createdAt: Date
    let createdBy: UUID?

    enum CodingKeys: String, CodingKey {
        case id
        case familyId = "family_id"
        case name
        case category
        case caloriesPerContainer = "calories_per_container"
        case containerSizeGrams = "container_size_grams"
        case imageUrl = "image_url"
        case createdAt = "created_at"
        case createdBy = "created_by"
    }
}
