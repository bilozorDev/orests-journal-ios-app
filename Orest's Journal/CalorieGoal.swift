//
//  CalorieGoal.swift
//  Orest's Journal
//
//  Model for pet daily calorie goals.
//

import Foundation

struct CalorieGoal: Codable, Identifiable {
    let id: UUID
    let petId: UUID
    let dailyCalories: Double
    let notes: String?
    let createdAt: Date
    let createdBy: String?
}

struct CalorieGoalCreate: Encodable {
    let petId: UUID
    let dailyCalories: Double
    let notes: String?
}
