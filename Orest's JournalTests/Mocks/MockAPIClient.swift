//
//  MockAPIClient.swift
//  Orest's JournalTests
//
//  Mock implementation of APIClientProtocol for testing.
//

import Foundation
@testable import Orest_s_Journal

/// Mock API client for unit testing.
/// Allows stubbing responses and capturing requests for verification.
final class MockAPIClient: APIClientProtocol {
    var authToken: String?
    var currentFamilyId: String?

    // MARK: - Stubbed Responses

    /// Dictionary of stubbed responses keyed by path
    var stubbedGetResponses: [String: Any] = [:]
    var stubbedPostResponses: [String: Any] = [:]
    var stubbedPatchResponses: [String: Any] = [:]
    var stubbedDeleteResponses: [String: Any] = [:]

    /// Error to throw for specific paths
    var stubbedErrors: [String: Error] = [:]

    // MARK: - Request Tracking

    /// Captured GET request paths
    var capturedGetPaths: [String] = []

    /// Captured POST requests (path, body)
    var capturedPostRequests: [(path: String, body: Any)] = []

    /// Captured PATCH requests (path, body)
    var capturedPatchRequests: [(path: String, body: Any)] = []

    /// Captured DELETE request paths
    var capturedDeletePaths: [String] = []

    // MARK: - APIClientProtocol Implementation

    func get<T: Decodable>(_ path: String, queryItems: [URLQueryItem]?) async throws -> T {
        capturedGetPaths.append(path)

        if let error = stubbedErrors[path] {
            throw error
        }

        guard let response = stubbedGetResponses[path] as? T else {
            throw APIError.notFound
        }

        return response
    }

    func post<T: Decodable, B: Encodable>(_ path: String, body: B, queryItems: [URLQueryItem]?) async throws -> T {
        capturedPostRequests.append((path: path, body: body))

        if let error = stubbedErrors[path] {
            throw error
        }

        guard let response = stubbedPostResponses[path] as? T else {
            throw APIError.notFound
        }

        return response
    }

    func patch<T: Decodable, B: Encodable>(_ path: String, body: B) async throws -> T {
        capturedPatchRequests.append((path: path, body: body))

        if let error = stubbedErrors[path] {
            throw error
        }

        guard let response = stubbedPatchResponses[path] as? T else {
            throw APIError.notFound
        }

        return response
    }

    func delete(_ path: String) async throws {
        capturedDeletePaths.append(path)

        if let error = stubbedErrors[path] {
            throw error
        }
    }

    func deleteWithResponse<T: Decodable>(_ path: String) async throws -> T {
        capturedDeletePaths.append(path)

        if let error = stubbedErrors[path] {
            throw error
        }

        guard let response = stubbedDeleteResponses[path] as? T else {
            throw APIError.notFound
        }

        return response
    }

    // MARK: - Helper Methods

    /// Reset all captured data and stubbed responses
    func reset() {
        stubbedGetResponses.removeAll()
        stubbedPostResponses.removeAll()
        stubbedPatchResponses.removeAll()
        stubbedDeleteResponses.removeAll()
        stubbedErrors.removeAll()
        capturedGetPaths.removeAll()
        capturedPostRequests.removeAll()
        capturedPatchRequests.removeAll()
        capturedDeletePaths.removeAll()
    }
}
