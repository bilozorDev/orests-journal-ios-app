//
//  HealthCategoryHelper.swift
//  Orest's Journal
//
//  Shared utilities for health category icons and colors.
//

import SwiftUI

/// Helper for health category display properties (icons and colors).
enum HealthCategoryHelper {
    /// Get the SF Symbol name for a category based on its normalized name.
    static func icon(for categoryNormalized: String) -> String {
        switch categoryNormalized {
        case "vet visit", "vet", "veterinary":
            return "stethoscope"
        case "vaccination", "vaccine", "shot":
            return "syringe"
        case "medication", "medicine":
            return "pills"
        case "surgery", "operation":
            return "scissors"
        case "blood work", "blood test", "lab work":
            return "drop"
        case "weight", "weigh-in":
            return "scalemass"
        case "dental", "teeth", "dental cleaning":
            return "mouth"
        case "grooming", "bath":
            return "scissors.badge.ellipsis"
        case "allergy", "allergic reaction":
            return "exclamationmark.triangle"
        case "injury", "wound", "hurt":
            return "bandage"
        case "vomiting", "vomit", "sick", "illness":
            return "facemask"
        case "diarrhea", "digestive":
            return "stomach"
        case "hot spot", "skin", "rash":
            return "allergens"
        case "ear", "ear infection":
            return "ear"
        case "eye", "eye issue":
            return "eye"
        default:
            return "heart.text.square"
        }
    }

    /// Get a consistent color for a category based on its normalized name.
    /// Uses djb2 hash algorithm for deterministic, stable colors across app launches.
    static func color(for categoryNormalized: String) -> Color {
        let hash = djb2Hash(categoryNormalized)
        let colors: [Color] = [.red, .orange, .yellow, .green, .blue, .purple, .pink]
        return colors[Int(hash) % colors.count]
    }

    /// djb2 hash algorithm - deterministic and stable across app launches
    /// Unlike String.hashValue, this produces the same result every time
    private static func djb2Hash(_ string: String) -> UInt {
        var hash: UInt = 5381
        for char in string.utf8 {
            hash = ((hash << 5) &+ hash) &+ UInt(char)  // hash * 33 + char
        }
        return hash
    }
}

// MARK: - HealthCategory Extension

extension HealthCategory {
    /// SF Symbol icon name for this category.
    var icon: String {
        HealthCategoryHelper.icon(for: nameNormalized)
    }

    /// Display color for this category.
    var color: Color {
        HealthCategoryHelper.color(for: nameNormalized)
    }
}
