//
//  SearchQueryParser.swift
//  Orest's Journal
//
//  Created by Alex on 10/4/25.
//

import Foundation

enum SearchIntent {
    case first      // Find the first/earliest occurrence
    case last       // Find the last/most recent occurrence
    case all        // Find all occurrences
}

struct ParsedSearchQuery {
    let originalQuery: String
    let intent: SearchIntent
    let cleanedQuery: String // Query with intent keywords removed
}

class SearchQueryParser {
    // Keywords that indicate searching for the first occurrence
    private static let firstKeywords = [
        "first", "earliest", "initial", "when was first", "when did first",
        "first time", "starting", "beginning"
    ]

    // Keywords that indicate searching for the last occurrence
    private static let lastKeywords = [
        "last", "latest", "most recent", "recent", "when was last",
        "when did last", "last time"
    ]

    static func parse(_ query: String) -> ParsedSearchQuery {
        let lowercaseQuery = query.lowercased().trimmingCharacters(in: .whitespacesAndNewlines)

        // Check for "first" intent
        for keyword in firstKeywords {
            if lowercaseQuery.contains(keyword) {
                let cleanedQuery = cleanQuery(lowercaseQuery, removing: keyword)
                return ParsedSearchQuery(
                    originalQuery: query,
                    intent: .first,
                    cleanedQuery: cleanedQuery
                )
            }
        }

        // Check for "last" intent
        for keyword in lastKeywords {
            if lowercaseQuery.contains(keyword) {
                let cleanedQuery = cleanQuery(lowercaseQuery, removing: keyword)
                return ParsedSearchQuery(
                    originalQuery: query,
                    intent: .last,
                    cleanedQuery: cleanedQuery
                )
            }
        }

        // Default to showing all results
        return ParsedSearchQuery(
            originalQuery: query,
            intent: .all,
            cleanedQuery: query
        )
    }

    private static func cleanQuery(_ query: String, removing keyword: String) -> String {
        var cleaned = query.replacingOccurrences(of: keyword, with: "")

        // Remove common filler words
        let fillerWords = ["when", "was", "did", "the", "a", "an"]
        for word in fillerWords {
            cleaned = cleaned.replacingOccurrences(of: " \(word) ", with: " ")
        }

        // Clean up extra spaces
        cleaned = cleaned.components(separatedBy: .whitespacesAndNewlines)
            .filter { !$0.isEmpty }
            .joined(separator: " ")
            .trimmingCharacters(in: .whitespacesAndNewlines)

        return cleaned
    }
}
