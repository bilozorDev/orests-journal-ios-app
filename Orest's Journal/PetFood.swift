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
    let orgId: String  // Family ID
    let name: String
    let category: FoodCategory
    let caloriesPerKg: Double
    let containerSize: Double
    let containerSizeUnit: ContainerUnit
    let imageUrl: String?
    let createdAt: Date
    let createdBy: String?

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
    let fedBy: String
    let fedAt: Date
    let amount: Double
    let amountUnit: ContainerUnit
    let calories: Double
    let notes: String?
    let createdAt: Date
}

struct CalorieGoal: Codable, Identifiable {
    let id: UUID
    let petId: UUID
    let dailyCalories: Double
    let effectiveFrom: Date
    let effectiveUntil: Date?
    let notes: String?
    let createdAt: Date
    let createdBy: String?
}
