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
}
