//
//  Formatters.swift
//  Orest's Journal
//
//  Shared formatters to avoid recreating expensive formatter instances.
//

import Foundation

enum Formatters {
    static let shortDate: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateStyle = .short
        return formatter
    }()

    static let weight: NumberFormatter = {
        let formatter = NumberFormatter()
        formatter.minimumFractionDigits = 0
        formatter.maximumFractionDigits = 1
        return formatter
    }()

    static func formatWeight(_ weight: Double) -> String {
        Formatters.weight.string(from: NSNumber(value: weight)) ?? "\(weight)"
    }

    /// Formats a display name from first/last name components.
    /// Returns "FirstName L." format if both names provided, just firstName if no lastName,
    /// or the fallback value if no firstName.
    static func formatDisplayName(firstName: String?, lastName: String?, fallback: String = "Unknown") -> String {
        guard let firstName = firstName, !firstName.isEmpty else {
            return fallback
        }
        if let lastName = lastName, !lastName.isEmpty {
            let initial = String(lastName.prefix(1)).uppercased()
            return "\(firstName) \(initial)."
        }
        return firstName
    }
}
