//
//  SearchQueryParserTests.swift
//  Orest's JournalTests
//
//  Unit tests for SearchQueryParser utility.
//

import XCTest
@testable import Orest_s_Journal

final class SearchQueryParserTests: XCTestCase {

    // MARK: - First Intent Tests

    func testParseFirstKeyword() {
        let result = SearchQueryParser.parse("first vomit")

        XCTAssertEqual(result.intent, .first)
        XCTAssertEqual(result.originalQuery, "first vomit")
        XCTAssertEqual(result.cleanedQuery, "vomit")
    }

    func testParseEarliestKeyword() {
        let result = SearchQueryParser.parse("earliest diarrhea")

        XCTAssertEqual(result.intent, .first)
        XCTAssertEqual(result.cleanedQuery, "diarrhea")
    }

    func testParseWhenWasFirst() {
        let result = SearchQueryParser.parse("when was first seizure")

        XCTAssertEqual(result.intent, .first)
        // Should remove "when was first" keyword
        XCTAssertFalse(result.cleanedQuery.contains("when was first"))
        // The cleaned query should contain the main search term
        XCTAssertTrue(result.cleanedQuery.contains("seizure"))
    }

    func testParseFirstTime() {
        let result = SearchQueryParser.parse("first time he threw up")

        XCTAssertEqual(result.intent, .first)
    }

    func testParseInitialKeyword() {
        let result = SearchQueryParser.parse("initial symptoms")

        XCTAssertEqual(result.intent, .first)
        XCTAssertTrue(result.cleanedQuery.contains("symptoms"))
    }

    // MARK: - Last Intent Tests

    func testParseLastKeyword() {
        let result = SearchQueryParser.parse("last vomit")

        XCTAssertEqual(result.intent, .last)
        XCTAssertEqual(result.originalQuery, "last vomit")
        XCTAssertEqual(result.cleanedQuery, "vomit")
    }

    func testParseLatestKeyword() {
        let result = SearchQueryParser.parse("latest feeding")

        XCTAssertEqual(result.intent, .last)
        XCTAssertEqual(result.cleanedQuery, "feeding")
    }

    func testParseMostRecentKeyword() {
        let result = SearchQueryParser.parse("most recent medication dose")

        XCTAssertEqual(result.intent, .last)
        XCTAssertTrue(result.cleanedQuery.contains("medication"))
        XCTAssertTrue(result.cleanedQuery.contains("dose"))
    }

    func testParseRecentKeyword() {
        let result = SearchQueryParser.parse("recent health event")

        XCTAssertEqual(result.intent, .last)
    }

    func testParseWhenWasLast() {
        let result = SearchQueryParser.parse("when was last vet visit")

        XCTAssertEqual(result.intent, .last)
    }

    func testParseLastTime() {
        let result = SearchQueryParser.parse("last time she ate")

        XCTAssertEqual(result.intent, .last)
    }

    // MARK: - All Intent Tests (Default)

    func testParseNoKeywordDefaultsToAll() {
        let result = SearchQueryParser.parse("vomit")

        XCTAssertEqual(result.intent, .all)
        XCTAssertEqual(result.originalQuery, "vomit")
        XCTAssertEqual(result.cleanedQuery, "vomit")
    }

    func testParseRegularQueryDefaultsToAll() {
        let result = SearchQueryParser.parse("show me all health events")

        XCTAssertEqual(result.intent, .all)
        XCTAssertEqual(result.cleanedQuery, "show me all health events")
    }

    func testParseEmptyQueryDefaultsToAll() {
        let result = SearchQueryParser.parse("")

        XCTAssertEqual(result.intent, .all)
        XCTAssertEqual(result.cleanedQuery, "")
    }

    // MARK: - Query Cleaning Tests

    func testCleaningRemovesFillerWords() {
        let result = SearchQueryParser.parse("when was the first time a seizure happened")

        XCTAssertEqual(result.intent, .first)
        // Filler words like "when", "was", "the", "a" should be removed
        XCTAssertFalse(result.cleanedQuery.contains(" the "))
        XCTAssertFalse(result.cleanedQuery.contains(" a "))
    }

    func testCleaningTrimsWhitespace() {
        let result = SearchQueryParser.parse("   first vomit   ")

        XCTAssertEqual(result.intent, .first)
        XCTAssertEqual(result.cleanedQuery, "vomit")
    }

    func testCleaningNormalizesMultipleSpaces() {
        let result = SearchQueryParser.parse("first   multiple   spaces")

        XCTAssertEqual(result.intent, .first)
        // Should not have multiple consecutive spaces
        XCTAssertFalse(result.cleanedQuery.contains("  "))
    }

    // MARK: - Case Insensitivity Tests

    func testCaseInsensitiveFirst() {
        let result1 = SearchQueryParser.parse("FIRST event")
        let result2 = SearchQueryParser.parse("First event")
        let result3 = SearchQueryParser.parse("first event")

        XCTAssertEqual(result1.intent, .first)
        XCTAssertEqual(result2.intent, .first)
        XCTAssertEqual(result3.intent, .first)
    }

    func testCaseInsensitiveLast() {
        let result1 = SearchQueryParser.parse("LAST event")
        let result2 = SearchQueryParser.parse("Last event")
        let result3 = SearchQueryParser.parse("last event")

        XCTAssertEqual(result1.intent, .last)
        XCTAssertEqual(result2.intent, .last)
        XCTAssertEqual(result3.intent, .last)
    }

    // MARK: - Original Query Preservation Tests

    func testOriginalQueryPreserved() {
        let originalQuery = "When Was First Vomit"
        let result = SearchQueryParser.parse(originalQuery)

        XCTAssertEqual(result.originalQuery, originalQuery)
    }

    func testOriginalQueryPreservedWithWhitespace() {
        let originalQuery = "  last event  "
        let result = SearchQueryParser.parse(originalQuery)

        XCTAssertEqual(result.originalQuery, originalQuery)
    }

    // MARK: - Edge Cases

    func testParseOnlyKeyword() {
        let result = SearchQueryParser.parse("first")

        XCTAssertEqual(result.intent, .first)
        XCTAssertEqual(result.cleanedQuery, "")
    }

    func testParseKeywordInMiddle() {
        let result = SearchQueryParser.parse("show first vomit recorded")

        XCTAssertEqual(result.intent, .first)
        XCTAssertTrue(result.cleanedQuery.contains("show"))
        XCTAssertTrue(result.cleanedQuery.contains("vomit"))
        XCTAssertTrue(result.cleanedQuery.contains("recorded"))
    }

    func testFirstKeywordTakesPrecedenceOverLast() {
        // If both keywords appear, the first one found should win
        // Based on implementation, "first" keywords are checked before "last"
        let result = SearchQueryParser.parse("first and last events")

        XCTAssertEqual(result.intent, .first)
    }
}
