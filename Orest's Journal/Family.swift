//
//  Family.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import Foundation

/// APIClient uses automatic snake_case conversion
struct Family: Codable, Identifiable {
    let id: UUID
    let name: String
    let createdAt: Date
    let createdBy: UUID?
}
