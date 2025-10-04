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

enum ContainerUnit: String, Codable, CaseIterable {
    case grams = "g"
    case ounces = "oz"
    case kilograms = "kg"
    case pounds = "lb"

    var displayName: String {
        switch self {
        case .grams: return "Grams (g)"
        case .ounces: return "Ounces (oz)"
        case .kilograms: return "Kilograms (kg)"
        case .pounds: return "Pounds (lb)"
        }
    }

    var abbreviation: String {
        return self.rawValue
    }

    // Convert any unit to grams for calculations
    func toGrams(_ value: Double) -> Double {
        switch self {
        case .grams:
            return value
        case .ounces:
            return value * 28.3495
        case .kilograms:
            return value * 1000
        case .pounds:
            return value * 453.592
        }
    }
}

struct PetFood: Codable, Identifiable, Hashable {
    let id: UUID
    let familyId: UUID
    let name: String
    let category: FoodCategory
    let caloriesPerKg: Double
    let containerSize: Double
    let containerSizeUnit: ContainerUnit
    let imageUrl: String?
    let createdAt: Date
    let createdBy: UUID?

    enum CodingKeys: String, CodingKey {
        case id
        case familyId = "family_id"
        case name
        case category
        case caloriesPerKg = "calories_per_kg"
        case containerSize = "container_size"
        case containerSizeUnit = "container_size_unit"
        case imageUrl = "image_url"
        case createdAt = "created_at"
        case createdBy = "created_by"
    }

    var caloriesPerGram: Double {
        return caloriesPerKg / 1000
    }

    var caloriesPerContainer: Double {
        let sizeInGrams = containerSizeUnit.toGrams(containerSize)
        return caloriesPerGram * sizeInGrams
    }

    func calculateCalories(for amount: Double, unit: ContainerUnit) -> Double {
        let amountInGrams = unit.toGrams(amount)
        return caloriesPerGram * amountInGrams
    }
}

struct PetFeeding: Codable, Identifiable {
    let id: UUID
    let petId: UUID
    let foodId: UUID
    let fedBy: UUID
    let fedAt: Date
    let amount: Double
    let amountUnit: ContainerUnit
    let calories: Double
    let notes: String?
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id
        case petId = "pet_id"
        case foodId = "food_id"
        case fedBy = "fed_by"
        case fedAt = "fed_at"
        case amount
        case amountUnit = "amount_unit"
        case calories
        case notes
        case createdAt = "created_at"
    }
}

struct CalorieGoal: Codable, Identifiable {
    let id: UUID
    let petId: UUID
    let dailyCalories: Double
    let effectiveFrom: Date
    let effectiveUntil: Date?
    let notes: String?
    let createdAt: Date
    let createdBy: UUID?

    enum CodingKeys: String, CodingKey {
        case id
        case petId = "pet_id"
        case dailyCalories = "daily_calories"
        case effectiveFrom = "effective_from"
        case effectiveUntil = "effective_until"
        case notes
        case createdAt = "created_at"
        case createdBy = "created_by"
    }
}
